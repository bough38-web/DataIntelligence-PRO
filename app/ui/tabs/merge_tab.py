import os
import glob
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFileDialog, QListWidget, QListWidgetItem, QComboBox, 
    QTextEdit, QCheckBox, QSplitter, QMessageBox, QFrame
)
from app.utils.common import (
    clean_text, get_readable_file_path, is_file_locked
)
from app.core.handlers import get_sheet_names, extract_columns_fast, load_file_to_df
from app.core.workers import MergeWorker
from app.ui.widgets import ColumnCheckGrid, ConditionEditor, DataPreviewTable, PresetSelector

class MergeTab(QWidget):
    def __init__(self, log_cb):
        super().__init__()
        self.log_cb = log_cb
        self.files = []
        self.current_folder = ""
        self.worker = None
        self.build_ui()

    def build_ui(self):
        root = QVBoxLayout(self)
        
        top = QHBoxLayout()
        self.btn_select_folder = QPushButton("📁 병합 폴더 선택")
        self.btn_select_folder.clicked.connect(self.select_folder)
        top.addWidget(self.btn_select_folder)
        
        self.lbl_folder = QLabel("폴더를 선택하세요")
        top.addWidget(self.lbl_folder)
        top.addStretch()
        
        top.addWidget(QLabel("시트"))
        self.cmb_sheet = QComboBox()
        self.cmb_sheet.currentIndexChanged.connect(self.refresh_common_columns)
        top.addWidget(self.cmb_sheet)
        
        self.btn_merge = QPushButton("🚀 병합 실행")
        self.btn_merge.setStyleSheet("background-color: #4f46e5; font-size: 11pt;")
        self.btn_merge.clicked.connect(self.run_merge)
        top.addWidget(self.btn_merge)
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
        
        self.chk_normalize_keys = QCheckBox("지능형 컬럼 매칭")
        self.chk_normalize_keys.setChecked(True)
        expert_l.addWidget(self.chk_normalize_keys)
        
        expert_l.addStretch()
        options_row.addWidget(expert_card, 1)
        
        self.preset_selector = PresetSelector("merge")
        self.preset_selector.preset_loaded.connect(self.handle_preset)
        options_row.addWidget(self.preset_selector, 1)
        root.addLayout(options_row)

        split = QSplitter(Qt.Horizontal)
        
        # Left: File List
        left_card = QFrame(); left_card.setObjectName("cardFrame")
        left_l = QVBoxLayout(left_card)
        lbl_files = QLabel("📂 대상 파일 목록"); lbl_files.setObjectName("sectionTitle")
        left_l.addWidget(lbl_files)
        self.list_files = QListWidget()
        self.list_files.itemChanged.connect(self.refresh_common_columns)
        left_l.addWidget(self.list_files)
        split.addWidget(left_card)

        # Center: Column Grid
        center_card = QFrame(); center_card.setObjectName("cardFrame")
        center_l = QVBoxLayout(center_card)
        self.col_grid = ColumnCheckGrid("🔗 공통 컬럼 설정")
        center_l.addWidget(self.col_grid)
        split.addWidget(center_card)

        # Right: Condition Editor
        right_card = QFrame(); right_card.setObjectName("cardFrame")
        right_l = QVBoxLayout(right_card)
        self.condition_editor = ConditionEditor("🔍 필터링 조건")
        self.condition_editor.set_source_getters(self.get_first_readable_selected_file, self.get_selected_sheet_name)
        right_l.addWidget(self.condition_editor)
        split.addWidget(right_card)

        split.setStretchFactor(0, 2)
        split.setStretchFactor(1, 3)
        split.setStretchFactor(2, 4)
        root.addWidget(split, 4)

        # Bottom: Preview
        preview_card = QFrame(); preview_card.setObjectName("cardFrame")
        preview_l = QVBoxLayout(preview_card)
        preview_l.addWidget(QLabel("👀 데이터 미리보기 (선택된 첫 번째 파일)"))
        self.tbl_preview = DataPreviewTable()
        preview_l.addWidget(self.tbl_preview)
        root.addWidget(preview_card, 2)

    def log(self, msg):
        self.log_cb(f"[병합] {msg}")

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "병합 폴더 선택")
        if not folder: return
        self.current_folder = folder
        patterns = ["*.csv", "*.xlsx", "*.xlsm", "*.xls", "*.html", "*.htm"]
        files = []
        for p in patterns:
            files.extend(glob.glob(os.path.join(folder, "**", p), recursive=True))
        self.files = sorted(set(files))
        self.lbl_folder.setText(f"{folder} ({len(self.files)}개 파일)")
        
        self.list_files.clear()
        for f in self.files:
            label = os.path.relpath(f, folder)
            if is_file_locked(f): label += " [열림]"
            item = QListWidgetItem(label)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            self.list_files.addItem(item)
            
        self.cmb_sheet.clear()
        if self.files:
            names = get_sheet_names(get_readable_file_path(self.files[0]))
            if names: self.cmb_sheet.addItems(names)
            else: self.cmb_sheet.addItem("(기본)")
        self.refresh_common_columns()

    def get_selected_files(self):
        res = []
        for i in range(self.list_files.count()):
            if self.list_files.item(i).checkState() == Qt.Checked:
                res.append(self.files[i])
        return res

    def get_selected_sheet_name(self):
        t = self.cmb_sheet.currentText()
        return None if t == "(기본)" else t

    def get_first_readable_selected_file(self):
        files = self.get_selected_files() or self.files
        return get_readable_file_path(files[0]) if files else None

    def refresh_common_columns(self):
        files = self.get_selected_files()
        if not files:
            self.col_grid.set_columns([])
            self.condition_editor.set_columns([])
            self.tbl_preview.display_df(None)
            return
            
        sheet = self.get_selected_sheet_name()
        common = None
        for f in files:
            try:
                cols = set(extract_columns_fast(get_readable_file_path(f), sheet_name=sheet))
                common = cols if common is None else common & cols
            except:
                pass
                
        common_cols = sorted(common) if common else []
        prev = set(self.col_grid.get_checked_columns())
        self.col_grid.set_columns(common_cols, checked=True, preserve_checked=prev)
        self.condition_editor.set_columns(common_cols)
        
        try:
            df = load_file_to_df(get_readable_file_path(files[0]), sheet_name=sheet)
            self.tbl_preview.display_df(df)
        except:
            self.tbl_preview.display_df(None)

    def run_merge(self):
        files = self.get_selected_files()
        cols = self.col_grid.get_checked_columns()
        if not files or not cols:
            QMessageBox.warning(self, "알림", "파일과 컬럼을 선택하세요.")
            return
            
        out, _ = QFileDialog.getSaveFileName(self, "저장", "병합결과.csv", "CSV (*.csv)")
        if not out: return
        
        self.worker = MergeWorker(
            files=files,
            output_path=out,
            sheet_name=self.get_selected_sheet_name(),
            selected_columns=cols,
            conditions=self.condition_editor.parse_conditions(),
            fill_service=self.chk_fill_service.isChecked()
        )
        self.worker.status_changed.connect(self.log_cb)
        self.worker.finished_ok.connect(lambda m: QMessageBox.information(self, "완료", m))
        self.worker.error_occurred.connect(lambda m: QMessageBox.critical(self, "오류", m))
        self.worker.start()

    def handle_preset(self, data):
        if data.get("__action__") == "request_data":
            # Collect current UI state
            payload = {
                "columns": self.col_grid.get_checked_columns(),
                "conditions": self.condition_editor.parse_conditions(),
                "fill_service": self.chk_fill_service.isChecked()
            }
            self.preset_selector.finalize_save(data["name"], payload)
        else:
            # Apply data to UI
            cols = data.get("columns", [])
            self.col_grid.set_columns(self.col_grid.all_columns, preserve_checked=cols)
            
            # Apply conditions (Clear and refill table)
            self.condition_editor.table.setRowCount(0)
            for c in data.get("conditions", []):
                self.condition_editor.add_condition_row(
                    use=True,
                    col=c.get("column"),
                    mode=c.get("mode"),
                    vals_str=", ".join(c.get("values", []))
                )
            self.chk_fill_service.setChecked(data.get("fill_service", True))
            QMessageBox.information(self, "알림", "프리셋이 적용되었습니다.")
