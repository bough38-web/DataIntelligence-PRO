class ModernStyles:
    THEMES = {
        "Ocean": {
            "bg": "#f4f8fb", 
            "card": "#ffffff", 
            "line": "#dbe4ef", 
            "text": "#1f2937", 
            "primary": "#2563eb", 
            "primary_hover": "#1d4ed8", 
            "primary_press": "#1e40af", 
            "chunk": "#22c55e", 
            "header": "#eff6ff",
            "accent": "#3b82f6"
        },
        "Forest": {
            "bg": "#f5faf6", 
            "card": "#ffffff", 
            "line": "#d8e7db", 
            "text": "#203126", 
            "primary": "#2f855a", 
            "primary_hover": "#276749", 
            "primary_press": "#22543d", 
            "chunk": "#38a169", 
            "header": "#edf7f1",
            "accent": "#48bb78"
        },
        "Sunset": {
            "bg": "#fff8f3", 
            "card": "#ffffff", 
            "line": "#f0ddd2", 
            "text": "#3f2d22", 
            "primary": "#dd6b20", 
            "primary_hover": "#c05621", 
            "primary_press": "#9c4221", 
            "chunk": "#ed8936", 
            "header": "#fff1e8",
            "accent": "#f6ad55"
        },
        "Plum": {
            "bg": "#faf7fc", 
            "card": "#ffffff", 
            "line": "#e7def0", 
            "text": "#2d1f3a", 
            "primary": "#805ad5", 
            "primary_hover": "#6b46c1", 
            "primary_press": "#553c9a", 
            "chunk": "#9f7aea", 
            "header": "#f3ecff",
            "accent": "#b794f4"
        },
        "Dark Slate": {
            "bg": "#0f172a", 
            "card": "#1e293b", 
            "line": "#334155", 
            "text": "#f8fafc", 
            "primary": "#3b82f6", 
            "primary_hover": "#60a5fa", 
            "primary_press": "#2563eb", 
            "chunk": "#10b981", 
            "header": "#1e293b",
            "accent": "#6366f1"
        },
    }

    @staticmethod
    def get_qss(theme_name="Ocean"):
        t = ModernStyles.THEMES.get(theme_name, ModernStyles.THEMES["Ocean"])
        return f"""
            QWidget {{
                background-color: {t['bg']};
                color: {t['text']};
                font-family: 'Segoe UI', 'Malgun Gothic', sans-serif;
                font-size: 10pt;
            }}
            
            QMainWindow {{
                background-color: {t['bg']};
            }}

            QFrame {{
                background: {t['card']};
                border: 1px solid {t['line']};
                border-radius: 12px;
            }}

            QPushButton {{
                background-color: {t['primary']};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {t['primary_hover']};
            }}
            QPushButton:pressed {{
                background-color: {t['primary_press']};
            }}
            QPushButton:disabled {{
                background-color: {t['line']};
                color: #9ca3af;
            }}

            QLineEdit, QComboBox, QTextEdit, QTableWidget {{
                background-color: {t['card']};
                border: 1px solid {t['line']};
                border-radius: 8px;
                padding: 6px;
                selection-background-color: {t['primary']};
            }}
            
            QComboBox::drop-down {{
                border: none;
            }}

            QHeaderView::section {{
                background-color: {t['header']};
                padding: 4px;
                border: 1px solid {t['line']};
                font-weight: bold;
            }}

            QProgressBar {{
                border: 1px solid {t['line']};
                border-radius: 4px;
                text-align: center;
                background-color: {t['card']};
            }}
            QProgressBar::chunk {{
                background-color: {t['chunk']};
                border-radius: 3px;
            }}

            QTabWidget::pane {{
                border: 1px solid {t['line']};
                border-radius: 8px;
                background: {t['card']};
                top: -1px;
            }}
            QTabBar::tab {{
                background: {t['bg']};
                border: 1px solid {t['line']};
                border-bottom: none;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                padding: 8px 16px;
                margin-right: 4px;
            }}
            QTabBar::tab:selected {{
                background: {t['card']};
                border-bottom: 2px solid {t['primary']};
                font-weight: bold;
            }}

            QScrollBar:vertical {{
                border: none;
                background: transparent;
                width: 10px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {t['line']};
                min-height: 20px;
                border-radius: 5px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            
            QLabel#titleLabel {{
                font-size: 24pt;
                font-weight: 800;
                color: {t['primary']};
                margin-top: 10px;
                margin-bottom: 5px;
            }}
            
            QLabel#sectionTitle {{
                font-size: 12pt;
                font-weight: 700;
                color: #334155;
                margin-top: 5px;
            }}
            
            QFrame#cardFrame {{
                background: {t['card']};
                border: 1px solid {t['line']};
                border-radius: 16px;
            }}

            QFrame#premiumCard {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #ffffff, stop:1 #f8fafc);
                border: 1px solid {t['line']};
                border-radius: 20px;
                padding: 20px;
            }}

            QFrame#expertCard {{
                background: #eff6ff;
                border: 1px solid #bfdbfe;
                border-radius: 16px;
                padding: 15px;
                color: #1e40af;
            }}

            QScrollArea {{
                border: none;
                background: transparent;
            }}
        """
