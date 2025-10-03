# fileview.py - Camellia cipher decryptor used in GARbro's Malie engine handler
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
import io
import mmap
import struct  # for unpack/pack, uint32 처리
import codecs  # optional: encoding if needed
import logging  # 디버깅 로그용
from io import BytesIO

CP932 = 'cp932'  # 혹은 'shift_jis' 와 동일하게 동작

#FileView (ArcView에 해당):.dat/.lib 파일을 메모리 맵으로 열어 읽을 수 있도록 처리
class FileView:
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.file = open(filepath, "rb")
        self.size = os.path.getsize(filepath)
        self.name = os.path.basename(filepath)
        self.stream = self.file
        self.mmap = mmap.mmap(self.file.fileno(), length=0, access=mmap.ACCESS_READ)
        self.offset = 0
        self._size = os.fstat(self.file.fileno()).st_size

        print(f"[fileview] '{self.name}' 열림 (크기: {self.size} bytes)")

    def __len__(self):
        return self._size

    def read(self, offset: int, length: int) -> bytes:
        logging.debug(f"[fileview] Read 호출 (offset=0x{offset:X}, size={length})")
        self.mmap.seek(offset)
        return self.mmap.read(length)
    
    def read_at(self, offset: int, size: int) -> bytes:
        logging.debug(f"[fileview] read_at 호출 - offset=0x{offset:X}, size={size}, file_size={self.size}")

        if offset < 0 or offset >= self.size:
            logging.debug("[fileview] read_at 오류 - offset 범위 초과")
            raise ValueError("Seek offset out of range")

        # 읽기 가능한 최대 바이트 수 계산
        available = self.size - offset
        read_size = min(size, available)

        self.stream.seek(offset)
        data = self.stream.read(read_size)

        logging.debug(f"[fileview] read_at 결과 ({read_size} bytes): {data[:64].hex()}")
        return data

    def read_byte(self, offset: int) -> int:
        value = self.read(offset, 1)[0]
        logging.debug(f"[fileview] read_byte(offset=0x{offset:X}) => 0x{value:02X}")
        return value

    def read_uint32_le(self, offset: int) -> int:
        value = struct.unpack('<I', self.read(offset, 4))[0]
        logging.debug(f"[fileview] read_uint32_le(offset=0x{offset:X}) => 0x{value:08X}")
        return value
    

    # 전체 파일 크기 (최대 오프셋) 반환
    def get_max_offset(self) -> int:
        return self.size

    # 메모리 맵과 파일 닫기
    def close(self):
        self.mmap.close()
        self.file.close()
        logging.debug(f"[FileView] '{self.name}' 닫힘")
    
    # FileView 내 특정 오프셋에서 size만큼의 영역을 스트림으로 생성 ArcView.CreateStream에 해당
    def create_stream(self, offset: int, size: int = None):
        from formats.arccommon import StreamRegion
        if size is None:
            size = self.size - offset
        logging.debug(f"[fileview] create_stream(offset=0x{offset:X}, size={size})")
        return StreamRegion(self.file, self.offset + offset, size, name=self.name)
    
    def create_frame(self, offset: int, size: int):
        logging.debug(f"[fileview] create_frame(offset=0x{offset:X}, size={size})")
        return FileFrame(self, offset, size)
    
    @classmethod
    def from_stream(cls, stream: BytesIO, name="<memory>") -> "FileView":
        data = stream.getvalue()
        fake_file = io.BytesIO(data)
        fake_file.name = name  # PIL과의 호환 위해 이름 부여
        return cls(fake_file, name=name)
    

