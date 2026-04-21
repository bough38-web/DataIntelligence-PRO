import os
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QComboBox, QLineEdit, QCheckBox, QScrollArea, QGridLayout, 
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QFrame,
    QAbstractItemView, QInputDialog
)
from app.utils.common import clean_text
from app.core.handlers import extract_unique_values_fast
from app.utils.presets import PresetManager

class PresetSelector(QWidget):
    preset_loaded = Signal(dict)
    
    def __init__(self, category="default"):
        super().__init__()
        self.category = category
        self.manager = PresetManager(preset_dir=f"presets/{category}")
        os.makedirs(f"presets/{category}", exist_ok=True)
        self.build_ui()

    def build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        layout.addWidget(QLabel("📋 프리셋:"))
        self.cmb_presets = QComboBox()
        self.refresh_list()
        layout.addWidget(self.cmb_presets, 1)
        
        self.btn_load = QPushButton("불러오기")
        self.btn_load.clicked.connect(self.on_load)
        layout.addWidget(self.btn_load)
        
        self.btn_save = QPushButton("저장")
        self.btn_save.clicked.connect(self.on_save)
        layout.addWidget(self.btn_save)
        
        self.btn_delete = QPushButton("삭제")
        self.btn_delete.clicked.connect(self.on_delete)
        layout.addWidget(self.btn_delete)

    def refresh_list(self):
        self.cmb_presets.clear()
        self.cmb_presets.addItems(["-- 선택 --"] + self.manager.list_presets())

    def on_save(self):
        name, ok = QInputDialog.getText(self, "프리셋 저장", "프리셋 이름을 입력하세요:")
        if ok and name.strip():
            self.preset_loaded.emit({"__action__": "request_data", "name": name.strip()})

    def finalize_save(self, name, data):
        self.manager.save_preset(name, data)
        self.refresh_list()
        self.cmb_presets.setCurrentText(name)
        QMessageBox.information(self, "알림", f"'{name}' 프리셋이 저장되었습니다.")

    def on_load(self):
        name = self.cmb_presets.currentText()
        if name == "-- 선택 --": return
        data = self.manager.load_preset(name)
        if data:
            self.preset_loaded.emit(data)

    def on_delete(self):
        name = self.cmb_presets.currentText()
        if name == "-- 선택 --": return
        if QMessageBox.question(self, "삭제", f"'{name}' 프리셋을 삭제하시겠습니까?") == QMessageBox.Yes:
            self.manager.delete_preset(name)
            self.refresh_list()

class DataPreviewTable(QTableWidget):
    def __init__(self):
        super().__init__()
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setAlternatingRowColors(True)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.horizontalHeader().setStretchLastSection(True)
        self.verticalHeader().setVisible(False)
        self.setStyleSheet("QTableWidget { gridline-color: #dbe4ef; }")

    def display_df(self, df, max_rows=100):
        self.clear()
        if df is None or df.empty:
            self.setRowCount(0)
            self.setColumnCount(0)
            return

        cols = df.columns.tolist()
        self.setColumnCount(len(cols))
        self.setHorizontalHeaderLabels(cols)

        # Truncate for performance
        display_df = df.head(max_rows).fillna("")
        self.setRowCount(len(display_df))

        for r_idx, row in enumerate(display_df.values):
            for c_idx, val in enumerate(row):
                item = QTableWidgetItem(str(val))
                self.setItem(r_idx, c_idx, item)
        
        self.resizeColumnsToContents()
        # Cap column width
        for i in range(self.columnCount()):
            if self.columnWidth(i) > 400:
                self.setColumnWidth(i, 400)

