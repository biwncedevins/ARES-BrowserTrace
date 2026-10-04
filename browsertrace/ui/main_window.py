from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from .. import __version__
from ..models import Session
from ..resources import icon_path
from . import theme
from .loader_worker import LoadWorker
from .pages.artifact import BookmarksPage, DownloadsPage, HistoryPage, TimelinePage
from .pages.domains import DomainsPage
from .pages.findings import FindingsPage
from .pages.overview import OverviewPage
from .pages.reports import ReportsPage
from .source_dialog import SourceDialog

PAGE_KEYS = ["overview", "timeline", "history", "downloads", "bookmarks", "domains", "findings", "reports"]
NAV_LABELS = {
    "overview": "Overview",
    "timeline": "Timeline",
    "history": "History",
    "downloads": "Downloads",
    "bookmarks": "Bookmarks",
    "domains": "Domains",
    "findings": "Findings",
    "reports": "Reports",
}


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"BrowserTrace — Browser Artifact Analysis  v{__version__}")
        self.resize(1360, 840)
        self.setMinimumSize(1040, 700)
        self.setWindowIcon(QIcon(icon_path()))
        self.session = Session(self)
        self.worker = None
        self._build()

    def _build(self):
        central = QWidget()
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.sidebar = self._build_sidebar()
        layout.addWidget(self.sidebar)
        self.stack = QStackedWidget()
        layout.addWidget(self.stack, 1)
        self.setCentralWidget(central)

        on_nav = self.navigate
        self.pages = {
            "overview": OverviewPage(self.session, on_nav),
            "timeline": TimelinePage(self.session),
            "history": HistoryPage(self.session),
            "downloads": DownloadsPage(self.session),
            "bookmarks": BookmarksPage(self.session),
            "domains": DomainsPage(self.session),
            "findings": FindingsPage(self.session, self.locate_event),
            "reports": ReportsPage(self.session),
        }
        for key in PAGE_KEYS:
            self.stack.addWidget(self.pages[key])

        self._build_statusbar()
        self.navigate("overview")

    def _build_sidebar(self):
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(212)
        lay = QVBoxLayout(sidebar)
        lay.setContentsMargins(14, 16, 14, 12)
        lay.setSpacing(2)

        brand_row = QHBoxLayout()
        brand_row.setSpacing(10)
        icon_label = QLabel()
        pix = QIcon(icon_path()).pixmap(38, 38)
        if not pix.isNull():
            icon_label.setPixmap(pix)
        icon_label.setFixedSize(40, 40)
        brand_col = QVBoxLayout()
        brand_col.setSpacing(0)
        brand = QLabel("BrowserTrace")
        brand.setObjectName("BrandTitle")
        sub_brand = QLabel("FORENSIC ANALYSIS")
        sub_brand.setObjectName("BrandSub")
        brand_col.addWidget(brand)
        brand_col.addWidget(sub_brand)
        brand_row.addWidget(icon_label, 0, Qt.AlignVCenter)
        brand_row.addLayout(brand_col)
        lay.addLayout(brand_row)
        lay.addSpacing(18)

        nav_caption = QLabel("NAVIGATION")
        nav_caption.setObjectName("SectionCaption")
        lay.addWidget(nav_caption)

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        for key in PAGE_KEYS:
            btn = QPushButton(NAV_LABELS[key])
            btn.setObjectName("navButton")
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _=False, k=key: self.navigate(k))
            self.nav_group.addButton(btn)
            lay.addWidget(btn)

        lay.addStretch(1)

        footer = QFrame()
        footer.setObjectName("SideFooter")
        fl = QVBoxLayout(footer)
        fl.setContentsMargins(10, 10, 10, 10)
        fl.setSpacing(6)
        cap = QLabel("CURRENT SOURCE")
        cap.setObjectName("SectionCaption")
        self.sidebar_source = QLabel("No source loaded")
        self.sidebar_source.setProperty("muted", True)
        self.sidebar_source.setWordWrap(True)
        change = QPushButton("Change Source…")
        change.clicked.connect(self.load_source)
        fl.addWidget(cap)
        fl.addWidget(self.sidebar_source)
        fl.addWidget(change)
        lay.addWidget(footer)
        return sidebar

    def _build_statusbar(self):
        bar = QStatusBar()
        self.setStatusBar(bar)
        self.status_source = QLabel("No source")
        sep = QLabel("|")
        sep.setProperty("dimmed", True)
        self.status_counts = QLabel("")
        sep2 = QLabel("|")
        sep2.setProperty("dimmed", True)
        offline = QLabel("● LOCAL · OFFLINE")
        offline.setStyleSheet(
            f"color:{theme.OK}; font-size:10px; font-weight:600; letter-spacing:1px;"
        )
        self.tz_btn = QPushButton("UTC")
        self.tz_btn.setFixedWidth(56)
        self.tz_btn.setToolTip("Toggle between UTC and local time display")
        self.tz_btn.clicked.connect(self._toggle_tz)
        bar.addWidget(self.status_source)
        bar.addWidget(sep)
        bar.addWidget(self.status_counts)
        bar.addPermanentWidget(offline)
        bar.addPermanentWidget(sep2)
        bar.addPermanentWidget(self.tz_btn)

    # ----- navigation -----
    def navigate(self, key: str):
        if key in self.pages:
            self.stack.setCurrentWidget(self.pages[key])
            buttons = self.nav_group.buttons()
            if PAGE_KEYS.index(key) < len(buttons):
                buttons[PAGE_KEYS.index(key)].setChecked(True)

    def locate_event(self, event_id: str):
        self.navigate("timeline")
        self.pages["timeline"].search_event(event_id)

    # ----- session handling -----
    def load_source(self):
        dialog = SourceDialog(self)
        if not dialog.exec():
            return
        spec = dialog.resolve()
        if spec is None:
            return
        self._run_worker(spec, dialog.sections())

    def _run_worker(self, spec, sections):
        if self.worker and self.worker.isRunning():
            return
        self.status_source.setText(f"Analyzing {spec.label}…")
        self.worker = LoadWorker(spec, sections, self)
        self.worker.progress.connect(self.status_source.setText)
        self.worker.finished_ok.connect(self._on_loaded)
        self.worker.failed.connect(self._on_failed)
        self.worker.finished.connect(self._worker_done)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.start()

    def _on_loaded(self, result):
        self.session = Session.from_result(result, self)
        for page in self.pages.values():
            page.set_session(self.session)
        self.sidebar_source.setText(self.session.source.label if self.session.source else "—")
        self.status_source.setText(
            f"{self.session.stats.get('total', 0):,} events · "
            f"{len(self.session.findings)} findings · {self.session.load_duration_s:.2f}s"
        )
        self.status_counts.setText(
            f"{self.session.stats.get('visits', 0):,} visits  "
            f"· {self.session.stats.get('downloads', 0):,} downloads  "
            f"· {self.session.stats.get('bookmarks', 0):,} bookmarks  "
            f"· {self.session.stats.get('domains', 0):,} domains"
        )
        self.navigate("overview")

    def _on_failed(self, message: str):
        self.status_source.setText("Analysis failed")
        from PySide6.QtWidgets import QMessageBox

        QMessageBox.critical(
            self,
            "Analysis failed",
            f"BrowserTrace could not parse the selected source.\n\n{message}",
        )

    def _worker_done(self):
        self.worker = None

    def _toggle_tz(self):
        self.session.display_local = not self.session.display_local
        self.tz_btn.setText("Local" if self.session.display_local else "UTC")
        for page in self.pages.values():
            page.refresh_display()
        self.session.request_refresh()