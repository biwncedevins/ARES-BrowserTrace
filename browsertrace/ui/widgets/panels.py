"""Reusable dark-forensic UI widgets."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QCursor
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .. import theme


def make_label(text: str = "", style: str = "", mono: bool = False, selectable: bool = False) -> QLabel:
    label = QLabel(text)
    label.setTextInteractionFlags(
        Qt.TextSelectableByMouse if selectable else Qt.NoTextInteraction
    )
    if style:
        label.setStyleSheet(style)
    if mono:
        label.setProperty("mono", True)
    return label


class StatCard(QFrame):
    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        self.setObjectName("StatCard")
        self.setFixedHeight(74)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(2)
        self._value = QLabel("0")
        self._value.setObjectName("StatValue")
        self._caption = QLabel(label.upper())
        self._caption.setObjectName("StatLabel")
        lay.addStretch(1)
        lay.addWidget(self._value)
        lay.addWidget(self._caption)

    def set_value(self, text) -> None:
        self._value.setText(str(text))
        if text in (0, "0", ""):
            self._value.setStyleSheet("color:" + theme.MUTED + ";")
        else:
            self._value.setStyleSheet("color:#FFFFFF;")


class EmptyState(QWidget):
    def __init__(self, title: str, subtitle: str = "", parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignCenter)
        head = QLabel(title)
        head.setObjectName("PageTitle")
        head.setAlignment(Qt.AlignCenter)
        sub = QLabel(subtitle)
        sub.setProperty("muted", True)
        sub.setWordWrap(True)
        sub.setAlignment(Qt.AlignCenter)
        sub.setMaximumWidth(460)
        lay.addWidget(head)
        lay.addWidget(sub)


class KeyValuePanel(QScrollArea):
    """Two-column key/value inspector used for the event and finding detail panes."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        body = QWidget()
        self._inner = QVBoxLayout(body)
        self._inner.setContentsMargins(14, 12, 14, 12)
        self._inner.setSpacing(0)
        self._inner.addStretch(1)
        self.setWidget(body)
        self._rows = []
        self.setMinimumWidth(300)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

    def set_header(self, title: str, subtitle: str = "") -> None:
        self.clear()
        if title:
            head = QLabel(title)
            head.setWordWrap(True)
            head.setObjectName("PageTitle")
            self._inner.insertWidget(0, head)
            self._rows.append(head)
        if subtitle:
            sub = QLabel(subtitle)
            sub.setWordWrap(True)
            sub.setProperty("muted", True)
            self._inner.insertWidget(1, sub)
            self._rows.append(sub)

    def clear(self) -> None:
        for w in list(self._rows):
            self._inner.removeWidget(w)
            w.deleteLater()
        self._rows.clear()

    def add_row(self, key: str, value: str) -> None:
        k = QLabel(key.upper())
        k.setProperty("dimmed", True)
        k.setStyleSheet("font-size:10px; letter-spacing:1px;")
        v = QLabel(value if value else "—")
        v.setTextInteractionFlags(Qt.TextSelectableByMouse)
        v.setWordWrap(True)
        if value and len(value) > 90:
            v.setStyleSheet("font-family:Consolas,'Cascadia Mono'; color:" + theme.TEXT + "; font-size:11.5px;")
        self._inner.insertWidget(max(0, self._inner.count() - 1), k)
        self._inner.insertWidget(max(0, self._inner.count() - 1), v)
        self._inner.addSpacing(8)
        self._rows.extend([k, v])

    def add_separator(self) -> None:
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color:" + theme.BORDER + ";")
        self._inner.insertWidget(max(0, self._inner.count() - 1), line)
        self._inner.addSpacing(8)
        self._rows.append(line)


class SeverityBadge(QLabel):
    def __init__(self, severity_value: str, parent=None):
        super().__init__(severity_value.upper())
        self.setProperty("mono", True)
        color = theme.severity_color(severity_value)
        self.setStyleSheet(
            f"font-size:10px; font-weight:700; letter-spacing:1px; color:{color};"
            f" background:{theme.PANEL_ACTIVE}; border:1px solid {theme.BORDER_LIGHT};"
            " border-radius:3px; padding:1px 7px;"
        )
        self.setAlignment(Qt.AlignCenter)


class KindBadge(QLabel):
    def __init__(self, kind_value: str, parent=None):
        super().__init__(kind_value.upper())
        color = theme.KIND_COLORS.get(kind_value, theme.MUTED)
        self.setStyleSheet(
            f"font-size:10px; font-weight:700; letter-spacing:1px; color:{color};"
            f" background:{theme.PANEL_ACTIVE}; border:1px solid {theme.BORDER_LIGHT};"
            " border-radius:3px; padding:1px 7px;"
        )
        self.setAlignment(Qt.AlignCenter)


class DomainBadge(QLabel):
    def __init__(self, domain: str, parent=None):
        super().__init__(domain)
        self.setProperty("mono", True)
        self.setStyleSheet(
            f"color:{theme.SEV_LOW}; background:{theme.PANEL_ACTIVE};"
            f" border:1px solid {theme.BORDER_LIGHT}; border-radius:3px; padding:1px 8px; font-size:11px;"
        )
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setToolTip("Filter timeline to this domain")
        self.setTextInteractionFlags(Qt.NoTextInteraction)