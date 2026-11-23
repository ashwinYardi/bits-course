"""Build the BitsByBlocks AI Engineering Notebook static site from curriculum.json and lessons/*/lesson.json.

Produces a complete static site in `dist/`:
- `dist/index.html` — The interactive Notebook & 49-Module Road-to-Pro Journey Map
- `dist/lessons/<id>/index.html` — The rich lesson view with interactive Next-Token Sandbox, Excalidraw figures, Lab & Verified Output, and Share Studio (X Thread + Instagram Carousel Deck + The Turn)
- `dist/lessons/<id>/lesson.json` — Raw lesson data
- `dist/lessons/<id>/post.md` — Portable Markdown export
- `dist/lessons/<id>/fig-NN.excalidraw` + `fig-NN.svg` — Editable Excalidraw scenes and rendered hand-drawn SVGs
- `dist/lessons/<id>/<code_file>` — Runnable Python lab file
"""

from __future__ import annotations

import html
import json
import re
import shutil
from pathlib import Path

from excalidraw import build_scene, lint, scene_to_svg

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"


def _esc(val: str) -> str:
    return html.escape(str(val or ""))


def _md_to_html(md: str) -> str:
    """Lightweight Markdown to HTML converter for lesson prose."""
    out: list[str] = []
    lines = md.strip().splitlines()
    buf: list[str] = []

    def inline(txt: str) -> str:
        txt = _esc(txt)
        txt = re.sub(r"`([^`]+)`", r"<code>\1</code>", txt)
        txt = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", txt)
        txt = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", txt)
        return txt

    def flush() -> None:
        nonlocal buf
        if not buf:
            return
        if all(b.lstrip().startswith("- ") for b in buf):
            items = "".join(f"<li>{inline(b.lstrip()[2:])}</li>" for b in buf)
            out.append(f"<ul>{items}</ul>")
        elif all(re.match(r"^\d+\.\s", b.lstrip()) for b in buf):
            items = "".join(
                f"<li>{inline(re.sub(r'^\d+\.\s*', '', b.lstrip()))}</li>" for b in buf
            )
            out.append(f"<ol>{items}</ol>")
        else:
            out.append(f"<p>{inline(' '.join(buf))}</p>")
        buf = []

    for line in lines:
        s = line.strip()
        if not s:
            flush()
        elif s.startswith("### "):
            flush()
            out.append(f"<h4>{inline(s[4:])}</h4>")
        elif s.startswith("## "):
            flush()
            out.append(f"<h3>{inline(s[3:])}</h3>")
        else:
            buf.append(s)
    flush()
    return "\n".join(out)


def _lesson_to_markdown(lesson: dict, fig_files: dict[str, str]) -> str:
    parts = [
        f"# {lesson['title']}\n",
        f"*{lesson['question']}*\n",
        f"> **In one line:** {lesson['one_line']}\n",
    ]
    for sec in lesson.get("sections", []):
        parts.append(f"\n## {sec['heading']}\n\n{sec['body_md']}\n")
        fid = sec.get("figure_id")
        if fid and fid in fig_files:
            fig_obj = next((f for f in lesson.get("figures", []) if f["id"] == fid), {})
            cap = fig_obj.get("caption", "")
            parts.append(f"\n![{cap}]({fig_files[fid]})\n*{cap}*\n")

    parts.append("\n## Jargon Decoder\n\n| Term | In plain words | Why you care |\n|---|---|---|\n")
    for row in lesson.get("jargon_decoder", []):
        parts.append(f"| **{row['term']}** | {row['plain_words']} | {row['why_you_care']} |\n")

    lab = lesson.get("lab", {})
    parts.append(f"\n## Hands-On Lab: {lab.get('title', '')}\n\n{lab.get('goal', '')}\n")
    return "".join(parts)


