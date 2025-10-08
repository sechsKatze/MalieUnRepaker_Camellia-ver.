# unpack.py - 말리 엔진 전체 언팩 코드
# 리팩에 필요한 메타데이터.json을 자동으로 출력함.

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import io
from io import BytesIO
import logging
from pathlib import Path
from tqdm import tqdm
import time

from formats.arcfile import ArcFile
from formats.fileview import FileView, FileFrame, FileStream
from formats.arccommon import AutoEntry, PrefixStream, NotTransform
from malie.malieunpack import DatOpener, LibOpener, read_encrypted
from malie.imagemgf import MgfFormat #말리 엔진 이미지 처리 코드
from malie.imagedzi import DziFormat #말리 엔진 이미지 처리 코드
from gameres.gameres import FormatCatalog
from gameres.audioogg import OggAudio, OggFormat

from gameres.imagepng import PngFormat 
from gameres.utility import TextSaver, BinarySaver, EntryMetadataManager


# 로거 설정
# ✅ 기존 핸들러 제거 안함 (GUI QtHandler 유지)
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

file_format = logging.Formatter("[%(levelname)s] %(message)s")

# 폴더 저장 경로
def ensure_dir(path):
    dir_path = os.path.dirname(path)
    if dir_path and not os.path.exists(dir_path):
        os.makedirs(dir_path, exist_ok=True)   

def run_serial_unpack(archive, view, output_dir):
    for i, entry in enumerate(tqdm(archive.entries, desc="복호화 진행중", unit="파일")):
        try:
            save_path = os.path.join(output_dir, entry.name)
            os.makedirs(os.path.dirname(save_path), exist_ok=True)

            print(f"[진행 중] {i+1}/{len(archive.entries)} → {entry.name}")  # ✅ 이제 i가 정의됨
            process_file(view, entry, save_path)
        except Exception as e:
            logging.error(f"[예외 - {entry.name}] {e}")

# 확장자 열기
def process_file(view, entry, save_path):
    try:
        if entry.is_dir:
            return

        ext = os.path.splitext(entry.name)[1].lower()

        # 포맷별 처리
        if ext == ".ogg":
            process_ogg_file(entry, save_path)

        elif ext in (".png", ".pn", ".mgf"):
            process_png_file(entry, save_path)

        elif ext == ".dzi":
            process_dzi_file(entry, save_path)

        elif ext == ".svg":
            process_svg_file(entry, save_path)

        elif ext in (".csv", ".txt", ".bat"):
            process_csv_file(entry, save_path)

        elif ext == ".mpg":
            process_mpg_file(entry, save_path)

        elif ext == ".swf":
            process_swf_file(entry, save_path)

        elif ext in [".psd", ""]:
            process_other_file(entry, save_path)
        else:
            return  # ❗확실히 무시

    except Exception as e:
        print(f"[unpack_test] {entry.name} 처리 중 예외 발생: {e}")

# FormatCatalog등록
FormatCatalog.add_format(OggFormat())
FormatCatalog.add_format(PngFormat())
FormatCatalog.add_format(MgfFormat())
FormatCatalog.add_format(DziFormat())

#ogg 파일 열람 처리
def process_ogg_file(entry, save_path):
    try:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)

        stream = decrypt_ogg_stream(entry)
        stream.seek(0)

        handler = OggFormat()
        OggAudio = handler.try_open(stream)  # 디코딩 시도 → 실패해도 무시

        # 무조건 저장
        stream.seek(0)
        with open(save_path, "wb") as f:
            f.write(stream.read())

        logging.debug(f"{entry.name} → 복호화 + 저장 완료 (.ogg)")

    except Exception as e:
        logging.error(f"{entry.name} 처리 중 예외 발생 (.ogg): {e}")

        
