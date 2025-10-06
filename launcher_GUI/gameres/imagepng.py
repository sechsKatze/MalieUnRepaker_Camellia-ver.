import logging
import struct
from io import BytesIO
from PIL import Image
from gameres.image import ImageFormat, ImageMetaData, ImageData
from gameres.utility import BigEndian

class PngFormat(ImageFormat):
    def __init__(self):
        super().__init__()
        self.extensions = ["png"]
        self.signatures = [b'\x89PNG\r\n\x1a\n']
        self.tag = "PNG"
        self.description = "Portable Network Graphics image"
        self.signature = b'\x89PNG'

    @property
    def type(self) -> str:
        return "image"

    def read_metadata(self, stream: BytesIO) -> ImageMetaData:
        stream.seek(0)
        sig = stream.read(8)
        if sig != b'\x89PNG\r\n\x1a\n':
            return None

        try:
            chunk_len_buf = stream.read(4)
            chunk_type = stream.read(4)
            if len(chunk_len_buf) < 4 or chunk_type != b'IHDR':
                return None
        except Exception:
            return None

        try:
            width = BigEndian.ToUInt32(stream.read(4), 0)
            height = BigEndian.ToUInt32(stream.read(4), 0)
            bpp = stream.read(1)[0]
            color_type = stream.read(1)[0]
        except Exception:
            return None

        if color_type == 0:
            bits = bpp
        elif color_type == 2:
            bits = bpp * 3
        elif color_type == 3:
            bits = bpp
        elif color_type == 4:
            bits = bpp * 2
        elif color_type == 6:
            bits = bpp * 4
        else:
            bits = bpp

        stream.read(7)  # skip rest of IHDR

        offset_x = 0
        offset_y = 0

        while True:
            try:
                chunk_len_data = stream.read(4)
                chunk_type = stream.read(4)
                if len(chunk_len_data) < 4 or len(chunk_type) < 4:
                    break
                chunk_len = BigEndian.ToUInt32(chunk_len_data, 0)

                if chunk_type == b'oFFs':
                    offset_x = BigEndian.ToInt32(stream.read(4), 0)
                    offset_y = BigEndian.ToInt32(stream.read(4), 0)
                    stream.read(1)  # unit
                    break
                elif chunk_type in [b'IDAT', b'IEND']:
                    break
                else:
                    stream.seek(chunk_len + 4, 1)
            except Exception:
                break

        return ImageMetaData(
            width=width,
            height=height,
            offset_x=offset_x,
            offset_y=offset_y,
            bpp=bits,
            ext=".png",
            bit_depth=bpp,
            color_type=color_type,
        )

    def read(self, stream: BytesIO, info: ImageMetaData) -> ImageData:
        try:
            stream.seek(0)
            img = Image.open(stream)
            img = img.convert("RGBA" if img.mode == "RGBA" or img.mode == "LA" else "RGB")
            raw_data = img.tobytes()
            bpp = len(img.getbands()) * 8
            return ImageData.create(info, bpp, raw_data)
        except Exception as e:
            logging.error(f"[imagepng] PIL 기반 PNG 디코딩 실패: {e}", exc_info=True)
            return None

    def write(self, file: BytesIO, image: ImageData):
        try:
            mode = "RGBA" if image.bpp == 32 else "RGB"
            img = Image.frombytes(mode, (image.width, image.height), image.data)

            # ✅ PNG 메타정보 준비 (offset 있음)
            if image.offset_x or image.offset_y:
                # oFFs 청크 삽입 (unit = 0)
                offs = struct.pack(">iiB", image.offset_x, image.offset_y, 0)

                # PNG 시그니처
                file.write(b'\x89PNG\r\n\x1a\n')

                # IHDR
                ihdr = struct.pack(
                    ">IIBBBBB",
                    image.width,
                    image.height,
                    8,
                    6 if mode == "RGBA" else 2,
                    0,
                    0,
                    0
                )
                self.write_chunk(file, b'IHDR', ihdr)
                self.write_chunk(file, b'oFFs', offs)

                # 이후 저장은 temp로 한 번 save하고 IDAT/IEND만 이어붙이기 필요
                temp = BytesIO()
                img.save(temp, format="PNG", optimize=True, compress_level=9)  # ✅ 최고 압축
                raw = temp.getvalue()

                # IDAT 위치 찾아서 뒤부터 붙임
                idat_pos = raw.find(b'IDAT') - 4
                file.write(raw[idat_pos:])
                return

            # 일반 저장 (offset 없음)
            img.save(file, format="PNG", optimize=True, compress_level=9)  # ✅ 최고 압축

            logging.debug("[imagepng] PIL 기반 PNG 저장 완료 (optimize=True, compress_level=9)")

        except Exception as e:
            logging.error(f"[imagepng] PIL 기반 PNG 저장 실패: {e}", exc_info=True)