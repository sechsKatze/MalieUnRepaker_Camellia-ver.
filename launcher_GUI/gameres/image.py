# image.py - Camellia cipher decryptor used in GARbro's Malie engine handler
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

from typing import Optional
from io import BytesIO
from dataclasses import dataclass
import cv2
import numpy as np
import logging
from gameres.gameres import FormatCatalog, InvalidFormatException, IResource


@dataclass(frozen=True)
class PixelFormat:
    bits_per_pixel: int
    name: str

    def __str__(self):
        return f"<PixelFormat {self.name} ({self.bits_per_pixel}bpp)>"

class PixelFormats:
    Bgra32 = PixelFormat(32, "Bgra32")
    Bgr24 = PixelFormat(24, "Bgr24")
    Gray8 = PixelFormat(8, "Gray8")
    Gray16 = PixelFormat(16, "Gray16")
    Indexed8 = PixelFormat(8, "Indexed8")
    Gray8Alpha = PixelFormat(16, "Gray8+Alpha")
    Unknown = PixelFormat(0, "Unknown")

class ImageMetaData:
    def __init__(self, width: int, height: int, offset_x: int = 0, offset_y: int = 0,
                 bpp: int = 0, filename: Optional[str] = None,
                 ext: Optional[str] = None, bit_depth: Optional[int] = None,
                 color_type: Optional[int] = None, palette: Optional[bytes] = None):
        self.width = width
        self.height = height
        self.offset_x = offset_x
        self.offset_y = offset_y
        self.bpp = bpp
        self.filename = filename
        self.ext = ext
        self.bit_depth = bit_depth
        self.color_type = color_type
        self.palette = palette
        self.bpp = bpp or self.infer_bpp(color_type, bit_depth)

    @staticmethod
    def infer_bpp(color_type, bit_depth):
        if color_type == 0:  # Grayscale
            return bit_depth
        if color_type == 2:  # RGB
            return bit_depth * 3
        if color_type == 3:  # Palette
            return bit_depth
        if color_type == 4:  # Grayscale + Alpha
            return bit_depth * 2
        if color_type == 6:  # RGBA
            return bit_depth * 4
        return bit_depth

    def get_pixel_format(self) -> PixelFormat:
        ct = self.color_type
        bd = self.bit_depth

        if ct == 0:  # Grayscale
            if bd == 8:
                return PixelFormats.Gray8
            elif bd == 16:
                return PixelFormats.Gray16
        elif ct == 2:  # RGB
            if bd == 8:
                return PixelFormats.Bgr24
        elif ct == 3:  # Palette
            if bd == 8:
                return PixelFormats.Indexed8
        elif ct == 4:  # Gray + Alpha
            if bd == 8:
                return PixelFormats.Gray8Alpha
        elif ct == 6:  # RGBA
            if bd == 8:
                return PixelFormats.Bgra32

        return PixelFormats.Unknown
    
        
class ImageEntry:
    def __init__(self, name: str, offset: int, size: int):
        self.name = name
        self.offset = offset
        self.size = size
        self.type = "image"

