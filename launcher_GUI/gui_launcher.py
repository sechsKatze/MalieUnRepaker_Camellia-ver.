import sys
import logging
from PySide6.QtWidgets import QApplication
from GUI.gui_mainwindow import MainWindow
from PySide6.QtCore import QObject, Signal


# ✅ Qt 로그 시그널 정의
class QtLogEmitter(QObject):
    sigLog = Signal(str)


# ✅ QtHandler 정의 (메시지 → QTextEdit)
class QtHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.emitter = QtLogEmitter()

    def emit(self, record):
        msg = self.format(record)
        self.emitter.sigLog.emit(msg)


# ✅ QtHandler 인스턴스 생성 및 Formatter 설정
qt_handler = QtHandler()
qt_handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))

# ✅ 루트 로거 및 기본 로거 모두에 핸들러 등록
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
root_logger.addHandler(qt_handler)

# ✅ 루트 로거 강제 등록 (스레드에서도 작동 보장)
logging.root.setLevel(logging.DEBUG)
logging.root.addHandler(qt_handler)

# ✅ 중복 핸들러 제거 (콘솔 중복 방지용)
if len(root_logger.handlers) > 1:
    root_logger.handlers = [qt_handler]

# ✅ GUI 앱 시작
app = QApplication(sys.argv)
window = MainWindow()

# ✅ 메시지 박스 로그 연결
qt_handler.emitter.sigLog.connect(window.append_log_unpack)
qt_handler.emitter.sigLog.connect(window.append_log_repack)
qt_handler.emitter.sigLog.connect(window.append_log_mgfpng)

window.show()
sys.exit(app.exec())


# ✅ 빌드 및 실행 진입점 보호 
if __name__ == "__main__":
    main()