#Png(+mgf) 파일 열람 처리
def process_png_file(entry, save_path_base):
    try:
        os.makedirs(os.path.dirname(save_path_base), exist_ok=True)

        ext = Path(entry.name).suffix.lower()
        is_mgf = ext == ".mgf"
        is_pn = ext == ".pn"

        # 🔹 MGF일 경우: .mgf 원본만 저장
        if is_mgf:
            stream = decrypt_mgf_stream(entry)
            if stream:
                mgf_path = str(Path(save_path_base).with_suffix(".mgf"))
                with open(mgf_path, "wb") as f:
                    f.write(stream.read())
                logging.debug(f"{entry.name} → MGF 원본 저장 완료: {mgf_path}")
            else:
                logging.warning(f"{entry.name} → decrypt_mgf_stream 실패")
            return  # ✅ PNG 변환 생략하고 여기서 종료

        # 🔸 PNG 또는 .pn 처리
        image = decrypt_png_stream(entry)
        if not image:
            logging.warning(f"{entry.name} → decrypt_png_stream 실패")
            return

        png_path = str(Path(save_path_base).with_suffix(".png"))
        with open(png_path, "wb") as f:
            stream = BytesIO()
            PngFormat().write(stream, image)
            f.write(stream.getvalue())

        if is_pn:
            logging.debug(f"{entry.name} → PNG 변환 저장 완료 (from .pn): {png_path}")
        else:
            logging.debug(f"{entry.name} → PNG 저장 완료: {png_path}")

    except Exception as e:
        logging.error(f"{entry.name} → 예외 발생: {e}")


# Dzi 파일 열람 처리
def process_dzi_file(entry, save_path):
    try:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)

        stream = decrypt_dzi_stream(entry)  # ✅ key_name 전달 제거
        if not stream:
            logging.warning(f"{entry.name} → decrypt_dzi_stream 실패")
            return

        with open(save_path, "w", encoding="utf-8") as f:
            stream.seek(0)
            f.write(stream.read().decode("utf-8"))

        logging.debug(f"{entry.name} → 복호화 + 저장 완료 (.dzi)")

    except Exception as e:
        logging.error(f"{entry.name} 처리 중 예외 발생 (.dzi): {e}")

#svg 파일 열람 처리
def process_svg_file(entry, save_path):
    try:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)

        stream = decrypt_svg_stream(entry) 
        if not stream:
            logging.warning(f"{entry.name} → decrypt_svg_stream 실패")
            return

        raw_data = stream.read()
        TextSaver.save_file(entry.name, raw_data, save_path)

    except Exception as e:
        logging.error(f"[오류 - svg] {entry.name} 처리 중 예외 발생: {e}")

#csv 파일 열람 처리
def process_csv_file(entry, save_path):
    try:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)

        stream = decrypt_csv_stream(entry)
        if not stream:
            logging.warning(f"{entry.name} → decrypt_csv_stream 실패")
            return

        raw_data = stream.read()
        TextSaver.save_file(entry.name, raw_data, save_path)

    except Exception as e:
        logging.error(f"[오류 - csv] {entry.name} 처리 중 예외 발생: {e}")

#mpg 파일 열람 처리
def process_mpg_file(entry, save_path):
    try:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)

        stream = decrypt_mpg_stream(entry)
        if not stream:
            logging.warning(f"{entry.name} → decrypt_mpg_stream 실패")
            return

        raw_data = stream.read()
        BinarySaver.save(entry.name, raw_data, save_path)

    except Exception as e:
        logging.error(f"[오류 - mpg] {entry.name} 처리 중 예외 발생: {e}")
        
#swf 파일 열람 처리 - 1차 암호화만 Camellia, 2차 언팩은 
def process_swf_file(entry, save_path):
    try:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)

        stream = decrypt_swf_stream(entry)  # ← 이미 복호화된 BytesIO 반환
        if not stream:
            logging.warning(f"{entry.name} → SWF 복호화 실패")
            return

        with open(save_path, "wb") as f:
            stream.seek(0)
            f.write(stream.read())

        logging.debug(f"{entry.name} → 복호화 + 저장 완료 (.swf)")

    except Exception as e:
        logging.error(f"{entry.name} 처리 중 예외 발생 (.swf): {e}")

