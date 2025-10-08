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
from formats.arcfile import ArcFile
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
# ✅ 기존 핸들러 제거 안함 (GUI QtHandler 유지)
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

file_format = logging.Formatter("[%(levelname)s] %(message)s")

# .dat 전체 복호화 + 스트링 테이블 포함
def decrypt_full_dat(archive, output_path: str):
    view = archive.file_view
    decryptor = archive.decryptor
    file_size = view.get_max_offset()
    block_size = 0x1000

    with open(output_path, "wb") as out:
        offset = 0
        while offset < file_size:
            to_read = min(block_size, file_size - offset)
            # 항상 블록 정렬 유지 (원본 그대로)
            aligned_len = (to_read + 0xF) & ~0xF
            buf = bytearray(aligned_len)
            read_encrypted(view, decryptor, offset, buf, 0, aligned_len)
            out.write(buf)
            offset += aligned_len

        out.flush()
        os.fsync(out.fileno())

    print(f"[완료] 1차 복호화: {output_path}")


#GUI용 실행 함수
def run_unpack_plain(input_path: str, output_dir: str):
    logging.info(f"[unpack_plain.py] 언팩 시작: {input_path} → {output_dir}")

    if not os.path.isfile(input_path):
        raise Exception(f"[오류] 파일이 존재하지 않습니다: {input_path}")

    # ✅ FileView 생성
    view = FileView(input_path)
    logging.debug(f"[fileview] '{input_path}' 열림 (크기: {view.size} bytes)")

    # ✅ archive 초기화
    archive = DatOpener().try_open(view)
    if not isinstance(archive, ArcFile):
        raise Exception(f"[오류] 아카이브 열기 실패: {input_path}")
    
    logging.info(f"[unpack_plain.py] 아카이브 오픈 성공: entries={len(archive.entries)}")

    # ✅ 출력 파일 경로 생성 (plain.dat)
    dat_name = os.path.splitext(os.path.basename(input_path))[0]
    output_path = os.path.join(output_dir, f"{dat_name}_plain.dat")
    logging.info(f"[unpack_plain.py] 복호화 결과 저장 위치: {output_path}")

    # ✅ 전체 복호화 실행
    decrypt_full_dat(archive, output_path)
    logging.info("✅ 1차 복호화 완료!")


#main은 삭제하면 안됨.
def main(args=None):
    if args is None:
        args = sys.argv[1:]

if __name__ == "__main__":
    print("[main] 실행 시작")
    main()
    print("[main] 실행 종료")  # 이게 안 뜨면 종료 안 되고 재진입