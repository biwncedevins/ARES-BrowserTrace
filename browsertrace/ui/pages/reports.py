from __future__ import annotations

import os
from datetime import datetime

from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from ...export import export_csv_report, export_html_report


class ReportsPage(QWidget):
    def __init__(self, session, parent=None):
        super().__init__(parent)
        self.session = session
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 18, 24, 18)
        root.setSpacing(12)

        head = QVBoxLayout()
        head.setSpacing(2)
        t = QLabel("Reports")
        t.setObjectName("PageTitle")
        sub = QLabel("Export the analyzed artifacts to a clean HTML report or machine-readable CSV files.")
        sub.setObjectName("PageSub")
        head.addWidget(t)
        head.addWidget(sub)
        root.addLayout(head)

        scope_card = QFrame()
        scope_card.setProperty("card", True)
        sc = QVBoxLayout(scope_card)
        sc.setContentsMargins(16, 12, 16, 12)

        caption = QLabel("INCLUDE SECTIONS")
        caption.setObjectName("SectionCaption")
        sc.addWidget(caption)
        grid = QHBoxLayout()
        grid.setSpacing(22)
        self.check_timeline = QCheckBox("Timeline")
        self.check_history = QCheckBox("History")
        self.check_downloads = QCheckBox("Downloads")
        self.check_bookmarks = QCheckBox("Bookmarks")
        self.check_findings = QCheckBox("Findings")
        self.check_domains = QCheckBox("Domains")
        for box in (self.check_timeline, self.check_findings):
            box.setChecked(True)
        for box in (self.check_timeline, self.check_history, self.check_downloads,
                    self.check_bookmarks, self.check_findings, self.check_domains):
            grid.addWidget(box)
        grid.addStretch(1)
        sc.addLayout(grid)
        root.addWidget(scope_card)

        fmt_card = QFrame()
        fmt_card.setProperty("card", True)
        fc = QVBoxLayout(fmt_card)
        fc.setContentsMargins(16, 12, 16, 12)
        caption2 = QLabel("FORMAT")
        caption2.setObjectName("SectionCaption")
        fc.addWidget(caption2)
        grid2 = QHBoxLayout()
        self.radio_html = QRadioButton("HTML report (self-contained, styled for review)")
        self.radio_csv = QRadioButton("CSV files (timeline + selected sections as CSV)")
        self.radio_html.setChecked(True)
        grid2.addWidget(self.radio_html)
        grid2.addWidget(self.radio_csv)
        grid2.addStretch(1)
        fc.addLayout(grid2)
        root.addWidget(fmt_card)

        dest_card = QFrame()
        dest_card.setProperty("card", True)
        dc = QVBoxLayout(dest_card)
        dc.setContentsMargins(16, 12, 16, 12)
        caption3 = QLabel("DESTINATION")
        caption3.setObjectName("SectionCaption")
        dc.addWidget(caption3)
        row = QHBoxLayout()
        self.dest = QLineEdit()
        self.dest.setPlaceholderText("Leave empty to write to the Desktop")
        browse = QPushButton("Browse…")
        browse.clicked.connect(self._browse)
        row.addWidget(self.dest, 1)
        row.addWidget(browse)
        dc.addLayout(row)
        self.status = QLabel("")
        self.status.setProperty("muted", True)
        self.status.setWordWrap(True)
        dc.addWidget(self.status)
        root.addWidget(dest_card)

        action_row = QHBoxLayout()
        self.export_btn = QPushButton("Export Report")
        self.export_btn.setObjectName("primary")
        self.export_btn.clicked.connect(self._export)
        self.open_btn = QPushButton("Open Output Folder")
        self.open_btn.setEnabled(False)
        self.open_btn.clicked.connect(self._open_output)
        action_row.addWidget(self.export_btn)
        action_row.addWidget(self.open_btn)
        action_row.addStretch(1)
        root.addLayout(action_row)

        note = QLabel("Reports contain only the selected artifacts. Credentials are never accessed. "
                      "Everything is generated locally.")
        note.setProperty("dimmed", True)
        note.setWordWrap(True)
        root.addWidget(note)
        root.addStretch(1)

    def set_session(self, session):
        self.session = session
        self.open_btn.setEnabled(False)
        self.status.setText("")

    def _browse(self):
        path = QFileDialog.getExistingDirectory(self, "Choose output folder")
        if path:
            self.dest.setText(path)
        self.open_btn.setEnabled(False)

    def _output_path(self) -> str:
        chosen = self.dest.text().strip()
        if chosen:
            return chosen
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        label = os.path.basename(self.session.source.label) if self.session.source else "session"
        return os.path.join(desktop, f"BrowserTrace_{label}_{stamp}")

    def _export(self):
        if not self.session.events and not self.session.findings:
            QMessageBox.warning(self, "Nothing to export", "Load a browser source before exporting.")
            return
        scope = {
            "timeline": self.check_timeline.isChecked(),
            "history": self.check_history.isChecked(),
            "downloads": self.check_downloads.isChecked(),
            "bookmarks": self.check_bookmarks.isChecked(),
            "findings": self.check_findings.isChecked(),
            "domains": self.check_domains.isChecked(),
        }
        out = self._output_path()
        try:
            if self.radio_html.isChecked():
                os.makedirs(out, exist_ok=True)
                path = os.path.join(out, "BrowserTrace_report.html")
                export_html_report(self.session, path, scope)
                written = [path]
            else:
                written = export_csv_report(self.session, out, scope)
        except OSError as exc:
            QMessageBox.critical(self, "Export failed", f"{exc}")
            return
        self._last_output = out
        self.status.setText("Wrote:\n" + "\n".join(written))
        self.open_btn.setEnabled(True)

    def _open_output(self):
        out = getattr(self, "_last_output", "")
        if out and os.path.isdir(out):
            os.startfile(out)

    def refresh_display(self):
        pass