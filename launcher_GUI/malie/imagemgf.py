# imagemgf.py - Camellia cipher decryptor used in GARbro's Malie engine handler
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
# 해당 코드는 원본 코드가 그러했듯 GUI 용으로 맞추어진 코드라 파일을 열어 뷰어로 볼 시 이미지를 미리보기 위해 만들어진 코드입니다.
# .mgf는 헤더만 MalieGF인 PNG 형식(청크를 보아 1998년도 기준)의 이미지입니다. 
# 원본 코드를 비롯해 GARBRO에는 PNG ↔ MGF 변환 옵션이 없음.

import io
import logging
from gameres.imagepng import PngFormat
from gameres.image import ImageMetaData, ImageData
from gameres.utility import ascii_equal

class MgfFormat(PngFormat):
    def __init__(self):
        super().__init__()
        self.extensions = ["mgf"]
        self.signatures = [b"MalieGF"] #0x
        self.signature = b'Mali' 
        
    @property
    def type(self) -> str:
        return "image"

    def read_metadata(self, stream: io.BytesIO) -> ImageMetaData | None:
        stream.seek(0)
        header = stream.read(8)
        logging.debug(f"[imagemgf] header={header} (len={len(header)})")
        if not ascii_equal(header[:7], 0, "MalieGF"):
            logging.warning("[imagemgf] MalieGF 시그니처 불일치")
            return None

        # PNG 헤더 붙이고 metadata 읽기
        png_data = b'\x89PNG\r\n\x1a\n' + stream.read()
        return super().read_metadata(io.BytesIO(png_data))

    def read(self, stream: io.BytesIO, info: ImageMetaData) -> ImageData:
        stream.seek(0)
        stream.read(8)  # skip MalieGF
        png_data = b'\x89PNG\r\n\x1a\n' + stream.read()
        return super().read(io.BytesIO(png_data), info)

    # PNG 헤더 제외 후 MalieGF 접두 붙이기 
    # 원본 코드(garbro, c#)는 사실상 더미인, 즉 실제로 구현(PNG -> MGF로 변환)되지 않았습니다.
    def write(self, file: io.BytesIO, image: ImageData):
        temp = io.BytesIO()
        super().write(temp, image)
        data = temp.getvalue()
        file.write(b'MalieGF' + data[8:]) 