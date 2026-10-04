from __future__ import annotations

from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QWidget

BG = "#0B0D0F"
PANEL = "#121519"
PANEL_ALT = "#161A1F"
PANEL_ACTIVE = "#1A1F25"
BORDER = "#232830"
BORDER_LIGHT = "#2C333C"
TEXT = "#E7EAEE"
MUTED = "#8A919A"
DIM = "#5A626B"
ACCENT = "#C7383E"
ACCENT_BRIGHT = "#E45056"
ACCENT_SOFT = "#8F242A"
ACCENT_BG = "rgba(199, 56, 62, 0.16)"
SEV_HIGH = "#E45555"
SEV_MEDIUM = "#DFA84A"
SEV_LOW = "#5FA3E2"
SEV_INFO = "#7E8791"
OK = "#57B06B"

KIND_COLORS = {
    "visit": "#6FB3E0",
    "download": "#E47373",
    "bookmark": "#82BF6E",
}


def severity_color(sev_value: str) -> str:
    return {
        "high": SEV_HIGH,
        "medium": SEV_MEDIUM,
        "low": SEV_LOW,
        "info": SEV_INFO,
    }.get(sev_value, MUTED)


def scrollbar_qss() -> str:
    return """
    QScrollBar:vertical { background: transparent; width:12px; margin:2px; }
    QScrollBar::handle:vertical { background:#2A313B; border-radius:4px; min-height:30px; }
    QScrollBar::handle:vertical:hover { background:#39424E; }
    QScrollBar:horizontal { background: transparent; height:12px; margin:2px; }
    QScrollBar::handle:horizontal { background:#2A313B; border-radius:4px; min-width:30px; }
    QScrollBar::add-line, QScrollBar::sub-line { width:0; height:0; }
    QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }
    """