class ImageData:
    default_dpi_x = 96
    default_dpi_y = 96

    def __init__(self, data: bytes, width: int, height: int, bpp: int,
                 offset_x: int = 0, offset_y: int = 0,
                 color_type: int = 6, bit_depth: int = 8, palette: bytes = None, stride=None):
        self.data = data
        self._width = width
        self._height = height
        self._bpp = bpp
        self.offset_x = offset_x
        self.offset_y = offset_y
        self.color_type = color_type
        self.bit_depth = bit_depth
        self.palette = palette
        self.stride = stride or ((self.bpp + 7) // 8) * self.width

        meta = ImageMetaData(width, height, offset_x, offset_y, bpp, bit_depth=bit_depth, color_type=color_type)
        self.pixel_format = meta.get_pixel_format()

    @property
    def width(self) -> int:
        return self._width

    @property
    def height(self) -> int:
        return self._height

    @property
    def bpp(self) -> int:
        return self._bpp
    
    @property
    def stride(self) -> int:
        return self._stride

    @stride.setter
    def stride(self, value: int):
        self._stride = value

    @classmethod
    def set_default_dpi(cls, x: float, y: float):
        cls.default_dpi_x = x
        cls.default_dpi_y = y

    @staticmethod
    def calc_stride(width: int, bpp: int) -> int:
        return width * ((bpp + 7) // 8)

    @classmethod
    def create(cls, info: ImageMetaData, bpp: int, raw_data: bytes,
            stride: Optional[int] = None, palette: Optional[bytes] = None):

        if bpp == 0:
            logging.warning("[ImageData.create] bpp=0 → 기본값 32(RGBA) 적용")
            bpp = 32  # 또는 24 (RGB)로 바꿔도 됨

        stride = stride or (info.width * ((bpp + 7) // 8))
        expected_len = stride * info.height
        actual_len = len(raw_data)

        if actual_len < expected_len:
            logging.warning(f"[ImageData.create] raw 길이 부족 → {actual_len} < {expected_len}")
            raw_data += bytes(expected_len - actual_len)
        elif actual_len > expected_len:
            logging.warning(f"[ImageData.create] raw 길이 초과 → {actual_len} > {expected_len}")
            raw_data = raw_data[:expected_len]

        return cls(
            data=raw_data,
            width=info.width,
            height=info.height,
            bpp=bpp,
            offset_x=info.offset_x,
            offset_y=info.offset_y,
            color_type=info.color_type,
            bit_depth=info.bit_depth,
            palette=palette
        )

    @classmethod
    def create_simple(cls, info: ImageMetaData, bpp: int, raw_data: bytes, palette: Optional[bytes] = None):
        stride = info.width * ((bpp + 7) // 8)
        return cls.create(info, bpp, raw_data, stride, palette)
    
    @classmethod
    def create_from_format(cls, info: ImageMetaData, format: PixelFormat, raw_data: bytes,
                        stride: Optional[int] = None, palette: Optional[bytes] = None):
        stride = stride or cls.calc_stride(info.width, format.bits_per_pixel)
        return cls.create(info, format.bits_per_pixel, raw_data, stride, palette)
    
    @classmethod
    def from_cv_image(cls, mat: np.ndarray, info: ImageMetaData):
        height, width = mat.shape[:2]
        bpp = mat.shape[2] * 8 if len(mat.shape) == 3 else 8
        raw_data = mat.tobytes()
        return cls(
            data=raw_data,
            width=width,
            height=height,
            bpp=bpp,
            offset_x=info.offset_x,
            offset_y=info.offset_y,
            color_type=info.color_type,
            bit_depth=info.bit_depth,
            palette=info.palette
        )


class ImageFormat(IResource):
    type = "image"
    
    def try_open(self, stream: BytesIO):
        try:
            meta = self.read_metadata(stream)
            if not meta:
                # logging.debug("[image] try_open 실패: 메타데이터 없음")
                return None
            stream.seek(0)
            return self.read(stream, meta)
        except Exception as e:
            # logging.warning(f"[image] try_open 예외 발생: {e}")
            return None

    def read_metadata(self, file: BytesIO) -> Optional[ImageMetaData]:
        raise NotImplementedError()

    def read(self, file: BytesIO, info: ImageMetaData) -> ImageData:
        raise NotImplementedError()

    def write(self, file: BytesIO, image: ImageData):
        raise NotImplementedError()

    @classmethod
    def read_auto(cls, file: BytesIO, filename: Optional[str] = None) -> ImageData:
        logging.debug(f"[Image] {filename or '<unknown>'} → OpenCV 기반 디코딩 시작")
        file.seek(0)
        np_arr = np.frombuffer(file.read(), np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_UNCHANGED)

        if img is None:
            raise InvalidFormatException(f"OpenCV 디코딩 실패: {filename or '<unknown>'}")

        height, width = img.shape[:2]
        channels = img.shape[2] if img.ndim == 3 else 1
        bpp = channels * 8

        info = ImageMetaData(width=width, height=height, ext=".png", bpp=bpp)
        raw = img.tobytes()
        return ImageData.create(info, bpp, raw)
    