#기타 파일들 처리(.psd 같은거)
def process_other_file(entry, save_path):
    try:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        stream = decrypt_other_stream(entry)
        if not stream:
            logging.warning(f"{entry.name} → decrypt_other_stream 실패")
            return

        raw_data = stream.read()
        BinarySaver.save(entry.name, raw_data, save_path)

    except Exception as e:
        logging.error(f"[오류 - mpg] {entry.name} 처리 중 예외 발생: {e}")

#OGG 복호화 로직
def decrypt_ogg_stream(entry):
    view = entry.archive.file_view
    decryptor = entry.archive.decryptor
    offset = entry.offset
    size = entry.size

    buf = bytearray(size)
    read_encrypted(view, decryptor, offset, buf, 0, size)
    return BytesIO(buf)
    
#PNG/MGF 분기 로직
def decrypt_png_stream(entry):
    try:
        view = entry.archive.file_view
        decryptor = entry.archive.decryptor
        offset = entry.offset
        size = entry.size

        buf = bytearray(size)
        read_encrypted(view, decryptor, offset, buf, 0, size)
        prefix = buf[:8]
        logging.debug(f"[decrypt_png_stream] {entry.name}에서 읽은 크기 = {len(buf)}")

        # PNG 시그니처 감지되면 처리
        if prefix.startswith(b'\x89PNG\r\n\x1a\n'):
            return decrypt_png_normal(entry, buf)

        # MGF 시그니처는 더 이상 여기서 처리하지 않음
        if prefix.startswith(b'MalieGF'):
            logging.debug(f"[decrypt_png_stream] {entry.name} → MGF 시그니처 감지, PNG 처리 생략")
            return None

        logging.warning(f"[decrypt_png_stream] {entry.name} → 알 수 없는 시그니처: {prefix}")
        return None

    except Exception as e:
        logging.error(f"[decrypt_png_stream] 예외 발생: {e}", exc_info=True)
        return None
    
#시그니처 감지 후 PNG일 경우 PNG로 처리
def decrypt_png_normal(entry, data):
    try:
        stream = BytesIO(data)

        # ✅ 확장자 없을 때 대비
        if entry.name and not hasattr(stream, "name"):
            stream.name = entry.name

        sig = stream.read(8)
        stream.seek(0)
        if sig != b'\x89PNG\r\n\x1a\n':
            logging.warning(f"[decrypt_png_normal] PNG 시그니처 불일치: {sig}")
            return None

        handler = PngFormat()
        metadata = handler.read_metadata(stream)
        if not metadata:
            logging.warning(f"[decrypt_png_normal] read_metadata 실패: {entry.name}")
            return None

        logging.debug(f"[decrypt_png_normal] read 호출 전: metadata = {metadata}, stream size = {len(data)}")
        result = handler.read(stream, metadata)
        logging.debug(f"[decrypt_png_normal] read 호출 완료")
        return result

    except Exception as e:
        logging.error(f"[decrypt_png_normal] 예외 발생: {e}", exc_info=True)
        return None
    
#MGF 원본으로 저장하고 싶으면 이쪽으로 
def decrypt_mgf_stream(entry) -> BytesIO | None:
    try:
        view = entry.archive.file_view
        decryptor = entry.archive.decryptor
        offset = entry.offset
        size = entry.size

        buf = bytearray(size)
        read_encrypted(view, decryptor, offset, buf, 0, size)

        if not buf.startswith(b'MalieGF'):
            logging.warning(f"[decrypt_mgf_stream] {entry.name} → 시그니처 불일치")
            return None

        return BytesIO(buf)

    except Exception as e:
        logging.error(f"[decrypt_mgf_stream] {entry.name} 예외 발생: {e}")
        return None

