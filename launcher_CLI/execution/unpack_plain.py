# unpack_plain.py - 1차 복호화만 된 .dat를 추출하기 위한 용도. 

import sys, os, io
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from numba import njit, uint32
from tqdm import tqdm
import numpy as np
import time

from formats.fileview import FileView
from malie.malieunpack import DatOpener, read_encrypted

class SafeRotatingFileHandler(RotatingFileHandler):
    def doRollover(self):
        try:
            super().doRollover()
        except PermissionError as e:
            logging.warning(f"[SafeRotatingFileHandler] 롤오버 실패 (무시됨): {e}")
        except Exception as e:
            logging.warning(f"[SafeRotatingFileHandler] 예상치 못한 오류 (무시됨): {e}")

# 로거 설정
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

for handler in logger.handlers[:]:
    logger.removeHandler(handler)

file_format = logging.Formatter("[%(levelname)s] %(message)s")

file_handler = SafeRotatingFileHandler(
    'debug_log.txt',
    mode='a',
    maxBytes=1_000_000_000,
    backupCount=100,
    encoding='utf-8'
)
file_handler.setLevel(logging.DEBUG)
logger.addHandler(file_handler)

# 콘솔 로그도 병렬 출력 (옵션)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.WARNING)
logger.addHandler(console_handler)


def run_serial_unpack_dat(archive, output_dir):
    for i, entry in enumerate(tqdm(archive.entries, desc="복호화 진행중 (.dat)", unit="파일")):
        try:
            save_path = os.path.join(output_dir, entry.name)
            os.makedirs(os.path.dirname(save_path), exist_ok=True)

            print(f"[진행 중] {i+1}/{len(archive.entries)} → {entry.name}")

            buf = bytearray(entry.size)
            read_encrypted(archive.file_view, archive.decryptor, entry.offset, buf, 0, entry.size)

            with open(save_path, "wb") as f:
                f.write(buf)

        except Exception as e:
            print(f"[오류] {entry.name} 처리 중 예외 발생: {e}")


# .dat 전체 복호화 + 스트링 테이블 포함, 패딩 제거 및 비제거 옵션
def decrypt_full_dat(archive, output_path: str, keep_padding: bool = False):
    view = archive.file_view
    decryptor = archive.decryptor
    file_size = view.get_max_offset()
    block_size = 0x1000

    with open(output_path, "wb") as out:
        offset = 0
        while offset < file_size:
            to_read = min(block_size, file_size - offset)

            # padding 고려 여부
            if keep_padding:
                aligned_len = (to_read + 0xF) & ~0xF
                buf = bytearray(aligned_len)
                read_encrypted(view, decryptor, offset, buf, 0, aligned_len)
                out.write(buf)
                offset += aligned_len  # ✅ 정렬된 길이만큼 증가
            else:
                buf = bytearray(to_read)
                read_encrypted(view, decryptor, offset, buf, 0, to_read)
                out.write(buf)
                offset += to_read  # ❗️entry.size만큼만 증가

        out.flush()
        os.fsync(out.fileno())

    print(f"[완료] 1차 복호화: {output_path} (padding {'유지' if keep_padding else '제거'})")
      

def main(args=None):
    if args is None:
        args = sys.argv[1:]

    try:
        if len(args) < 1:
            print("사용법: 1를 입력 후 <input.dat>/<ouput.dir>")
            return

        input_path = args[0]

        if not os.path.isfile(input_path):
            print(f"[오류] 파일이 존재하지 않습니다: {input_path}")
            return

        view = FileView(input_path)
        archive = DatOpener().try_open(view)
        if not archive:
            print("아카이브 열기 실패")
            return

        # ✅ 항상 _plain.dat로 출력
        output_path = input_path.replace(".dat", "_plain.dat")

        start = time.time()
        decrypt_full_dat(archive, output_path)  # keep_padding 제거
        elapsed = time.time() - start
        print(f"[완료] 1차 복호화 시간: {elapsed:.2f}초")
        print(f"[완료] 복호화된 파일: {output_path}")

    except KeyboardInterrupt:
        print("\n[취소] 사용자에 의해 중단되었습니다.")
        logging.warning("[main] 사용자 중단 (Ctrl+C)")
        os._exit(1)

    except Exception as e:
        logging.exception(f"[main] 예외 발생: {e}")

    finally:
        try:
            view.close()
            print("[main] FileView 닫힘")
        except Exception:
            pass
        print("[main] 실행 종료")
        logging.shutdown()

if __name__ == "__main__":
    print("[main] 실행 시작")
    main()
    print("[main] 실행 종료")
