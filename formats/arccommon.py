# arccommon.py - Camellia cipher decryptor used in GARbro's Malie engine handler
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

import io, os
import logging
from gameres.gameres import FormatCatalog
from gameres.utility import LittleEndian
from formats.fileview import FileView


class AutoEntry:
    def __init__(self, name: str, file_view: FileView, offset: int, size: int = None, archive=None):
        self.offset = offset
        self.file_view = file_view
        self._base_name = name
        self._res = self._init_resource()
        self.archive = archive
        self.signature = LittleEndian.ToUInt32(file_view.read_at(offset, 4), 0)
        self.format = FormatCatalog.lookup_signature(self.signature)
        self.name = self._get_name()
        self.type = self._get_type()
        self.size = size if size is not None else self._guess_size()
        self.raw_stream = file_view.create_stream(self.offset, self.size)
        self.archive = file_view
        self.key_name = None
        self.raw_stream = file_view.create_stream(offset, size)
        self.entry_index = None
        self.offset_index = None

        logging.debug(
            f"[arccommon] 생성됨: name={self.name}, offset=0x{self.offset:X}, size=0x{self.size:X}, "
            f"signature=0x{self.signature:08X}, type={self.type}"
        )
        
    def __repr__(self):
        return (
            f"<AutoEntry name={self.name}, "
            f"entry_index={getattr(self, 'entry_index', 'N/A')}, "
            f"offset_index={getattr(self, 'offset_index', 'N/A')}, "
            f"offset=0x{self.offset:X}, size=0x{self.size:X}>"
            f"is_dir={getattr(self, 'is_dir', False)}>"
        )
        
    def _init_resource(self):
        try:
            sig = self.file_view.read_at(self.offset, 4)
            return FormatCatalog.from_signature(sig, expected_type="any")
        except Exception:
            return None

    def _get_name(self):
        if not self.format:
            return self._base_name
        ext = self.format.get_default_extension()
        if not ext:
            return self._base_name
        return os.path.splitext(self._base_name)[0] + "." + ext

    def _get_type(self):
        if self._res:
            return self._res.resource_type  # 예: "image", "audio", "text"
        return None
    
    def _guess_size(self, next_offset: int = None):
        if next_offset is not None:
            logging.debug(f"[arccommon] next_offset 기반 size 추정: offset=0x{self.offset:X}, next_offset=0x{next_offset:X}")
            return next_offset - self.offset

        # fallback: 파일 끝까지
        max_offset = self.file_view.size
        guessed_size = max_offset - self.offset

        logging.warning(f"[arccommon] size 지정 안됨 → 파일 끝까지 추정: {guessed_size} bytes")
        return guessed_size

    def open(self):
        return self.raw_stream
    
    def read(self, offset: int, size: int) -> bytes:
        return self.file_view.read_at(self.offset + offset, size)
    
    @staticmethod
    def _guess_size_static(file_view: FileView, offset: int) -> int:
        max_offset = file_view.size
        scan_limit = min(max_offset - offset, 0x100000)  # 예: 1MB 범위 탐색
        for delta in range(0x10, scan_limit, 0x10):
            try:
                sig = file_view.read_at(offset + delta, 4)
                if FormatCatalog.lookup_signature(LittleEndian.ToUInt32(sig, 0)):
                    logging.debug(f"[arccommon] 시그니처 감지: offset=0x{offset:X} + 0x{delta:X} = 0x{offset+delta:X}")
                    return delta
            except:
                continue
        guessed = max_offset - offset
        logging.warning(f"[arccommon] 시그니처 못찾음 → 끝까지 추정: {guessed} bytes")
        return guessed

    # C#의 AutoEntry.Create(file, offset, base_name)과 동일한 역할 수행
    @staticmethod
    def create(file_view: FileView, offset: int, base_name: str, size: int = 0, next_offset: int = None, archive=None, key_name=None):
        logging.debug(f"[arccommon] Create 호출 (offset=0x{offset:X}, base_name='{base_name}')")

        try:
            data = file_view.read_at(offset, 4)
            signature = LittleEndian.ToUInt32(data, 0)
            logging.debug(f"[arccommon] 시그니처 읽음 (offset=0x{offset:X}, signature=0x{signature:08X})")

            try:
                res = FormatCatalog.lookup_signature(signature)
            except Exception as e:
                logging.info(f"[arccommon] FormatCatalog 조회 실패 (무해함): {e}")
                res = None

            # size 우선순위: 직접 지정 > next_offset > file 끝까지
            if size:
                entry_size = size
            elif next_offset:
                entry_size = next_offset - offset
            else:
                entry_size = AutoEntry._guess_size_static(file_view, offset)

            entry = AutoEntry(base_name, file_view, offset, entry_size, archive=archive)
            entry._res = res
            entry.key_name = key_name

            try:
                entry.name = entry._get_name()
                entry.type = entry._get_type()
            except Exception as e:
                logging.warning(f"[arccommon] 이름/타입 추정 실패 → 기본값 사용: {e}")
                entry.name = base_name
                entry.type = "bin"

            logging.info(
                f"[arccommon] 엔트리 생성 완료: name={entry.name}, offset=0x{entry.offset:X}, "
                f"size=0x{entry.size:X}, type={entry.type}, key={key_name}"
            )
            return entry

        except Exception as e:
            logging.warning(f"[arccommon] Create 실패 → fallback 진입: {e}")
            guessed_size = AutoEntry._guess_size_static(file_view, offset)
            entry = AutoEntry(base_name, file_view, offset, guessed_size)
            entry.archive = archive
            entry.key_name = key_name
            return entry
    

