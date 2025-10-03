# repack_plain.py - 평문 리팩용

import sys, os, struct, logging, argparse
from logging.handlers import RotatingFileHandler
from malie.malierepack import DatWriterplain
from gameres.utility import EntryMetadataApplier

# ✅ 안전한 로거 설정
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logger.handlers.clear()
formatter = logging.Formatter("[%(levelname)s] %(message)s")

file_handler = RotatingFileHandler('debug_log_repack.txt', maxBytes=100_000_000, backupCount=5, encoding='utf-8')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


def main(args=None):
    if args is None:
        args = sys.argv[1:]

    view = None
    try:
        if len(args) < 2 or len(args) > 3:
            print("사용법: python repack_test.py <input_dir> <output_dat> [entry_meta.json]")
            sys.exit(1)

        input_dir = args[0]
        output_dat = args[1]
        json_path = args[2] if len(args) == 3 else None

        logging.debug(f"[main] 입력 폴더: {input_dir}")
        logging.debug(f"[main] 출력 파일: {output_dat}")
        if json_path:
            logging.debug(f"[main] 메타데이터 JSON: {json_path}")
        else:
            logging.debug("[main] 메타데이터 JSON 없음 (생략됨)")

        writer = DatWriterplain(
            entry_list=[],
            base_dir=input_dir
        )

        logging.debug("[main] add_auto 시작")
        writer.add_auto(input_dir, "", root_dir=input_dir)
        logging.debug(f"[main] 등록된 entry 수: {len(writer.entries)}")

        if json_path:
            applier = EntryMetadataApplier(json_path)
            applier.apply_to_entries(writer.entries)
            applier.apply_order(writer.entries)

        for e in writer.entries[:20]:
            logging.debug(f"[DEBUG-apply entries] {e.get('arc_path')} | entry_index={e.get('entry_index')}")

        writer.finalize_folders()

        writer.write.write_header()
        writer.write.write_index_table()
        writer.write.calculate_base_offset()
        writer.write.write_data()
        writer.write.prepare_offsets()
        writer.write.write_offset_table()

        logging.debug("[main] 파일 저장 시작")
        writer.save.to_file(output_dat)
        logging.info(f"[완료] 리팩 성공 → {output_dat}")

    except KeyboardInterrupt:
        print("\n[취소] 사용자에 의해 중단되었습니다.")
        logging.warning("[main] 사용자 중단 (Ctrl+C)")
        os._exit(1)

    except Exception as e:
        logging.exception(f"[오류] 예외 발생: {e}")

    finally:
        try:
            if view:
                view.close()
                print("[repack_test] view 닫힘")
        except Exception:
            pass
        print("[main] 실행 종료")
        logging.shutdown()


if __name__ == "__main__":
    print("[main] 실행 시작")
    main()
    print("[main] 실행 종료")