class ColumnCheckGrid(QWidget):
    def __init__(self, title="출력 컬럼 선택", max_columns=4):
        super().__init__()
        self.all_columns = []
        self.checkboxes = {}
        self.max_columns = max_columns

        root = QVBoxLayout(self)
        top = QHBoxLayout()
        self.lbl_title = QLabel(title)
        self.lbl_title.setObjectName("sectionTitle")
        top.addWidget(self.lbl_title)
        top.addStretch()
        self.lbl_count = QLabel("0 / 0 선택")
        top.addWidget(self.lbl_count)
        root.addLayout(top)

        search_row = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("컬럼 검색")
        self.search.textChanged.connect(self.rebuild)
        search_row.addWidget(self.search)
        
        self.btn_all = QPushButton("전체 선택")
        self.btn_all.clicked.connect(self.check_all)
        search_row.addWidget(self.btn_all)
        
        self.btn_none = QPushButton("전체 해제")
        self.btn_none.clicked.connect(self.uncheck_all)
        search_row.addWidget(self.btn_none)
        root.addLayout(search_row)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.inner = QWidget()
        self.grid = QGridLayout(self.inner)
        self.grid.setContentsMargins(8, 8, 8, 8)
        self.grid.setHorizontalSpacing(12)
        self.grid.setVerticalSpacing(8)
        self.scroll.setWidget(self.inner)
        root.addWidget(self.scroll)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.rebuild()

    def set_columns(self, columns, checked=True, preserve_checked=None):
        prev_checked = set(preserve_checked or [])
        self.all_columns = list(columns)
        self.checkboxes = {}
        for col in self.all_columns:
            cb = QCheckBox(str(col))
            cb.setChecked((col in prev_checked) if prev_checked else checked)
            cb.stateChanged.connect(self.update_count)
            self.checkboxes[col] = cb
        self.rebuild()

    def visible_column_count(self):
        w = self.width()
        if w > 800: return 5
        if w > 600: return 4
        if w > 400: return 3
        return 2

    def rebuild(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            w = item.widget()
            if w: w.setParent(None)
            
        keyword = clean_text(self.search.text()).lower()
        columns = self.all_columns
        if keyword:
            columns = [c for c in columns if keyword in str(c).lower()]
            
        col_count = self.visible_column_count()
        for idx, col in enumerate(columns):
            row = idx // col_count
            c_idx = idx % col_count
            cb = self.checkboxes[col]
            self.grid.addWidget(cb, row, c_idx)
            
        for i in range(col_count):
            self.grid.setColumnStretch(i, 1)
        self.update_count()

    def update_count(self):
        total = len(self.all_columns)
        selected = len([c for c, cb in self.checkboxes.items() if cb.isChecked()])
        self.lbl_count.setText(f"{selected} / {total} 선택")

    def get_checked_columns(self):
        return [c for c, cb in self.checkboxes.items() if cb.isChecked()]

    def check_all(self):
        for cb in self.checkboxes.values(): cb.setChecked(True)
        self.update_count()

    def uncheck_all(self):
        for cb in self.checkboxes.values(): cb.setChecked(False)
        self.update_count()


class ValueFilterPanel(QWidget):
    def __init__(self, title="실제 값 선택", max_columns=3):
        super().__init__()
        self.all_values = []
        self.checkboxes = {}
        self.max_columns = max_columns
        
        root = QVBoxLayout(self)
        top = QHBoxLayout()
        self.lbl_title = QLabel(title)
        top.addWidget(self.lbl_title)
        top.addStretch()
        self.lbl_count = QLabel("0 / 0 선택")
        top.addWidget(self.lbl_count)
        root.addLayout(top)
        
        search_row = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("값 검색")
        self.search.textChanged.connect(self.rebuild)
        search_row.addWidget(self.search)
        
        self.btn_all = QPushButton("전체 선택")
        self.btn_all.clicked.connect(self.check_all)
        search_row.addWidget(self.btn_all)
        
        self.btn_none = QPushButton("전체 해제")
        self.btn_none.clicked.connect(self.uncheck_all)
        search_row.addWidget(self.btn_none)
        root.addLayout(search_row)
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.inner = QWidget()
        self.grid = QGridLayout(self.inner)
        self.grid.setContentsMargins(8, 8, 8, 8)
        self.grid.setHorizontalSpacing(12)
        self.grid.setVerticalSpacing(8)
        self.scroll.setWidget(self.inner)
        root.addWidget(self.scroll)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.rebuild()

    def set_values(self, values, checked=False):
        self.all_values = list(values)[:200]
        self.checkboxes = {}
        for v in self.all_values:
            cb = QCheckBox(str(v))
            cb.setChecked(checked)
            cb.stateChanged.connect(self.update_count)
            self.checkboxes[v] = cb
        self.rebuild()

    def rebuild(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            w = item.widget()
            if w: w.setParent(None)
            
        keyword = clean_text(self.search.text()).lower()
        values = self.all_values
        if keyword:
            values = [v for v in values if keyword in str(v).lower()]
            
        col_count = 3 if self.width() > 400 else 2
        for idx, v in enumerate(values):
            row = idx // col_count
            c_idx = idx % col_count
            self.grid.addWidget(self.checkboxes[v], row, c_idx)
            
        for i in range(col_count):
            self.grid.setColumnStretch(i, 1)
        self.update_count()

    def update_count(self):
        total = len(self.all_values)
        selected = len([v for v, cb in self.checkboxes.items() if cb.isChecked()])
        self.lbl_count.setText(f"{selected} / {total} 선택")

    def get_checked_values(self):
        return [v for v, cb in self.checkboxes.items() if cb.isChecked()]

    def check_all(self):
        for cb in self.checkboxes.values(): cb.setChecked(True)
        self.update_count()

    def uncheck_all(self):
        for cb in self.checkboxes.values(): cb.setChecked(False)
        self.update_count()


class ConditionEditor(QWidget):
    MODE_ITEMS = [
        ("같음 (=)", "eq", "값이 정확히 같은 행만 추출합니다.", "예: 강원본부"),
        ("같지 않음 (제외)", "neq", "입력한 값을 제외하고 추출합니다.", "예: 없음"),
        ("포함 (부분 일치)", "contains", "입력한 글자가 포함된 행을 추출합니다.", "예: 김, 장애"),
        ("포함 안함", "not_contains", "입력한 글자가 포함된 행을 제외합니다.", "예: 해지, 중지"),
        ("패턴 검색 (정규식)", "regex", "고급 패턴으로 찾습니다.", r"예: ^G\\d{3}"),
        ("숫자 초과 (>)", "gt", "입력값보다 큰 숫자만 추출합니다.", "예: 100000"),
        ("숫자 미만 (<)", "lt", "입력값보다 작은 숫자만 추출합니다.", "예: 100000"),
        ("숫자 범위 (A~B)", "between", "두 숫자 사이의 범위를 찾습니다.", "예: 1000,5000"),
        ("날짜와 같음", "date_eq", "입력한 날짜와 같은 행만 추출합니다.", "예: 2026-04-21"),
        ("날짜 범위", "date_between", "두 날짜 사이의 범위를 찾습니다.", "예: 2026-01-01,2026-03-31"),
    ]
    DISPLAY_TO_CODE = {display: code for display, code, _, _ in MODE_ITEMS}
    CODE_TO_DISPLAY = {code: display for display, code, _, _ in MODE_ITEMS}
    CODE_TO_DESC = {code: desc for _, code, desc, _ in MODE_ITEMS}
    CODE_TO_EXAMPLE = {code: example for _, code, _, example in MODE_ITEMS}

    def __init__(self, title="조건 설정"):
        super().__init__()
        self.source_path_getter = None
        self.sheet_name_getter = None
        self.custom_values_getter = None
        self.value_cache = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        
        top_title = QLabel(title)
        top_title.setObjectName("sectionTitle")
        root.addWidget(top_title)

        help_box = QFrame()
        help_box.setObjectName("helpCard")
        help_l = QVBoxLayout(help_box)
        self.lbl_mode_desc = QLabel("조건 종류를 고르면 예시가 표시됩니다.")
        self.lbl_mode_desc.setWordWrap(True)
        help_l.addWidget(self.lbl_mode_desc)
        root.addWidget(help_box)

        row = QHBoxLayout()
        self.cmb_col = QComboBox()
        self.cmb_col.currentIndexChanged.connect(self.refresh_values)
        row.addWidget(self.cmb_col, 3)

        self.cmb_mode = QComboBox()
        self.cmb_mode.addItems([display for display, _, _, _ in self.MODE_ITEMS])
        self.cmb_mode.currentIndexChanged.connect(self.update_mode_help)
        row.addWidget(self.cmb_mode, 2)

        self.edt_values = QLineEdit()
        self.edt_values.setPlaceholderText("값 직접 입력")
        row.addWidget(self.edt_values, 4)

        self.btn_add = QPushButton("조건 추가")
        self.btn_add.clicked.connect(self.add_row_from_ui)
        row.addWidget(self.btn_add, 1)
        root.addLayout(row)

        self.value_panel = ValueFilterPanel("선택 컬럼의 실제 값")
        root.addWidget(self.value_panel, 2)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["사용", "컬럼", "조건", "값", "설명"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        root.addWidget(self.table, 3)

        self.btn_remove = QPushButton("선택 조건 삭제")
        self.btn_remove.clicked.connect(self.remove_selected_rows)
        root.addWidget(self.btn_remove)

        self.update_mode_help()

    def set_source_getters(self, path_getter, sheet_getter=None):
        self.source_path_getter = path_getter
        self.sheet_name_getter = sheet_getter

    def set_custom_values_getter(self, getter):
        self.custom_values_getter = getter

    def set_columns(self, columns):
        self.cmb_col.blockSignals(True)
        self.cmb_col.clear()
        self.cmb_col.addItems(columns)
        self.cmb_col.blockSignals(False)
        if columns: self.refresh_values()

    def get_mode_code(self):
        return self.DISPLAY_TO_CODE.get(self.cmb_mode.currentText(), "eq")

    def update_mode_help(self):
        code = self.get_mode_code()
        desc = self.CODE_TO_DESC.get(code, "")
        example = self.CODE_TO_EXAMPLE.get(code, "")
        self.lbl_mode_desc.setText(f"<b>{desc}</b><br><font color='gray'>{example}</font>")

    def refresh_values(self):
        col = self.cmb_col.currentText()
        if not col: return
        
        try:
            if self.custom_values_getter:
                values = self.custom_values_getter(col)
            elif self.source_path_getter:
                path = self.source_path_getter()
                sheet = self.sheet_name_getter() if self.sheet_name_getter else None
                if not path: return
                values = extract_unique_values_fast(path, col, sheet_name=sheet)
            else:
                values = []
            self.value_panel.set_values(values)
        except:
            self.value_panel.set_values([])

    def add_row_from_ui(self):
        col = self.cmb_col.currentText()
        mode = self.get_mode_code()
        manual = clean_text(self.edt_values.text())
        vals = [clean_text(x) for x in manual.split(",") if x.strip()] if manual else self.value_panel.get_checked_values()
        
        if not col or not vals:
            QMessageBox.warning(self, "알림", "컬럼과 값을 선택하세요.")
            return
            
        self.add_condition_row(True, col, mode, ", ".join(vals))
        self.edt_values.clear()

    def add_condition_row(self, use, col, mode, vals_str):
        row = self.table.rowCount()
        self.table.insertRow(row)
        chk = QTableWidgetItem(); chk.setFlags(chk.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
        chk.setCheckState(Qt.Checked if use else Qt.Unchecked)
        self.table.setItem(row, 0, chk)
        self.table.setItem(row, 1, QTableWidgetItem(col))
        self.table.setItem(row, 2, QTableWidgetItem(self.CODE_TO_DISPLAY.get(mode, mode)))
        self.table.setItem(row, 3, QTableWidgetItem(vals_str))
        self.table.setItem(row, 4, QTableWidgetItem(self.CODE_TO_DESC.get(mode, "")))

    def remove_selected_rows(self):
        selected = self.table.selectionModel().selectedRows()
        for idx in sorted([r.row() for r in selected], reverse=True):
            self.table.removeRow(idx)

    def parse_conditions(self):
        res = []
        for r in range(self.table.rowCount()):
            if self.table.item(r, 0).checkState() == Qt.Checked:
                col = self.table.item(r, 1).text()
                mode_disp = self.table.item(r, 2).text()
                mode = self.DISPLAY_TO_CODE.get(mode_disp, "eq")
                vals = [x.strip() for x in self.table.item(r, 3).text().split(",")]
                res.append({"column": col, "mode": mode, "values": vals})
        return res
