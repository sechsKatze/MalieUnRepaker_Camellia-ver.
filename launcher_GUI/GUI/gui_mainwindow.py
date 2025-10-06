import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFileDialog, QLineEdit, QTabWidget, QTextEdit, QMessageBox
)
from PySide6.QtCore import QThread, Signal, Qt

from PySide6.QtGui import QFont

from execution.unpack_plain import run_unpack_plain
from execution.unpack import run_unpack
from execution.repack_plain import run_repack_plain
import logging

class WorkerThread(QThread):
    sigFinished = Signal()
    sigError = Signal(str)

    def __init__(self, target_func, *args, **kwargs):
        super().__init__()
        self.target_func = target_func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            self.target_func(*self.args, **self.kwargs)
        except Exception as e:
            import traceback
            self.sigError.emit(traceback.format_exc())
        finally:
            self.sigFinished.emit()

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Malie UnRepacker Tool GUI ver")
        self.setFixedSize(800, 469)

        layout = QVBoxLayout()
        self.setLayout(layout)

        # ✅ 상단 텍스트
        self.title_label = QLabel("Malie engine Unpack / Repack Tool GUI")
        self.title_label.setFont(QFont("Arial", 12, QFont.Bold))
        self.title_label.setAlignment(Qt.AlignLeft)  # 또는 Qt.AlignCenter
        self.title_label.setStyleSheet("color: black;")
        layout.addWidget(self.title_label)

        # ✅ 카피라이트 라벨 (작게)
        copyright_font = QFont("Arial", 8)
        copyright_font.setItalic(True)

        self.copyright_label = QLabel(
            "© 2014–2019 morkt, ported to Python by sechsKatze (MIT License)"
        )
        self.copyright_label.setFont(copyright_font)
        self.copyright_label.setStyleSheet("color: #666666;")
        layout.addWidget(self.copyright_label)

        # ✅ 탭 생성 (먼저 만들어야 함!)
        self.tabs = QTabWidget()
        self.unpack_tab = self.create_unpack_tab()
        self.repack_tab = self.create_repack_tab()
        self.information_tab = self.create_information_tab()

        self.tabs.addTab(self.unpack_tab, "Unpack / Plain decryption")
        self.tabs.addTab(self.repack_tab, "Repack")
        self.tabs.addTab(self.information_tab, "Info")

        # ✅ 마지막에 탭 추가
        layout.addWidget(self.tabs)

    # ✅ 메시지 로그 수신 함수
    def append_log_unpack(self, msg):
        # QTextEdit은 appendPlainText가 아닌 append를 사용해야 함
        self.log_output.append(msg)
        self.log_output.ensureCursorVisible()

        # ✅ 로그가 추가되면 항상 아래로 스크롤
        scrollbar = self.log_output.verticalScrollBar()  # ✅ 수정
        scrollbar.setValue(scrollbar.maximum())

    def append_log_repack(self, msg):
        self.log_output_repack.append(msg)
        self.log_output_repack.ensureCursorVisible()

        scrollbar = self.log_output_repack.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    # 언팩/1차 복호화 탭
    def create_unpack_tab(self):
        unpack_tab = QWidget()
        layout = QVBoxLayout(unpack_tab)

        file_layout = QHBoxLayout()
        file_layout.addWidget(QLabel("📂 DAT 파일:"))
        self.input_dat_path = QLineEdit()
        file_layout.addWidget(self.input_dat_path)
        btn_browse_input = QPushButton("파일 열기")
        btn_browse_input.clicked.connect(self.browse_input_file)
        file_layout.addWidget(btn_browse_input)

        folder_layout = QHBoxLayout()
        folder_layout.addWidget(QLabel("📁 저장 경로:"))
        self.output_dir = QLineEdit()
        folder_layout.addWidget(self.output_dir)
        btn_browse_output = QPushButton("경로 열기")
        btn_browse_output.clicked.connect(self.browse_output_folder)
        folder_layout.addWidget(btn_browse_output)

        self.btn_unpack_plain = QPushButton("1차 복호화 (.dat → _plain.dat)")
        self.btn_unpack_plain.clicked.connect(self.run_unpack_plain_clicked)

        self.btn_unpack = QPushButton("완전 언팩 (.dat → 폴더/파일/메타데이터.json)")
        self.btn_unpack.clicked.connect(self.run_unpack_clicked)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)

        layout.addLayout(file_layout)
        layout.addLayout(folder_layout)
        layout.addWidget(self.btn_unpack_plain)
        layout.addWidget(self.btn_unpack)
        layout.addWidget(self.log_output)

        return unpack_tab

    # 리팩 탭 (현재 평문 .dat 리팩만)
    def create_repack_tab(self):
        repack_tab = QWidget()
        layout = QVBoxLayout(repack_tab)

        folder_layout = QHBoxLayout()
        folder_layout.addWidget(QLabel("📂 입력 폴더:"))
        self.input_dir = QLineEdit()
        btn_browse_input = QPushButton("폴더 열기")
        btn_browse_input.clicked.connect(self.browse_input_folder)
        folder_layout.addWidget(self.input_dir)
        folder_layout.addWidget(btn_browse_input)

        outdir_layout = QHBoxLayout()
        outdir_layout.addWidget(QLabel("📁 저장 경로:"))
        self.output_dir_repack = QLineEdit()
        btn_browse_outdir = QPushButton("폴더 열기")
        btn_browse_outdir.clicked.connect(self.browse_output_folder_repack)
        outdir_layout.addWidget(self.output_dir_repack)
        outdir_layout.addWidget(btn_browse_outdir)

        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("📝 .dat 이름 (확장자 생략):"))
        self.output_name = QLineEdit()
        name_layout.addWidget(self.output_name)

        json_layout = QHBoxLayout()
        json_layout.addWidget(QLabel("📑 메타데이터:"))
        self.input_json = QLineEdit()
        btn_browse_json = QPushButton("파일 열기 (.json)")
        btn_browse_json.clicked.connect(self.browse_json_file)
        json_layout.addWidget(self.input_json)
        json_layout.addWidget(btn_browse_json)

        self.btn_repack_plain = QPushButton("평문 리팩 (폴더 → .dat)")
        self.btn_repack_plain.clicked.connect(self.run_repack_plain_clicked)

        self.log_output_repack = QTextEdit()
        self.log_output_repack.setReadOnly(True)

        layout.addLayout(folder_layout)
        layout.addLayout(outdir_layout)
        layout.addLayout(name_layout)
        layout.addLayout(json_layout)
        layout.addWidget(self.btn_repack_plain)
        layout.addWidget(self.log_output_repack)

        return repack_tab

    # 공지/정보 탭
    def create_information_tab(self):
        information_tab = QWidget()
        layout = QVBoxLayout(information_tab)

        info_label = QLabel(
            "📌 현재 제한 사항:\n"
            "1. .lib 리패킹은 아직 지원되지 않습니다.\n"
            "2. 암호화된 .dat 리패킹은 아직 지원되지 않습니다.\n"
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        return information_tab

    # 언팩/1차 복호화 탭의 파일 선택
    def browse_input_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "DAT 파일 선택", "", "DAT Files (*.dat);;All Files (*)")
        if file_path:
            self.input_dat_path.setText(file_path)

    def browse_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "출력 폴더 선택")
        if folder:
            self.output_dir.setText(folder)

    def browse_input_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "입력 폴더 선택")
        if folder:
            self.input_dir.setText(folder)

    def browse_output_dat(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "출력 DAT 파일 지정", "", "DAT Files (*.dat);;All Files (*)")
        if file_path:
            self.output_dat.setText(file_path)

    def browse_json_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "JSON 파일 선택", "", "JSON Files (*.json);;All Files (*)")
        if file_path:
            self.input_json.setText(file_path)

    def browse_output_folder_repack(self):
        folder = QFileDialog.getExistingDirectory(self, "출력 경로 선택")
        if folder:
            self.output_dir_repack.setText(folder)

    def run_unpack_plain_clicked(self):
        input_path = self.input_dat_path.text().strip()
        output_dir = self.output_dir.text().strip()

        # ⚠️ 입력값 검증
        if not input_path or not os.path.isfile(input_path):
            QMessageBox.warning(self, "입력 오류", "유효한 DAT 파일을 선택하세요.")
            return
        if not output_dir or not os.path.isdir(output_dir):
            QMessageBox.warning(self, "입력 오류", "출력 폴더 경로를 올바르게 지정하세요.")
            return

        self.thread = WorkerThread(run_unpack_plain, input_path, output_dir)
        self.thread.sigFinished.connect(self.on_task_finished)
        self.thread.sigError.connect(self.on_task_error)
        self.thread.start()

    def run_unpack_clicked(self):
        input_path = self.input_dat_path.text().strip()
        output_dir = self.output_dir.text().strip()

        # ⚠️ 입력값 검증
        if not input_path or not os.path.isfile(input_path):
            QMessageBox.warning(self, "입력 오류", "유효한 DAT 파일을 선택하세요.")
            return
        if not output_dir or not os.path.isdir(output_dir):
            QMessageBox.warning(self, "입력 오류", "출력 폴더 경로를 올바르게 지정하세요.")
            return

        self.thread = WorkerThread(run_unpack, input_path, output_dir)
        self.thread.sigFinished.connect(self.on_task_finished)
        self.thread.sigError.connect(self.on_task_error)
        self.thread.start()

    def run_repack_plain_clicked(self):
        input_dir = self.input_dir.text().strip()
        output_dir = self.output_dir_repack.text().strip()
        dat_name = self.output_name.text().strip()
        json_path = self.input_json.text().strip()

        # ⚠️ 입력값 검증
        if not input_dir or not os.path.isdir(input_dir):
            QMessageBox.warning(self, "입력 오류", "입력 폴더를 올바르게 지정하세요.")
            return
        if not output_dir or not os.path.isdir(output_dir):
            QMessageBox.warning(self, "입력 오류", "출력 폴더 경로를 올바르게 지정하세요.")
            return
        if not dat_name:
            QMessageBox.warning(self, "입력 오류", ".dat 파일 이름을 입력하세요.")
            return
        if not json_path or not os.path.isfile(json_path):
            QMessageBox.warning(self, "입력 오류", "유효한 JSON 파일을 선택하세요.")
            return

        # ✅ .dat 확장자 자동 추가
        if not dat_name.lower().endswith(".dat"):
            dat_name += ".dat"

        # ✅ 최종 출력 경로 생성
        output_path = os.path.join(output_dir, dat_name)

        # 🔄 비동기 스레드 실행
        self.thread = WorkerThread(run_repack_plain, input_dir, output_path, json_path)
        self.thread.sigFinished.connect(self.on_task_finished)
        self.thread.sigError.connect(self.on_task_error)
        self.thread.start()

    def on_task_finished(self):
        logging.info("🎉 작업이 완료되었습니다.")

    def on_task_error(self, msg):
        logging.error("❌ 에러 발생:\n" + msg)

    def run_unpack_plain(self):
        dat_path = self.input_dat_path.text()
        output_dir = self.output_dir.text()
        try:
            run_unpack_plain(dat_path, output_dir)
            self.append_log_unpack("[✓] 1차 복호화 완료.")
        except Exception as e:
            self.append_log_unpack(f"[에러] 1차 복호화 실패: {e}")

    def run_unpack(self):
        dat_path = self.input_dat_path.text()
        output_dir = self.output_dir.text()

        try:
            run_unpack(dat_path, output_dir)  # ✅ dat_name 붙이지 않고 그대로 넘김
            self.append_log_unpack("✅ 언팩 완료!")
        except Exception as e:
            self.append_log_unpack(f"[에러] 언팩 실패: {e}")

    def run_repack_plain(self):
        input_dir = self.input_dat_path.text().strip()
        output_dir = self.output_dir.text().strip()
        dat_name = self.dat_name_input.text().strip()
        json_path = self.meta_path.text().strip()

        self.append_log_repack(f"[INFO] [GUI] [0] 입력 확인")

        # 입력 검사
        if not os.path.isdir(input_dir):
            self.append_log_repack(f"[ERROR] ❌ 입력 폴더가 존재하지 않음: {input_dir}")
            return
        if not os.path.isdir(output_dir):
            self.append_log_repack(f"[ERROR] ❌ 저장 경로가 폴더가 아님: {output_dir}")
            return
        if not dat_name:
            self.append_log_repack(f"[ERROR] ❌ .dat 파일명이 비어 있습니다. 오른쪽 필드에 이름을 입력하세요.")
            return

        # 확장자 자동 추가
        if not dat_name.lower().endswith(".dat"):
            dat_name += ".dat"

        output_path = os.path.join(output_dir, dat_name)

        # 🔥 디렉토리 충돌 검사 제거
        # if os.path.isdir(output_path):
        #     self.append_log_repack(f"[ERROR] ❌ 리팩 중 오류 발생: 출력 경로가 파일이 아닌 디렉토리입니다. .dat 파일명을 입력하세요: {output_path}")
        #     return

        if not os.path.isfile(json_path):
            self.append_log_repack(f"[ERROR] ❌ 메타데이터 파일이 존재하지 않음: {json_path}")
            return

        self.append_log_repack(f"[INFO] [GUI] [1] 최종 출력 경로: {output_path}")

        try:
            run_repack_plain(input_dir, output_path, json_path)
            self.append_log_repack(f"[✓] 평문 리팩 성공: {output_path}")
        except Exception as e:
            self.append_log_repack(f"[ERROR] ❌ 리팩 실패: {e}")



