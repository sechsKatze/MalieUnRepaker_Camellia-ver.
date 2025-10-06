# imagedzi.py - Camellia cipher decryptor used in GARbro's Malie engine handler
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

import numpy as np
import cv2
import logging
from gameres.gameres import LittleEndian 
from gameres.image import ImageFormat, ImageMetaData, ImageData

class DziTile:
    def __init__(self, x, y, filename):
        self.x = x
        self.y = y
        self.filename = filename

class DziMetaData(ImageMetaData):
    def __init__(self, width, height, tiles):
        super().__init__(width, height, 0, 0, 32)
        self.tiles = tiles

class DziFormat(ImageFormat):
    def __init__(self):
        super().__init__()
        self.name = "DZI"
        self.extensions = ["dzi"]
        self.signatures = [b"DZI\r"]

    @property
    def type(self) -> str:
        return "image"

    def try_open(self, stream):
        fmt = DziFormat()
        info = fmt.read_metadata(stream)
        if not info:
            return None
        return fmt.read(stream, info)

    def read_metadata(self, stream):
        lines = stream.read().decode("utf-8").splitlines()
        if not lines or not lines[0].startswith("DZI"):
            return None

        width, height = map(int, lines[1].split(","))
        tile_group_count = int(lines[2])
        tiles = []
        line_idx = 3

        for _ in range(tile_group_count):
            _, block_h = map(int, lines[line_idx].split(","))
            line_idx += 1
            group = []
            y = 0
            for _ in range(block_h):
                x = 0
                filenames = lines[line_idx].strip().split(',')
                for name in filenames:
                    if name:
                        # ✅ 완전히 고정된 상대 경로
                        tile_path = f"tex/{name}.png"
                        group.append(DziTile(x, y, tile_path))
                    x += 256
                y += 256
                line_idx += 1
            tiles.append(group)

        return DziMetaData(width, height, tiles)

    def read(self, stream, info: DziMetaData) -> ImageData | None:
        try:
            canvas = np.zeros((info.height, info.width, 4), dtype=np.uint8)

            for tile in info.tiles[0]:  # 레이어 0만 사용
                tile_path = tile.filename.replace("\\", "/")
                tile_entry = None

                if self.archive:
                    tile_entry = self.archive.find(tile_path)

                if not tile_entry:
                    logging.warning(f"[imagedzi] 타일 누락: {tile_path}")
                    continue

                tile_data = tile_entry.open().read()
                np_arr = np.frombuffer(tile_data, np.uint8)
                tile_img = cv2.imdecode(np_arr, cv2.IMREAD_UNCHANGED)

                if tile_img is None:
                    logging.warning(f"[imagedzi] OpenCV 디코딩 실패: {tile_path}")
                    continue

                if tile_img.shape[2] == 3:  # BGR → BGRA
                    tile_img = cv2.cvtColor(tile_img, cv2.COLOR_BGR2BGRA)

                h, w = tile_img.shape[:2]
                x, y = tile.x, tile.y
                canvas[y:y+h, x:x+w] = tile_img

            # 실제 사이즈로 크롭
            result = canvas[0:info.actual_height, 0:info.actual_width]
            raw_bytes = result.tobytes()
            return ImageData(info.width, info.height, raw_bytes, bpp=32)

        except Exception as e:
            logging.error(f"[imagedzi] OpenCV read() 중 예외 발생: {e}")
            return None