SHARED_CSS = """
:root {
  --bg: #0b0d12;
  --bg-elev: #121620;
  --bg-card: #171c28;
  --bg-subtle: #1e2536;
  --ink: #f1f5f9;
  --muted: #94a3b8;
  --line: #262f45;
  --amber: #f59e0b;
  --amber-soft: rgba(245, 158, 11, 0.14);
  --cyan: #38bdf8;
  --cyan-soft: rgba(56, 189, 248, 0.14);
  --emerald: #10b981;
  --emerald-soft: rgba(16, 185, 129, 0.14);
  --rose: #f43f5e;
  --violet: #a855f7;
  --sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  --serif: 'Newsreader', 'Charter', 'Georgia', serif;
  --mono: 'JetBrains Mono', 'Fira Code', ui-monospace, SFMono-Regular, monospace;
}
[data-theme="light"] {
  --bg: #faf7f2;
  --bg-elev: #f3ede2;
  --bg-card: #ffffff;
  --bg-subtle: #ebe4d6;
  --ink: #18181b;
  --muted: #52525b;
  --line: #dfd7c8;
  --amber: #d97706;
  --amber-soft: rgba(217, 119, 6, 0.12);
  --cyan: #0284c7;
  --cyan-soft: rgba(2, 132, 199, 0.12);
  --emerald: #059669;
  --emerald-soft: rgba(5, 150, 105, 0.12);
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--ink);
  font-family: var(--sans);
  line-height: 1.65;
  -webkit-font-smoothing: antialiased;
}
a { color: var(--amber); text-decoration: none; }
a:hover { text-decoration: underline; }
.topbar {
  position: sticky;
  top: 0;
  z-index: 50;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.85rem 1.75rem;
  background: rgba(11, 13, 18, 0.86);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--line);
}
[data-theme="light"] .topbar {
  background: rgba(250, 247, 242, 0.88);
}
.brand {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-weight: 700;
  font-size: 1.02rem;
  color: var(--ink);
}
.brand-badge {
  background: var(--amber);
  color: #0b0d12;
  font-family: var(--mono);
  font-size: 0.75rem;
  font-weight: 800;
  padding: 0.2rem 0.55rem;
  border-radius: 6px;
  letter-spacing: 0.04em;
}
.top-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}
.btn {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  background: var(--bg-subtle);
  color: var(--ink);
  border: 1px solid var(--line);
  padding: 0.45rem 0.85rem;
  border-radius: 8px;
  font-size: 0.84rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
}
.btn:hover {
  border-color: var(--amber);
  text-decoration: none;
}
.btn-primary {
  background: var(--amber);
  color: #0b0d12;
  border-color: var(--amber);
}
.layout {
  display: grid;
  grid-template-columns: 300px 1fr;
  min-height: calc(100vh - 58px);
}
@media (max-width: 960px) {
  .layout { grid-template-columns: 1fr; }
  .sidebar { display: none; }
}
.sidebar {
  border-right: 1px solid var(--line);
  background: var(--bg-elev);
  padding: 1.25rem 1rem 3rem;
  overflow-y: auto;
  max-height: calc(100vh - 58px);
  position: sticky;
  top: 58px;
}
.rung-group {
  margin-bottom: 1.35rem;
}
.rung-header {
  font-family: var(--mono);
  font-size: 0.73rem;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  color: var(--muted);
  margin-bottom: 0.45rem;
  display: flex;
  justify-content: space-between;
}
.mod-link {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.42rem 0.6rem;
  border-radius: 7px;
  font-size: 0.84rem;
  color: var(--muted);
  margin-bottom: 0.2rem;
}
.mod-link.live {
  color: var(--ink);
  font-weight: 600;
  background: var(--amber-soft);
  border: 1px solid rgba(245, 158, 11, 0.35);
}
.mod-link.active {
  background: var(--amber);
  color: #0b0d12;
  font-weight: 700;
}
.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--line);
  flex-shrink: 0;
}
.status-dot.live {
  background: var(--emerald);
  box-shadow: 0 0 8px var(--emerald);
}
.main-content {
  max-width: 920px;
  margin: 0 auto;
  padding: 2.5rem 2rem 6rem;
  width: 100%;
}
.shelf-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.55rem;
  margin-bottom: 1rem;
}
.tag {
  font-family: var(--mono);
  font-size: 0.74rem;
  padding: 0.22rem 0.65rem;
  border-radius: 999px;
  background: var(--bg-subtle);
  border: 1px solid var(--line);
  color: var(--muted);
}
.tag-amber { background: var(--amber-soft); color: var(--amber); border-color: rgba(245,158,11,0.3); }
.tag-emerald { background: var(--emerald-soft); color: var(--emerald); border-color: rgba(16,185,129,0.3); }
.tag-cyan { background: var(--cyan-soft); color: var(--cyan); border-color: rgba(56,189,248,0.3); }
h1 {
  font-family: var(--serif);
  font-size: 2.55rem;
  line-height: 1.15;
  margin: 0.3rem 0 0.75rem;
  letter-spacing: -0.02em;
}
.question-lead {
  font-size: 1.22rem;
  color: var(--amber);
  font-family: var(--serif);
  font-style: italic;
  margin-bottom: 1.25rem;
}
.one-liner-box {
  background: var(--bg-card);
  border-left: 4px solid var(--amber);
  padding: 1.1rem 1.35rem;
  border-radius: 0 12px 12px 0;
  margin-bottom: 2rem;
  font-size: 1.02rem;
  box-shadow: 0 8px 24px rgba(0,0,0,0.18);
}
.mode-tabs {
  display: flex;
  gap: 0.5rem;
  border-bottom: 1px solid var(--line);
  margin-bottom: 2rem;
  padding-bottom: 0.75rem;
  flex-wrap: wrap;
}
.tab-btn {
  background: var(--bg-card);
  color: var(--muted);
  border: 1px solid var(--line);
  padding: 0.6rem 1.1rem;
  border-radius: 10px;
  font-weight: 600;
  font-size: 0.88rem;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
}
.tab-btn.active {
  background: var(--amber);
  color: #0b0d12;
  border-color: var(--amber);
}
.tab-panel { display: none; }
.tab-panel.active { display: block; }
.spine-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 0.9rem;
  margin-bottom: 2.5rem;
}
.spine-card {
  background: var(--bg-card);
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 1rem 1.15rem;
}
.spine-label {
  font-family: var(--mono);
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--amber);
  margin-bottom: 0.35rem;
}
.lesson-section {
  background: var(--bg-card);
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 1.65rem 1.85rem;
  margin-bottom: 1.75rem;
}
.sec-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 0.9rem;
}
.sec-header h2 {
  margin: 0;
  font-size: 1.4rem;
  font-family: var(--serif);
}
.figure-card {
  margin: 1.5rem 0 0.5rem;
  background: #ffffff;
  color: #1e1e1e;
  border-radius: 12px;
  padding: 1.25rem;
  border: 2px solid var(--line);
}
.figure-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.82rem;
  color: #475569;
  margin-top: 0.75rem;
  padding-top: 0.6rem;
  border-top: 1px dashed #cbd5e1;
}
.sandbox-card {
  background: linear-gradient(145deg, var(--bg-card), var(--bg-subtle));
  border: 1px solid var(--amber);
  border-radius: 14px;
  padding: 1.5rem;
  margin-bottom: 2rem;
}
.sandbox-controls {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  align-items: center;
  margin: 1rem 0;
}
.prob-bar-row {
  display: grid;
  grid-template-columns: 110px 70px 1fr 65px;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.5rem;
  font-family: var(--mono);
  font-size: 0.83rem;
}
.prob-track {
  background: var(--bg);
  height: 18px;
  border-radius: 6px;
  overflow: hidden;
  border: 1px solid var(--line);
}
.prob-fill {
  background: var(--amber);
  height: 100%;
  transition: width 0.2s ease;
}
table.decoder-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
  background: var(--bg-card);
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid var(--line);
}
.decoder-table th, .decoder-table td {
  padding: 0.85rem 1rem;
  text-align: left;
  border-bottom: 1px solid var(--line);
  vertical-align: top;
}
.decoder-table th {
  background: var(--bg-subtle);
  font-family: var(--mono);
  font-size: 0.76rem;
  text-transform: uppercase;
  color: var(--muted);
}
pre {
  background: #090b10;
  color: #e2e8f0;
  padding: 1.15rem;
  border-radius: 10px;
  overflow-x: auto;
  font-family: var(--mono);
  font-size: 0.83rem;
  border: 1px solid var(--line);
  line-height: 1.55;
}
code {
  font-family: var(--mono);
  font-size: 0.88em;
  background: var(--bg-subtle);
  padding: 0.15rem 0.4rem;
  border-radius: 5px;
}
pre code { background: none; padding: 0; }
.turn-card {
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.16), rgba(168, 85, 247, 0.14));
  border: 1px solid var(--amber);
  border-radius: 14px;
  padding: 1.5rem 1.75rem;
  margin-bottom: 2rem;
}
.tweet-card {
  background: var(--bg-card);
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 1.1rem 1.3rem;
  margin-bottom: 0.85rem;
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: flex-start;
}
.ig-deck {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
  gap: 1rem;
  margin-top: 1rem;
}
.ig-slide {
  aspect-ratio: 4 / 5;
  background: linear-gradient(160deg, #131824 0%, #1e1b2e 100%);
  border: 2px solid var(--amber);
  border-radius: 16px;
  padding: 1.4rem;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  color: #f8fafc;
  box-shadow: 0 10px 25px rgba(0,0,0,0.3);
}
.ig-slide-num {
  font-family: var(--mono);
  font-size: 0.75rem;
  color: var(--amber);
  letter-spacing: 0.08em;
}
.ig-slide h4 {
  font-family: var(--serif);
  font-size: 1.35rem;
  line-height: 1.2;
  margin: 0.5rem 0;
}
.ig-slide p {
  font-size: 0.88rem;
  color: #cbd5e1;
  margin: 0;
}
.ig-slide-footer {
  font-family: var(--mono);
  font-size: 0.7rem;
  color: #94a3b8;
  border-top: 1px solid rgba(255,255,255,0.12);
  padding-top: 0.55rem;
  display: flex;
  justify-content: space-between;
}
"""


