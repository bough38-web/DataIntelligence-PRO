import sys
import traceback
from PySide6.QtWidgets import QApplication, QInputDialog, QLineEdit, QMessageBox
from PySide6.QtGui import QFont
from app.ui.main_window import MainWindow

APP_PASSWORD = "0303"

def request_startup_password():
    password, ok = QInputDialog.getText(
        None,
        "접속 확인",
        "접속 비밀번호를 입력하세요",
        QLineEdit.Password,
    )
    if not ok:
        return False
    return password == APP_PASSWORD

def main():
    try:
        app = QApplication(sys.argv)
        app.setFont(QFont("Malgun Gothic", 10))

        if not request_startup_password():
            QMessageBox.warning(None, "접속 실패", "비밀번호가 올바르지 않거나 입력이 취소되었습니다.")
            sys.exit(0)

        win = MainWindow()
        win.show()
        sys.exit(app.exec())
    except Exception as e:
        error_msg = f"{str(e)}\n\n{traceback.format_exc()}"
        print(error_msg)
        # Use a fresh QApplication if the old one is gone or wasn't even started
        if not QApplication.instance():
            app = QApplication(sys.argv)
        QMessageBox.critical(None, "실행 오류", f"프로그램 시작 중 오류가 발생했습니다:\n\n{error_msg}")
        with open("crash_log.txt", "w", encoding="utf-8") as f:
            f.write(error_msg)

if __name__ == "__main__":
    main()
