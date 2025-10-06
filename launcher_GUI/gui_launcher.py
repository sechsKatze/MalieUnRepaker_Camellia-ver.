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

# ✅ 전역 핸들러 등록
qt_handler = QtHandler()
qt_handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
logging.getLogger().addHandler(qt_handler)
logging.getLogger().setLevel(logging.DEBUG)

# ✅ GUI 시작
app = QApplication(sys.argv)
window = MainWindow()

# ✅ 메시지 박스 연결
qt_handler.emitter.sigLog.connect(window.append_log_unpack)
qt_handler.emitter.sigLog.connect(window.append_log_repack)

window.show()
sys.exit(app.exec())


# ✅ 빌드 및 실행 진입점 보호 
if __name__ == "__main__":
    main()