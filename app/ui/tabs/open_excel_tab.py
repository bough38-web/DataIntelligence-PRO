from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QComboBox, QTextEdit, QCheckBox, QSplitter, QMessageBox, QFrame,
    QFileDialog
)
from app.utils.common import clean_text, raw_rows_preview_text
from app.core.handlers import (
    WIN32_AVAILABLE, list_open_excel_workbooks, extract_open_excel_columns,
    load_open_excel_sheet_df, read_open_excel_sheet_rows, extract_open_excel_unique_values
)
from app.core.workers import OpenExcelExportWorker
from app.ui.widgets import ColumnCheckGrid, ConditionEditor, DataPreviewTable

class OpenExcelTab(QWidget):
    def __init__(self, log_cb):
        super().__init__()
        self.log_cb = log_cb
        self.open_items = []
        self.worker = None
        self.build_ui()

    def build_ui(self):
        root = QVBoxLayout(self)
        
        top = QHBoxLayout()
        self.btn_refresh = QPushButton("🔄 엑셀 목록 새로고침")
        self.btn_refresh.clicked.connect(self.refresh_open_workbooks)
        top.addWidget(self.btn_refresh)
        
        self.cmb_workbook = QComboBox()
        self.cmb_workbook.currentIndexChanged.connect(self.on_workbook_changed)
        top.addWidget(self.cmb_workbook)
        
        self.cmb_sheet = QComboBox()
        self.cmb_sheet.currentIndexChanged.connect(self.refresh_preview)
        top.addWidget(self.cmb_sheet)
        
        top.addWidget(QLabel("헤더행"))
        self.cmb_header = QComboBox()
        self.cmb_header.addItem("자동", None)
        for i in range(1, 11): self.cmb_header.addItem(f"{i}행", i-1)
        self.cmb_header.currentIndexChanged.connect(self.refresh_preview)
        top.addWidget(self.cmb_header)
        
        self.btn_extract = QPushButton("📤 열린 엑셀 추출")
        self.btn_extract.setStyleSheet("background-color: #7c3aed; font-size: 11pt;")
        self.btn_extract.clicked.connect(self.run_export)
        top.addWidget(self.btn_extract)
        root.addLayout(top)

        # Expert / Options Row
        options_row = QHBoxLayout()
        
        expert_card = QFrame(); expert_card.setObjectName("expertCard")
        expert_l = QHBoxLayout(expert_card)
        expert_l.setContentsMargins(10, 5, 10, 5)
        expert_l.addWidget(QLabel("<b>🚀 전문가 옵션:</b>"))
        
        self.chk_fill_service = QCheckBox("서비스(소) 자동 채움")
        self.chk_fill_service.setChecked(True)
        expert_l.addWidget(self.chk_fill_service)
        
        self.chk_live_sync = QCheckBox("실시간 시트 동기화")
        self.chk_live_sync.setChecked(True)
        expert_l.addWidget(self.chk_live_sync)
        
        expert_l.addStretch()
        options_row.addWidget(expert_card, 1)
        root.addLayout(options_row)

        if not WIN32_AVAILABLE:
            warn = QLabel("⚠️ pywin32가 설치되지 않았거나 Mac 환경입니다. '열려있는 엑셀' 기능은 Windows 전용입니다.")
            warn.setStyleSheet("color: #dc2626; font-weight: bold;")
            root.addWidget(warn)

        split = QSplitter(Qt.Horizontal)
        
        left_card = QFrame(); left_card.setObjectName("cardFrame")
        left_l = QVBoxLayout(left_card)
        self.col_grid = ColumnCheckGrid("📂 열린 시트 컬럼")
        left_l.addWidget(self.col_grid)
        split.addWidget(left_card)

        center_card = QFrame(); center_card.setObjectName("cardFrame")
        center_l = QVBoxLayout(center_card)
        self.condition_editor = ConditionEditor("🔍 필터링 조건")
        self.condition_editor.set_custom_values_getter(self.get_open_excel_unique_values)
        center_l.addWidget(self.condition_editor)
        split.addWidget(center_card)

        right_card = QFrame(); right_card.setObjectName("cardFrame")
        right_l = QVBoxLayout(right_card)
        right_l.addWidget(QLabel("👀 데이터 미리보기"))
        self.tbl_preview = DataPreviewTable()
        right_l.addWidget(self.tbl_preview)
        split.addWidget(right_card)

        split.setStretchFactor(0, 3)
        split.setStretchFactor(1, 4)
        split.setStretchFactor(2, 3)
        root.addWidget(split, 4)

        self.refresh_open_workbooks()

    def log(self, msg):
        self.log_cb(f"[열린엑셀] {msg}")

    def get_header_idx(self):
        return self.cmb_header.currentData()

    def refresh_open_workbooks(self):
        if not WIN32_AVAILABLE: return
        self.open_items = list_open_excel_workbooks()
        self.cmb_workbook.clear()
        if not self.open_items:
            self.cmb_workbook.addItem("(열려있는 엑셀 없음)")
            return
        for item in self.open_items:
            label = item['name'] + (" [저장안됨]" if not item['full_name'] else "")
            self.cmb_workbook.addItem(label)
        self.on_workbook_changed()

    def get_current_item(self):
        idx = self.cmb_workbook.currentIndex()
        if idx < 0 or idx >= len(self.open_items): return None
        return self.open_items[idx]

    def on_workbook_changed(self):
        item = self.get_current_item()
        self.cmb_sheet.clear()
        if item:
            self.cmb_sheet.addItems(item.get("sheet_names", []))
        self.refresh_preview()

    def get_open_excel_unique_values(self, col):
        item = self.get_current_item()
        sheet = self.cmb_sheet.currentText()
        if not item or not sheet: return []
        return extract_open_excel_unique_values(
            item["name"], sheet, col, 
            header_row_idx=self.get_header_idx()
        )

    def refresh_preview(self):
        item = self.get_current_item()
        sheet = self.cmb_sheet.currentText()
        if not item or not sheet:
            self.col_grid.set_columns([])
            self.condition_editor.set_columns([])
            self.tbl_preview.display_df(None)
            return

        try:
            cols = extract_open_excel_columns(
                item["name"], sheet, 
                header_row_idx=self.get_header_idx()
            )
            prev = set(self.col_grid.get_checked_columns())
            self.col_grid.set_columns(cols, checked=True, preserve_checked=prev)
            self.condition_editor.set_columns(cols)
            
            df = load_open_excel_sheet_df(
                item["name"], sheet, max_rows=300, 
                header_row_idx=self.get_header_idx()
            )
            self.tbl_preview.display_df(df)
        except Exception as e:
            self.tbl_preview.display_df(None)

    def show_raw_structure(self):
        item = self.get_current_item()
        sheet = self.cmb_sheet.currentText()
        if not item or not sheet: return
        try:
            rows = read_open_excel_sheet_rows(item["name"], sheet, max_rows=20)
            QMessageBox.information(self, "원본 구조", raw_rows_preview_text(rows))
        except Exception as e:
            QMessageBox.warning(self, "오류", str(e))

    def run_export(self):
        item = self.get_current_item()
        sheet = self.cmb_sheet.currentText()
        if not item or not sheet: return
        cols = self.col_grid.get_checked_columns()
        if not cols:
            QMessageBox.warning(self, "알림", "컬럼을 선택하세요.")
            return
            
        out, _ = QFileDialog.getSaveFileName(self, "저장", "열린엑셀_결과.csv", "CSV (*.csv)")
        if not out: return
        
        self.worker = OpenExcelExportWorker(
            workbook_name=item["name"],
            sheet_name=sheet,
            output_path=out,
            selected_columns=cols,
            conditions=self.condition_editor.parse_conditions(),
            fill_service=self.chk_fill_service.isChecked(),
            header_row_idx=self.get_header_idx()
        )
        self.worker.status_changed.connect(self.log_cb)
        self.worker.finished_ok.connect(lambda m: QMessageBox.information(self, "완료", m))
        self.worker.error_occurred.connect(lambda m: QMessageBox.critical(self, "오류", m))
        self.worker.start()