def _render_sidebar(curriculum: dict, live_ids: set[str], active_id: str | None, prefix: str) -> str:
    levels = {lvl["level"]: lvl for lvl in curriculum.get("levels", [])}
    by_lvl: dict[int, list[dict]] = {k: [] for k in levels}
    for m in curriculum.get("modules", []):
        by_lvl[m["level"]].append(m)

    parts = ['<aside class="sidebar">']
    parts.append(
        f'<div style="margin-bottom:1.25rem;padding:0.75rem;background:var(--bg-card);border-radius:10px;border:1px solid var(--line);">'
        f'<div style="font-family:var(--mono);font-size:0.75rem;color:var(--amber);">JOURNEY PROGRESS</div>'
        f'<div style="font-size:1.3rem;font-weight:800;margin-top:0.2rem;">{len(live_ids)} / {len(curriculum.get("modules", []))} <span style="font-size:0.82rem;font-weight:500;color:var(--muted);">modules seeded</span></div>'
        f'</div>'
    )
    for lvl_num, lvl_meta in levels.items():
        mods = by_lvl.get(lvl_num, [])
        done_count = sum(1 for m in mods if m["id"] in live_ids)
        parts.append('<div class="rung-group">')
        parts.append(
            f'<div class="rung-header"><span>Rung {lvl_num} · {_esc(lvl_meta["name"])}</span><span>{done_count}/{len(mods)}</span></div>'
        )
        for m in mods:
            mid = m["id"]
            is_live = mid in live_ids
            is_active = mid == active_id
            cls = "mod-link"
            if is_active:
                cls += " active"
            elif is_live:
                cls += " live"
            href = f"{prefix}lessons/{mid}/index.html" if is_live else f"{prefix}index.html#{mid}"
            dot_cls = "status-dot live" if is_live else "status-dot"
            parts.append(
                f'<a class="{cls}" href="{href}">'
                f'<span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{_esc(m["title"])}</span>'
                f'<span class="{dot_cls}"></span>'
                f'</a>'
            )
        parts.append("</div>")
    parts.append("</aside>")
    return "\n".join(parts)


