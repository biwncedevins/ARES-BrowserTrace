from __future__ import annotations

import traceback

from PySide6.QtCore import QThread, Signal

from ..parsing import pipeline


class LoadWorker(QThread):
    progress = Signal(str)
    finished_ok = Signal(object)
    failed = Signal(str)

    def __init__(self, spec, sections, parent=None):
        super().__init__(parent)
        self.spec = spec
        self.sections = sections

    def run(self):
        try:
            result = pipeline(
                self.spec,
                progress=lambda msg: self.progress.emit(msg),
                load_sections=self.sections,
            )
            self.finished_ok.emit(result)
        except Exception as exc:  # noqa: BLE001
            traceback.print_exc()
            self.failed.emit(str(exc))