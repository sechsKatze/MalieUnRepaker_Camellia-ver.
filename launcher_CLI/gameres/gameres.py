# gameRes.py - Camellia cipher decryptor used in GARbro's Malie engine handler
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

# GARbro(by. morkt) 1.1.6 ver.을 기준으로 Python으로 포팅. gameres는 GameRes.cs와 MultiDict.cs, garStrings.Designer.cs를 같이 통합했습니다.

import os
from abc import ABC, abstractmethod
import logging
from typing import BinaryIO, TYPE_CHECKING, Optional, Callable
from io import BytesIO
from collections import defaultdict
from enum import Enum

from formats.fileview import FileView
from gameres.utility import LittleEndian


# 엔트리
class Entry:
    def __init__(self, name: str, offset: int, size: int):
        self.name = name
        self.offset = offset
        self.size = size

# 리소스 기능
class IResource(ABC):
    def __init__(self):
        self._name = getattr(self, "__class__").__name__  # 기본값 설정

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str):
        self._name = value

    @property
    @abstractmethod
    def type(self) -> str:
        pass

    def create_entry(self, name: str, offset: int, size: int) -> 'Entry':
        return Entry(name=name, offset=offset, size=size)
    
class ArchiveOperation(Enum):
    CONTINUE = "continue"
    SKIP = "skip"
    ABORT = "abort"
    
EntryCallback = Callable[[int, 'Entry', str], ArchiveOperation]

# 아카이브 포맷
class ArchiveFormat(IResource):
    def __init__(self):
        super().__init__()
        self.name = "unknown"
        self.extensions = []
        self.signatures = []

    @property
    def type(self) -> str:
        return "archive"

    def try_open(self, view):
        raise NotImplementedError("포맷 오프너 구현 필요")
    
    # 유효한 항목 수 검사
    @staticmethod
    def is_sane_count(count: int, max_reasonable: int = 0x10000) -> bool:
        if count <= 0 or count > max_reasonable:
            logging.warning(f"[gameres] 항목 수 비정상: {count} (최대 허용: {max_reasonable})")
            return False
        logging.debug(f"[gameres] 항목 수 정상: {count}")
        return True

    # 전체 Entry를 지정된 폴더에 추출
    def extract(self, arc, entry: Entry, out_dir: str, callback: Optional[EntryCallback] = None, index: int = 0):
        if callback:
            decision = callback(index, entry, f"[{entry.name}]")
            if decision == ArchiveOperation.ABORT:
                logging.warning("[extract] 사용자 요청으로 중단됨")
                raise InterruptedError("User aborted extraction")
            elif decision == ArchiveOperation.SKIP:
                logging.info(f"[extract] 스킵됨: {entry.name}")
                return  # 항목 건너뜀

        path = os.path.join(out_dir, entry.name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            arc.stream.seek(entry.offset)
            f.write(arc.stream.read(entry.size))
        logging.info(f"[extract] 추출 완료: {entry.name}")

    # Entry에 대한 스트림 열기
    def open_entry(self, arc, entry):
        logging.debug(f"[gameres] Entry 스트림 열기: {entry.name}")
        return arc.open_entry(entry)

    # Entry 내용을 output_path로 복사
    def copy_entry(self, arc, entry, output_path: str):
        logging.debug(f"[gameres] '{entry.name}' 복사 시작 → {output_path}")
        with self.open_entry(arc, entry) as src:
            with self.create_file(output_path) as dst:
                while True:
                    chunk = src.read(8192)
                    if not chunk:
                        break
                    dst.write(chunk)
        logging.debug(f"[gameres] '{entry.name}' 복사 완료")


    # 지정 경로에 파일 생성 (상위 디렉토리도 생성)
    def create_file(self, path: str):
        self.create_path(path)
        return open(path, 'wb')

    # 경로 상의 디렉토리를 생성
    def create_path(self, path: str):
        dir_path = os.path.dirname(path)
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path)
            
# 이미지 포맷
class ImageFormat(IResource):
    @abstractmethod
    def read_metadata(self, stream: BytesIO):
        pass

    @abstractmethod
    def read(self, stream: BytesIO, meta):
        pass

    def try_open(self, stream: BytesIO):
        meta = self.read_metadata(stream)
        if meta:
            stream.seek(0)
            return self.read(stream, meta)
        return None
    