STYLESHEET = f"""
QMainWindow, QDialog {{ background: {BG}; }}
QWidget {{ color: {TEXT}; }}

#Sidebar {{ background: {PANEL}; border-right: 1px solid {BORDER}; }}
#SideFooter {{ background: {BG}; border-top: 1px solid {BORDER}; }}
#BrandIcon {{ background: {BG}; border: 1px solid {BORDER}; border-radius: 7px; }}

QLabel {{ background: transparent; }}
QLabel#PageTitle {{ font-size: 17px; font-weight: 700; color: #FFFFFF; letter-spacing: .3px; }}
QLabel#PageSub {{ color: {MUTED}; font-size: 11.5px; }}
QLabel#BrandTitle {{ font-size: 15px; font-weight: 700; color: #FFFFFF; letter-spacing: .5px; }}
QLabel#BrandSub {{ font-size: 8.5px; color: {MUTED}; letter-spacing: 2px; }}
QLabel#SectionCaption {{ color: {DIM}; font-size: 10px; letter-spacing: 1.6px; }}
QLabel[muted="true"] {{ color: {MUTED}; }}
QLabel[dimmed="true"] {{ color: {DIM}; }}
QLabel[mono="true"] {{ font-family: Consolas, "Cascadia Mono"; }}

#StatValue {{ font-size: 22px; font-weight: 700; color: #FFFFFF; }}
#StatLabel {{ color: {MUTED}; font-size: 10px; letter-spacing: 1px; }}
#StatCard {{ background: {PANEL}; border: 1px solid {BORDER}; border-radius: 7px; }}
#StatCard:hover {{ border-color: {BORDER_LIGHT}; }}

QFrame[card="true"] {{ background: {PANEL}; border: 1px solid {BORDER}; border-radius: 7px; }}

QPushButton {{ background: #1C2128; border: 1px solid {BORDER_LIGHT}; border-radius: 5px;
              padding: 6px 13px; color: {TEXT}; font-size: 12px; }}
QPushButton:hover {{ border-color: {ACCENT}; }}
QPushButton:pressed {{ background: #242B34; }}
QPushButton:disabled {{ color: {DIM}; border-color: {BORDER}; background: {PANEL}; }}
QPushButton#primary {{ background: {ACCENT_SOFT}; border-color: {ACCENT}; color: #FFFFFF; font-weight: 600; }}
QPushButton#primary:hover {{ background: {ACCENT}; }}
QPushButton#navButton {{ background: transparent; border: none; border-left: 3px solid transparent;
                         border-radius: 0; text-align: left; padding: 9px 14px; color: {MUTED};
                         font-size: 13px; }}
QPushButton#navButton:hover {{ color: #FFFFFF; background: {PANEL_ACTIVE}; }}
QPushButton#navButton:checked {{ color: #FFFFFF; background: {ACCENT_BG};
                                 border-left: 3px solid {ACCENT}; font-weight: 600; }}

QLineEdit, QComboBox, QDateTimeEdit, QSpinBox, QDateEdit {{ background: {PANEL_ALT};
    border: 1px solid {BORDER}; border-radius: 5px; padding: 5px 9px; color: {TEXT};
    selection-background-color: {ACCENT_SOFT}; }}
QLineEdit:focus, QComboBox:focus, QDateTimeEdit:focus {{ border-color: {ACCENT}; }}
QComboBox::drop-down {{ border: none; width: 20px; }}
QComboBox QAbstractItemView {{ background: {PANEL_ALT}; border: 1px solid {BORDER};
    selection-background-color: {ACCENT_SOFT}; selection-color: #FFFFFF; outline: none; }}

QCheckBox, QRadioButton {{ spacing: 6px; color: {TEXT}; font-size: 12px; }}
QCheckBox::indicator, QRadioButton::indicator {{ width: 14px; height: 14px; border: 1px solid {BORDER_LIGHT};
    background: {PANEL_ALT}; border-radius: 3px; }}
QCheckBox::indicator:checked {{ background: {ACCENT}; border-color: {ACCENT}; }}
QRadioButton::indicator {{ border-radius: 7px; }}
QRadioButton::indicator:checked {{ background: {ACCENT}; border-color: {ACCENT}; }}

QTableView {{ background: {PANEL}; alternate-background-color: {PANEL}; gridline-color: #1B2027;
    border: 1px solid {BORDER}; border-radius: 6px; selection-background-color: #2A323D;
    selection-color: #FFFFFF; outline: none; }}
QTableView::item {{ border-bottom: 1px solid #161B20; padding: 2px 6px; }}
QHeaderView::section {{ background: #14181D; color: {MUTED}; border: none; border-bottom: 1px solid {BORDER};
    padding: 7px 8px; font-size: 10px; letter-spacing: 1.1px; text-transform: uppercase; }}
QTableCornerButton::section {{ background: #14181D; border: none; }}

QSplitter::handle {{ background: transparent; width: 6px; height: 6px; }}
QSplitter::handle:hover {{ background: {ACCENT_BG}; }}

QStatusBar {{ background: {PANEL}; border-top: 1px solid {BORDER}; color: {MUTED}; }}
QStatusBar QLabel {{ color: {MUTED}; font-size: 11.5px; }}

QGroupBox {{ border: 1px solid {BORDER}; border-radius: 7px; margin-top: 12px; padding-top: 4px; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 5px; color: {MUTED};
    font-size: 10.5px; letter-spacing: 1px; }}

QMenuBar {{ background: {PANEL}; }}
QMenu {{ background: {PANEL_ALT}; border: 1px solid {BORDER}; padding: 4px; }}
QMenu::item {{ padding: 6px 22px; border-radius: 4px; color: {TEXT}; }}
QMenu::item:selected {{ background: {ACCENT_SOFT}; }}

QToolTip {{ background: {PANEL_ACTIVE}; color: {TEXT}; border: 1px solid {BORDER_LIGHT};
    padding: 4px 8px; font-size: 11.5px; }}

QListWidget, QTreeWidget, QListWidget::item {{ background: {PANEL_ALT}; border: none; }}
QListWidget::item {{ padding: 6px 8px; border-radius: 4px; }}
QListWidget::item:selected, QListWidget::item:hover {{ background: #212831; }}
QTreeWidget::item {{ padding: 4px 2px; }}
QTreeWidget::item:selected {{ background: {ACCENT_SOFT}; color: #FFFFFF; }}

QTabBar::tab {{ background: {PANEL_ACTIVE}; color: {MUTED}; padding: 7px 16px; border: 1px solid {BORDER};
    border-bottom: none; border-top-left-radius: 5px; border-top-right-radius: 5px; }}
QTabBar::tab:selected {{ background: {PANEL}; color: #FFFFFF; border-top: 2px solid {ACCENT}; }}

QProgressBar {{ background: {PANEL_ALT}; border: 1px solid {BORDER}; border-radius: 5px;
    height: 8px; text-align: center; }}
QProgressBar::chunk {{ background: {ACCENT}; border-radius: 4px; }}

QTextBrowser, QTextEdit {{ background: {PANEL_ALT}; border: 1px solid {BORDER}; border-radius: 6px;
    color: {TEXT}; }}
""" + scrollbar_qss()


def apply(app, accent: str = None) -> None:
    app.setStyle("Fusion")
    if accent:
        app.setProperty("accent", accent)
    app.setPalette(palette())
    app.setStyleSheet(STYLESHEET)
    font = QFont("Segoe UI", 9)
    font.setStyleStrategy(QFont.PreferAntialias)
    app.setFont(font)


def palette():
    from PySide6.QtGui import QPalette

    pal = QPalette()
    pal.setColor(QPalette.Window, QColor(BG))
    pal.setColor(QPalette.WindowText, QColor(TEXT))
    pal.setColor(QPalette.Base, QColor(PANEL))
    pal.setColor(QPalette.AlternateBase, QColor(PANEL))
    pal.setColor(QPalette.ToolTipBase, QColor(PANEL_ACTIVE))
    pal.setColor(QPalette.ToolTipText, QColor(TEXT))
    pal.setColor(QPalette.Text, QColor(TEXT))
    pal.setColor(QPalette.Button, QColor("#1C2128"))
    pal.setColor(QPalette.ButtonText, QColor(TEXT))
    pal.setColor(QPalette.Highlight, QColor(ACCENT))
    pal.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))
    pal.setColor(QPalette.PlaceholderText, QColor(DIM))
    pal.setColor(QPalette.Link, QColor(SEV_LOW))
    return pal