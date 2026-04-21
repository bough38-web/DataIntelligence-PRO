import os
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFileDialog, QComboBox, QTextEdit, QCheckBox, QSplitter, 
    QMessageBox, QFrame, QTableWidget, QTableWidgetItem, QHeaderView
)
from app.utils.common import (
    clean_text, get_readable_file_path, is_file_locked,
    raw_rows_preview_text
)
from app.core.handlers import (
    get_sheet_names, extract_columns_fast, load_file_to_df, 
    extract_unique_values_fast, load_file_sample_rows
)
from app.core.workers import ExportWorker
from app.ui.widgets import ColumnCheckGrid, ConditionEditor, DataPreviewTable, PresetSelector

class SingleFileTab(QWidget):
    def __init__(self, log_cb):
        super().__init__()
        self.log_cb = log_cb
        self.file_path = ""
        self.worker = None
        self.build_ui()

    def build_ui(self):
        root = QVBoxLayout(self)
        
        top = QHBoxLayout()
        self.btn_open = QPushButton("📄 단일 파일 열기")
        self.btn_open.clicked.connect(self.select_file)
        top.addWidget(self.btn_open)
        
        self.lbl_file = QLabel("파일을 선택하세요")
        top.addWidget(self.lbl_file)
        top.addStretch()
        
        top.addWidget(QLabel("시트"))
        self.cmb_sheet = QComboBox()
        self.cmb_sheet.currentIndexChanged.connect(self.refresh_all)
        top.addWidget(self.cmb_sheet)
        
        top.addWidget(QLabel("헤더행"))
        self.cmb_header = QComboBox()
        self.cmb_header.addItem("자동", None)
        for i in range(1, 11): self.cmb_header.addItem(f"{i}행", i-1)
        self.cmb_header.currentIndexChanged.connect(self.refresh_all)
        top.addWidget(self.cmb_header)
        
        self.chk_force_html = QCheckBox("HTML 강제")
        self.chk_force_html.stateChanged.connect(self.refresh_all)
        top.addWidget(self.chk_force_html)
        
        self.btn_export = QPushButton("📤 추출 실행")
        self.btn_export.setStyleSheet("background-color: #059669; font-size: 11pt;")
        self.btn_export.clicked.connect(self.run_export)
        top.addWidget(self.btn_export)
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
        
        self.chk_trim_whitespace = QCheckBox("데이터 공백 자동 제거")
        self.chk_trim_whitespace.setChecked(True)
        expert_l.addWidget(self.chk_trim_whitespace)
        
        expert_l.addStretch()
        options_row.addWidget(expert_card, 1)
        
        # Preset Row (Part of options)
        self.preset_selector = PresetSelector("single")
        self.preset_selector.preset_loaded.connect(self.handle_preset)
        options_row.addWidget(self.preset_selector, 1)
        
        root.addLayout(options_row)

        split = QSplitter(Qt.Horizontal)
        
        # Left: Column Selection
        left_card = QFrame(); left_card.setObjectName("cardFrame")
        left_l = QVBoxLayout(left_card)
        self.col_grid = ColumnCheckGrid("📂 출력 컬럼 선택")
        left_l.addWidget(self.col_grid)
        split.addWidget(left_card)

        # Center: Condition Editor
        center_card = QFrame(); center_card.setObjectName("cardFrame")
        center_l = QVBoxLayout(center_card)
        self.condition_editor = ConditionEditor("🔍 필터링 조건")
        self.condition_editor.set_custom_values_getter(self.get_single_unique_values)
        center_l.addWidget(self.condition_editor)
        split.addWidget(center_card)

        # Right: Sort & Dedup
        right_card = QFrame(); right_card.setObjectName("cardFrame")
        right_l = QVBoxLayout(right_card)
        lbl_sd = QLabel("⚙️ 정렬 및 중복 필터"); lbl_sd.setObjectName("sectionTitle")
        right_l.addWidget(lbl_sd)
        
        sort_row = QHBoxLayout()
        self.cmb_sort_col = QComboBox(); sort_row.addWidget(self.cmb_sort_col, 2)
        self.cmb_sort_order = QComboBox(); self.cmb_sort_order.addItems(["오름차순", "내림차순"]); sort_row.addWidget(self.cmb_sort_order, 1)
        self.btn_add_sort = QPushButton("+"); self.btn_add_sort.clicked.connect(self.add_sort_row); sort_row.addWidget(self.btn_add_sort)
        right_l.addLayout(sort_row)
        
        self.tbl_sorts = QTableWidget(0, 3)
        self.tbl_sorts.setHorizontalHeaderLabels(["사용", "컬럼", "정렬"])
        self.tbl_sorts.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_sorts.verticalHeader().setVisible(False)
        right_l.addWidget(self.tbl_sorts)
        
        self.btn_remove_sort = QPushButton("선택 정렬 삭제")
        self.btn_remove_sort.clicked.connect(self.remove_sort_rows)
        right_l.addWidget(self.btn_remove_sort)

        dedup_box = QFrame()
        dedup_l = QHBoxLayout(dedup_box)
        self.chk_enable_dedup = QCheckBox("중복 제거")
        dedup_l.addWidget(self.chk_enable_dedup)
        self.cmb_dedup_col = QComboBox(); dedup_l.addWidget(self.cmb_dedup_col)
        self.cmb_dedup_keep = QComboBox(); self.cmb_dedup_keep.addItems(["첫 행", "마지막 행"]); dedup_l.addWidget(self.cmb_dedup_keep)
        right_l.addWidget(dedup_box)
        
        split.addWidget(right_card)

        split.setStretchFactor(0, 3)
        split.setStretchFactor(1, 4)
        split.setStretchFactor(2, 3)
        root.addWidget(split, 4)

        # Bottom Preview
        preview_card = QFrame(); preview_card.setObjectName("cardFrame")
        preview_l = QVBoxLayout(preview_card)
        preview_l.addWidget(QLabel("👀 데이터 미리보기"))
        self.tbl_preview = DataPreviewTable()
        preview_l.addWidget(self.tbl_preview)
        root.addWidget(preview_card, 2)

    def log(self, msg):
        self.log_cb(f"[단일] {msg}")

    def select_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "파일 선택", "", "Data (*.csv *.xlsx *.xlsm *.xls *.html *.htm)")
        if not path: return
        self.file_path = path
        self.lbl_file.setText(path + (" [열림]" if is_file_locked(path) else ""))
        
        self.cmb_sheet.clear()
        readable = get_readable_file_path(path)
        names = get_sheet_names(readable)
        if names: self.cmb_sheet.addItems(names)
        else: self.cmb_sheet.addItem("(기본)")
        self.refresh_all()

    def get_header_idx(self):
        return self.cmb_header.currentData()

    def get_selected_sheet(self):
        t = self.cmb_sheet.currentText()
        return None if t == "(기본)" else t

    def get_single_unique_values(self, col):
        if not self.file_path: return []
        return extract_unique_values_fast(
            get_readable_file_path(self.file_path),
            col, sheet_name=self.get_selected_sheet(),
            header_row_idx=self.get_header_idx(),
            force_html=self.chk_force_html.isChecked()
        )

    def refresh_all(self):
        if not self.file_path: return
        readable = get_readable_file_path(self.file_path)
        try:
            cols = extract_columns_fast(
                readable, 
                sheet_name=self.get_selected_sheet(),
                header_row_idx=self.get_header_idx(),
                force_html=self.chk_force_html.isChecked()
            )
            prev = set(self.col_grid.get_checked_columns())
            self.col_grid.set_columns(cols, checked=True, preserve_checked=prev)
            self.condition_editor.set_columns(cols)
            
            for c in [self.cmb_sort_col, self.cmb_dedup_col]:
                c.clear(); c.addItems(cols)
                
            df = load_file_to_df(
                readable, 
                sheet_name=self.get_selected_sheet(),
                header_row_idx=self.get_header_idx(),
                force_html=self.chk_force_html.isChecked()
            )
            self.tbl_preview.display_df(df)
        except Exception as e:
            self.tbl_preview.display_df(None)

    def show_raw_structure(self):
        if not self.file_path: return
        try:
            rows = load_file_sample_rows(
                get_readable_file_path(self.file_path),
                sheet_name=self.get_selected_sheet(),
                force_html=self.chk_force_html.isChecked()
            )
            QMessageBox.information(self, "원본 구조", raw_rows_preview_text(rows))
        except Exception as e:
            QMessageBox.warning(self, "오류", str(e))

    def add_sort_row(self):
        col = self.cmb_sort_col.currentText()
        order = self.cmb_sort_order.currentText()
        if not col: return
        row = self.tbl_sorts.rowCount()
        self.tbl_sorts.insertRow(row)
        chk = QTableWidgetItem(); chk.setFlags(chk.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled); chk.setCheckState(Qt.Checked)
        self.tbl_sorts.setItem(row, 0, chk)
        self.tbl_sorts.setItem(row, 1, QTableWidgetItem(col))
        self.tbl_sorts.setItem(row, 2, QTableWidgetItem(order))

    def remove_sort_rows(self):
        for idx in sorted([r.row() for r in self.tbl_sorts.selectionModel().selectedRows()], reverse=True):
            self.tbl_sorts.removeRow(idx)

    def run_export(self):
        if not self.file_path: return
        cols = self.col_grid.get_checked_columns()
        if not cols:
            QMessageBox.warning(self, "알림", "컬럼을 선택하세요.")
            return
            
        out, _ = QFileDialog.getSaveFileName(self, "저장", "추출결과.csv", "CSV (*.csv)")
        if not out: return
        
        sorts = []
        for r in range(self.tbl_sorts.rowCount()):
            if self.tbl_sorts.item(r, 0).checkState() == Qt.Checked:
                sorts.append({
                    "column": self.tbl_sorts.item(r, 1).text(),
                    "order": "desc" if self.tbl_sorts.item(r, 2).text() == "내림차순" else "asc"
                })
        
        dedup = None
        if self.chk_enable_dedup.isChecked():
            dedup = {
                "column": self.cmb_dedup_col.currentText(),
                "keep": "last" if self.cmb_dedup_keep.currentText() == "마지막 행" else "first"
            }

        self.worker = ExportWorker(
            source_path=self.file_path,
            output_path=out,
            sheet_name=self.get_selected_sheet(),
            selected_columns=cols,
            conditions=self.condition_editor.parse_conditions(),
            fill_service=self.chk_fill_service.isChecked(),
            sort_specs=sorts,
            dedup_spec=dedup,
            header_row_idx=self.get_header_idx(),
            force_html=self.chk_force_html.isChecked()
        )
        self.worker.status_changed.connect(self.log_cb)
        self.worker.finished_ok.connect(lambda m: QMessageBox.information(self, "완료", m))
        self.worker.error_occurred.connect(lambda m: QMessageBox.critical(self, "오류", m))
        self.worker.start()

    def handle_preset(self, data):
        if data.get("__action__") == "request_data":
            # Collect Current State
            sorts = []
            for r in range(self.tbl_sorts.rowCount()):
                if self.tbl_sorts.item(r, 0).checkState() == Qt.Checked:
                    sorts.append({
                        "column": self.tbl_sorts.item(r, 1).text(),
                        "order": "desc" if self.tbl_sorts.item(r, 2).text() == "내림차순" else "asc"
                    })
            
            payload = {
                "columns": self.col_grid.get_checked_columns(),
                "conditions": self.condition_editor.parse_conditions(),
                "sorts": sorts,
                "dedup_enabled": self.chk_enable_dedup.isChecked(),
                "dedup_col": self.cmb_dedup_col.currentText(),
                "dedup_keep": self.cmb_dedup_keep.currentText(),
                "fill_service": self.chk_fill_service.isChecked(),
                "header_idx": self.get_header_idx()
            }
            self.preset_selector.finalize_save(data["name"], payload)
        else:
            # Apply Preset
            cols = data.get("columns", [])
            self.col_grid.set_columns(self.col_grid.all_columns, preserve_checked=cols)
            
            self.condition_editor.table.setRowCount(0)
            for c in data.get("conditions", []):
                self.condition_editor.add_condition_row(
                    use=True,
                    col=c.get("column"),
                    mode=c.get("mode"),
                    vals_str=", ".join(c.get("values", []))
                )
            
            self.tbl_sorts.setRowCount(0)
            for s in data.get("sorts", []):
                row = self.tbl_sorts.rowCount()
                self.tbl_sorts.insertRow(row)
                chk = QTableWidgetItem(); chk.setFlags(chk.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled); chk.setCheckState(Qt.Checked)
                self.tbl_sorts.setItem(row, 0, chk)
                self.tbl_sorts.setItem(row, 1, QTableWidgetItem(s["column"]))
                self.tbl_sorts.setItem(row, 2, QTableWidgetItem("내림차순" if s["order"] == "desc" else "오름차순"))
            
            self.chk_enable_dedup.setChecked(data.get("dedup_enabled", False))
            self.cmb_dedup_col.setCurrentText(data.get("dedup_col", ""))
            self.cmb_dedup_keep.setCurrentText(data.get("dedup_keep", "첫 행"))
            self.chk_fill_service.setChecked(data.get("fill_service", True))
            
            h_idx = data.get("header_idx")
            for i in range(self.cmb_header.count()):
                if self.cmb_header.itemData(i) == h_idx:
                    self.cmb_header.setCurrentIndex(i)
                    break
            
            QMessageBox.information(self, "알림", "프리셋이 적용되었습니다.")