#dzi 복호화 로직
def decrypt_dzi_stream(entry):
    try:
        view = entry.archive.file_view
        decryptor = entry.archive.decryptor
        offset = entry.offset
        size = entry.size

        buf = bytearray(size)
        read_encrypted(view, decryptor, offset, buf, 0, size)
        stream = BytesIO(buf)

        # ✅ DziFormat 사용해 메타데이터만 검사 (png 추출 아님)
        fmt = DziFormat()
        metadata = fmt.read_metadata(stream)
        if not metadata:
            logging.warning("[decrypt_dzi_stream] DZI 메타데이터 읽기 실패")
            return None

        stream.seek(0)
        return stream

    except Exception as e:
        logging.error(f"[decrypt_dzi_stream] DZI 처리 중 예외 발생: {e}")
        return None

#svg 복호화 로직
def decrypt_svg_stream(entry) -> io.BytesIO | None:
    try:
        view = entry.archive.file_view
        decryptor = entry.archive.decryptor
        offset = entry.offset
        size = entry.size

        buf = bytearray(size)
        read_encrypted(view, decryptor, offset, buf, 0, size)

        stream = io.BytesIO(buf)
        stream.seek(0)

        logging.debug(f"[성공 - decrypt_svg_stream] SVG 복호화 성공")
        return stream
    except Exception as e:
        logging.error(f"[오류 - decrypt_svg_stream] SVG 처리 중 예외 발생: {e}")
        return None
    
#csv 복호화 로직
def decrypt_csv_stream(entry) -> io.BytesIO | None:
    try:
        if entry.size < 16:
            logging.debug(f"[arccommon 적용] 작은 CSV 파일 (size={entry.size}) → NotTransform() 사용")

            # 🔒 반드시 새로 BytesIO 생성
            try:
                raw_data = entry.archive.open_entry(entry)
                if not raw_data or all(b == 0 for b in raw_data):
                    logging.warning(f"[decrypt_csv_stream] {entry.name} → 내용이 모두 0x00")
                    return None
                
                transformer = NotTransform()
                raw = transformer.transform_block(raw_data)
                return io.BytesIO(raw)

            except Exception as e:
                logging.warning(f"[decrypt_csv_stream] {entry.name} → raw_stream 생성 실패: {e}")
                return None

        # 📌 일반적인 암호화된 CSV 처리
        view = entry.archive.file_view
        decryptor = entry.archive.decryptor
        offset = entry.offset
        size = entry.size

        buf = bytearray(size)
        read_encrypted(view, decryptor, offset, buf, 0, size)

        return io.BytesIO(buf)

    except Exception as e:
        logging.warning(f"[decrypt_csv_stream] {entry.name} → 예외 발생: {e}")
        return None
    
#mpg 복호화 로직 
def decrypt_mpg_stream(entry) -> io.BytesIO | None:
    try:
        view = entry.archive.file_view
        decryptor = entry.archive.decryptor
        offset = entry.offset
        size = entry.size

        logging.debug(f"[decrypt_mpg_stream] 시작: {entry.name} offset=0x{offset:X}, size={size}")

        buf = bytearray(size)
        logging.debug(f"[decrypt_mpg_stream] read_encrypted 호출 전")

        read_encrypted(view, decryptor, offset, buf, 0, size)

        logging.debug(f"[decrypt_mpg_stream] read_encrypted 호출 후")

        stream = io.BytesIO(buf)
        stream.seek(0)

        logging.debug(f"[성공 - decrypt_mpg_stream] MPG 복호화 성공")
        return stream
    except Exception as e:
        logging.error(f"[오류 - decrypt_mpg_stream] MPG 처리 중 예외 발생: {e}")
        return None
    
#swf 복호화 로직
def decrypt_swf_stream(entry) -> io.BytesIO | None:
    try:
        view = entry.archive.file_view
        decryptor = entry.archive.decryptor
        offset = entry.offset
        size = entry.size

        buf = bytearray(size)
        read_encrypted(view, decryptor, offset, buf, 0, size)
        stream = io.BytesIO(buf)
        stream.seek(0)

        # 시그니처 검사
        sig = stream.read(3)
        if sig not in (b"CWS", b"FWS", b"ZWS"):
            logging.warning(f"[decrypt_swf_stream] SWF 시그니처 불일치: {sig.hex()}")
            return None

        stream.seek(0)
        return stream

    except Exception as e:
        logging.error(f"[decrypt_swf_stream] 예외 발생: {e}")
        return None
    
