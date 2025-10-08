# audioogg.py - Camellia cipher decryptor used in GARbro's Malie engine handler
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
# pyogg 등 Python의 OGG를 담당하는 모듈은 강제로 디코딩하는 기능이 있어 코드로 방지했습니다.

import io
import logging
import pyogg
import zlib
from gameres.audio import SoundInput, AudioFormat

class OggInput(SoundInput):
    def __init__(self, source: io.BytesIO):
        super().__init__(None)
        self._source = source  # 원본 stream 저장

        source.seek(0)
        self._reader = pyogg.VorbisFile(source)
        self._samples = self._reader.buffer
        self._channels = self._reader.channels
        self._samplerate = self._reader.frequency
        self._framecount = len(self._samples) // (self._channels * 2)

        self.format = {
            'format_tag': 1,
            'channels': self._channels,
            'sample_rate': self._samplerate,
            'avg_bytes': self._samplerate * self._channels * 2,
            'block_align': 2 * self._channels,
            'bits_per_sample': 16
        }

        self.pcm_size = len(self._samples)

    def read(self, size=-1) -> bytes:
        if size == -1:
            return self._samples
        return self._samples[:size]
    
    def get_original_stream(self) -> io.BytesIO:
        self._source.seek(0)
        return self._source
    
class OggFormat(AudioFormat):
    def __init__(self):
        super().__init__() 
        self.name = "OGG"
        self.extensions = ["ogg"]
        self.signatures = [b'OggS']
        
    @property
    def type(self) -> str:
        return "audio"

    def try_open(self, file: io.BytesIO):
        return OggAudio().try_open(file)


class OggAudio:
    def try_open(self, stream: io.BytesIO) -> OggInput | None:
        try:
            return OggInput(stream)
        except Exception as e:
            logging.debug(f"[audioogg] 디코딩 실패 (원본 저장이라면 무시해도 됨.): {e}") 
            return None
        