def _render_lesson_page(curriculum: dict, lesson: dict, live_ids: set[str], code_text: str) -> str:
    lid = lesson["id"]
    sidebar_html = _render_sidebar(curriculum, live_ids, lid, "../../")
    spine = lesson["story_spine"]

    # Render sections
    figs_by_id = {f["id"]: f for f in lesson.get("figures", [])}
    sections_html = []
    for idx, sec in enumerate(lesson.get("sections", []), 1):
        fig_block = ""
        fid = sec.get("figure_id")
        if fid and fid in figs_by_id:
            fobj = figs_by_id[fid]
            fig_block = (
                f'<div class="figure-card">'
                f'<img src="{_esc(fid)}.svg" alt="{_esc(fobj["title"])}" style="width:100%;height:auto;display:block;" />'
                f'<div class="figure-meta">'
                f'<span><strong>{_esc(fobj["title"])}:</strong> {_esc(fobj["caption"])}</span>'
                f'<a href="{_esc(fid)}.excalidraw" download style="color:#0284c7;font-family:var(--mono);font-size:0.75rem;">⬇ .excalidraw</a>'
                f'</div>'
                f'</div>'
            )
        sections_html.append(
            f'<section class="lesson-section">'
            f'<div class="sec-header">'
            f'<h2>{idx}. {_esc(sec["heading"])}</h2>'
            f'<span class="tag tag-amber">{_esc(sec.get("badge", f"Step {idx}"))}</span>'
            f'</div>'
            f'{_md_to_html(sec["body_md"])}'
            f'{fig_block}'
            f'</section>'
        )

    # Jargon table
    jargon_rows = "".join(
        f"<tr><td><strong>{_esc(r['term'])}</strong></td><td>{_esc(r['plain_words'])}</td><td>{_esc(r['why_you_care'])}</td></tr>"
        for r in lesson.get("jargon_decoder", [])
    )

    # Lab tab
    lab = lesson["lab"]
    lab_steps = "".join(f"<li>{_md_to_html(s)}</li>" for s in lab.get("steps", []))
    acc_cards = "".join(
        f'<div class="spine-card" style="border-left:4px solid var(--emerald);">'
        f'<div class="spine-label" style="color:var(--emerald);">✓ VERIFIED CRITERION</div>'
        f'<div style="font-weight:600;margin-bottom:0.35rem;">{_esc(a["criterion"])}</div>'
        f'<div style="font-family:var(--mono);font-size:0.78rem;color:var(--muted);">Evidence: {_esc(a["evidence"])}</div>'
        f'</div>'
        for a in lab.get("acceptance", [])
    )

    # Share studio tab
    sh = lesson["shareable"]
    tweets_html = "".join(
        f'<div class="tweet-card">'
        f'<div style="white-space:pre-line;font-size:0.95rem;">{_esc(t)}</div>'
        f'<button class="btn" onclick="navigator.clipboard.writeText(this.previousElementSibling.innerText);this.innerText=\'Copied!\'">Copy</button>'
        f'</div>'
        for t in sh.get("x_thread", [])
    )
    all_thread_js = json.dumps("\n\n".join(sh.get("x_thread", [])))

    ig_slides = "".join(
        f'<div class="ig-slide">'
        f'<div class="ig-slide-num">SLIDE 0{s["slide"]} / 0{len(sh.get("instagram_carousel", []))} · {_esc(sh["notebook_shelf"])}</div>'
        f'<div><h4>{_esc(s["headline"])}</h4><p style="white-space:pre-line;">{_esc(s["body"])}</p></div>'
        f'<div class="ig-slide-footer"><span>@ashwinYardi</span><span>BitsByBlocks</span></div>'
        f'</div>'
        for s in sh.get("instagram_carousel", [])
    )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{_esc(lesson["title"])} · BitsByBlocks AI Notebook</title>
  <style>{SHARED_CSS}</style>
