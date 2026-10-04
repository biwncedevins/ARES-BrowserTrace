from __future__ import annotations

import html
import os
from datetime import datetime, timezone

from ..core.timeforge import TimeForge
from ..models import EventKind, Severity
from .csv_export import TIMELINE_COLUMNS

CSS = """
:root {
  --bg:#0b0d0f; --panel:#13161a; --panel2:#181c21; --border:#242a31;
  --text:#e8ebee; --muted:#8b939c; --dim:#5c646d; --accent:#c7383e;
  --high:#e05252; --med:#e0a540; --low:#5ea0e0; --info:#7e8791;
}
* { box-sizing: border-box; }
body { background: var(--bg); color: var(--text); font: 13px/1.5 "Segoe UI", Arial, sans-serif; margin:0; }
.wrap { max-width: 1280px; margin: 0 auto; padding: 24px 28px 60px; }
header { display:flex; align-items:center; gap:16px; border-bottom:1px solid var(--border); padding-bottom:18px; margin-bottom:20px; }
.logo { width:46px; height:46px; border-radius:8px; background:#0f1114; border:1px solid var(--border); display:flex; align-items:center; justify-content:center; }
h1 { font-size:20px; margin:0; letter-spacing:.4px; }
.sub { color: var(--muted); font-size:12px; letter-spacing:2px; text-transform:uppercase; margin-top:2px; }
.meta { margin-left:auto; text-align:right; color:var(--muted); font-size:12px; }
h2 { font-size:15px; margin:26px 0 10px; color:#fff; border-left:3px solid var(--accent); padding-left:8px; }
.card { background:var(--panel); border:1px solid var(--border); border-radius:6px; padding:14px 16px; }
.stats { display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:10px; }
.stat { background:var(--panel); border:1px solid var(--border); border-radius:6px; padding:12px 14px; }
.stat b { display:block; font-size:22px; }
.stat span { color:var(--muted); font-size:11px; text-transform:uppercase; letter-spacing:1px; }
table { width:100%; border-collapse:collapse; background:var(--panel); border:1px solid var(--border); border-radius:6px; overflow:hidden; }
th { text-align:left; padding:7px 10px; background:var(--panel2); color:var(--muted); font-size:11px; text-transform:uppercase; letter-spacing:.5px; border-bottom:1px solid var(--border); }
td { padding:6px 10px; border-bottom:1px solid #1b2026; vertical-align:top; font-size:12.5px; }
tr:last-child td { border-bottom:none; }
tr:hover td { background:#161b20; }
.mono { font-family:Consolas,"Cascadia Mono",monospace; font-size:12px; }
.muted { color:var(--muted); }
.tag { display:inline-block; padding:1px 7px; border-radius:3px; font-size:10.5px; letter-spacing:1px; font-weight:600; }
.tag-visit { background:#11202e; color:#6fb3e0; }
.tag-download { background:#301618; color:#e56666; }
.tag-bookmark { background:#1e2b1c; color:#82bf6e; }
.sev-high { background:#3a1717; color:#ff7a7a; }
.sev-medium { background:#332a13; color:#e8b75a; }
.sev-low { background:#14263a; color:#7db6e8; }
.sev-info { background:#232930; color:#aeb6c0; }
.filter { margin-bottom:10px; display:flex; gap:10px; align-items:center; }
.filter input { background:var(--panel2); border:1px solid var(--border); color:var(--text); border-radius:4px; padding:6px 10px; font-size:12.5px; width:320px; outline:none; }
.filter input:focus { border-color:var(--accent); }
.badge { color:var(--accent); font-size:11px; letter-spacing:1px; }
.foot { margin-top:40px; padding-top:14px; border-top:1px solid var(--border); color:var(--dim); font-size:11.5px; }
a { color:#7db6e8; text-decoration:none; word-break:break-all; }
details { background:var(--panel); border:1px solid var(--border); border-radius:6px; margin-bottom:8px; padding:10px 14px; }
summary { cursor:pointer; color:#fff; font-weight:600; }
"""

JS = """
function filterRows(inputId, tableId){
  const q = document.getElementById(inputId).value.toLowerCase();
  const rows = document.querySelectorAll('#'+tableId+' tbody tr');
  rows.forEach(r => {
    const match = r.getAttribute('data-k') ? r.getAttribute('data-k').includes(q) : true;
    r.style.display = match ? '' : 'none';
  });
}
"""


def _esc(value) -> str:
    return html.escape(str(value) if value is not None else "")


def _utc(dt) -> str:
    return TimeForge.iso_utc(dt) if dt is not None else "—"


