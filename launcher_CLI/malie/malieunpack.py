# malielib.py - Camellia cipher decryptor used in GARbro's Malie engine handler
# Ported from C# by morkt (GARbro: https://github.com/morkt/GARbro)

# MIT License (for GARbro ported structure)
# Copyright (c) morkt

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

# GARbro(by. morkt) 1.1.6 ver.을 기준으로 Python으로 포팅했습니다.

import os
import logging
from io import BytesIO
from struct import unpack
from formats.fileview import FileView
from formats.arcfile import ArcFile, Entry
from formats.arccommon import AutoEntry
from gameres.gameres import ArchiveFormat
from gameres.utility import ascii_equal, get_cstring, LittleEndian
from malie.camellia import Camellia
from malie.maliekeys import KnownKeys


#.lib 언팩용 (비암호화) - ArcLIB.cs의 LibOpener에 해당.
class LibOpener(ArchiveFormat):
    def __init__(self):
        super().__init__()
        self.name = "Malie LIB archive" # [설명용 텍스트]
        self.extensions = ["lib"]  # [역할] 확장자 등록 (.lib)
        self.signatures = [0x0042494C]  # [역할] 시그니처 'LIB' (ASCII → 리틀엔디안)
        self.is_hierarchic = True # [C# 대응] Hierarchic = true
        self.can_create = False # [C# 대응] CanCreate = false

    @property
    def type(self) -> str:
        return "archive" # [역할] 파일 유형 분류 (아카이브 포맷)

    # ArcLIB.cs - LibOpener의 TryOpen
    # [역할] 내부 Reader를 통해 index 디렉토리 파싱 시도
    def try_open(self, view: FileView):
        reader = self.Reader(view)

        if reader.read_index("", 0, view.get_max_offset):
            return ArcFile(view, self, reader.dir)
        
        else:
            return None
        
    # ArcLIB.cs - LibOpener의 Reader    
    class Reader:
        def __init__(self, view: FileView):
            self.view = view.create_frame(0, view.get_max_offset()) # [역할] 전체 파일 범위를 읽기 가능한 프레임으로 확보
            self.dir = []  # [역할] Entry 리스트 (디렉토리 역할)

        # ArcLIB.cs - LibOpener의 ReadIndex   
        def read_index(self, root: str, base_offset: int, size: int) -> bool:
            signature = LittleEndian.ToUInt32(self.view.read(base_offset, 4), 0) # [역할] 시그니처 검사 ('LIB'인지 확인)
            if signature != 0x0042494C: # 'LIB'
                return False

            count = LittleEndian.ToInt16(base_offset + 8) # [역할] index 엔트리 개수 추출
            if count <= 0:
                return False

            index_offset = base_offset + 0x10
            index_size = 0x30 * count # [역할] 각 엔트리 크기 0x30 = 48 bytes
            if index_size > size:
                return False

            data_offset = index_offset + index_size # [역할] 데이터 시작 위치 계산 (index 블록 뒤쪽)

            # [역할] 엔트리 필드 파싱
            for i in range(count):
                name = LittleEndian.ToUInt32(index_offset, 0x24)
                entry_size = LittleEndian.ToUInt32(index_offset + 0x24)
                offset_rel = LittleEndian.ToUInt32(index_offset + 0x28)
                offset = base_offset + offset_rel # [역할] 상대 오프셋 → 절대 오프셋으로
                index_offset += 0x30 # 다음 엔트리로 이동

                ext = os.path.splitext(name)[1]
                full_name = os.path.join(root, name).replace("\\", "/")

                # [역할] 확장자 없는 경우, 서브 디렉토리로 간주하고 재귀 처리
                if not ext and self.read_index(full_name, offset, entry_size):
                    continue

                # [역할] 오프셋/사이즈 유효성 검사 (index 영역 침범 방지)
                if offset < data_offset or offset + entry_size > base_offset + size:
                    return False

                # [역할] Entry 객체 생성
                entry = Entry(full_name)
                entry.offset = offset
                entry.size = entry_size
                self.dir.append(entry)

            return True # [역할] index 파싱 성공

