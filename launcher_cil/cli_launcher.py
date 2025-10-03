import sys
import os
import logging
from execution import unpack_plain, unpack, repack_plain

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
   _____         .__  .__          ____ ___     __________                __                 
  /     \ _____  |  | |__| ____   |    |   \____\______   \_____    ____ |  | __ ___________ 
 /  \ /  \\__  \ |  | |  |/ __ \  |    |   /    \|     ___/\__  \ _/ ___\|  |/ // __ \_  __ \
/    Y    \/ __ \|  |_|  \  ___/  |    |  /   |  \    |     / __ \\  \___|    <\  ___/|  | \/
\____|__  (____  /____/__|\___  > |______/|___|  /____|    (____  /\___  >__|_ \\___  >__|   
        \/     \/             \/               \/               \/     \/     \/    \/       
  Malie UnPacker / RePacker Tool CIL v1.0.0
  -------------------------------
    """
    print(banner)

def main():
    print_banner()
    print("실행할 작업을 선택하세요:")
    print("  [1] 평문 복호화")
    print("  [2] 완전 언팩")
    print("  [3] 평문 리팩")
    print("")

    choice = input("▶ 번호 선택: ").strip()
    logging.info(f"[선택] 사용자 입력: {choice}")

    if choice == "1":
        dat_path = input("언팩할 .dat 경로 입력 (1차 복호화) : ").strip('" ')
        out_dir = input("출력 폴더 경로 입력 (비우면 기본 './output'): ").strip('" ')
        if not out_dir:
            out_dir = os.path.join(base_dir, "output")

        logging.info(f"[1차 복호화] dat_path: {dat_path}, out_dir: {out_dir}")
        unpack_plain.main([dat_path, out_dir])

    elif choice == "2":
        dat_path = input("언팩할 .dat 경로 입력 (언패킹) : ").strip('" ')
        out_dir = input("출력 폴더 경로 입력 (비우면 기본 './output'): ").strip('" ')
        if not out_dir:
            out_dir = os.path.join(base_dir, "output")

        logging.info(f"[완전 언팩] dat_path: {dat_path}, out_dir: {out_dir}")
        unpack.main([dat_path, out_dir])

    elif choice == "3":
        json_path = input("메타데이터 .json 경로 입력 : ").strip('" ')
        input_dir = input("원본 파일이 있는 폴더 경로 입력 : ").strip('" ')
        out_dat = input("출력할 .dat 파일 이름 입력 : ").strip('" ')

        logging.info(f"[평문 리팩] json_path: {json_path}, input_dir: {input_dir}, out_dat: {out_dat}")
        repack_plain.main([json_path, input_dir, out_dat])

    else:
        logging.warning(f"[경고] 잘못된 입력: {choice}")
        print("올바른 번호를 입력하세요.")

if __name__ == "__main__":
    try:
        logging.info("==== 실행 시작 ====")
        main()
        logging.info("==== 실행 종료 ====")
    except Exception as e:
        logging.exception("예외 발생:")
        print(f"예기치 않은 오류가 발생했습니다. 자세한 내용은 'cli_runlog.txt'를 확인하세요.")