#기타 파일들 복호화 로직(.psd, 확장자 없는 일부 파일도 대응.)
def decrypt_other_stream(entry) -> io.BytesIO | None:
    try:
        view = entry.archive.file_view
        decryptor = entry.archive.decryptor
        offset = entry.offset
        size = entry.size

        buf = bytearray(size)
        read_encrypted(view, decryptor, offset, buf, 0, size)

        sig = buf[:512]  # svg는 앞부분 넉넉하게 봐도 좋음
        preview = sig.decode("utf-8", errors="ignore")

        # 확장자 없음 + <svg 감지> 전용 처리
        if b"<svg" in sig or preview.lstrip().startswith("<svg"):
            logging.debug(f"[detect] SVG 감지 → svg 처리")
            return decrypt_svg_stream(entry)

        # 기타는 BytesIO로 반환
        return io.BytesIO(buf)

    except Exception as e:
        logging.error(f"[decrypt_other_stream] {entry.name} 예외 발생: {e}")
        return None
    
# GUI용 실행 함수
def run_unpack(input_path: str, output_dir: str):
    # ✅ GUI 메시지 박스 연결 테스트 로그
    logging.info(f"[unpack.py] 언팩 시작: {input_path} → {output_dir}")

    # ✅ 여기서 dat 이름으로 하위 폴더 생성
    dat_name = os.path.splitext(os.path.basename(input_path))[0]
    full_output_dir = os.path.join(output_dir, dat_name)
    os.makedirs(full_output_dir, exist_ok=True)

    view = FileView(input_path)

    # LibOpener → DatOpener 순서로 시도
    archive = LibOpener().try_open(view)
    if archive:
        logging.debug("[unpack] LibOpener 성공")
    else:
        logging.debug("[unpack] LibOpener 실패 → DatOpener 시도")
        view.close()
        view = FileView(input_path)
        archive = DatOpener().try_open(view)
        if archive:
            print(f"[DatOpener] entries 개수: {len(archive.entries)}")
            logging.debug("[unpack] DatOpener 성공")
        else:
            logging.error("[unpack] DatOpener 실패 → 아카이브 열기 실패")
            return

    # JSON 메타데이터 자동 처리
    json_path = os.path.splitext(input_path)[0] + "_entries.json"
    for entry in archive.entries:
        entry.source_archive = os.path.basename(input_path)

    meta_manager = EntryMetadataManager(json_path)
    meta_manager.assign_order(archive.entries)
    meta_manager.update_padding(archive.entries, view.size, base_offset=archive.base_offset)

    if os.path.isfile(json_path):
        logging.info(f"[unpack] JSON 메타데이터 불러오기: {json_path}")
        meta_manager.apply_to_entries(archive.entries)
    else:
        logging.info(f"[unpack] JSON 메타데이터 파일이 없어 새로 생성합니다: {json_path}")

    meta_manager.save_metadata(archive.entries)

    # 언팩 실행 (하위 폴더를 만든 full_output_dir에)
    start = time.time()
    run_serial_unpack(archive, view, full_output_dir)
    elapsed = time.time() - start
    print(f"[완료] 전체 언팩 시간: {elapsed:.2f}초")

    try:
        view.close()
        logging.debug("[unpack] view 닫힘")
    except Exception:
        pass


#main은 삭제하면 안됨.
def main(args=None):
    if args is None:
        args = sys.argv[1:]

if __name__ == "__main__":
    print("[main] 실행 시작")
    main()
    print("[main] 실행 종료")  # 이게 안 뜨면 종료 안 되고 재진입
