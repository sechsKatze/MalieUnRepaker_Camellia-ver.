import os
import logging
from io import BytesIO
from formats.fileview import FileView
from malie.imagemgf import MgfFormat
from gameres.imagepng import PngFormat

def convert_mgf_to_png(mgf_path):
    base, _ = os.path.splitext(mgf_path)
    png_output_path = base + ".png"

    logging.info(f"[MGF→PNG] {mgf_path} → {png_output_path}")

    try:
        view = FileView(mgf_path)
        logging.debug(f"[debug] FileView 열기 성공: size={view.size}")

        data = view.read(0, view.size)
        logging.debug(f"[debug] 파일 전체 데이터 read 성공 (bytes={len(data)})")

        stream = BytesIO(data)
        handler = MgfFormat()

        logging.debug("[debug] read_metadata() 호출")
        info = handler.read_metadata(stream)
        if not info:
            raise ValueError("read_metadata 실패")
        logging.debug(f"[debug] 메타데이터 추출 성공: {info}")

        stream.seek(0)
        logging.debug("[debug] read() 호출")
        image = handler.read(stream, info)
        logging.debug(f"[debug] 이미지 객체 복원 성공: {type(image)}")

        logging.debug("[debug] PNG 저장 시작")
        with open(png_output_path, "wb") as f:
            PngFormat().write(f, image)

        logging.info(f"[완료] 저장됨: {png_output_path}")
        return True

    except Exception as e:
        logging.error(f"[오류] MGF→PNG 변환 실패: {e}", exc_info=True)
        return False

def convert_png_to_mgf(png_path: str):
    output_path = os.path.splitext(png_path)[0] + ".mgf"
    logging.info(f"[PNG→MGF] {png_path} → {output_path}")

    try:
        view = FileView(png_path)
        logging.debug(f"[debug] FileView 열기 성공: size={view.size}")

        data = view.read(0, view.size)
        stream = BytesIO(data)

        handler = PngFormat()
        logging.debug("[debug] read_metadata() 호출")
        info = handler.read_metadata(stream)
        if not info:
            raise ValueError("read_metadata 실패")

        stream.seek(0)
        logging.debug("[debug] read() 호출")
        image = handler.read(stream, info)
        if image is None:
            raise ValueError("이미지 디코딩 실패")

        logging.debug(f"[debug] MGF 저장 시작 → {output_path}")
        with open(output_path, "wb") as f:
            MgfFormat().write(f, image)

        logging.info(f"[완료] PNG→MGF 변환 성공: {output_path}")
        return True

    except Exception as e:
        logging.error(f"[오류] PNG→MGF 변환 실패: {e}", exc_info=True)
        return False

# ✅ GUI 전용 진입점 (절대 logger 설정 건들지 않음!)
def run_mgfpng(input_path: str, output_path: str) -> bool:
    ext = os.path.splitext(input_path)[1].lower()

    if ext == ".mgf":
        return convert_mgf_to_png(input_path)
    elif ext == ".png":
        return convert_png_to_mgf(input_path)
    else:
        logging.error("❌ 변환 실패: 지원하지 않는 확장자입니다.")
        return False


def main():
    ()

if __name__ == "__main__":
    main()