class PrefixStream(io.RawIOBase):
    def __init__(self, header: bytes, stream: io.BufferedReader):
        if isinstance(header, io.BytesIO):
            header = header.getvalue() # BytesIO → bytes

        self.header = header
        self.stream = stream
        self.pos = 0
        self.header_len = len(header)

    def read(self, size=-1):
        data = b''
        if self.pos < self.header_len:
            head_remain = self.header_len - self.pos
            to_read = head_remain if size < 0 else min(size, head_remain)
            data += self.header[self.pos:self.pos+to_read]
            self.pos += to_read
            if size > 0:
                size -= to_read
        if size != 0:
            body_data = self.stream.read(size)
            data += body_data
            self.pos += len(body_data)
        return data

    def seek(self, offset, whence=io.SEEK_SET):
        if whence == io.SEEK_SET:
            new_pos = offset
        elif whence == io.SEEK_CUR:
            new_pos = self.pos + offset
        elif whence == io.SEEK_END:
            stream_end = self.header_len + self.stream.seek(0, io.SEEK_END)
            new_pos = stream_end + offset
        else:
            raise ValueError("Invalid whence value")

        if new_pos < self.header_len:
            self.pos = new_pos
            self.stream.seek(0)
        else:
            self.pos = new_pos
            self.stream.seek(self.pos - self.header_len)
        return self.pos

    def tell(self):
        return self.pos

    def readable(self):
        return True

    def seekable(self):
        return True

    def readinto(self, b):
        data = self.read(len(b))
        n = len(data)
        b[:n] = data
        return n
    
class StreamRegion(io.RawIOBase):
    def __init__(self, base_stream: io.BufferedReader, offset: int, length: int, name: str = None):
        self.stream = base_stream
        self.begin = offset
        self.length = length
        self.end = self.begin + self.length
        self.pos = 0
        self.name = name or "unnamed" 
        self.stream.seek(self.begin)

    def read(self, size=-1):
        current = self.begin + self.pos
        self.stream.seek(current)
        max_read = self.end - current
        if size < 0 or size > max_read:
            size = max_read
        data = self.stream.read(size)
        self.pos += len(data)
        return data

class HuffmanDecoder:
    def __init__(self, src: bytes, dst_len: int):
        self.src = src
        self.dst = bytearray(dst_len)
        self.lhs = [0]*512
        self.rhs = [0]*512
        self.token = 256
        self.pos = 0
        self.remain = len(src)
        self.cache = 0
        self.bits = 0

    def unpack(self):
        root = self._create_tree()
        i = 0
        while i < len(self.dst):
            node = root
            while node >= 0x100:
                bit = self._get_bits(1)
                node = self.rhs[node] if bit else self.lhs[node]
            self.dst[i] = node
            i += 1
        return bytes(self.dst)

    def _create_tree(self):
        if self._get_bits(1):
            node = self.token
            self.token += 1
            self.lhs[node] = self._create_tree()
            self.rhs[node] = self._create_tree()
            return node
        else:
            return self._get_bits(8)

    def _get_bits(self, n):
        while self.bits < n:
            if self.remain == 0:
                raise ValueError("Invalid huffman stream")
            self.cache |= self.src[self.pos] << self.bits
            self.bits += 8
            self.pos += 1
            self.remain -= 1
        val = self.cache & ((1 << n) - 1)
        self.cache >>= n
        self.bits -= n
        return val
    
class NotTransform:
    def transform_block(self, data: bytes) -> bytes:
        return bytes(~b & 0xFF for b in data)

class XorTransform:
    def __init__(self, key: int = 0xFF):
        self.key = key

    def transform_block(self, data: bytes) -> bytes:
        return bytes(b ^ self.key for b in data)

class RotateTransform:
    def __init__(self, shift: int = 1):
        self.shift = shift

    def transform_block(self, data: bytes) -> bytes:
        shift = self.shift % len(data)
        return data[shift:] + data[:shift]

class NoTransform:
    def transform_block(self, data: bytes) -> bytes:
        return data