def _sev_tag(sev) -> str:
    return f'<span class="tag sev-{sev.value}">{sev.value.upper()}</span>'


def _kind_tag(kind) -> str:
    name = "visit" if kind == EventKind.VISIT else ("download" if kind == EventKind.DOWNLOAD else "bookmark")
    return f'<span class="tag tag-{name}">{name.upper()}</span>'


def export_html_report(session, out_path: str, scope: dict) -> str:
    html_parts = []
    html_parts.append("<!doctype html><html lang='en'><head><meta charset='utf-8'>")
    html_parts.append("<title>BrowserTrace Report</title>")
    html_parts.append(f"<style>{CSS}</style></head><body>")
    html_parts.append(f"<script>{JS}</script>")
    html_parts.append("<div class='wrap'>")

    html_parts.append("<header>"
                      "<div class='logo'><svg width='34' height='34' viewBox='0 0 48 48'><rect x='8' y='12' width='32' height='24' rx='3' fill='none' stroke='#c7383e' stroke-width='2.5'/><path d='M8 18h32' stroke='#3a4149' stroke-width='2.5'/><circle cx='13' cy='15' r='1.6' fill='#c7383e'/><circle cx='17' cy='15' r='1.6' fill='#6b737c'/><circle cx='21' cy='15' r='1.6' fill='#6b737c'/><path d='M34 38l9 9' stroke='#c7383e' stroke-width='2.5'/><circle cx='29' cy='30' r='9' fill='none' stroke='#e8ebee' stroke-width='2.5'/></svg></div>"
                      "<div><h1>BrowserTrace</h1><div class='sub'>Artifact Analysis Report</div></div>"
                      f"<div class='meta'>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>"
                      f"Source: {_esc(session.source.label if session.source else '—')}</div></header>")

    stats = session.stats
    html_parts.append("<section class='stats'>"
                      f"<div class='stat'><b>{stats.get('total', 0)}</b><span>Events</span></div>"
                      f"<div class='stat'><b>{stats.get('visits', 0)}</b><span>Visits</span></div>"
                      f"<div class='stat'><b>{stats.get('downloads', 0)}</b><span>Downloads</span></div>"
                      f"<div class='stat'><b>{stats.get('bookmarks', 0)}</b><span>Bookmarks</span></div>"
                      f"<div class='stat'><b>{stats.get('domains', 0)}</b><span>Domains</span></div>"
                      f"<div class='stat'><b>{len(session.findings)}</b><span>Findings</span></div>"
                      "</section>")

    source = session.source
    if source and hasattr(source, "notes"):
        pass
    html_parts.append(f"<h2>Source</h2><div class='card mono muted'>{_esc(source.label if source else 'No source')}"
                      + ("<br>" + _esc(" | ".join(source.notes)) if source and getattr(source, "notes", []) else "")
                      + "</div>")

    if session.warnings:
        html_parts.append("<h2>Warnings</h2><div class='card'>")
        for w in session.warnings:
            html_parts.append(f"<div class='muted'>⚠ {_esc(w)}</div>")
        html_parts.append("</div>")

    if scope.get("findings", True) and session.findings:
        html_parts.append("<h2>Findings</h2><table><thead><tr><th>Severity</th><th>Category</th><th>Title</th><th>Domain</th><th>Count</th><th>First Seen (UTC)</th></tr></thead><tbody>")
        for f in session.findings:
            html_parts.append("<tr>"
                              f"<td>{_sev_tag(f.severity)}</td>"
                              f"<td class='muted'>{_esc(f.category)}</td>"
                              f"<td>{_esc(f.title)}</td>"
                              f"<td class='mono'>{_esc(f.domain)}</td>"
                              f"<td>{f.count}</td>"
                              f"<td class='mono muted'>{_utc(f.timestamps[0]) if f.timestamps else '—'}</td>"
                              "</tr>")
        html_parts.append("</tbody></table>")

    if scope.get("domains", True) and session.domains:
        html_parts.append("<h2>Domains</h2><table><thead><tr><th>Domain</th><th>Events</th><th>Visits</th><th>Downloads</th><th>Bookmarks</th><th>First Seen (UTC)</th><th>Last Seen (UTC)</th></tr></thead><tbody>")
        for row in session.domains:
            html_parts.append("<tr>"
                              f"<td class='mono'>{_esc(row.domain)}</td>"
                              f"<td>{row.total}</td><td>{row.visits}</td><td>{row.downloads}</td><td>{row.bookmarks}</td>"
                              f"<td class='mono muted'>{_utc(row.first_seen)}</td>"
                              f"<td class='mono muted'>{_utc(row.last_seen)}</td>"
                              "</tr>")
        html_parts.append("</tbody></table>")

    timeline_events = [e for e in session.events]
    if scope.get("timeline", True):
        html_parts.append("<h2>Timeline</h2>")
        html_parts.append("<div class='filter'><input id='tlq' placeholder='Filter timeline by URL / domain / title…' onkeyup='filterRows(\"tlq\",\"tlt\")'></div>")
        html_parts.append("<table id='tlt'><thead><tr><th>Time (UTC)</th><th>Type</th><th>Domain</th><th>Detail</th><th>URL / Path</th></tr></thead><tbody>")
        for ev in timeline_events:
            cell = ev.title or ev.file_name or ev.url or "—"
            target = ev.url if ev.kind != EventKind.DOWNLOAD else (ev.target_path or ev.url)
            key = _esc((cell + " " + ev.domain).lower())
            html_parts.append(
                f"<tr data-k='{key}'>"
                f"<td class='mono muted'>{_utc(ev.timestamp)}</td>"
                f"<td>{_kind_tag(ev.kind)}</td>"
                f"<td class='mono'>{_esc(ev.domain)}</td>"
                f"<td>{_esc(ev.detail)}</td>"
                f"<td class='mono'>{_esc(cell)}</td>"
                "</tr>")
        html_parts.append("</tbody></table>")

    if scope.get("history", False):
        rows = [e for e in session.events if e.kind == EventKind.VISIT]
        html_parts.append("<h2>History</h2><table><thead><tr><th>Time (UTC)</th><th>Domain</th><th>Title</th><th>URL</th><th>Visits</th><th>Transition</th></tr></thead><tbody>")
        for ev in rows:
            html_parts.append("<tr>"
                              f"<td class='mono muted'>{_utc(ev.timestamp)}</td>"
                              f"<td class='mono'>{_esc(ev.domain)}</td>"
                              f"<td>{_esc(ev.title)}</td>"
                              f"<td class='mono'><a href='{_esc(ev.url)}'>{_esc(ev.url)}</a></td>"
                              f"<td>{ev.visit_count}</td><td class='muted'>{_esc(ev.transition)}</td>"
                              "</tr>")
        html_parts.append("</tbody></table>")

    if scope.get("downloads", False):
        rows = [e for e in session.events if e.kind == EventKind.DOWNLOAD]
        html_parts.append("<h2>Downloads</h2><table><thead><tr><th>Time (UTC)</th><th>Domain</th><th>File</th><th>Target Path</th><th>State</th><th>Bytes</th></tr></thead><tbody>")
        for ev in rows:
            html_parts.append("<tr>"
                              f"<td class='mono muted'>{_utc(ev.timestamp)}</td>"
                              f"<td class='mono'>{_esc(ev.domain)}</td>"
                              f"<td>{_esc(ev.file_name)}</td>"
                              f"<td class='mono'>{_esc(ev.target_path)}</td>"
                              f"<td class='muted'>{_esc(ev.state)}</td>"
                              f"<td>{ev.total_bytes or ''}</td>"
                              "</tr>")
        html_parts.append("</tbody></table>")

    if scope.get("bookmarks", False):
        rows = [e for e in session.events if e.kind == EventKind.BOOKMARK]
        html_parts.append("<h2>Bookmarks</h2><table><thead><tr><th>Added (UTC)</th><th>Domain</th><th>Title</th><th>URL</th><th>Folder</th></tr></thead><tbody>")
        for ev in rows:
            html_parts.append("<tr>"
                              f"<td class='mono muted'>{_utc(ev.timestamp)}</td>"
                              f"<td class='mono'>{_esc(ev.domain)}</td>"
                              f"<td>{_esc(ev.title)}</td>"
                              f"<td class='mono'>{_esc(ev.url)}</td>"
                              f"<td class='mono muted'>{_esc(ev.folder_path)}</td>"
                              "</tr>")
        html_parts.append("</tbody></table>")

    html_parts.append("<div class='foot'>"
                      "BrowserTrace — privacy-first browser artifact analysis.<br>"
                      "No credentials, passwords, cookies or tokens are ever extracted, decrypted or stored. "
                      "All processing occurred locally and offline. Times shown in UTC.<br>"
                      f"Report generated by BrowserTrace {__import__('browsertrace').__version__}."
                      "</div>")
    html_parts.append("</div></body></html>")

    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(html_parts))
    return out_path