</head>
<body>
  <header class="topbar">
    <a class="brand" href="../../index.html">
      <span class="brand-badge">BitsByBlocks</span>
      <span>AI Engineering Notebook</span>
    </a>
    <div class="top-actions">
      <a class="btn" href="../../index.html">← All 49 Modules</a>
      <a class="btn" href="lesson.json" target="_blank">lesson.json</a>
      <button class="btn" onclick="toggleTheme()">☀/☾ Theme</button>
    </div>
  </header>

  <div class="layout">
    {sidebar_html}
    <main class="main-content">
      <div class="shelf-tags">
        <span class="tag tag-amber">{_esc(sh["notebook_shelf"])}</span>
        <span class="tag tag-cyan">Rung {lesson["level"]}: {_esc(lesson["level_name"])}</span>
        <span class="tag tag-emerald">✓ Lab Verified</span>
        <span class="tag">{lesson.get("read_time_minutes", 8)} min read + build</span>
      </div>

      <h1>{_esc(lesson["title"])}</h1>
      <div class="question-lead">“{_esc(lesson["question"])}”</div>

      <div class="one-liner-box">
        <strong>The One-Line Takeaway:</strong> {_esc(lesson["one_line"])}
      </div>

      <div class="mode-tabs">
        <button class="tab-btn active" onclick="switchTab('concept', this)">1. Concept & Interactive Sandbox</button>
        <button class="tab-btn" onclick="switchTab('lab', this)">2. Hands-On Lab & Verified Output</button>
        <button class="tab-btn" onclick="switchTab('share', this)">3. Share Studio (X + IG + The Turn)</button>
      </div>

      <!-- TAB 1: CONCEPT -->
      <div id="tab-concept" class="tab-panel active">
        <div class="sandbox-card">
          <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:0.5rem;">
            <div>
              <div class="spine-label">INTERACTIVE MECHANISM SANDBOX</div>
              <h3 style="margin:0.2rem 0;font-family:var(--serif);">Play with the Next-Token Loop Live</h3>
            </div>
            <span class="tag tag-amber">Prompt: "the server"</span>
          </div>
          <p style="font-size:0.9rem;color:var(--muted);margin:0.5rem 0 1rem;">
            Drag the <strong>Temperature</strong> slider to see how the exact same raw logit scores reshape into probabilities, then click <strong>Sample Next Token</strong> to roll the weighted die and append to the prompt.
          </p>
          <div class="sandbox-controls">
            <label style="font-family:var(--mono);font-size:0.85rem;">
              Temperature: <strong id="temp-val" style="color:var(--amber);">1.0</strong>
            </label>
            <input id="temp-slider" type="range" min="0" max="2.0" step="0.1" value="1.0" oninput="updateSandbox()" style="width:220px;accent-color:var(--amber);" />
            <button class="btn btn-primary" onclick="sampleOneStep()">Sample & Append Next Token →</button>
            <button class="btn" onclick="resetSandbox()">Reset Prompt</button>
          </div>
          <div id="prob-bars" style="margin:1rem 0;"></div>
          <div style="background:var(--bg);padding:0.85rem 1rem;border-radius:8px;border:1px solid var(--line);font-family:var(--mono);font-size:0.88rem;">
            <span style="color:var(--muted);">Context window:</span> <strong id="live-context" style="color:var(--amber);">the server</strong>
          </div>
        </div>

        <h3 style="font-family:var(--serif);margin-bottom:0.75rem;">The Story Spine</h3>
        <div class="spine-grid">
          <div class="spine-card"><div class="spine-label">The Surprise</div><div>{_esc(spine["surprise"])}</div></div>
          <div class="spine-card"><div class="spine-label">What Breaks</div><div>{_esc(spine["broken"])}</div></div>
          <div class="spine-card"><div class="spine-label">The Turn</div><div>{_esc(spine["turn"])}</div></div>
          <div class="spine-card"><div class="spine-label">Honest Limit</div><div>{_esc(spine["honest_limit"])}</div></div>
        </div>

        {"".join(sections_html)}

        <h2 style="font-family:var(--serif);margin-top:2.5rem;">Jargon Decoder</h2>
        <table class="decoder-table">
          <thead><tr><th>Term</th><th>In Plain Words</th><th>Why You Care</th></tr></thead>
          <tbody>{jargon_rows}</tbody>
        </table>
      </div>

      <!-- TAB 2: HANDS-ON LAB -->
      <div id="tab-lab" class="tab-panel">
        <div class="lesson-section">
          <div class="sec-header">
            <h2>{_esc(lab["title"])}</h2>
            <a class="btn btn-primary" href="{_esc(lab["code_file"])}" download>⬇ Download {_esc(lab["code_file"])}</a>
          </div>
          <p>{_esc(lab["goal"])}</p>
          <h3>Steps to Run Locally</h3>
          <ol>{lab_steps}</ol>
        </div>

        <h3 style="font-family:var(--serif);">Verified Acceptance Criteria</h3>
        <div class="spine-grid">{acc_cards}</div>

        <div class="lesson-section">
          <div class="sec-header">
            <h2>Real Verified Terminal Output</h2>
            <span class="tag tag-emerald">Exit code 0 · Verified</span>
          </div>
          <pre><code>{_esc(lab["real_output"])}</code></pre>
        </div>

        <div class="lesson-section">
          <div class="sec-header">
            <h2>Reference Code (`{_esc(lab["code_file"])}`)</h2>
            <button class="btn" onclick="navigator.clipboard.writeText(document.getElementById('lab-code-block').innerText);this.innerText='Copied!'">Copy Code</button>
          </div>
          <pre><code id="lab-code-block">{_esc(code_text)}</code></pre>
        </div>

        <div class="lesson-section">
          <h2>Code-by-Code Walkthrough</h2>
          {_md_to_html(lab["walkthrough_md"])}
        </div>
      </div>

      <!-- TAB 3: SHARE STUDIO -->
      <div id="tab-share" class="tab-panel">
        <div class="turn-card">
          <div class="spine-label">THE NOTEBOOK TURN · PERSONAL REFLECTION</div>
          <div style="font-family:var(--serif);font-size:1.35rem;line-height:1.4;margin:0.4rem 0 0.75rem;">
            “{_esc(sh["the_turn"])}”
          </div>
          <div style="font-size:0.86rem;color:var(--muted);">
            <strong>Reel / Voiceover Hook:</strong> {_esc(sh["reel_hook"])}
          </div>
        </div>

        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem;">
          <h2 style="font-family:var(--serif);margin:0;">Ready-to-Post X Thread ({len(sh.get("x_thread", []))} posts)</h2>
          <button class="btn btn-primary" onclick='navigator.clipboard.writeText({all_thread_js});this.innerText="Copied Full Thread!"'>Copy Full Thread</button>
        </div>
        {tweets_html}

        <h2 style="font-family:var(--serif);margin-top:2.5rem;">Instagram Carousel Card Deck (4:5 Preview)</h2>
        <p style="color:var(--muted);font-size:0.9rem;">Each card is framed at 4:5 aspect ratio so you can screenshot or export directly for Instagram carousels.</p>
        <div class="ig-deck">
          {ig_slides}
        </div>
      </div>
    </main>
  </div>

  <script>
    function toggleTheme() {{
      const cur = document.documentElement.getAttribute('data-theme');
      document.documentElement.setAttribute('data-theme', cur === 'light' ? 'dark' : 'light');
    }}
    function switchTab(name, btn) {{
      document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.getElementById('tab-' + name).classList.add('active');
      btn.classList.add('active');
    }}

    const LOGIT_TABLE = {{
      "the server": {{"crashed": 3.2, "responded": 2.9, "timed": 2.4, "melted": 0.4, "danced": -1.5}},
      "server crashed": {{"because": 3.6, "after": 2.5, "at": 1.8, "quietly": 0.9}},
      "server responded": {{"in": 3.4, "with": 2.8, "after": 1.7, "slowly": 1.1}},
      "server timed": {{"out": 4.5, "at": 1.1, "twice": 0.8}},
      "crashed because": {{"memory": 3.3, "traffic": 2.9, "disk": 2.1, "aliens": -2.0}},
      "responded in": {{"twelve": 3.1, "two": 2.8, "forty": 2.2}},
      "timed out": {{"after": 3.5, "during": 2.7, "under": 2.2}}
    }};
    const DEFAULT_LOGITS = {{"and": 2.2, "then": 2.0, "stopped": 2.6, "recovered": 2.3}};
    let tokens = ["the", "server"];

    function getSoftmax(logits, temp) {{
      const entries = Object.entries(logits);
      if (temp <= 0.01) {{
        let best = entries[0][0], bestV = entries[0][1];
        entries.forEach(([k, v]) => {{ if (v > bestV) {{ best = k; bestV = v; }} }});
        const out = {{}};
        entries.forEach(([k]) => out[k] = (k === best ? 1.0 : 0.0));
        return out;
      }}
      const scaled = entries.map(([k, v]) => [k, v / temp]);
      const maxL = Math.max(...scaled.map(x => x[1]));
      const exps = scaled.map(([k, v]) => [k, Math.exp(v - maxL)]);
      const sum = exps.reduce((a, b) => a + b[1], 0);
      const out = {{}};
      exps.forEach(([k, e]) => out[k] = e / sum);
      return out;
    }}

    function updateSandbox() {{
      const temp = parseFloat(document.getElementById('temp-slider').value);
      document.getElementById('temp-val').innerText = temp.toFixed(1);
      const key = tokens.slice(-2).join(" ");
      const logits = LOGIT_TABLE[key] || DEFAULT_LOGITS;
      const probs = getSoftmax(logits, temp);
      const container = document.getElementById('prob-bars');
      const sorted = Object.entries(probs).sort((a, b) => b[1] - a[1]);
      container.innerHTML = sorted.map(([tok, p]) => {{
        const pct = (p * 100).toFixed(1);
        const lval = logits[tok].toFixed(1);
        return `<div class="prob-bar-row">
          <strong>${{tok}}</strong>
          <span style="color:var(--muted);">logit ${{lval}}</span>
          <div class="prob-track"><div class="prob-fill" style="width:${{pct}}%;"></div></div>
          <span style="text-align:right;">${{pct}}%</span>
        </div>`;
      }}).join("");
      document.getElementById('live-context').innerText = tokens.join(" ");
    }}

    function sampleOneStep() {{
      const temp = parseFloat(document.getElementById('temp-slider').value);
      const key = tokens.slice(-2).join(" ");
      const logits = LOGIT_TABLE[key] || DEFAULT_LOGITS;
      const probs = getSoftmax(logits, temp);
      let r = Math.random(), acc = 0, pick = Object.keys(probs)[0];
      for (const [tok, p] of Object.entries(probs)) {{
        acc += p;
        if (r <= acc) {{ pick = tok; break; }}
      }}
      tokens.push(pick);
      updateSandbox();
    }}

    function resetSandbox() {{
      tokens = ["the", "server"];
      updateSandbox();
    }}
    updateSandbox();
  </script>
