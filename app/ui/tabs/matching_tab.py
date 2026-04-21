import os
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFileDialog, QComboBox, QMessageBox, QFrame, QSplitter
)
from app.utils.common import get_readable_file_path
from app.core.handlers import get_sheet_names, extract_columns_fast, load_file_to_df
from app.core.workers import MatchingWorker
from app.ui.widgets import ColumnCheckGrid, DataPreviewTable

class MatchingTab(QWidget):
    def __init__(self, log_cb):
        super().__init__()
        self.log_cb = log_cb
        self.base_file = ""
        self.ref_file = ""
        self.worker = None
        self.build_ui()

    def build_ui(self):
        root = QVBoxLayout(self)
        
        # Files Selection Row
        files_row = QHBoxLayout()
        
        # Left: Base File
        base_group = QFrame(); base_group.setObjectName("cardFrame")
        base_l = QVBoxLayout(base_group)
        base_l.addWidget(QLabel("<b>1. 원본 데이터 (Base)</b>"))
        
        base_btn_l = QHBoxLayout()
        self.btn_select_base = QPushButton("📁 원본 파일 선택")
        self.btn_select_base.clicked.connect(self.select_base_file)
        base_btn_l.addWidget(self.btn_select_base)
        self.lbl_base_file = QLabel("파일을 선택하세요")
        base_btn_l.addWidget(self.lbl_base_file, 1)
        base_l.addLayout(base_btn_l)
        
        base_opt_l = QHBoxLayout()
        base_opt_l.addWidget(QLabel("시트:"))
        self.cmb_base_sheet = QComboBox()
        self.cmb_base_sheet.currentIndexChanged.connect(self.refresh_base_columns)
        base_opt_l.addWidget(self.cmb_base_sheet, 1)
        base_opt_l.addWidget(QLabel("기준 컬럼(Key):"))
        self.cmb_base_key = QComboBox()
        base_opt_l.addWidget(self.cmb_base_key, 2)
        base_l.addLayout(base_opt_l)
        
        files_row.addWidget(base_group, 1)
        
        # Right: Reference File
        ref_group = QFrame(); ref_group.setObjectName("cardFrame")
        ref_l = QVBoxLayout(ref_group)
        ref_l.addWidget(QLabel("<b>2. 참조 데이터 (Reference)</b>"))
        
        ref_btn_l = QHBoxLayout()
        self.btn_select_ref = QPushButton("📁 참조 파일 선택")
        self.btn_select_ref.clicked.connect(self.select_ref_file)
        ref_btn_l.addWidget(self.btn_select_ref)
        self.lbl_ref_file = QLabel("파일을 선택하세요")
        ref_btn_l.addWidget(self.lbl_ref_file, 1)
        ref_l.addLayout(ref_btn_l)
        
        ref_opt_l = QHBoxLayout()
        ref_opt_l.addWidget(QLabel("시트:"))
        self.cmb_ref_sheet = QComboBox()
        self.cmb_ref_sheet.currentIndexChanged.connect(self.refresh_ref_columns)
        ref_opt_l.addWidget(self.cmb_ref_sheet, 1)
        ref_opt_l.addWidget(QLabel("기준 컬럼(Key):"))
        self.cmb_ref_key = QComboBox()
        ref_opt_l.addWidget(self.cmb_ref_key, 2)
        ref_l.addLayout(ref_opt_l)
        
        files_row.addWidget(ref_group, 1)
        root.addLayout(files_row)

        # Main Content: Column Selection and Previews
        split_v = QSplitter(Qt.Vertical)
        
        # Middle: Reference Columns to Add
        col_group = QFrame(); col_group.setObjectName("cardFrame")
        col_l = QVBoxLayout(col_group)
        self.col_grid = ColumnCheckGrid("🔗 가져올 참조 컬럼 선택")
        col_l.addWidget(self.col_grid)
        split_v.addWidget(col_group)
        
        # Bottom Previews
        preview_split = QSplitter(Qt.Horizontal)
        
        base_prev_group = QFrame(); base_prev_group.setObjectName("cardFrame")
        base_prev_l = QVBoxLayout(base_prev_group)
        lbl_bp = QLabel("👀 원본 미리보기"); lbl_bp.setObjectName("sectionTitle")
        base_prev_l.addWidget(lbl_bp)
        self.tbl_base_preview = DataPreviewTable()
        base_prev_l.addWidget(self.tbl_base_preview)
        preview_split.addWidget(base_prev_group)
        
        ref_prev_group = QFrame(); ref_prev_group.setObjectName("cardFrame")
        ref_prev_l = QVBoxLayout(ref_prev_group)
        lbl_rp = QLabel("👀 참조 미리보기"); lbl_rp.setObjectName("sectionTitle")
        ref_prev_l.addWidget(lbl_rp)
        self.tbl_ref_preview = DataPreviewTable()
        ref_prev_l.addWidget(self.tbl_ref_preview)
        preview_split.addWidget(ref_prev_group)
        
        split_v.addWidget(preview_split)
        
        root.addWidget(split_v, 1)
        
        # Action Row
        action_row = QHBoxLayout()
        action_row.addStretch()
        self.btn_run = QPushButton("🚀 매칭 실행 및 저장")
        self.btn_run.setStyleSheet("padding: 10px 30px; font-weight: bold; font-size: 11pt;")
        self.btn_run.clicked.connect(self.run_matching)
        action_row.addWidget(self.btn_run)
        root.addLayout(action_row)

    def set_running_state(self, running):
        self.btn_run.setEnabled(not running)
        self.btn_select_base.setEnabled(not running)
        self.btn_select_ref.setEnabled(not running)
        if running:
            self.btn_run.setText("⏳ 처리 중...")
        else:
            self.btn_run.setText("🚀 매칭 실행 및 저장")

    def log(self, msg):
        self.log_cb(f"[매칭] {msg}")

    def select_base_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "원본 파일 선택", "", "Data (*.xlsx *.xlsm *.xls *.csv *.html *.htm)")
        if not path: return
        self.base_file = path
        self.lbl_base_file.setText(os.path.basename(path))
        
        readable = get_readable_file_path(path)
        names = get_sheet_names(readable)
        self.cmb_base_sheet.clear()
        if names: self.cmb_base_sheet.addItems(names)
        else: self.cmb_base_sheet.addItem("(기본)")
        self.refresh_base_columns()

    def select_ref_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "참조 파일 선택", "", "Data (*.xlsx *.xlsm *.xls *.csv *.html *.htm)")
        if not path: return
        self.ref_file = path
        self.lbl_ref_file.setText(os.path.basename(path))
        
        readable = get_readable_file_path(path)
        names = get_sheet_names(readable)
        self.cmb_ref_sheet.clear()
        if names: self.cmb_ref_sheet.addItems(names)
        else: self.cmb_ref_sheet.addItem("(기본)")
        self.refresh_ref_columns()

    def refresh_base_columns(self):
        if not self.base_file: return
        sheet = self.cmb_base_sheet.currentText()
        if sheet == "(기본)": sheet = None
        
        try:
            readable = get_readable_file_path(self.base_file)
            cols = extract_columns_fast(readable, sheet_name=sheet)
            self.cmb_base_key.clear()
            self.cmb_base_key.addItems(cols)
            
            df = load_file_to_df(readable, sheet_name=sheet)
            self.tbl_base_preview.display_df(df)
        except Exception as e:
            self.log(f"원본 컬럼 로드 실패: {e}")

    def refresh_ref_columns(self):
        if not self.ref_file: return
        sheet = self.cmb_ref_sheet.currentText()
        if sheet == "(기본)": sheet = None
        
        try:
            readable = get_readable_file_path(self.ref_file)
            cols = extract_columns_fast(readable, sheet_name=sheet)
            self.cmb_ref_key.clear()
            self.cmb_ref_key.addItems(cols)
            
            self.col_grid.set_columns(cols, checked=True)
            
            df = load_file_to_df(readable, sheet_name=sheet)
            self.tbl_ref_preview.display_df(df)
        except Exception as e:
            self.log(f"참조 컬럼 로드 실패: {e}")

    def run_matching(self):
        if not self.base_file or not self.ref_file:
            QMessageBox.warning(self, "알림", "원본 파일과 참조 파일을 모두 선택하세요.")
            return
            
        base_key = self.cmb_base_key.currentText()
        ref_key = self.cmb_ref_key.currentText()
        ref_cols = self.col_grid.get_checked_columns()
        
        if not base_key or not ref_key or not ref_cols:
            QMessageBox.warning(self, "알림", "기준 컬럼과 가져올 컬럼을 선택하세요.")
            return
            
        out, _ = QFileDialog.getSaveFileName(self, "저장", "매칭결과.csv", "CSV (*.csv)")
        if not out: return
        self.worker = MatchingWorker(
            base_path=self.base_file,
            ref_path=self.ref_file,
            output_path=out,
            base_sheet=self.cmb_base_sheet.currentText() if self.cmb_base_sheet.currentText() != "(기본)" else None,
            ref_sheet=self.cmb_ref_sheet.currentText() if self.cmb_ref_sheet.currentText() != "(기본)" else None,
            base_key=base_key,
            ref_key=ref_key,
            ref_columns=ref_cols
        )
        
        # Connect signals
        self.worker.status_changed.connect(self.log_cb)
        
        # Connect progress to parent main window if possible
        parent_mw = self.window()
        if hasattr(parent_mw, "set_progress"):
            self.worker.progress_changed.connect(parent_mw.set_progress)
            
        self.worker.finished_ok.connect(self.on_matching_finished)
        self.worker.error_occurred.connect(self.on_matching_error)
        
        self.set_running_state(True)
        self.worker.start()

    def on_matching_finished(self, msg):
        self.set_running_state(False)
        QMessageBox.information(self, "완료", msg)
        
    def on_matching_error(self, msg):
        self.set_running_state(False)
        QMessageBox.critical(self, "오류", msg)
