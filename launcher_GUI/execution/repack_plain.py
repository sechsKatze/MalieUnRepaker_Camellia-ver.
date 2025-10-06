# repack_plain.py - 평문 리팩용

import sys, os, struct, logging, argparse
from logging.handlers import RotatingFileHandler
from malie.malierepack import DatWriterplain
from gameres.utility import EntryMetadataApplier

# 로거 설정
# ✅ 기존 핸들러 제거 안함 (GUI QtHandler 유지)
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

file_format = logging.Formatter("[%(levelname)s] %(message)s")

#GUI 용
# GUI 용 평문 리팩 실행 함수
def run_repack_plain(input_dir: str, output_dat: str, json_path: str):
    try:
        logging.info("[GUI] [0] 입력 확인")

        # 입력 경로 검증
        if not os.path.isdir(input_dir):
            raise FileNotFoundError(f"입력 폴더가 존재하지 않습니다: {input_dir}")
        if not os.path.isfile(json_path):
            raise FileNotFoundError(f"메타데이터 JSON 파일이 존재하지 않습니다: {json_path}")

        # ✅ .dat 확장자 자동 추가
        if not output_dat.lower().endswith(".dat"):
            output_dat += ".dat"

        # ✅ 상대 경로 보정 (디렉토리 없이 파일명만 입력 시 → input_dir 상위 디렉토리에 저장)
        if not os.path.isabs(output_dat) and not os.path.dirname(output_dat):
            parent_dir = os.path.dirname(os.path.abspath(input_dir))
            output_dat = os.path.join(parent_dir, output_dat)

        # ✅ 디렉토리 오입력 방지
        if os.path.isdir(output_dat):
            raise ValueError(f"출력 경로가 파일이 아닌 디렉토리입니다. .dat 파일명을 입력하세요: {output_dat}")

        logging.info(f"[GUI] [1] 평문 리팩 시작: 입력={input_dir}, 출력={output_dat}, JSON={json_path}")

        # 리팩커 생성
        writer = DatWriterplain(entry_list=[], base_dir=input_dir)
        logging.info("[GUI] [2] writer 생성 완료")

        writer.add_auto(input_dir, "", root_dir=input_dir)
        logging.info("[GUI] [3] add_auto 완료")

        # 메타데이터 적용
        applier = EntryMetadataApplier(json_path)
        applier.apply_to_entries(writer.entries)
        applier.apply_order(writer.entries)
        logging.info("[GUI] [4] 메타데이터 적용 완료")

        writer.finalize_folders()
        logging.info("[GUI] [5] finalize_folders 완료")

        writer.write.write_header()
        logging.info("[GUI] [6] write_header 완료")

        writer.write.write_index_table()
        logging.info("[GUI] [7] write_index_table 완료")

        writer.write.calculate_base_offset()
        logging.info("[GUI] [8] calculate_base_offset 완료")

        writer.write.write_data()
        logging.info("[GUI] [9] write_data 완료")

        writer.write.prepare_offsets()
        logging.info("[GUI] [10] prepare_offsets 완료")

        writer.write.write_offset_table()
        logging.info("[GUI] [11] write_offset_table 완료")

        logging.info("[GUI] [12] 저장 직전")
        writer.save.to_file(output_dat)

        logging.info(f"[GUI] ✅ 평문 리팩 성공 → {output_dat}")
        return True

    except Exception as e:
        logging.exception(f"[GUI] ❌ 리팩 중 오류 발생: {e}")
        return False



#main은 삭제하면 안됨.
def main(args=None):
    if args is None:
        args = sys.argv[1:]

if __name__ == "__main__":
    print("[main] 실행 시작")
    main()
    print("[main] 실행 종료")  # 이게 안 뜨면 종료 안 되고 재진입