# 오디오 포맷
class AudioFormat(IResource):
    @abstractmethod
    def try_open(self, stream: BytesIO):
        pass

# 예외 처리
class InvalidFormatException(Exception):
    pass

# GARbro의 MultiDict.cs의 해당.
class MultiValueDict:
    def __init__(self):
        self._store = defaultdict(list)
        logging.debug("[gameres - MultiValueDict] 초기화 완료")

    def add(self, key, value):
        if value not in self._store[key]:
            self._store[key].append(value)
            logging.debug(f"[gameres - MultiValueDict] 추가: ({key}, {value})")
        else:
            logging.debug(f"[gameres - MultiValueDict] 이미 존재함: ({key}, {value})")

    def remove(self, key, value):
        if key in self._store and value in self._store[key]:
            self._store[key].remove(value)
            logging.debug(f"[gameres - MultiValueDict] 제거 완료: ({key}, {value})")
            if not self._store[key]:
                del self._store[key]
                logging.debug(f"[gameres - MultiValueDict] 키 삭제됨 (빈 값): {key}")
        else:
            logging.debug(f"[gameres - MultiValueDict] 제거 실패 (존재하지 않음): ({key}, {value})")

    def get(self, key, return_empty_list=False):
        if key in self._store:
            return self._store[key]
        if return_empty_list:
            return []
        return None

    def __getitem__(self, key):
        return self._store[key]

    def __contains__(self, key):
        return key in self._store

    def keys(self):
        return self._store.keys()

    def values(self):
        return self._store.values()

    def items(self):
        return self._store.items()

    def clear(self):
        self._store.clear()
        

# GARbro의 garStrings.Designer.cs의 해당.
class GarStrings:
    MsgFileTooLarge = "File is too large"
    MsgInvalidEncryption = "Inappropriate encryption scheme"
    MsgInvalidFileName = "Invalid file name"
    MsgInvalidFormat = "Invalid file format"
    MsgUnknownEncryption = "Unknown encryption scheme"   

