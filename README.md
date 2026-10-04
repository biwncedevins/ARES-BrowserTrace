# BrowserTrace

**Privacy-first browser artifact analysis for Windows.**

BrowserTrace reads browser artifacts from **Google Chrome**, **Microsoft Edge**
and **Mozilla Firefox** and turns them into a clear forensic timeline. It is an
*artifact viewer and timeline analyzer* — never a credential-recovery tool.

> **Privacy promise.** BrowserTrace never extracts, displays, decrypts or recovers
> passwords, cookies, tokens, autofill data or any other credentials. It only reads
> history, download and bookmark artifacts that **you explicitly select**. All
> parsing, timestamp normalization, grouping and heuristics run **locally and
> offline**. Nothing ever leaves the machine; there are no telemetry endpoints.

---

## Features

- **Auto-detection** of installed Chrome / Edge / Firefox profiles from default
  installation locations.
- **Manual selection** of any profile folder or individual artifact files
  (`History`, `places.sqlite`, `Bookmarks`).
- **Parsers** for browser history, downloads and bookmarks across all three browsers.
- **TimeForge timestamp normalization** — every native timestamp (Chromium/WebKit
  microseconds since 1601, Firefox PRTime, Unix seconds/milliseconds/microseconds
  and ISO-8601 strings) is normalized into one canonical timezone-aware format.
- **Unified Timeline** combining visits, downloads and bookmark activity,
  sortable and filterable by keyword, event type, domain and time range.
- **Domain grouping** with per-domain counts, activity span and source browsers.
- **Forensic heuristics** that flag:
  - suspicious / disguised downloads (double extensions, executable extensions,
    raw-IP hosts, URL shorteners, first-contact downloads)
  - uncommon domains (domains outside a known-traffic reference list)
  - repeated visits and heavily used URLs / domains
  - unusual activity patterns (off-hours activity, one-minute bursts,
    rapid successive downloads, long-running campaigns)
- **Local exports** to a styled **HTML report** and/or multiple **CSV** files.
- Professional near-black forensic UI with a single crimson accent.

## Requirements

- Windows 10 / 11 (Windows-first; runs wherever Python does)
- Python **3.11+**
- PySide6

## Quick start (run from source)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py          # or double-click run.bat
```

## Build the standalone Windows .exe

```powershell
.\build.bat
```

or manually:

```powershell
pip install -r requirements.txt -r requirements-build.txt
python scripts\make_icon.py          # regenerate the application icon
python tests\selftest.py             # verify the pipeline
python -m PyInstaller --noconfirm --clean BrowserTrace.spec
```

The result is `dist\BrowserTrace.exe` — a single windowed executable with the
custom BrowserTrace icon and version resource embedded.

## Workflow

```
SELECT SOURCE → PARSE SQLITE → NORMALIZE TIME → GROUP EVENTS → FLAG ANOMALIES → TIMELINE → REPORT
```

1. Launch BrowserTrace. On first run the **Select Source** dialog appears.
2. Pick an auto-detected profile, browse to a profile folder, or open artifact
   files directly.
3. BrowserTrace snapshots the SQLite files (so the browser lock never blocks it),
   parses history/downloads/bookmarks, normalizes every timestamp with TimeForge,
   groups by domain and runs the heuristic engine.
4. Review the **Overview**, **Timeline**, per-artifact tabs, **Domains** and
   **Findings**. Double-click a cell in any table to copy a URL; double-click a
   finding to jump to its place in the timeline.
5. Export a report from the **Reports** page.

## Project structure

```
├── run.py                      Entry point
├── run.bat                     Source launcher
├── build.bat                   One-step .exe build
├── BrowserTrace.spec           PyInstaller spec (icon + version resource)
├── requirements.txt            Runtime dependencies
├── requirements-build.txt      Build-time dependencies
│
├── browsertrace/
│   ├── app.py                  QApplication bootstrap
│   ├── resources.py            Frozen/source resource path helper
│   │
│   ├── models/                 Data layer (events, findings, source, session)
│   ├── core/                   timeforge.py, domains.py, format.py, stats.py
│   ├── parsing/                reader, detector, chromium, firefox, loader
│   ├── heuristics/             analyzer.py + known-domain reference list
│   ├── export/                 csv_export.py, html_export.py
│   └── ui/                     theme, sidebar/main window, pages, widgets
│
├── resources/ (browsertrace/resources)
│   ├── icon.ico / icon.png     Original BrowserTrace icon
├── scripts/make_icon.py        Icon generator (vector-style, no stock art)
└── tests/                      selftest.py + ui_smoke.py
```

## TimeForge normalization

Browser vendors store time in incompatible epochs. TimeForge detects and converts
each value into a single UTC-aware `datetime`:

| Source                    | Format                                | Hint     |
|---------------------------|---------------------------------------|----------|
| Chrome / Edge history     | microseconds since 1601-01-01 UTC     | `chrome` |
| Firefox PRTime            | microseconds since 1601-01-01 UTC     | `prtime` |
| Any webkit/CRT epoch      | microseconds since 1601-01-01 UTC     | `webkit` |
| Unix-style                | seconds / ms / µs / ns                | `unix_*` |
| ISO-8601 strings          | `YYYY-MM-DD…T…`                       | `iso`    |

Times are rendered as `YYYY-MM-DD HH:MM:SS.mmm UTC` (or local time — toggle us in
the status bar).

## Heuristics

Findings are categorized and severity-rated:

| Category               | Examples                                                        |
|------------------------|-----------------------------------------------------------------|
| `suspicious-download`  | disguised `pdf.exe` payloads, script/executable extensions,      |
|                        | raw-IP hosts, URL shorteners, first-contact downloads            |
| `uncommon-domain`      | domains outside the known-traffic reference set                  |
| `repeated-usage`       | URLs opened dozens/hundreds of times, heavy domains              |
| `unusual-pattern`      | off-hours activity, 1-minute activity bursts, rapid bulk        |
|                        | downloads, multi-hundred-day campaigns                           |

Heuristics are intentionally conservative and inspectable — every finding links
to the underlying events.

## Exports

- **HTML report** — self-contained, styled to match the forensic UI, with the
  timeline, findings, domain aggregates and per-artifact sections.
- **CSV** — `browsertrace_timeline.csv` plus per-section CSVs (`history`,
  `downloads`, `bookmarks`, `findings`, `domains`), UTF-8 with UTC timestamps.

## Tests

```powershell
python tests\selftest.py     # synthetic Chrome+Firefox databases through the full pipeline
python tests\ui_smoke.py     # offscreen Qt integration test
```

## License

[MIT](LICENSE)

---

BrowserTrace is a local analysis tool and is not affiliated with Google, Microsoft,
or Mozilla. Browser databases belong to the user; analyze only data you are
authorized to examine.