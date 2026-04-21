from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QComboBox, QProgressBar, QTabWidget, QTextEdit, QFrame
)
from app.ui.styles import ModernStyles
from app.ui.tabs.merge_tab import MergeTab
from app.ui.tabs.single_tab import SingleFileTab
from app.ui.tabs.open_excel_tab import OpenExcelTab
from app.ui.tabs.analysis_tab import AnalysisTab
from app.ui.tabs.matching_tab import MatchingTab

class WelcomeTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        
        icon_label = QLabel("📊")
        icon_label.setStyleSheet("font-size: 64pt;")
        layout.addWidget(icon_label, alignment=Qt.AlignCenter)
        
        title = QLabel("Data Intelligence PRO")
        title.setObjectName("titleLabel")
        layout.addWidget(title, alignment=Qt.AlignCenter)
        
        desc = QLabel("최첨단 알고리즘 기반 데이터 통합 솔루션")
        desc.setStyleSheet("font-size: 13pt; color: #64748b; margin-bottom: 20px;")
        layout.addWidget(desc, alignment=Qt.AlignCenter)
        
        # Action Grid
        info = QFrame()
        info.setObjectName("premiumCard")
        info.setFixedWidth(650)
        info_l = QVBoxLayout(info)
        info_l.setSpacing(12)
        
        features = [
            ("🔗 1. 데이터 매칭", "두 데이터를 키 기준으로 병합 (VLOOKUP)"),
            ("📄 2. 단일 파일 추출", "필터링, 정렬, 중복제거를 포함한 정밀 추출"),
            ("📊 3. 열려있는 엑셀", "작업 중인 엑셀 시트에서 즉시 데이터 파싱"),
            ("📂 4. 병합", "동일 규격의 여러 파일을 하나의 통합본으로 결합"),
            ("📈 5. 데이터 분석", "데이터 분포, 빈도, 통계 자동 리포팅")
        ]
        
        for name, d in features:
            row = QHBoxLayout()
            row.addWidget(QLabel(f"<b>{name}</b>"))
            row.addStretch()
            row.addWidget(QLabel(f"<font color='#64748b'>{d}</font>"))
            info_l.addLayout(row)
            
        layout.addWidget(info, alignment=Qt.AlignCenter)
        
        # Expert Section
        expert_box = QFrame()
        expert_box.setObjectName("expertCard")
        expert_box.setFixedWidth(650)
        expert_l = QVBoxLayout(expert_box)
        expert_l.addWidget(QLabel("<b>🚀 전문가 기법 TOP 10</b>"))
        
        tips = [
            "1. 키 컬럼 정규화 (공백 제거 및 대소문자 통일)",
            "2. 데이터 타입 강제 변환 (문자/숫자 불일치 해결)",
            "3. 참조 데이터 중복 제거 (원본 행 팽창 방지)",
            "4. 다중 조건 지능형 필터링 (노이즈 원천 차단)",
            "5. 정규식(Regex) 활용 패턴 기반 정밀 추출",
            "6. 열려있는 엑셀 실시간 연동 및 동기화",
            "7. 서비스(소) 결측치 자동 추론 채움 기술",
            "8. 고유값 빈도 분석을 통한 데이터 품질 검증",
            "9. HTML/웹 데이터 테이블 자동 파싱 및 복원",
            "10. 스마트 인코딩 감지 (한글 깨짐 현상 자동 방지)"
        ]
        
        tips_row = QHBoxLayout()
        left_tips = QVBoxLayout(); right_tips = QVBoxLayout()
        for i, tip in enumerate(tips):
            label = QLabel(f"• {tip}")
            label.setStyleSheet("font-size: 10pt; color: #1e40af;")
            if i < 5: left_tips.addWidget(label)
            else: right_tips.addWidget(label)
        
        tips_row.addLayout(left_tips)
        tips_row.addLayout(right_tips)
        expert_l.addLayout(tips_row)
        layout.addWidget(expert_box, alignment=Qt.AlignCenter)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("통합 데이터 병합·추출기 PRO")
        self.resize(1280, 850)
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.root_layout = QVBoxLayout(self.central_widget)
        
        self.build_ui()
        self.apply_theme("Ocean")

    def build_ui(self):
        # Header
        header = QHBoxLayout()
        title = QLabel("Data Extractor PRO")
        title.setObjectName("titleLabel")
        header.addWidget(title)
        header.addStretch()
        
        header.addWidget(QLabel("테마 설정"))
        self.cmb_theme = QComboBox()
        self.cmb_theme.addItems(list(ModernStyles.THEMES.keys()))
        self.cmb_theme.currentTextChanged.connect(self.apply_theme)
        header.addWidget(self.cmb_theme)
        self.root_layout.addLayout(header)

        # Progress Bar
        self.progress = QProgressBar()
        self.progress.setFixedHeight(12)
        self.progress.setVisible(False)
        self.root_layout.addWidget(self.progress)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.addTab(WelcomeTab(), "🏠 홈")
        
        self.matching_tab = MatchingTab(self.log)
        self.tabs.addTab(self.matching_tab, "🔗 1. 데이터 매칭")
        
        self.single_tab = SingleFileTab(self.log)
        self.tabs.addTab(self.single_tab, "📄 2. 단일 파일 추출")
        
        self.open_excel_tab = OpenExcelTab(self.log)
        self.tabs.addTab(self.open_excel_tab, "📊 3. 열려있는 엑셀")
        
        self.merge_tab = MergeTab(self.log)
        self.tabs.addTab(self.merge_tab, "📂 4. 병합")
        
        self.analysis_tab = AnalysisTab(self.log)
        self.tabs.addTab(self.analysis_tab, "📈 5. 데이터 분석")
        
        self.root_layout.addWidget(self.tabs)

        # Log
        log_card = QFrame(); log_card.setObjectName("cardFrame")
        log_l = QVBoxLayout(log_card)
        log_l.addWidget(QLabel("🔔 알림 및 상태 로그"))
        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setMaximumHeight(150)
        log_l.addWidget(self.txt_log)
        self.root_layout.addWidget(log_card)

    def apply_theme(self, name):
        self.setStyleSheet(ModernStyles.get_qss(name))

    def log(self, msg):
        self.txt_log.append(f"• {msg}")
        
    def set_progress(self, val):
        self.progress.setVisible(True)
        self.progress.setValue(val)
        if val >= 100:
            self.progress.setVisible(False)
            self.progress.setValue(0)

    def closeEvent(self, event):
        # Stop background workers if running
        tabs = [self.matching_tab, self.single_tab, self.open_excel_tab, self.merge_tab]
        for tab in tabs:
            if hasattr(tab, "worker") and tab.worker and tab.worker.isRunning():
                tab.worker.terminate()
                tab.worker.wait()
        event.accept()
