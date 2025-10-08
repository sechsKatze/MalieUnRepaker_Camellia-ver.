# audio.py - Camellia cipher decryptor used in GARbro's Malie engine handler
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

# GARbro(by. morkt) 1.1.6 ver.을 기준으로 Python으로 포팅.


import io
from io import IOBase, BytesIO
from typing import Optional
import logging
from gameres.gameres import FormatCatalog, InvalidFormatException, IResource

# 오디오 포맷 목록 (FormatCatalog.Instance.AudioFormats 대체)
registered_audio_formats = []

def register_audio_format(fmt):
    registered_audio_formats.append(fmt)
    logging.debug(f"[Audio] 포맷 등록: {fmt.__class__.__name__} (tag={fmt.tag}, signature={fmt.signature.hex()})")

# 기본은 wav
class WaveFormat:
    def __init__(self, format_tag, channels, sample_rate, avg_bytes, block_align, bits_per_sample, extra_size=0):
        self.format_tag = format_tag
        self.channels = channels
        self.sample_rate = sample_rate
        self.avg_bytes = avg_bytes
        self.block_align = block_align
        self.bits_per_sample = bits_per_sample
        self.extra_size = extra_size

class SoundInput(IOBase):
    def __init__(self, source: IOBase):
        self.source = source
        self.format = None
        self.pcm_size = 0
        self._position = 0

    def read(self, size=-1):
        raise NotImplementedError("read()는 하위 클래스에서 반드시 오버라이드해야 합니다")
    
    #ogg, mpg 등은 원본 스트림 그대로 반환 : 원본 코드의 포팅이 아닌 파이썬의 한계상 직접 넣은 코드.
    def get_original_stream(self) -> io.BytesIO:
        raise NotImplementedError()

    def seek(self, offset, whence=0):
        if whence == 0:
            self._position = offset
        elif whence == 1:
            self._position += offset
        elif whence == 2:
            self._position = self.pcm_size + offset
        self.source.seek(self._position)
        logging.debug(f"[Audio] 스트림 위치 이동: {self._position}")
        return self._position

    def tell(self):
        return self._position

    def readable(self): return self.source.readable()
    def writable(self): return False
    def seekable(self): return self.source.seekable()
    def close(self):
        if self.source and not self.source.closed:
            self.source.close()
        super().close()

class AudioFormat(IResource):
    type = "audio"
    name = "unknown"
    extensions = []
    signatures = []
    
    @property
    def type(self) -> str:
        return "audio"

    def try_open(self, file: IOBase) -> Optional[SoundInput]:
        raise NotImplementedError(f"{self.__class__.__name__}.try_open() must be implemented")

    def write(self, source: SoundInput, output: IOBase, convert_output: bool = False):
        if convert:
            logging.info("[audioogg] PCM 변환 후 저장 (wav)")
            output.write(source.read())  # PCM data
        else:
            logging.info("[audioogg] 원본 ogg 스트림 그대로 저장")
            stream = source.get_original_stream()
            output.write(stream.read())

    @staticmethod
    def read(file: IOBase) -> Optional[SoundInput]:
        logging.debug("[Audio] AudioFormat.read() 호출됨")
        data = file.read()
        stream = BytesIO(data)
        try:
            sound = AudioFormat.find_format(stream)
            if sound:
                logging.debug("[Audio] 포맷 감지 성공, 스트림 반환")
                return sound
            return None
        finally:
            if not sound:
                logging.debug("[Audio] 감지 실패: 스트림 해제")
                stream.close()

    @staticmethod
    def find_format(file: IOBase) -> Optional[SoundInput]:
        file.seek(0)
        sig = file.read(4)
        file.seek(0)
        logging.debug(f"[Audio] 시그니처 감지: {sig.hex()}")
        fmt = FormatCatalog.from_signature(sig, expected_type="audio")
        if not fmt:
            raise InvalidFormatException(f"[Audio] 포맷 미감지: 시그니처={sig.hex()}")

        try:
            sound = fmt.try_open(file)
            logging.debug("[Audio] 오디오 포맷 감지 및 try_open 성공")
            return sound
        except Exception as e:
            logging.error(f"[Audio] try_open 실패: {e}")
            return None