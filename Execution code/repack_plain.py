#repack_plain.py - 암호화 없는 평문 리팩 실행 코드
# 언팩 시 나온 메타데이터.json 참고 필수

import sys, os, logging

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


# ✅ 메인 실행부
def main():
    print(f"[DEBUG][{__file__}] sys.argv: {sys.argv}")
    print(f"[DEBUG][{__file__}] cwd: {os.getcwd()}")

    view = None
    try:
        if len(sys.argv) < 3 or len(sys.argv) > 4:
            print("사용법: python repack_test.py <input_dir(리팩할 디렉토리)> <output_dat(저장할 .dat)> [entry_meta.json(메타데이터가 기록된 json)]")
            sys.exit(1)

        input_dir = sys.argv[1]
        output_dat = sys.argv[2]
        json_path = sys.argv[3] if len(sys.argv) == 4 else None

        logging.debug(f"[main] 입력 폴더: {input_dir}")
        logging.debug(f"[main] 출력 파일: {output_dat}")
        if json_path:
            logging.debug(f"[main] 메타데이터 JSON: {json_path}")
        else:
            logging.debug("[main] 메타데이터 JSON 없음 (생략됨)")

        # DatWriterTest 인스턴스
        writer = DatWriterplain(
            entry_list=[],
            base_dir=input_dir
        )

        # 1) input_dir 전체 등록
        logging.debug("[main] add_auto 시작")
        writer.add_auto(input_dir, "", root_dir=input_dir)
        logging.debug(f"[main] 등록된 entry 수: {len(writer.entries)}")
        
        # 2) 메타데이터 적용
        if json_path:
            applier = EntryMetadataApplier(json_path)
            applier.apply_to_entries(writer.entries)
            applier.apply_order(writer.entries)


        for e in writer.entries[:20]:  # 앞 50개만 디버그 출력
            logging.debug(f"[DEBUG-apply entries] {e.get('arc_path')} | entry_index={e.get('entry_index')}")

        # 3) 폴더 정보 보강 (루트 포함)
        writer.finalize_folders()
        
        # 4) .dat 작성 
        # (순서 : 헤더 → 파일 인덱스 테이블 → 베이스 오프셋 계산 → 파일 데이터 리전 작성 → 오프셋 계산 → 오프셋 테이블 작성)
        writer.write.write_header()
        writer.write.write_index_table()
        writer.write.calculate_base_offset()
        writer.write.write_data()
        writer.write.prepare_offsets() 
        writer.write.write_offset_table()

        # 4) 저장
        logging.debug("[main] 파일 저장 시작")
        writer.save.to_file(output_dat)
        logging.info(f"[완료] 리팩 성공 → {output_dat}")

    except KeyboardInterrupt:
        print("\n[취소] 사용자에 의해 중단되었습니다.")
        logging.warning("[main] 사용자 중단 (Ctrl+C)")
        os._exit(1)

    except Exception as e:
        logging.exception(f"[오류] 예외 발생: {e}")
        # 계속 진행하지 않고 종료하도록 그대로 둠

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
    print("[main] 실행 종료")  # 이게 안 뜨면 종료 안 되고 재진입