</body>
</html>
"""


def _render_index_page(curriculum: dict, lessons: dict[str, dict]) -> str:
    live_ids = set(lessons.keys())
    sidebar_html = _render_sidebar(curriculum, live_ids, None, "")
    course = curriculum["course"]

    # Featured latest lesson
    first_lesson = next(iter(lessons.values()), None)
    featured_html = ""
    if first_lesson:
        sh = first_lesson["shareable"]
        featured_html = f"""
        <div class="sandbox-card" style="margin-bottom:2.5rem;">
          <div class="shelf-tags">
            <span class="tag tag-amber">LATEST SEEDED ENTRY · {_esc(sh["notebook_shelf"])}</span>
            <span class="tag tag-emerald">✓ Lab & Excalidraw Figures Live</span>
          </div>
          <h2 style="font-family:var(--serif);font-size:1.85rem;margin:0.3rem 0;">{_esc(first_lesson["title"])}</h2>
          <div class="question-lead" style="font-size:1.1rem;margin-bottom:0.75rem;">“{_esc(first_lesson["question"])}”</div>
          <p style="margin-bottom:1rem;">{_esc(first_lesson["one_line"])}</p>
          <div style="background:var(--bg);padding:0.9rem 1.15rem;border-radius:10px;border:1px solid var(--line);margin-bottom:1.15rem;font-family:var(--serif);font-style:italic;">
            <strong>The Turn:</strong> “{_esc(sh["the_turn"])}”
          </div>
          <div style="display:flex;gap:0.75rem;flex-wrap:wrap;">
            <a class="btn btn-primary" href="lessons/{_esc(first_lesson["id"])}/index.html">Open Interactive Lesson & Lab →</a>
            <a class="btn" href="lessons/{_esc(first_lesson["id"])}/lesson.json">View lesson.json</a>
          </div>
        </div>
        """

    # Build Rung cards
    levels = {lvl["level"]: lvl for lvl in curriculum.get("levels", [])}
    by_lvl: dict[int, list[dict]] = {k: [] for k in levels}
    for m in curriculum.get("modules", []):
        by_lvl[m["level"]].append(m)

    rungs_html = []
    for lvl_num, lvl_meta in levels.items():
        mods = by_lvl.get(lvl_num, [])
        cards = []
        for m in mods:
            mid = m["id"]
            is_live = mid in live_ids
            badge = '<span class="tag tag-emerald">LIVE · LAB + SHARE STUDIO</span>' if is_live else '<span class="tag">UPCOMING IN SPINE</span>'
            href = f'lessons/{mid}/index.html' if is_live else f'#{mid}'
            border = 'border-color:var(--amber);' if is_live else ''
            cards.append(
                f'<div id="{_esc(mid)}" class="spine-card" style="{border}display:flex;flex-direction:column;justify-content:space-between;">'
                f'<div>'
                f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.5rem;">'
                f'<span style="font-family:var(--mono);font-size:0.74rem;color:var(--muted);">{_esc(mid)}</span>'
                f'{badge}'
                f'</div>'
                f'<h3 style="font-family:var(--serif);margin:0.2rem 0 0.45rem;font-size:1.18rem;">'
                f'<a href="{href}" style="color:var(--ink);">{_esc(m["title"])}</a>'
                f'</h3>'
                f'<div style="font-size:0.88rem;color:var(--amber);font-style:italic;margin-bottom:0.5rem;">“{_esc(m["question"])}”</div>'
                f'<p style="font-size:0.84rem;color:var(--muted);margin:0 0 0.75rem;"><strong>Unlock:</strong> {_esc(m["can"])}</p>'
                f'</div>'
                f'<div style="border-top:1px solid var(--line);padding-top:0.6rem;font-size:0.76rem;color:var(--muted);font-family:var(--mono);">'
                f'Proof: {_esc(", ".join(m.get("proof", [])[:2]))}'
                f'</div>'
                f'</div>'
            )
        rungs_html.append(
            f'<section style="margin-bottom:2.75rem;">'
            f'<div style="display:flex;justify-content:space-between;align-items:baseline;border-bottom:1px solid var(--line);padding-bottom:0.6rem;margin-bottom:1.1rem;flex-wrap:wrap;">'
            f'<h2 style="font-family:var(--serif);margin:0;">Rung {lvl_num}: {_esc(lvl_meta["name"])}</h2>'
            f'<span style="color:var(--muted);font-size:0.9rem;">After this rung: <em>{_esc(lvl_meta["after"])}</em></span>'
            f'</div>'
            f'<div class="spine-grid">{"".join(cards)}</div>'
            f'</section>'
        )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{_esc(course["title"])}</title>
  <style>{SHARED_CSS}</style>
</head>
<body>
  <header class="topbar">
    <a class="brand" href="index.html">
      <span class="brand-badge">BitsByBlocks</span>
      <span>AI Engineering Notebook</span>
    </a>
    <div class="top-actions">
      <a class="btn" href="curriculum.json" target="_blank">curriculum.json</a>
      <a class="btn" href="lesson.schema.json" target="_blank">lesson.schema.json</a>
      <button class="btn" onclick="toggleTheme()">☀/☾ Theme</button>
    </div>
  </header>

  <div class="layout">
    {sidebar_html}
    <main class="main-content">
      <div class="shelf-tags">
        <span class="tag tag-amber">THE LIVING NOTEBOOK · ASHWIN YARDI</span>
        <span class="tag tag-cyan">49 Spine Modules · 6 Rungs</span>
        <span class="tag tag-emerald">Triangulated: CS336 · Karpathy · Raschka · Huyen</span>
      </div>
      <h1>From Zero to Building Real Models — In Public</h1>
      <p style="font-size:1.12rem;color:var(--muted);max-width:46rem;margin-bottom:2rem;">
        Every module in this notebook pairs three things: <strong>hand-drawn Excalidraw mechanisms</strong>, a <strong>runnable pure-Python lab verified against acceptance criteria</strong>, and a <strong>Share Studio</strong> (X thread, 4:5 Instagram carousel deck, and <em>The Turn</em> — what building it changed in how I see things).
      </p>

      {featured_html}

      {"".join(rungs_html)}
    </main>
  </div>

  <script>
    function toggleTheme() {{
      const cur = document.documentElement.getAttribute('data-theme');
      document.documentElement.setAttribute('data-theme', cur === 'light' ? 'dark' : 'light');
    }}
  </script>
</body>
</html>
"""