# FormatCatalog - 포맷 레지스트리
class FormatCatalog:
    _formats_by_ext = MultiValueDict()  
    _formats_by_sig = []
    formats = []
    _formats = {}
    SIGNATURE_MAP = {
        b"\x89PNG\r\n\x1a\n": "png",       # PNG
        b"MalieGF": "mgf",                  # MGF
        b"OggS": "ogg",                    # Ogg/OGG
        b"PK\x03\x04": "zip",             # ZIP (혹은 ODT/EPUB 등)
        b"<svg": "svg",                   # SVG with inline tag
        b"<?xml": "svg",                  # XML 선언형 SVG
        b"DZI": "dzi",                    # DZI (텍스트 기반)
        b"\x00\x00\x01\xBA": "mpg",       # MPEG-PS (Packet Stream) 시그니처
        b"\x00\x00\x01\xB3": "mpg",       # MPEG-1 video sequence header
        b"FWS": "swf",                    # SWF (uncompressed)
        b"CWS": "swf",                    # SWF (zlib compressed)
        b"ZWS": "swf",                    # SWF (LZMA compressed)
        b"LIBP": "dat",                   # Malie engin archive
    }
    EXT_TO_TYPE = {
    "png": "image",
    "mgf": "image",
    "ogg": "audio",
    "mpg": "video",
    "svg": "text",
    "csv": "text",
    "swf": "flash",
    "dzi": "image",
    "dat": "archive",  
    }
    
    @classmethod
    def add_format_by_key(cls, key, handler):
        cls._formats[key] = handler

    @classmethod
    def get_format(cls, key):
        return cls._formats.get(key)

    @classmethod
    def add_format(cls, fmt: IResource):
        cls.formats.append(fmt)
        for ext in getattr(fmt, "extensions", []):
            cls._formats_by_ext.add(ext.lower(), fmt)
            logging.debug(f"[gameres] 확장자 등록: {ext.lower()} → {fmt.name}")

        for sig in fmt.signatures:
            if isinstance(sig, bytes):
                if len(sig) < 4:
                    continue
                sig_val = LittleEndian.ToUInt32(sig, 0)
            elif isinstance(sig, int):
                sig_val = sig
            else:
                continue
            cls._formats_by_sig.append((sig_val, fmt))
        
    @classmethod
    def lookup_signature(cls, sig: bytes):
        if not isinstance(sig, bytes) or len(sig) < 4:
            return None
        value = LittleEndian.ToUInt32(sig, 0)
        for sig_val, fmt in cls._formats_by_sig:
            if value == sig_val:
                return fmt
        return None

    @classmethod
    def from_extension(cls, ext: str, expected_type: Optional[str] = None):
        fmts = cls._formats_by_ext.get(ext.lower(), return_empty_set=True)
        for fmt in fmts:
            if expected_type is None or getattr(fmt, "type", None) == expected_type:
                return fmt
        return None

    @classmethod
    def from_signature(cls, data: bytes, expected_type=None):
        for sig, ext in cls.SIGNATURE_MAP.items():
            if isinstance(sig, bytes) and data.startswith(sig):
                if expected_type is None or cls.EXT_TO_TYPE.get(ext) == expected_type:
                    handlers = cls._formats_by_ext.get(ext)
                    if handlers:
                        return list(handlers)[0]  # ✅ set → list로 변환
        return None
    
    @classmethod
    def detect_format(cls, filename: str, stream) -> ArchiveFormat | None:
        # 1. 확장자 기반 탐지
        ext = os.path.splitext(filename)[1].lower()
        if ext in [".csv", ".svg", ".txt",".json", ".mpg", ".mp4", "avi", ".mov", ".wmv"]:
            return None
        
        fmt = cls.from_extension(ext)
        if fmt:
            return fmt

        # 2. 시그니처 기반 fallback 탐지
        try:
            pos = stream.tell()
            header = stream.read(32)
            stream.seek(pos)
            return cls.from_signature(header)
        except Exception as e:
            logging.warning(f"[gameres] 시그니처 탐지 중 오류 발생: {e}")
            return None

    # 시그니처 읽기 유틸
    @classmethod
    def read_signature(file) -> bytes:
        file.seek(0)
        sig = file.read(4)
        logging.debug(f"[gameres] 시그니처 읽음: {sig.hex()}")
        return sig

    # 포맷 감지 유틸
    @classmethod
    def get_archive_format_by_extension(cls, filename: str):
        ext = os.path.splitext(filename)[1][1:].lower()
        logging.debug(f"[gameres] 파일 확장자: {ext}")
        fmt = cls.from_extension(ext)
        if fmt:
            logging.debug(f"[gameres] 확장자 기반 포맷 감지 성공: {fmt.name}")
        else:
            logging.debug("[gameres] 확장자 기반 포맷 감지 실패")
        return fmt

    @classmethod
    def get_archive_format_by_signature(cls, file: BinaryIO):
        sig = cls.read_signature(file)
        fmt = cls.from_signature(sig)
        if fmt:
            logging.debug(f"[gameres] 시그니처 기반 포맷 감지 성공: {fmt.name}")
        else:
            logging.debug("[gameres] 시그니처 기반 포맷 감지 실패")
        return fmt

    @classmethod
    def open_archive(cls, filename: str):
        logging.debug(f"[gameres] 아카이브 열기 시도: {filename}")
        fmt = cls.get_archive_format_by_extension(filename)
        if fmt is None:
            logging.debug("[gameres] 확장자 기반 실패 → 시그니처 기반 재시도")
            with open(filename, 'rb') as f:
                fmt = cls.get_archive_format_by_signature(f)
        if fmt is None:
            logging.error("[gameres] 포맷 감지 실패")
            raise InvalidFormatException("파일 포맷을 인식할 수 없습니다.")
        
        view = FileView(filename)
        arc = fmt.try_open(view)
        if arc is None:
            logging.error("[gameres] 포맷 감지 성공했지만 아카이브 열기 실패")
            raise InvalidFormatException("파일 포맷은 감지되었으나, 아카이브 열기에 실패했습니다.")
        
        logging.debug(f"[gameres] 아카이브 열기 성공: {fmt.name}, 항목 수: {len(arc.entries)}")
        return arc

