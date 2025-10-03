# arcfile.py - Camellia cipher decryptor used in GARbro's Malie engine handler
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
import logging
from typing import List, Optional
from formats.fileview import FileView


# 기본 Entry 구조 정의
class Entry:
    def __init__(self, name: str, offset: int, size: int, unpacked_size: Optional[int] = None, archive=None):
        self.name = name
        self.offset = offset
        self.size = size
        self.unpacked_size = unpacked_size if unpacked_size is not None else size
        self.index = -1  # 위치 정보 (선택사항)
        self.archive = archive

    def is_packed(self) -> bool:
        return self.size != self.unpacked_size
    
# PackedEntry: 압축된 항목 전용 구조
class PackedEntry(Entry):
    def __init__(self, name: str, offset: int, size: int, unpacked_size: int):
        super().__init__(name, offset, size, unpacked_size)

# ArcFile 컨테이너
class ArcFile:
    def __init__(self, view, format, entries: List[Entry]):
        self.view = view
        self.format = format
        self.name = view.name if hasattr(view, 'name') else "unnamed"

        # 오프셋 기준 정렬
        self.entries = sorted(entries, key=lambda e: e.offset)

        for i, entry in enumerate(self.entries):
            entry.index = i

        logging.debug(f"[ArcFile] '{self.name}' 초기화, 항목 수: {len(self.entries)})")
        
    #내부 View 리소스를 정리
    def close(self):
        self.view.close()
        logging.debug(f"[ArcFile] '{self.name}' 닫힘")

    #개별 항목을 파일로 추출
    def extract_entry(self, entry: Entry, output_path: str):
        with open(output_path, 'wb') as f:
            stream = self.open_entry(entry)
            while True:
                chunk = stream.read(8192)
                if not chunk:
                    break
                f.write(chunk)
            stream.close()
        logging.debug(f"[ArcFile] '{entry.name}' 추출 완료: {output_path}")

    #항목 데이터를 스트림으로 열기
    def open_entry(self, entry: Entry) -> io.BytesIO:
        if hasattr(entry, "raw_stream") and entry.raw_stream:
            return entry.raw_stream

        if entry.offset < 0 or entry.size <= 0:
            logging.warning(f"[ArcFile] 잘못된 entry: {entry.name} (offset={entry.offset}, size={entry.size})")
            return io.BytesIO()

        if entry.offset + entry.size > self.view.size:
            logging.error(f"[ArcFile] 범위 초과 오류: {entry.name} @0x{entry.offset:X} + {entry.size} > {self.view.size}")
            return io.BytesIO()

        data = self.view.read_at(entry.offset, entry.size)
        return io.BytesIO(data)
    
    #시커블(BytesIO)로 복사된 스트림 반환
    def open_seekable_entry(self, entry: Entry) -> io.BytesIO:
        logging.debug(f"[ArcFile] '{entry.name}' seekable 스트림 준비됨")
        return self.open_entry(entry)

    #전체 항목을 지정된 폴더로 추출
    def extract_all(self, output_dir: str):
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        for entry in self.entries:
            output_path = os.path.join(output_dir, entry.name)
            self.extract_entry(entry, output_path)
        logging.info(f"[ArcFile] 전체 추출 완료: {output_dir}")

    def create_file(self, entry: Entry) -> io.BufferedWriter:
        path = entry.name
        dir_name = os.path.dirname(path)
        if dir_name and not os.path.exists(dir_name):
            os.makedirs(dir_name)
            logging.debug(f"[ArcFile] 디렉토리 생성: {dir_name}")
        return open(path, 'wb')
    
    @staticmethod
    def try_open(filename: str, openers: list) -> Optional["ArcFile"]:
        if not os.path.exists(filename):
            logging.error(f"[ArcFile] 파일이 존재하지 않음: {filename}")
            return None

        view = FileView(filename)
        sig = view.peek(4)

        matching_openers = []
        for opener in openers:
            for sig_bytes in getattr(opener, 'signatures', []):
                if sig == sig_bytes:
                    matching_openers.append(opener)
                    break
        openers_to_try = matching_openers if matching_openers else openers

        for opener in openers_to_try:
            arc = opener.try_open(view)
            if arc:
                logging.info(f"[ArcFile] 오픈 성공: {opener.__class__.__name__} → {filename}")
                return arc

        logging.warning(f"[ArcFile] 오픈 실패: {filename}")
        view.close()
        return None
        

# AppendStream: ArcFile에서 기존 파일 뒤에 데이터를 추가하기 위한 출력 스트림 (압축/복호화 후 데이터를 덧붙이기 위한 용도)     
class AppendStream(io.RawIOBase):
    def __init__(self, base_stream: io.RawIOBase):
        self.base = base_stream
        self.base.seek(0, io.SEEK_END)
        self._closed = False
        logging.debug("[ArcFile] 스트림 끝에서 쓰기 시작")

    def write(self, b: bytes) -> int:
        if self._closed:
            raise ValueError("스트림이 닫혔습니다.")
        written = self.base.write(b)
        logging.debug(f"[ArcFile] {written} 바이트 기록됨")
        return written

    def flush(self):
        self.base.flush()

    def close(self):
        if not self._closed:
            self.flush()
            self.base.close()
            self._closed = True
            logging.debug("[ArcFile] 스트림 닫힘")

    @property
    def closed(self) -> bool:
        return self._closed

    def writable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return False

    def readable(self) -> bool:
        return False