def build_site() -> None:
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True, exist_ok=True)

    curriculum = json.loads((ROOT / "curriculum.json").read_text())
    shutil.copy2(ROOT / "curriculum.json", DIST / "curriculum.json")
    shutil.copy2(ROOT / "lesson.schema.json", DIST / "lesson.schema.json")
    (DIST / ".nojekyll").write_text("")

    lessons_dir = ROOT / "lessons"
    lessons: dict[str, dict] = {}

    for ldir in sorted(lessons_dir.iterdir()):
        lfile = ldir / "lesson.json"
        if not lfile.exists():
            continue
        lesson = json.loads(lfile.read_text())
        lid = lesson["id"]
        lessons[lid] = lesson

        out_dir = DIST / "lessons" / lid
        out_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(lfile, out_dir / "lesson.json")

        # Copy lab script if present
        code_file = lesson.get("lab", {}).get("code_file", "lab_main.py")
        code_path = ldir / code_file
        code_text = ""
        if code_path.exists():
            shutil.copy2(code_path, out_dir / code_file)
            code_text = code_path.read_text()

        # Render figures (.excalidraw + .svg)
        fig_files: dict[str, str] = {}
        for idx, fspec in enumerate(lesson.get("figures", []), 1):
            fid = fspec.get("id", f"fig-{idx:02d}")
            scene = build_scene(fspec)
            problems = lint(fspec, scene)
            if problems:
                print(f"  [WARN] {lid}/{fid} lint notes: {problems}")
            (out_dir / f"{fid}.excalidraw").write_text(json.dumps(scene, indent=2) + "\n")
            svg_str = scene_to_svg(scene)
            (out_dir / f"{fid}.svg").write_text(svg_str + "\n")
            fig_files[fid] = f"{fid}.svg"

        # Generate post.md
        (out_dir / "post.md").write_text(_lesson_to_markdown(lesson, fig_files))

    # Render lesson HTML pages
    live_ids = set(lessons.keys())
    for lid, lesson in lessons.items():
        out_dir = DIST / "lessons" / lid
        code_file = lesson.get("lab", {}).get("code_file", "lab_main.py")
        code_text = (out_dir / code_file).read_text() if (out_dir / code_file).exists() else ""
        html_str = _render_lesson_page(curriculum, lesson, live_ids, code_text)
        (out_dir / "index.html").write_text(html_str)

    # Render main index.html
    (DIST / "index.html").write_text(_render_index_page(curriculum, lessons))
    docs = ROOT / "docs"
    if docs.exists():
        shutil.rmtree(docs)
    shutil.copytree(DIST, docs)
    print(f"Built static site in {DIST} and {docs} with {len(lessons)} seeded lesson(s) and {len(curriculum['modules'])} curriculum modules.")


if __name__ == "__main__":
    build_site()