# ============ .dat 관련 로직들 ============
# camellia 복호화 로직 - ArcLIB의 ReadEncrypted. python은 순서 문제로 위로 옮김.
def read_encrypted(view, decryptor, offset: int, buffer: bytearray, index: int, length: int) -> int:
    offset_pad = offset & 0xF
    aligned_len = (offset_pad + length + 0xF) & ~0xF
    aligned_buf = buffer if aligned_len == length else bytearray(aligned_len)
    block = index if aligned_buf is buffer else 0

    try:
        data = view.read_at(offset - offset_pad, aligned_len)
    except Exception:
        return 0

    if len(data) < offset_pad:
        return 0

    aligned_buf[block:block+len(data)] = data

    current_offset = offset - offset_pad
    for _ in range(aligned_len // 0x10):
        decryptor.decrypt_block(current_offset, aligned_buf, block)
        block += 0x10
        current_offset += 0x10

    if aligned_buf is not buffer:
        buffer[index:index+length] = aligned_buf[offset_pad:offset_pad+length]

    return min(length, len(data) - offset_pad)

#.dat 언팩용 (암호화 + Camellia(read_encrypted)와 연동)
# ArcLIB.cs의 MalieArchive에 해당.
# # Camellia 복호화를 포함하는 ArcFile 래퍼. 파일 목록(Entry)을 가지고 복호화 스트림을 제공함.
class MalieArchive(ArcFile):
    def __init__(self, file_view, format, entries, decryptor, key_name):
        super().__init__(file_view, format, entries) # [C# 대응] base(file, format, dir), [역할] 부모 ArcFile 초기화 → 원본 파일(view), 포맷 정보, 엔트리 리스트
        self.decryptor = decryptor                 # [C# 대응] this.Encryption = decryptor; [역할] Camellia 복호화기 인스턴스 저장
        self.file_view = file_view                 # [C# 대응] ArcFile.File (기본적으로 ArcView), [역할] FileView 보존 (open_entry 시 접근용)
        self.key_name = key_name                   # [역할] 현재 아카이브에 적용된 키 이름 (디버깅/분기용)
        self.base_offset = 0

# ArcLIB.cs의 DatOpener에 해당.
# "LIBP" 시그니처를 가진 암호화 아카이브를 처리. 복호화에는 Camellia 사용.
class DatOpener(ArchiveFormat):
    def __init__(self):
        super().__init__()
        self.tag = "LIBP" # [C# 대응] public override string Tag => "LIBP"
        self.description = "Malie engine encrypted archive" # [설명용 텍스트]
        self.signature = 0  # 시그니처 자동 인식 안 함 (암호화된 상태라서 판단 불가)
        self.is_hierarchic = True # [역할] 폴더 구조 지원
        self.can_create = False # [역할] 생성은 불가능 (읽기 전용)
        self.extensions = ["dat"] # [역할] .dat 확장자 등록
        self.entries = [] # [C#에서는 따로 entries 없음 → Python용 보조 필드]

    def type(self):
        return "dat" # [역할] 포맷 구분자. "archive"와 다르게 따로 처리 가능

    # ArcLIB.cs - DatOpener의 TryOpen  
    # 암호화된 아카이브 열기. KnownKeys 전체에 대해 복호화 시도 → 성공하면 MalieArchive 리턴  
    def try_open(self, view: FileView):
        for key_name, key_data in KnownKeys.items():
            decryptor = Camellia(key_data)
            reader = self.Reader(view, self)
            archive = MalieArchive(view, self, [], decryptor, key_name)
            reader.set_archive(archive)

            if reader.read_index(decryptor, key_name):
                archive.base_offset = reader.base_offset
                archive.dir = reader.dir
                archive.entries = reader.dir
                logging.debug(f"[DatOpener] ✅ 성공 (key={key_name}, entries={len(reader.dir)})")
                return archive
            else:
                logging.debug(f"[DatOpener] ❌ read_index 실패 (key={key_name})")

        return None
        
    # ArcLIB.cs - DatOpener의 OpenEntry
    # 아카이브 내부 개별 Entry를 열어 복호화된 데이터 스트림으로 반환
    def open_entry(arc: ArcFile, entry):
        if not isinstance(arc, MalieArchive):
            return arc.file_view.create_stream(entry.offset, entry.size) # [역할] 비암호화 아카이브라면 그대로 평문 스트림 반환

        # [역할] Camellia 복호화가 필요한 경우
        data = bytearray(entry.size)
        read_encrypted(arc.file_view, arc.encryption, entry.offset, data, 0, entry.size)
        return BytesIO(data) # 복호화된 데이터를 메모리 스트림으로 반환

    # ArcLIB.cs - DatOpener의 Reader
    # 암호화된 index/header를 읽어 Entry 디렉토리 구성
    class Reader:
        def __init__(self, view: FileView, outer):
            self.view = view
            self.max_offset = view.get_max_offset # [역할] 파일 끝 위치 확보용
            self.base_offset = 0 # [역할] 복호화 기준 시작 offset
            self.decryptor = None
            self.dir = [] # [역할] Entry 객체 리스트
            self.header = bytearray(0x10) # [역할] LIBP 헤더 (16바이트)
            self.index = None # [역할] 엔트리 메타정보 테이블
            self.offset_table = None # [역할] 실 데이터의 오프셋 테이블
            self._arc = None # [역할] MalieArchive 참조
            self.outer = outer # [보조용]
            self.max_offset = view.get_max_offset()
    
        # [역할] 이 Reader 인스턴스에 아카이브 객체(MalieArchive) 연결
        def set_archive(self, archive):
            self._arc = archive

        # ArcLIB.cs - DatOpener의 ReadIndex  
        # 암호화된 index 블록 복호화 + Entry 생성
        def read_index(self, encryption: Camellia, key_name: str) -> bool:
            self.base_offset = 0
            self.decryptor = encryption

            # 1. 헤더 읽기 (0x10 bytes) → 'LIBP' 시그니처 확인
            if 0x10 != read_encrypted(self.view, self.decryptor, self.base_offset, self.header, 0, 0x10):
                return False

            if not ascii_equal(self.header, 0, b'LIBP'):
                return False

            # 2. 헤더에서 엔트리 수, 오프셋 테이블 길이 추출
            count = LittleEndian.ToInt32(self.header, 4)
            if count <= 0:
                return False

            offset_count = LittleEndian.ToInt32(self.header, 8)

            # 3. index 블록, offset 테이블 할당
            self.index = bytearray(0x20 * count)  # 엔트리 메타정보
            offsets = bytearray(4 * offset_count) # offset 테이블

            self.base_offset += 0x10  # [역할] 본문 블록 시작

            # 4. index 블록 복호화
            if len(self.index) != read_encrypted(self.view, self.decryptor, self.base_offset, self.index, 0, len(self.index)):
                return False
            
            self.base_offset += len(self.index)

            # 5. offset 테이블 복호화
            if len(offsets) != read_encrypted(self.view, self.decryptor, self.base_offset, offsets, 0, len(offsets)):
                return False
            
            # 6. offset 테이블 정리 (UInt32 리스트로 변환)
            self.offset_table = []
            for i in range(0, len(offsets), 4):
                val = LittleEndian.ToUInt32(offsets, i)
                self.offset_table.append(val)

            # 7. 데이터 본문 시작 offset → 0x1000 정렬
            pre_align = self.base_offset
            self.base_offset += len(offsets)
            aligned_base = (self.base_offset + 0xFFF) & ~0xFFF
            self.base_offset = aligned_base

            # 8. Entry 디렉토리 파싱
            self.dir = []
            self.read_dir(key_name, "", 0, 1)

            # ✅ base_offset 저장 (원래 offset 계산에 쓰인 값)
            for e in self.dir:
                if not getattr(e, "is_dir", False):
                    e.base_offset = pre_align  # ❗ offset 계산에 사용된 원래 값

            # ✅ C#과 동일하게 엔트리 존재 여부 반환
            return len(self.dir) > 0
        
        
        # ArcLIB.cs - DatOpener의 ReadDir  
        # index 및 offset_table을 기반으로 Entry 생성
        # offset_index의 메타데이터 기록을 위해 원본 코드를 커스텀.
        def read_dir(self, key_name, root: str, entry_index: int, count: int):
            current_offset = entry_index * 0x20

            for i in range(count):
                name = get_cstring(self.index, current_offset, 0x20)
                flags = LittleEndian.ToInt32(self.index, current_offset + 0x14)
                offset = LittleEndian.ToInt32(self.index, current_offset + 0x18)
                size = LittleEndian.ToUInt32(self.index, current_offset + 0x1C)
                full_name = os.path.join(root, name)
                this_entry_index = entry_index + i
                current_offset += 0x20

                is_dir = (flags & 0x10000) == 0

                if is_dir:
                    dummy = AutoEntry(full_name, self.view, 0, 0)
                    dummy.entry_index = this_entry_index
                    dummy.offset_index = None
                    dummy.archive = self._arc
                    dummy.key_name = key_name
                    dummy.size = size
                    dummy.type = "dir"
                    dummy.is_dir = True
                    entry_raw = self.index[current_offset - 0x20 : current_offset]
                    dummy.index_tail_raw = entry_raw[0x18:0x1C].hex()
                    self.dir.append(dummy)

                    if offset > entry_index:
                        self.read_dir(key_name, full_name, offset, size)
                    continue

                entry_offset = self.base_offset + (int(self.offset_table[offset]) << 10)
                entry = AutoEntry(full_name, self.view, entry_offset, size)
                entry.entry_index = this_entry_index
                entry.offset_index = offset
                entry.archive = self._arc
                entry.key_name = key_name
                entry.is_dir = False
                entry.base_offset = self.base_offset

                # ✅ PNG일 경우 원본 압축 크기 저장
                if full_name.lower().endswith(".png"):
                    entry.original_compressed_size = size
                    
                self.dir.append(entry)