import os
import sys
import argparse
import logging
from io import BytesIO
from formats.fileview import FileView
from malie.imagemgf import MgfFormat
from gameres.imagepng import PngFormat

def setup_logger():
    # 기존 핸들러 제거
    root = logging.getLogger()
    if root.handlers:
        for handler in root.handlers[:]:
            root.removeHandler(handler)

    logging.basicConfig(
        level=logging.DEBUG,  # 디버그 로그 출력
        format="%(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )

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
    logging.info(f"[PNG→MGF] {png_path} → {os.path.splitext(png_path)[0]}.mgf")

    try:
        # FileView로 PNG 파일 열기
        view = FileView(png_path)
        logging.debug(f"[debug] FileView 열기 성공: size={view.size}")

        # PNG 데이터 읽기
        data = view.read(0, view.size)
        stream = BytesIO(data)

        handler = PngFormat()
        logging.debug("[debug] read_metadata() 호출")
        info = handler.read_metadata(stream)
        if not info:
            raise ValueError("read_metadata 실패")

        logging.debug("[debug] read() 호출")
        stream.seek(0)
        image = handler.read(stream, info)
        if image is None:
            raise ValueError("이미지 디코딩 실패")

        # MGF로 저장
        output_path = os.path.splitext(png_path)[0] + ".mgf"
        logging.debug(f"[debug] MGF 저장 시작 → {output_path}")
        with open(output_path, "wb") as f:
            MgfFormat().write(f, image)

        logging.info(f"[완료] PNG→MGF 변환 성공: {output_path}")
        return True

    except Exception as e:
        logging.error(f"[오류] PNG→MGF 변환 실패: {e}", exc_info=True)
        return False



def main():
    setup_logger()

    parser = argparse.ArgumentParser(description="Convert between MGF and PNG formats.")
    parser.add_argument("input", help="Input file (.mgf or .png)")
    parser.add_argument("--to-png", action="store_true", help="Convert MGF to PNG")
    parser.add_argument("--to-mgf", action="store_true", help="Convert PNG to MGF")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.to_png:
        success = convert_mgf_to_png(args.input)
        sys.exit(0 if success else 1)
    elif args.to_mgf:
        success = convert_png_to_mgf(args.input)
        sys.exit(0 if success else 1)
    else:
        logging.error("❌ 변환 방향을 지정하세요: --to-png 또는 --to-mgf")
        sys.exit(1)

if __name__ == "__main__":
    main()