#FileFrame (Frame에 해당): FileView에서 특정 오프셋 범위를 제한하여 읽기 전용으로 접근할 수 있는 뷰
class FileFrame:
    def __init__(self, file_view: FileView, offset: int, size: int):
        self.view = file_view
        self.offset = offset
        self.size = size
        logging.debug(f"[fileview] 생성됨 (offset=0x{offset:X}, size={size})")

    def read(self, rel_offset: int, length: int) -> bytes:
        self.reserve(rel_offset, length)
        abs_offset = self.offset + rel_offset
        logging.debug(f"[fileview] read: rel_offset=0x{rel_offset:X}, abs_offset=0x{abs_offset:X}, size={length}")
        return self.view.read(abs_offset, length)

    def reserve(self, rel_offset: int, length: int):
        abs_offset = self.offset + rel_offset

        # 현재 프레임 범위를 벗어나면 재생성
        if rel_offset < 0 or rel_offset + length > self.size:
            logging.debug(f"[fileview] reserve: 범위 초과 감지 → 프레임 갱신 시도")

            # 새로운 기준 offset: 요청 offset의 0x1000 단위 정렬 (페이지 단위)
            new_offset = abs_offset & ~0xFFF
            end_offset = abs_offset + length
            new_size = ((end_offset - new_offset + 0xFFF) // 0x1000) * 0x1000

            # 파일 크기 초과 방지
            max_size = self.view.get_max_offset()
            if new_offset + new_size > max_size:
                new_size = max_size - new_offset

            # 프레임 정보 갱신
            self.offset = new_offset
            self.size = new_size
            logging.debug(f"[fileview] reserve: 새로운 프레임 범위 = 0x{new_offset:X} ~ 0x{new_offset + new_size:X}")
    
    def read_uint32_le(self, rel_offset: int) -> int:
        val = struct.unpack('<I', self.read(rel_offset, 4))[0]
        logging.debug(f"[fileview] read_uint32_le: rel_offset=0x{rel_offset:X}, val=0x{val:08X}")
        return val

    def ascii_equal(self, rel_offset: int, s: str) -> bool:
        data = self.read(rel_offset, len(s))
        result = data == s.encode('ascii')
        logging.debug(f"[fileview] ascii_equal: offset=0x{rel_offset:X}, cmp='{s}', result={result}")
        return result
    
    #프레임 내 상대 오프셋에서 리틀 엔디안 uint16을 읽음
    def read_uint16_le(self, rel_offset: int) -> int:
        val = struct.unpack('<H', self.read(rel_offset, 2))[0]
        logging.debug(f"[fileview (uint16_le)] read_uint16_le @0x{rel_offset:X} = 0x{val:04X}")
        return val

    #프레임 내 상대 오프셋에서 리틀 엔디안 int16을 읽음
    def read_int16_le(self, rel_offset: int) -> int:
        val = struct.unpack('<h', self.read(rel_offset, 2))[0]
        logging.debug(f"[fileview (int16_le)] read_int16_le @0x{rel_offset:X} = {val}")
        return val

    #프레임 내 상대 오프셋에서 리틀 엔디안 int32를 읽음
    def read_int32_le(self, rel_offset: int) -> int:
        val = struct.unpack('<i', self.read(rel_offset, 4))[0]
        logging.debug(f"[fileview (int32_le)] read_int32_le @0x{rel_offset:X} = {val}")
        return val

    #프레임 내 상대 오프셋에서 리틀 엔디안 uint64를 읽음 : 
    def read_uint64_le(self, rel_offset: int) -> int:
        val = struct.unpack('<Q', self.read(rel_offset, 8))[0]
        logging.debug(f"[fileview (uint64_le)] read_uint64_le @0x{rel_offset:X} = 0x{val:016X}")
        return val

    #프레임 내 상대 오프셋에서 리틀 엔디안 int64를 읽음
    def read_int64_le(self, rel_offset: int) -> int:
        val = struct.unpack('<q', self.read(rel_offset, 8))[0]
        logging.debug(f"[fileview (int64_le)] read_int64_le @0x{rel_offset:X} = {val}")
        return val

    #프레임 내 상대 오프셋에서 signed byte (int8)를 읽음
    def read_sbyte(self, rel_offset: int) -> int:
        val = struct.unpack('b', self.read(rel_offset, 1))[0]
        logging.debug(f"[fileview] read_sbyte @0x{rel_offset:X} = {val}")
        return val

    #프레임 내 문자열을 지정된 인코딩으로 읽어 문자열로 반환. 널 문자 이전까지만 사용됨
    def read_string(self, rel_offset: int, size: int, encoding='shift_jis') -> str:
        raw = self.read(rel_offset, size)
        decoded = raw.split(b'\x00')[0].decode(encoding, errors='ignore')
        logging.debug(f"[fileview] read_string @0x{rel_offset:X}, size={size} => '{decoded}'")
        return decoded

    #FileFrame은 직접 리소스를 소유하지 않지만, 명시적 해제를 지원함. 실제 파일 리소스는 FileView가 관리함.
    def close(self):
        logging.debug("[fileview] 프레임 해제 호출됨 (리소스 소유 없음)")
        # 아무 작업도 하지 않음 (view.close()를 명시적으로 호출해야 함)
        pass

#FileStream (ArcStream에 해당): FileView 또는 FileFrame을 기반으로 파일을 스트림처럼 읽을 수 있도록 구현
class FileStream(io.RawIOBase):
    def __init__(self, frame, offset: int = 0, size: int = None):
        self.frame = frame
        self.start = offset
        self.size = size if size is not None else frame.size - offset
        self.pos = 0
        logging.debug(f"[fileview] 생성됨 (start: {self.start}, size: {self.size})")

    #스트림에서 length만큼 읽음. -1이면 끝까지 읽음
    def read(self, length: int = -1) -> bytes:
        if self.closed or self.pos >= self.size:
            return b''
        if length < 0 or self.pos + length > self.size:
            length = self.size - self.pos
        data = self.frame.read(self.start + self.pos - self.frame.offset, length)
        self.pos += len(data)
        logging.debug(f"[fileview] read: pos={self.pos}, read={len(data)}")
        return data

    #주어진 버퍼 b에 데이터를 채움
    def readinto(self, b) -> int:
        data = self.read(len(b))
        b[:len(data)] = data
        return len(data)

    def read_byte(self) -> int:
        byte = self.read(1)
        val = byte[0] if byte else -1
        logging.debug(f"[fileview] read_byte: pos=0x{self.pos - 1:X}, val=0x{val:02X}")
        return val

    def read_signature(self) -> int:
        sig = self.frame.read_uint32_le(self.start)
        logging.debug(f"[fileview] read_signature: offset=0x{self.start:X}, sig=0x{sig:08X}")
        return sig

    def seek(self, offset: int, whence: int = io.SEEK_SET) -> int:
        old_pos = self.pos
        if whence == io.SEEK_SET:
            self.pos = offset
        elif whence == io.SEEK_CUR:
            self.pos += offset
        elif whence == io.SEEK_END:
            self.pos = self.size + offset
        else:
            raise ValueError("seek() whence 값이 잘못됨")
        self.pos = max(0, min(self.pos, self.size))
        logging.debug(f"[fileview] seek: from=0x{old_pos:X} to=0x{self.pos:X}")
        return self.pos

    def tell(self) -> int:
        return self.pos

    def readable(self) -> bool:
        return True

    def writable(self) -> bool:
        return False

    def seekable(self) -> bool:
        return True

    def close(self):
        if not self.closed:
            logging.warning("[fileview] close() 호출됨 (닫혀있지 않음)")

#Reader 클래스는 FileFrame 기반으로 바이너리 데이터를 편리하게 읽기 위한 래퍼(C#의 BinaryReader 또는 ArcView.cs의 Reader와 유사)     
class Reader:
    def __init__(self, frame):
        self.frame = frame
        self.offset = 0
        logging.debug(f"[fileview] 생성됨 (초기 offset=0x{self.offset:X})")

    def read_uint8(self) -> int:
        result = self.frame.read(self.offset, 1)[0]
        logging.debug(f"[fileview] read_uint8 @0x{self.offset:X} = 0x{result:02X}")
        self.offset += 1
        return result

    def read_sbyte(self) -> int:
        result = struct.unpack('b', self.frame.read(self.offset, 1))[0]
        logging.debug(f"[fileview] read_sbyte @0x{self.offset:X} = {result}")
        self.offset += 1
        return result

    def read_uint16(self) -> int:
        result = struct.unpack('<H', self.frame.read(self.offset, 2))[0]
        logging.debug(f"[fileview] read_uint16 @0x{self.offset:X} = 0x{result:04X}")
        self.offset += 2
        return result

    def read_int16(self) -> int:
        result = struct.unpack('<h', self.frame.read(self.offset, 2))[0]
        logging.debug(f"[fileview] read_int16 @0x{self.offset:X} = {result}")
        self.offset += 2
        return result

    def read_uint32(self) -> int:
        result = struct.unpack('<I', self.frame.read(self.offset, 4))[0]
        logging.debug(f"[fileview] read_uint32 @0x{self.offset:X} = 0x{result:08X}")
        self.offset += 4
        return result

    def read_int32(self) -> int:
        result = struct.unpack('<i', self.frame.read(self.offset, 4))[0]
        logging.debug(f"[fileview] read_int32 @0x{self.offset:X} = {result}")
        self.offset += 4
        return result

    def read_bytes(self, size: int) -> bytes:
        result = self.frame.read(self.offset, size)
        logging.debug(f"[fileview] read_bytes @0x{self.offset:X}, size={size} => {result[:16].hex()}...")
        self.offset += size
        return result

    def read_string(self, size: int, encoding='shift_jis') -> str:
        raw = self.read_bytes(size)
        decoded = raw.split(b'\x00')[0].decode(encoding, errors='ignore')
        logging.debug(f"[fileview] read_string @0x{self.offset - size:X}, size={size} => '{decoded}'")
        return decoded

    def seek(self, offset: int):
        logging.debug(f"[fileview] seek: from 0x{self.offset:X} to 0x{offset:X}")
        self.offset = offset

    def tell(self) -> int:
        return self.offset

    #NULL 종료된 문자열을 읽음 (최대 max_size 제한)
    def read_cstring(self, max_size: int = 256, encoding: str = CP932) -> str:
        result = bytearray()
        for _ in range(max_size):
            b = self.read_uint8()
            if b == 0:
                break
            result.append(b)
        decoded = result.decode(encoding, errors='ignore')
        logging.debug(f"[fileview] read_cstring (최대 {max_size}) => '{decoded}'")
        return decoded


__all__ = ["FileView", "FileFrame", "FileStream", "Reader"]