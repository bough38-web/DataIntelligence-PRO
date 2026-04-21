import os
import pandas as pd
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFileDialog, QComboBox, QTableWidget, QTableWidgetItem, 
    QHeaderView, QSplitter, QFrame, QScrollArea, QCheckBox
)
from app.utils.common import get_readable_file_path, is_file_locked
from app.core.handlers import get_sheet_names, load_file_to_df

class AnalysisTab(QWidget):
    def __init__(self, log_cb):
        super().__init__()
        self.log_cb = log_cb
        self.df = None
        self.build_ui()

    def build_ui(self):
        root = QVBoxLayout(self)
        
        top = QHBoxLayout()
        self.btn_load = QPushButton("📊 분석할 파일 로드")
        self.btn_load.clicked.connect(self.select_file)
        top.addWidget(self.btn_load)
        
        self.lbl_file = QLabel("파일을 선택하세요")
        top.addWidget(self.lbl_file)
        top.addStretch()
        
        self.cmb_sheet = QComboBox()
        self.cmb_sheet.currentIndexChanged.connect(self.reload_data)
        top.addWidget(self.cmb_sheet)
        
        self.btn_refresh = QPushButton("새로고침")
        self.btn_refresh.clicked.connect(self.reload_data)
        top.addWidget(self.btn_refresh)
        root.addLayout(top)

        # Expert / Options Row
        options_row = QHBoxLayout()
        
        expert_card = QFrame(); expert_card.setObjectName("expertCard")
        expert_l = QHBoxLayout(expert_card)
        expert_l.setContentsMargins(10, 5, 10, 5)
        expert_l.addWidget(QLabel("<b>🚀 전문가 분석:</b>"))
        
        self.chk_auto_detect = QCheckBox("데이터 타입 자동 추론")
        self.chk_auto_detect.setChecked(True)
        expert_l.addWidget(self.chk_auto_detect)
        
        self.chk_outlier = QCheckBox("이상치(Outlier) 강조")
        self.chk_outlier.setChecked(True)
        expert_l.addWidget(self.chk_outlier)
        
        expert_l.addStretch()
        options_row.addWidget(expert_card, 1)
        root.addLayout(options_row)

        split = QSplitter(Qt.Horizontal)
        
        # Left: Column Stats
        left_card = QFrame(); left_card.setObjectName("cardFrame")
        left_l = QVBoxLayout(left_card)
        lbl_stats = QLabel("📝 컬럼별 기본 통계"); lbl_stats.setObjectName("sectionTitle")
        left_l.addWidget(lbl_stats)
        self.tbl_stats = QTableWidget(0, 4)
        self.tbl_stats.setHorizontalHeaderLabels(["컬럼명", "데이터수", "고유값수", "결측치"])
        self.tbl_stats.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_stats.itemSelectionChanged.connect(self.on_column_selected)
        left_l.addWidget(self.tbl_stats)
        split.addWidget(left_card)

        # Right: Frequency / Details
        right_card = QFrame(); right_card.setObjectName("cardFrame")
        right_l = QVBoxLayout(right_card)
        self.lbl_detail_title = QLabel("🔍 빈도 분석 (TOP 50)")
        right_l.addWidget(self.lbl_detail_title)
        
        self.tbl_freq = QTableWidget(0, 3)
        self.tbl_freq.setHorizontalHeaderLabels(["값", "빈도(건)", "비중(%)"])
        self.tbl_freq.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        right_l.addWidget(self.tbl_freq)
        split.addWidget(right_card)

        split.setStretchFactor(0, 4)
        split.setStretchFactor(1, 6)
        root.addWidget(split)

    def log(self, msg):
        self.log_cb(f"[분석] {msg}")

    def select_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "분석 파일 선택", "", "Data (*.csv *.xlsx *.xlsm *.xls *.html *.htm)")
        if not path: return
        self.file_path = path
        self.lbl_file.setText(os.path.basename(path))
        
        readable = get_readable_file_path(path)
        names = get_sheet_names(readable)
        self.cmb_sheet.clear()
        if names: self.cmb_sheet.addItems(names)
        else: self.cmb_sheet.addItem("(기본)")
        self.reload_data()

    def reload_data(self):
        if not hasattr(self, 'file_path'): return
        try:
            sheet = self.cmb_sheet.currentText()
            if sheet == "(기본)": sheet = None
            self.df = load_file_to_df(get_readable_file_path(self.file_path), sheet_name=sheet)
            self.refresh_stats()
            self.log(f"데이터 로드 완료: {len(self.df):,}행")
        except Exception as e:
            self.log(f"로드 실패: {e}")

    def refresh_stats(self):
        if self.df is None: return
        self.tbl_stats.setRowCount(0)
        for col in self.df.columns:
            row_idx = self.tbl_stats.rowCount()
            self.tbl_stats.insertRow(row_idx)
            
            non_null = self.df[col].count()
            unique = self.df[col].nunique()
            nulls = self.df[col].isna().sum()
            
            self.tbl_stats.setItem(row_idx, 0, QTableWidgetItem(str(col)))
            self.tbl_stats.setItem(row_idx, 1, QTableWidgetItem(f"{non_null:,}"))
            self.tbl_stats.setItem(row_idx, 2, QTableWidgetItem(f"{unique:,}"))
            self.tbl_stats.setItem(row_idx, 3, QTableWidgetItem(f"{nulls:,}"))

    def on_column_selected(self):
        selected = self.tbl_stats.selectedItems()
        if not selected or self.df is None: return
        col_name = self.tbl_stats.item(selected[0].row(), 0).text()
        self.lbl_detail_title.setText(f"🔍 '{col_name}' 빈도 분석 (TOP 50)")
        
        counts = self.df[col_name].value_counts(dropna=False).head(50)
        total = len(self.df)
        
        self.tbl_freq.setRowCount(0)
        for val, count in counts.items():
            row_idx = self.tbl_freq.rowCount()
            self.tbl_freq.insertRow(row_idx)
            
            percent = (count / total * 100) if total > 0 else 0
            
            self.tbl_freq.setItem(row_idx, 0, QTableWidgetItem(str(val)))
            self.tbl_freq.setItem(row_idx, 1, QTableWidgetItem(f"{count:,}"))
            self.tbl_freq.setItem(row_idx, 2, QTableWidgetItem(f"{percent:.1f}%"))
