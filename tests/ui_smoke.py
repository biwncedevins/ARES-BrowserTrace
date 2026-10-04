"""Offscreen integration test: drive real artifacts through the Qt UI.

Use on machines with a display or headless (Qt offscreen platform fallback):

    python tests/ui_smoke.py
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from PySide6.QtWidgets import QApplication


def main() -> int:
    from browsertrace.models import Session
    from browsertrace.parsing import pipeline, resolve_source
    from browsertrace.ui import apply
    from browsertrace.ui.main_window import MainWindow

    import tests.selftest as st

    work = tempfile.mkdtemp(prefix="browsertrace_ui_")
    try:
        chrome_dir = os.path.join(work, "chrome")
        ff_dir = os.path.join(work, "ff")
        os.makedirs(chrome_dir)
        os.makedirs(ff_dir)
        st.chrome_history_db(os.path.join(chrome_dir, "History"))
        st.chrome_bookmarks(os.path.join(chrome_dir, "Bookmarks"))
        st.firefox_places_db(os.path.join(ff_dir, "places.sqlite"))

        app = QApplication(sys.argv)
        apply(app)
        window = MainWindow()
        window.show()

        spec = resolve_source(folder=chrome_dir)
        result = pipeline(spec)
        window._on_loaded(result)
        app.processEvents()

        assert window.session.stats.get("total", 0) > 0
        for key, page in window.pages.items():
            if hasattr(page, "set_session"):
                page.set_session(window.session)
            app.processEvents()
            print(f"page {key:10} ok")
        app.processEvents()

        window._toggle_tz()
        app.processEvents()
        window._toggle_tz()
        window.navigate("timeline")
        window.locate_event(window.session.events[0].id)
        app.processEvents()

        reports = window.pages["reports"]
        out_dir = os.path.join(work, "out")
        reports.dest.setText(out_dir)
        reports.check_history.setChecked(True)
        reports.check_downloads.setChecked(True)
        reports.check_bookmarks.setChecked(True)
        reports.check_domains.setChecked(True)
        reports.radio_html.setChecked(True)
        reports._export()
        assert os.listdir(out_dir)
        print("export files:", sorted(os.listdir(out_dir)))

        csv_dir = os.path.join(work, "csv")
        reports.dest.setText(csv_dir)
        reports.radio_csv.setChecked(True)
        reports._export()
        print("csv files:", sorted(os.listdir(csv_dir)))

        window.close()
        print("UI INTEGRATION OK")
        return 0
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())