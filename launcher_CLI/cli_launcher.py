import sys
import os
import logging
from execution import unpack_plain, unpack, repack_plain, mgfpng_change

# Nuitka 대응: 실행 경로 기반으로 base_dir 설정
if getattr(sys, 'frozen', False):
    base_dir = os.path.dirname(sys.executable)
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))

if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

# 로그 설정
log_path = os.path.join(base_dir, "cli_runlog.txt")
logging.basicConfig(
    filename=log_path,
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# CLI 헤더
def print_banner():
    banner = r"""
    ___  ___        _  _         _   _        ______       ______               _                
    |  \/  |       | |(_)       | | | |       | ___ \      | ___ \             | |               
    | .  . |  __ _ | | _   ___  | | | | _ __  | |_/ /  ___ | |_/ /  __ _   ___ | | __  ___  _ __ 
    | |\/| | / _` || || | / _ \ | | | || '_ \ |    /  / _ \|  __/  / _` | / __|| |/ / / _ \| '__|
    | |  | || (_| || || ||  __/ | |_| || | | || |\ \ |  __/| |    | (_| || (__ |   < |  __/| |   
    \_|  |_/ \__,_||_||_| \___|  \___/ |_| |_|\_| \_| \___|\_|     \__,_| \___||_|\_\ \___||_|   
                                                                                                                                                                
  Malie Engine UnPacker / RePacker Tool CLI ver.
  ※ 현재 .lib 확장자 리팩은 테스트를 못함, .dat의 암호화 리팩은 게임 인식이 안되는 문제로 지원을 안하고 있습니다. ※ 
  -------------------------------
    """
    print(banner)

def main():
    while True:
        print_banner()
        print("실행할 작업을 선택하세요 :")
        print("  [1] 1차 복호화 (.dat 전용)")
        print("  [2] 완전 언팩 (.lib/.dat)")
        print("  [3] 평문 리팩 (.dat만 지원)")
        print("  [4] MGF ↔ PNG 변환")
        print("  [Q] 종료")
        print("")

        choice = input("▶ 번호 선택: ").strip().lower()
        logging.info(f"[선택] 사용자 입력: {choice}")

        if choice == "q":
            print("프로그램을 종료합니다.")
            break

        elif choice == "1":
            dat_path = input("언팩할 .dat 경로 입력 (1차 복호화) [q = 취소]: ").strip('" ')
            if dat_path.lower() in ["q", "취소"]:
                continue

            out_dir = input("출력 폴더 경로 입력 (비우면 기본 './output') [q = 취소]: ").strip('" ')
            if out_dir.lower() in ["q", "취소"]:
                continue
            if not out_dir:
                out_dir = os.path.join(base_dir, "output")

            logging.info(f"[1차 복호화] dat_path: {dat_path}, out_dir: {out_dir}")
            unpack_plain.main([dat_path, out_dir])

        elif choice == "2":
            dat_path = input("언팩할 .dat 경로 입력 (언패킹) [q = 취소]: ").strip('" ')
            if dat_path.lower() in ["q", "취소"]:
                continue

            out_dir = input("출력 폴더 경로 입력 (비우면 기본 './output') [q = 취소]: ").strip('" ')
            if out_dir.lower() in ["q", "취소"]:
                continue
            if not out_dir:
                out_dir = os.path.join(base_dir, "output")

            logging.info(f"[완전 언팩] dat_path: {dat_path}, out_dir: {out_dir}")
            unpack.main([dat_path, out_dir])

        elif choice == "3":
            input_dir = input("원본 파일이 있는 폴더 경로 입력 [q = 취소]: ").strip('" ')
            if input_dir.lower() in ["q", "취소"]:
                continue

            out_dat = input("출력할 .dat 파일 이름 입력 [q = 취소]: ").strip('" ')
            if out_dat.lower() in ["q", "취소"]:
                continue

            json_path = input("메타데이터 .json 경로 입력 [q = 취소]: ").strip('" ')
            if json_path.lower() in ["q", "취소"]:
                continue

            logging.info(f"[평문 리팩] json_path: input_dir: {input_dir}, out_dat: {out_dat}, {json_path}")
            repack_plain.main([input_dir, out_dat, json_path])

        elif choice == "4":
            file_path = input("변환할 .mgf 또는 .png 파일 경로 입력 [q = 취소]: ").strip('" ')
            if file_path.lower() in ["q", "취소"]:
                continue

            if not os.path.isfile(file_path):
                print(f"[오류] 파일이 존재하지 않습니다: {file_path}")
                continue

            ext = os.path.splitext(file_path)[1].lower()

            if ext == ".mgf":
                logging.info(f"[MGF→PNG] 파일: {file_path}")
                success = mgfpng_change.convert_mgf_to_png(file_path)
            elif ext == ".png":
                logging.info(f"[PNG→MGF] 파일: {file_path}")
                success = mgfpng_change.convert_png_to_mgf(file_path)
            else:
                logging.warning(f"[오류] 확장자 지원 안 함: {ext}")
                print("❌ 지원되지 않는 확장자입니다. .mgf 또는 .png만 허용됩니다.")
                continue

            if not success:
                print("⚠️ 변환 중 오류가 발생했습니다. 로그를 확인하세요.")

        else:
            logging.warning(f"[경고] 잘못된 입력: {choice}")
            print("올바른 번호를 입력하세요.")
            continue

        # ✅ 완료 후 선택
        while True:
            go_back = input("작업이 완료되었습니다. 메인 메뉴로 돌아가시겠습니까? (Y/N): ").strip().lower()
            if go_back == "y":
                break  # 루프 계속 → 메인 화면으로 이동
            elif go_back == "n":
                print("프로그램을 종료합니다.")
                break 
            else:
                print("Y 또는 N으로 입력해주세요.")

if __name__ == "__main__":
    try:
        logging.info("==== 실행 시작 ====")
        main()
        logging.info("==== 실행 종료 ====")
    except Exception as e:
        logging.exception("예외 발생:")
        print(f"예기치 않은 오류가 발생했습니다. 자세한 내용은 'cli_runlog.txt'를 확인하세요.")

