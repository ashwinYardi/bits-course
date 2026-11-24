"""Build the BitsByBlocks AI University RPG & Interactive Room Course from curriculum.json and lessons/*/lesson.json.

Produces a complete static site in `dist/` and `docs/`:
- `index.html` — The 2D Top-Down AI University Campus & Building Interior RPG (walk Ashwin across 6 Rung Buildings, enter Building 0, walk from Room to Room, press E / Enter to inspect stations, pass the Gate Challenge at the Room Terminal to unlock the door to the next Room, and mint a shareable Room Cleared Card).
- `lessons/<id>/index.html` — Dedicated Room Workstation view with the interactive mechanism simulator, Story Spine, Excalidraw figures, Runnable Lab, Gate Challenge Boss Check, and Share Studio.
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


GATE_CHALLENGES: dict[str, list[dict]] = {
    "l0-what-is-an-llm": [
        {
            "q": "1. In our lab, after the prompt 'the server', the raw logits are crashed=3.2 and responded=2.9. What happens when you lower temperature from 1.0 down to 0.2?",
            "options": [
                "The model updates its weights to remember 'crashed' permanently.",
                "Softmax sharpens the gap: 'crashed' jumps from 44.2% to 80.6% probability.",
                "The probability splits 50/50 between 'crashed' and 'responded'."
            ],
            "correct": 1,
            "explain": "Dividing logits by a small temperature (0.2) amplifies the gap before exponentiating in softmax, giving 'crashed' 80.6% of the probability mass."
        },
        {
            "q": "2. Why did running the loop 5 times at temperature 0.0 produce 1/5 unique outputs while temperature 1.0 produced 5/5 unique trajectories?",
            "options": [
                "Temperature 0.0 is greedy decoding (always picks the top logit), and once an early token is appended at Temp 1.0 it changes the prompt context for every token after it.",
                "Temperature 1.0 randomly scrambles the prompt order before running.",
                "The model fetches live server logs from the internet when temperature > 0."
            ],
            "correct": 0,
            "explain": "Every sampled token is glued onto the prompt context for the next step — so one different pick on token #3 branches the entire rest of the sentence."
        },
        {
            "q": "3. Why is asking an LLM for 'YES/NO on line 1, then explain why on line 2' a production bug?",
            "options": [
                "Because YES and NO cost more tokens than numbers.",
                "Because the model is a forward-only predictor: once it commits to 'YES' on token 1, 'YES' is in its context and it is forced to rationalize it.",
                "Because softmax cannot score uppercase words."
            ],
            "correct": 1,
            "explain": "An LLM cannot plan backwards. Emitting the verdict token first traps the remaining forward passes into defending that first roll."
        }
    ],
    "l0-tokens": [
        {
            "q": "1. Why does an LLM struggle to count the three 'r' letters in 'strawberry' when asked directly?",
            "options": [
                "It never receives the 10 individual characters; the BPE tokenizer converts 'strawberry' into 3 integer IDs [496, 675, 15717] where two 'r's are sealed inside token 15717 ('berry').",
                "The letter 'r' is removed during UTF-8 encoding.",
                "Neural networks cannot count higher than 2."
            ],
            "correct": 0,
            "explain": "Token 15717 ('berry') is an atomic integer at the input layer. Forcing spaces ('s t r a w b e r r y') splits each letter into its own token ID."
        },
        {
            "q": "2. In our BPE lab output, how did the token fertility of Hindi ('नमस्ते दुनिया') compare to English prose?",
            "options": [
                "Hindi used fewer tokens per character than English.",
                "Hindi and English had the exact same 0.28 tokens/char ratio.",
                "Hindi took 0.92 tokens/char vs English 0.28 tokens/char — a 3.3x cost and latency multiplier."
            ],
            "correct": 2,
            "explain": "Because BPE merges are trained predominantly on English/code corpora, multi-byte UTF-8 scripts split into more fragments per character, multiplying both cost and decode latency."
        },
        {
            "q": "3. How does a byte-level BPE tokenizer build its 100k vocabulary from scratch?",
            "options": [
                "Linguists hand-write dictionary prefixes and suffixes.",
                "It starts with the 256 raw UTF-8 bytes and repeatedly merges the most frequent adjacent pair into a new token ID.",
                "It hashes every word in Wikipedia using SHA-256."
            ],
            "correct": 1,
            "explain": "In our 30-line lab, just 8 greedy adjacent-pair merges compressed 39 raw UTF-8 bytes down to 11 subword tokens (28.2%)."
        }
    ]
}


SHARED_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600;700;800&family=Newsreader:ital,opsz,wght@0,6..72,500;0,6..72,700;1,6..72,400&family=Press+Start+2P&display=swap');

:root {
  --bg: #080b11;
  --bg-elev: #0f1420;
  --bg-card: #151c2c;
  --bg-subtle: #1d263b;
  --ink: #f8fafc;
  --muted: #94a3b8;
  --line: #28344f;
  --amber: #f59e0b;
  --amber-soft: rgba(245, 158, 11, 0.16);
  --cyan: #38bdf8;
  --cyan-soft: rgba(56, 189, 248, 0.16);
  --emerald: #10b981;
  --emerald-soft: rgba(16, 185, 129, 0.16);
  --rose: #f43f5e;
  --violet: #a855f7;
  --sans: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  --serif: 'Newsreader', Georgia, serif;
  --mono: 'JetBrains Mono', monospace;
  --pixel: 'Press Start 2P', 'JetBrains Mono', monospace;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--ink);
  font-family: var(--sans);
  line-height: 1.6;
  overflow-x: hidden;
}
a { color: var(--amber); text-decoration: none; }
a:hover { text-decoration: underline; }
.hud-bar {
  position: sticky;
  top: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.7rem 1.4rem;
  background: rgba(8, 11, 17, 0.92);
  backdrop-filter: blur(12px);
  border-bottom: 2px solid var(--line);
  gap: 1rem;
  flex-wrap: wrap;
}
.hud-brand {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  color: var(--ink);
  font-weight: 800;
  font-size: 0.95rem;
}
.pixel-tag {
  font-family: var(--pixel);
  font-size: 0.62rem;
  background: var(--amber);
  color: #080b11;
  padding: 0.35rem 0.6rem;
  border-radius: 4px;
  letter-spacing: 0.04em;
  box-shadow: 0 2px 0 #b45309;
}
.hud-stats {
  display: flex;
  align-items: center;
  gap: 0.9rem;
  font-family: var(--mono);
  font-size: 0.8rem;
  flex-wrap: wrap;
}
.stat-pill {
  background: var(--bg-card);
  border: 1px solid var(--line);
  padding: 0.3rem 0.75rem;
  border-radius: 8px;
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
}
.xp-bar-wrap {
  width: 110px;
  height: 10px;
  background: #05070b;
  border-radius: 99px;
  overflow: hidden;
  border: 1px solid var(--line);
}
.xp-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--amber), var(--emerald));
  width: 4%;
  transition: width 0.35s ease;
}
.btn {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  background: var(--bg-subtle);
  color: var(--ink);
  border: 1px solid var(--line);
  padding: 0.5rem 0.95rem;
  border-radius: 8px;
  font-size: 0.83rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
  font-family: var(--sans);
}
.btn:hover {
  border-color: var(--amber);
  transform: translateY(-1px);
  text-decoration: none;
}
.btn-primary {
  background: var(--amber);
  color: #080b11;
  border-color: var(--amber);
  font-weight: 700;
  box-shadow: 0 3px 0 #b45309;
}
.btn-primary:hover {
  background: #fbbf24;
}
.btn-emerald {
  background: var(--emerald);
  color: #051b11;
  border-color: var(--emerald);
  font-weight: 700;
  box-shadow: 0 3px 0 #047857;
}
.tag {
  font-family: var(--mono);
  font-size: 0.73rem;
  padding: 0.22rem 0.65rem;
  border-radius: 999px;
  background: var(--bg-subtle);
  border: 1px solid var(--line);
  color: var(--muted);
}
.tag-amber { background: var(--amber-soft); color: var(--amber); border-color: rgba(245,158,11,0.35); }
.tag-emerald { background: var(--emerald-soft); color: var(--emerald); border-color: rgba(16,185,129,0.35); }
.tag-cyan { background: var(--cyan-soft); color: var(--cyan); border-color: rgba(56,189,248,0.35); }
"""


def _render_university_index(curriculum: dict, lessons: dict[str, dict], code_by_id: dict[str, str]) -> str:
    """Render the interactive 2D AI University Campus & Building Interior RPG."""
    # Bundle full lesson data + gate challenges + code into JSON so rooms open instantaneously inside the game
    game_lessons = {}
    for lid, ldata in lessons.items():
        copy_l = dict(ldata)
        copy_l["code_text"] = code_by_id.get(lid, "")
        copy_l["gate_challenge"] = GATE_CHALLENGES.get(lid, [])
        game_lessons[lid] = copy_l

    curriculum_json = json.dumps(curriculum)
    lessons_json = json.dumps(game_lessons)

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>BitsByBlocks AI University · Interactive Learning RPG</title>
  <style>
    {SHARED_CSS}
    .game-shell {{
      display: grid;
      grid-template-columns: 1fr 370px;
      height: calc(100vh - 56px);
      overflow: hidden;
    }}
    @media (max-width: 1024px) {{
      .game-shell {{
        grid-template-columns: 1fr;
        height: auto;
        overflow: visible;
      }}
    }}
    .viewport-wrap {{
      position: relative;
      background: #070a10;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      overflow: hidden;
      padding: 0.75rem;
      user-select: none;
    }}
    #game-canvas {{
      width: 100%;
      max-width: 1060px;
      aspect-ratio: 16 / 10;
      background: #0d131f;
      border: 3px solid var(--line);
      border-radius: 14px;
      box-shadow: 0 20px 60px rgba(0, 0, 0, 0.65), inset 0 0 40px rgba(0,0,0,0.5);
      image-rendering: pixelated;
      cursor: pointer;
    }}
    .canvas-overlay-top {{
      position: absolute;
      top: 1.35rem;
      left: 1.5rem;
      right: 1.5rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
      pointer-events: none;
      gap: 0.75rem;
      flex-wrap: wrap;
    }}
    .canvas-overlay-top > * {{
      pointer-events: auto;
    }}
    .location-banner {{
      background: rgba(15, 20, 32, 0.92);
      border: 2px solid var(--amber);
      padding: 0.45rem 0.9rem;
      border-radius: 10px;
      display: flex;
      align-items: center;
      gap: 0.65rem;
      box-shadow: 0 8px 24px rgba(0,0,0,0.45);
    }}
    .location-title {{
      font-family: var(--pixel);
      font-size: 0.68rem;
      color: var(--amber);
    }}
    .controls-toast {{
      position: absolute;
      bottom: 1.35rem;
      left: 50%;
      transform: translateX(-50%);
      background: rgba(15, 20, 32, 0.94);
      border: 2px solid var(--line);
      padding: 0.55rem 1.15rem;
      border-radius: 999px;
      font-family: var(--mono);
      font-size: 0.8rem;
      color: var(--ink);
      display: flex;
      align-items: center;
      gap: 0.85rem;
      box-shadow: 0 10px 28px rgba(0,0,0,0.55);
      white-space: nowrap;
    }}
    .kbd {{
      background: var(--bg-subtle);
      border: 1px solid var(--amber);
      color: var(--amber);
      padding: 0.1rem 0.45rem;
      border-radius: 5px;
      font-weight: 700;
      font-size: 0.75rem;
    }}
    .quest-sidebar {{
      background: var(--bg-elev);
      border-left: 2px solid var(--line);
      display: flex;
      flex-direction: column;
      height: calc(100vh - 56px);
      overflow-y: auto;
      padding: 1.15rem;
    }}
    .quest-card {{
      background: var(--bg-card);
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 1rem;
      margin-bottom: 0.9rem;
    }}
    .quest-card.active-target {{
      border-color: var(--amber);
      box-shadow: 0 0 0 1px rgba(245, 158, 11, 0.25);
    }}
    .room-pill-list {{
      display: flex;
      flex-direction: column;
      gap: 0.45rem;
    }}
    .room-pill {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0.55rem 0.75rem;
      border-radius: 9px;
      background: var(--bg-card);
      border: 1px solid var(--line);
      font-size: 0.82rem;
      cursor: pointer;
      transition: all 0.15s ease;
      gap: 0.5rem;
    }}
    .room-pill:hover {{
      border-color: var(--amber);
    }}
    .room-pill.cleared {{
      border-color: rgba(16, 185, 129, 0.5);
      background: rgba(16, 185, 129, 0.08);
    }}
    .room-pill.unlocked {{
      border-color: var(--amber);
      background: rgba(245, 158, 11, 0.11);
    }}
    .room-pill.locked {{
      opacity: 0.55;
    }}

    /* ROOM WORKSTATION MODAL */
    .modal-backdrop {{
      position: fixed;
      inset: 0;
      z-index: 200;
      background: rgba(4, 6, 10, 0.86);
      backdrop-filter: blur(8px);
      display: none;
      align-items: center;
      justify-content: center;
      padding: 1.25rem;
    }}
    .modal-backdrop.open {{
      display: flex;
    }}
    .workstation-window {{
      background: var(--bg-elev);
      border: 2px solid var(--amber);
      border-radius: 16px;
      width: 100%;
      max-width: 1120px;
      height: 90vh;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      box-shadow: 0 25px 80px rgba(0,0,0,0.85);
    }}
    .ws-header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0.9rem 1.4rem;
      background: var(--bg-card);
      border-bottom: 1px solid var(--line);
      gap: 1rem;
      flex-wrap: wrap;
    }}
    .ws-tabs {{
      display: flex;
      gap: 0.5rem;
      padding: 0.7rem 1.4rem;
      background: #0b0f18;
      border-bottom: 1px solid var(--line);
      flex-wrap: wrap;
    }}
    .ws-tab {{
      background: var(--bg-card);
      color: var(--muted);
      border: 1px solid var(--line);
      padding: 0.5rem 0.95rem;
      border-radius: 8px;
      font-size: 0.83rem;
      font-weight: 600;
      cursor: pointer;
    }}
    .ws-tab.active {{
      background: var(--amber);
      color: #080b11;
      border-color: var(--amber);
      font-weight: 700;
    }}
    .ws-body {{
      flex: 1;
      overflow-y: auto;
      padding: 1.6rem 2rem 3rem;
    }}
    .ws-pane {{ display: none; }}
    .ws-pane.active {{ display: block; }}

    .spine-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 0.85rem;
      margin: 1rem 0 1.75rem;
    }}
    .spine-card {{
      background: var(--bg-card);
      border: 1px solid var(--line);
      border-radius: 11px;
      padding: 0.95rem 1.1rem;
    }}
    .spine-label {{
      font-family: var(--mono);
      font-size: 0.7rem;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: var(--amber);
      margin-bottom: 0.3rem;
    }}
    .figure-box {{
      background: #ffffff;
      color: #1e1e1e;
      border-radius: 12px;
      padding: 1.15rem;
      margin: 1.15rem 0;
      border: 2px solid var(--line);
    }}
    .quiz-option {{
      display: block;
      width: 100%;
      text-align: left;
      background: var(--bg-card);
      color: var(--ink);
      border: 1px solid var(--line);
      padding: 0.75rem 1rem;
      border-radius: 9px;
      margin-bottom: 0.5rem;
      cursor: pointer;
      font-size: 0.9rem;
      transition: all 0.12s ease;
    }}
    .quiz-option:hover {{
      border-color: var(--amber);
    }}
    .quiz-option.selected {{
      border-color: var(--amber);
      background: var(--amber-soft);
    }}
    .quiz-option.correct {{
      border-color: var(--emerald);
      background: var(--emerald-soft);
    }}
    .quiz-option.wrong {{
      border-color: var(--rose);
      background: rgba(244, 63, 94, 0.16);
    }}
    .share-badge-card {{
      background: linear-gradient(145deg, #111827 0%, #1e1b4b 55%, #064e3b 100%);
      border: 2px solid var(--amber);
      border-radius: 16px;
      padding: 1.5rem 1.75rem;
      margin-bottom: 1.5rem;
      box-shadow: 0 16px 40px rgba(0,0,0,0.45);
    }}
    .ig-deck {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(215px, 1fr));
      gap: 0.9rem;
      margin-top: 1rem;
    }}
    .ig-slide {{
      aspect-ratio: 4 / 5;
      background: linear-gradient(160deg, #131824 0%, #1e1b2e 100%);
      border: 2px solid var(--amber);
      border-radius: 14px;
      padding: 1.2rem;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }}
    pre {{
      background: #06080d;
      color: #e2e8f0;
      padding: 1rem;
      border-radius: 10px;
      overflow-x: auto;
      font-family: var(--mono);
      font-size: 0.81rem;
      border: 1px solid var(--line);
    }}
    code {{
      font-family: var(--mono);
      background: var(--bg-subtle);
      padding: 0.12rem 0.35rem;
      border-radius: 4px;
      font-size: 0.88em;
    }}
    pre code {{ background: none; padding: 0; }}
  </style>
</head>
<body>
  <header class="hud-bar">
    <div class="hud-brand">
      <span class="pixel-tag">BITS UNIVERSITY</span>
      <span>Ashwin's AI Engineering Campus</span>
    </div>
    <div class="hud-stats">
      <div class="stat-pill">
        <span>🧙‍♂️ Player: <strong>Ashwin</strong></span>
      </div>
      <div class="stat-pill">
        <span>🏛️ <strong id="hud-building-name">Building 0: Ground Floor Hall</strong></span>
      </div>
      <div class="stat-pill">
        <span>🔑 Rooms Cleared: <strong id="hud-cleared-count" style="color:var(--emerald);">0 / 49</strong></span>
        <div class="xp-bar-wrap"><div id="hud-xp-fill" class="xp-bar-fill"></div></div>
      </div>
      <button class="btn" onclick="switchScene(state.scene === 'campus' ? 'building' : 'campus')" id="scene-toggle-btn">
        🗺️ View Campus Overworld
      </button>
    </div>
  </header>

  <div class="game-shell">
    <!-- 2D RPG CANVAS VIEWPORT -->
    <div class="viewport-wrap">
      <div class="canvas-overlay-top">
        <div class="location-banner">
          <span class="location-title" id="canvas-loc-title">BUILDING 0 · GROUND FLOOR HALL</span>
          <span class="tag tag-emerald" id="canvas-loc-sub">Walk into a Room & press [E] at the Terminal</span>
        </div>
        <div style="display:flex;gap:0.5rem;">
          <button class="btn" onclick="switchScene('campus')">🌍 Campus Map (6 Buildings)</button>
          <button class="btn btn-primary" onclick="switchScene('building')">🏛️ Inside Building 0</button>
        </div>
      </div>

      <canvas id="game-canvas" width="1060" height="662"></canvas>

      <div class="controls-toast" id="controls-toast">
        <span>Move: <span class="kbd">W A S D</span> or <span class="kbd">← ↑ → ↓</span> or <strong>Click Floor</strong></span>
        <span>·</span>
        <span>Interact: <span class="kbd">E</span> or <span class="kbd">Enter</span></span>
      </div>
    </div>

    <!-- RIGHT SIDEBAR: QUEST LOG & ROOM TELEPORTER -->
    <aside class="quest-sidebar">
      <div class="quest-card active-target">
        <div class="spine-label">ACTIVE QUEST OBJECTIVE</div>
        <div id="quest-headline" style="font-weight:700;font-size:1.02rem;margin-bottom:0.35rem;">
          Clear Room 101: What an LLM actually is
        </div>
        <div id="quest-desc" style="font-size:0.84rem;color:var(--muted);margin-bottom:0.75rem;">
          Walk Ashwin into Room 101 (top-left door) and press <strong>E</strong> at the Workstation Terminal. Pass the 3-question Lab Gate Check to unlock the laser door to Room 102!
        </div>
        <div style="display:flex;gap:0.5rem;flex-wrap:wrap;">
          <button class="btn btn-primary" onclick="openCurrentOrNextRoom()" id="quick-enter-btn">
            ⚡ Enter Active Room Workstation
          </button>
          <button class="btn" onclick="resetProgress()" title="Reset saved progress">↺ Reset</button>
        </div>
      </div>

      <div style="display:flex;justify-content:space-between;align-items:center;margin:0.4rem 0 0.6rem;">
        <span style="font-family:var(--pixel);font-size:0.62rem;color:var(--muted);">BUILDING 0 · ROOMS (8)</span>
        <select id="building-selector" onchange="selectBuilding(parseInt(this.value))" style="background:var(--bg-card);color:var(--ink);border:1px solid var(--line);padding:0.25rem 0.5rem;border-radius:6px;font-size:0.78rem;font-family:var(--mono);">
          <option value="0">Bldg 0: Ground floor (8 rooms)</option>
          <option value="1">Bldg 1: Inside the box (8 rooms)</option>
          <option value="2">Bldg 2: AI engineer (8 rooms)</option>
          <option value="3">Bldg 3: Adapter (8 rooms)</option>
          <option value="4">Bldg 4: Operator (9 rooms)</option>
          <option value="5">Bldg 5: Builder (8 rooms)</option>
        </select>
      </div>

      <div id="sidebar-room-list" class="room-pill-list"></div>
    </aside>
  </div>

  <!-- ROOM WORKSTATION & GATE CHALLENGE MODAL -->
  <div id="room-modal" class="modal-backdrop">
    <div class="workstation-window">
      <div class="ws-header">
        <div>
          <div style="display:flex;align-items:center;gap:0.6rem;margin-bottom:0.2rem;">
            <span class="pixel-tag" id="ws-room-code">ROOM 101</span>
            <span class="tag tag-emerald" id="ws-room-status">UNLOCKED</span>
            <a id="ws-standalone-link" href="#" class="tag tag-cyan">Open Full Page ↗</a>
          </div>
          <h2 id="ws-title" style="margin:0;font-family:var(--serif);font-size:1.55rem;">What an LLM actually is</h2>
        </div>
        <div style="display:flex;gap:0.6rem;align-items:center;">
          <button class="btn btn-emerald" onclick="switchWsTab('gate')">🔑 Pass Room Gate Challenge</button>
          <button class="btn" onclick="closeRoomModal()">✕ Back to Hallway (Esc)</button>
        </div>
      </div>

      <div class="ws-tabs">
        <button class="ws-tab active" data-tab="sim" onclick="switchWsTab('sim')">1. Interactive Simulator & Story</button>
        <button class="ws-tab" data-tab="diagrams" onclick="switchWsTab('diagrams')">2. Excalidraw Diagrams & Jargon</button>
        <button class="ws-tab" data-tab="lab" onclick="switchWsTab('lab')">3. Python Lab & Verified Output</button>
        <button class="ws-tab" data-tab="gate" onclick="switchWsTab('gate')">4. 🔑 Gate Challenge (Unlock Next Room)</button>
        <button class="ws-tab" data-tab="share" onclick="switchWsTab('share')">5. 🏆 Share Studio (X + IG Card)</button>
      </div>

      <div class="ws-body">
        <div id="ws-pane-sim" class="ws-pane active"></div>
        <div id="ws-pane-diagrams" class="ws-pane"></div>
        <div id="ws-pane-lab" class="ws-pane"></div>
        <div id="ws-pane-gate" class="ws-pane"></div>
        <div id="ws-pane-share" class="ws-pane"></div>
      </div>
    </div>
  </div>

  <script>
    const CURRICULUM = {curriculum_json};
    const SEEDED_LESSONS = {lessons_json};

    // Persistent game progression
    const STORAGE_KEY = "bits_university_cleared_v2";
    let clearedRooms = new Set(JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]"));

    const state = {{
      scene: "building", // 'building' (interior with 8 rooms) or 'campus' (overworld with 6 buildings)
      buildingLevel: 0,
      player: {{ x: 530, y: 330, targetX: null, targetY: null, speed: 4.3, dir: "down", frame: 0 }},
      campusPlayer: {{ x: 240, y: 240, targetX: null, targetY: null }},
      keys: {{}},
      nearbyRoomIndex: -1,
      nearbyBuildingIndex: -1,
      activeLessonId: null,
      quizAnswers: {{}}
    }};

    // 8 Room coordinates inside a Building Floorplan (4 top rooms, 4 bottom rooms, central hallway)
    const ROOM_RECTS = [
      {{ idx: 0, x: 55,  y: 55,  w: 215, h: 185, doorX: 162, doorY: 240, termX: 162, termY: 130 }},
      {{ idx: 1, x: 300, y: 55,  w: 215, h: 185, doorX: 407, doorY: 240, termX: 407, termY: 130 }},
      {{ idx: 2, x: 545, y: 55,  w: 215, h: 185, doorX: 652, doorY: 240, termX: 652, termY: 130 }},
      {{ idx: 3, x: 790, y: 55,  w: 215, h: 185, doorX: 897, doorY: 240, termX: 897, termY: 130 }},
      {{ idx: 4, x: 55,  y: 420, w: 215, h: 185, doorX: 162, doorY: 420, termX: 162, termY: 515 }},
      {{ idx: 5, x: 300, y: 420, w: 215, h: 185, doorX: 407, doorY: 420, termX: 407, termY: 515 }},
      {{ idx: 6, x: 545, y: 420, w: 215, h: 185, doorX: 652, doorY: 420, termX: 652, termY: 515 }},
      {{ idx: 7, x: 790, y: 420, w: 215, h: 185, doorX: 897, doorY: 420, termX: 897, termY: 515 }}
    ];

    // 6 University Buildings on the Campus Overworld
    const CAMPUS_BUILDINGS = [
      {{ level: 0, name: "Ground Floor Hall", sub: "Tokens, Sampling & APIs", x: 90,  y: 95,  w: 250, h: 175, color: "#f59e0b" }},
      {{ level: 1, name: "Transformer Tower", sub: "Attention, Blocks & KV Cache", x: 405, y: 95,  w: 250, h: 175, color: "#38bdf8" }},
      {{ level: 2, name: "AI Systems Lab", sub: "Evals, RAG & Agents", x: 720, y: 95,  w: 250, h: 175, color: "#10b981" }},
      {{ level: 3, name: "Adaptation Foundry", sub: "SFT, LoRA, RLHF & DPO", x: 90,  y: 395, w: 250, h: 175, color: "#a855f7" }},
      {{ level: 4, name: "Inference Reactor", sub: "Batching, Quantization & Security", x: 405, y: 395, w: 250, h: 175, color: "#f43f5e" }},
      {{ level: 5, name: "Frontier Citadel", sub: "Kernels, MoE & Pretraining", x: 720, y: 395, w: 250, h: 175, color: "#eab308" }}
    ];

    function getModulesForLevel(lvl) {{
      return CURRICULUM.modules.filter(m => m.level === lvl);
    }}

    function isRoomUnlocked(lvl, idxInLevel) {{
      const mods = getModulesForLevel(lvl);
      if (idxInLevel === 0 && lvl === 0) return true;
      if (idxInLevel > 0) {{
        const prevMod = mods[idxInLevel - 1];
        return prevMod && clearedRooms.has(prevMod.id);
      }}
      // First room of higher building requires previous building cleared
      const prevMods = getModulesForLevel(lvl - 1);
      return prevMods.length > 0 && prevMods.every(m => clearedRooms.has(m.id));
    }}

    function saveProgress() {{
      localStorage.setItem(STORAGE_KEY, JSON.stringify([...clearedRooms]));
      updateHudAndSidebar();
    }}

    function resetProgress() {{
      clearedRooms.clear();
      saveProgress();
    }}

    function updateHudAndSidebar() {{
      const total = CURRICULUM.modules.length;
      const done = clearedRooms.size;
      document.getElementById("hud-cleared-count").innerText = `${{done}} / ${{total}}`;
      document.getElementById("hud-xp-fill").style.width = `${{Math.max(4, (done / total) * 100)}}%`;

      const bldg = CAMPUS_BUILDINGS[state.buildingLevel];
      document.getElementById("hud-building-name").innerText = `Building ${{bldg.level}}: ${{bldg.name}}`;
      document.getElementById("building-selector").value = String(state.buildingLevel);

      if (state.scene === "campus") {{
        document.getElementById("canvas-loc-title").innerText = "BITS UNIVERSITY · CAMPUS OVERWORLD";
        document.getElementById("canvas-loc-sub").innerText = "Walk to any Building entrance & press [E]";
        document.getElementById("scene-toggle-btn").innerText = "🏛️ Enter Building " + state.buildingLevel;
      }} else {{
        document.getElementById("canvas-loc-title").innerText = `BUILDING ${{bldg.level}} · ${{bldg.name.toUpperCase()}}`;
        document.getElementById("canvas-loc-sub").innerText = bldg.sub;
        document.getElementById("scene-toggle-btn").innerText = "🗺️ View Campus Overworld";
      }}

      // Render room pills
      const mods = getModulesForLevel(state.buildingLevel);
      const listEl = document.getElementById("sidebar-room-list");
      let nextTargetMod = null;

      listEl.innerHTML = mods.map((m, idx) => {{
        const cleared = clearedRooms.has(m.id);
        const unlocked = isRoomUnlocked(state.buildingLevel, idx);
        const seeded = Boolean(SEEDED_LESSONS[m.id]);
        if (!cleared && unlocked && !nextTargetMod) nextTargetMod = {{ m, idx }};

        let statusBadge = "🔒 Locked";
        let cls = "room-pill locked";
        if (cleared) {{
          statusBadge = "✅ Cleared";
          cls = "room-pill cleared";
        }} else if (unlocked) {{
          statusBadge = seeded ? "🟢 Unlocked" : "🟡 Preview";
          cls = "room-pill unlocked";
        }}

        const roomNum = `${{state.buildingLevel + 1}}0${{idx + 1}}`;
        return `<div class="${{cls}}" onclick="walkToAndOpenRoom(${{idx}})">
          <div style="overflow:hidden;">
            <div style="font-family:var(--mono);font-size:0.7rem;color:var(--amber);">ROOM ${{roomNum}} ${{seeded ? '· FULL LAB' : ''}}</div>
            <div style="font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${{m.title}}</div>
          </div>
          <span style="font-family:var(--mono);font-size:0.72rem;white-space:nowrap;">${{statusBadge}}</span>
        </div>`;
      }}).join("");

      if (nextTargetMod) {{
        const rnum = `${{state.buildingLevel + 1}}0${{nextTargetMod.idx + 1}}`;
        document.getElementById("quest-headline").innerText = `Clear Room ${{rnum}}: ${{nextTargetMod.m.title}}`;
        document.getElementById("quest-desc").innerText = `Question: "${{nextTargetMod.m.question}}" — Walk into Room ${{rnum}} and pass the Gate Challenge at the terminal to unlock Room ${{state.buildingLevel + 1}}0${{nextTargetMod.idx + 2}}!`;
      }} else {{
        document.getElementById("quest-headline").innerText = `Building ${{state.buildingLevel}} Completed!`;
        document.getElementById("quest-desc").innerText = `Every room in this building is cleared. Head to the Campus Overworld to enter the next building.`;
      }}
    }}

    function switchScene(newScene) {{
      state.scene = newScene;
      updateHudAndSidebar();
    }}

    function selectBuilding(lvl) {{
      state.buildingLevel = lvl;
      state.scene = "building";
      state.player.x = 530;
      state.player.y = 330;
      state.player.targetX = null;
      state.player.targetY = null;
      updateHudAndSidebar();
    }}

    function walkToAndOpenRoom(idx) {{
      if (state.scene !== "building") {{
        state.scene = "building";
        updateHudAndSidebar();
      }}
      const r = ROOM_RECTS[idx];
      if (!r) return;
      state.player.targetX = r.termX;
      state.player.targetY = r.termY + (idx < 4 ? 28 : -28);
      state.pendingOpenRoomIdx = idx;
    }}

    function openCurrentOrNextRoom() {{
      const mods = getModulesForLevel(state.buildingLevel);
      if (state.nearbyRoomIndex >= 0 && state.nearbyRoomIndex < mods.length) {{
        openRoomModal(state.nearbyRoomIndex);
        return;
      }}
      // Find first unlocked but uncleared room
      let targetIdx = 0;
      for (let i = 0; i < mods.length; i++) {{
        if (isRoomUnlocked(state.buildingLevel, i) && !clearedRooms.has(mods[i].id)) {{
          targetIdx = i;
          break;
        }}
      }}
      walkToAndOpenRoom(targetIdx);
    }}

    // KEYBOARD & MOUSE CONTROLS
    window.addEventListener("keydown", e => {{
      if (document.getElementById("room-modal").classList.contains("open")) {{
        if (e.key === "Escape") closeRoomModal();
        return;
      }}
      state.keys[e.key.toLowerCase()] = true;
      if (["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", " "].includes(e.key)) {{
        e.preventDefault();
      }}
      if (e.key.toLowerCase() === "e" || e.key === "Enter") {{
        triggerInteraction();
      }}
    }});

    window.addEventListener("keyup", e => {{
      state.keys[e.key.toLowerCase()] = false;
    }});

    const canvas = document.getElementById("game-canvas");
    const ctx = canvas.getContext("2d");

    canvas.addEventListener("click", e => {{
      const rect = canvas.getBoundingClientRect();
      const scaleX = canvas.width / rect.width;
      const scaleY = canvas.height / rect.height;
      const cx = (e.clientX - rect.left) * scaleX;
      const cy = (e.clientY - rect.top) * scaleY;

      if (state.scene === "campus") {{
        // Check if clicked on a building
        for (const b of CAMPUS_BUILDINGS) {{
          if (cx >= b.x && cx <= b.x + b.w && cy >= b.y && cy <= b.y + b.h) {{
            selectBuilding(b.level);
            return;
          }}
        }}
        state.campusPlayer.targetX = cx;
        state.campusPlayer.targetY = cy;
      }} else {{
        // Check if clicked inside a room terminal box
        const mods = getModulesForLevel(state.buildingLevel);
        for (let i = 0; i < Math.min(ROOM_RECTS.length, mods.length); i++) {{
          const r = ROOM_RECTS[i];
          if (cx >= r.x && cx <= r.x + r.w && cy >= r.y && cy <= r.y + r.h) {{
            walkToAndOpenRoom(i);
            return;
          }}
        }}
        state.player.targetX = cx;
        state.player.targetY = cy;
        state.pendingOpenRoomIdx = null;
      }}
    }});

    function triggerInteraction() {{
      if (state.scene === "campus") {{
        if (state.nearbyBuildingIndex >= 0) {{
          selectBuilding(state.nearbyBuildingIndex);
        }}
      }} else {{
        if (state.nearbyRoomIndex >= 0) {{
          openRoomModal(state.nearbyRoomIndex);
        }}
      }}
    }}

    // GAME LOOP: UPDATE & RENDER
    function updateGame() {{
      let dx = 0, dy = 0;
      if (state.keys["w"] || state.keys["arrowup"]) dy -= 1;
      if (state.keys["s"] || state.keys["arrowdown"]) dy += 1;
      if (state.keys["a"] || state.keys["arrowleft"]) dx -= 1;
      if (state.keys["d"] || state.keys["arrowright"]) dx += 1;

      const activePlayer = state.scene === "campus" ? state.campusPlayer : state.player;

      if (dx !== 0 || dy !== 0) {{
        activePlayer.targetX = null;
        activePlayer.targetY = null;
        state.pendingOpenRoomIdx = null;
        const len = Math.hypot(dx, dy);
        activePlayer.x += (dx / len) * state.player.speed;
        activePlayer.y += (dy / len) * state.player.speed;
        state.player.frame += 0.2;
      }} else if (activePlayer.targetX !== null && activePlayer.targetY !== null) {{
        const tx = activePlayer.targetX - activePlayer.x;
        const ty = activePlayer.targetY - activePlayer.y;
        const dist = Math.hypot(tx, ty);
        if (dist <= state.player.speed * 1.2) {{
          activePlayer.x = activePlayer.targetX;
          activePlayer.y = activePlayer.targetY;
          activePlayer.targetX = null;
          activePlayer.targetY = null;
          if (state.pendingOpenRoomIdx !== null && state.pendingOpenRoomIdx !== undefined) {{
            const idx = state.pendingOpenRoomIdx;
            state.pendingOpenRoomIdx = null;
            openRoomModal(idx);
          }}
        }} else {{
          activePlayer.x += (tx / dist) * state.player.speed * 1.25;
          activePlayer.y += (ty / dist) * state.player.speed * 1.25;
          state.player.frame += 0.25;
        }}
      }}

      // Clamp bounds
      activePlayer.x = Math.max(40, Math.min(canvas.width - 40, activePlayer.x));
      activePlayer.y = Math.max(45, Math.min(canvas.height - 45, activePlayer.y));

      // Proximity checks
      if (state.scene === "campus") {{
        state.nearbyBuildingIndex = -1;
        for (const b of CAMPUS_BUILDINGS) {{
          const bx = b.x + b.w / 2;
          const by = b.y + b.h / 2;
          if (Math.hypot(activePlayer.x - bx, activePlayer.y - by) < 135) {{
            state.nearbyBuildingIndex = b.level;
            break;
          }}
        }}
      }} else {{
        state.nearbyRoomIndex = -1;
        const mods = getModulesForLevel(state.buildingLevel);
        for (let i = 0; i < Math.min(ROOM_RECTS.length, mods.length); i++) {{
          const r = ROOM_RECTS[i];
          if (activePlayer.x >= r.x - 15 && activePlayer.x <= r.x + r.w + 15 &&
              activePlayer.y >= r.y - 25 && activePlayer.y <= r.y + r.h + 25) {{
            state.nearbyRoomIndex = i;
            break;
          }}
        }}
      }}
    }}

    function drawAvatar(x, y, label) {{
      const bounce = Math.sin(state.player.frame) * 2.2;
      // Shadow
      ctx.fillStyle = "rgba(0, 0, 0, 0.45)";
      ctx.beginPath();
      ctx.ellipse(x, y + 16, 13, 6, 0, 0, Math.PI * 2);
      ctx.fill();

      // Body (Amber hoodie)
      ctx.fillStyle = "#f59e0b";
      ctx.fillRect(x - 10, y - 4 + bounce, 20, 16);
      ctx.strokeStyle = "#080b11";
      ctx.lineWidth = 2;
      ctx.strokeRect(x - 10, y - 4 + bounce, 20, 16);

      // Head
      ctx.fillStyle = "#fde68a";
      ctx.fillRect(x - 9, y - 19 + bounce, 18, 15);
      ctx.strokeRect(x - 9, y - 19 + bounce, 18, 15);

      // Glasses / Eyes
      ctx.fillStyle = "#0f172a";
      ctx.fillRect(x - 6, y - 13 + bounce, 4, 4);
      ctx.fillRect(x + 2, y - 13 + bounce, 4, 4);

      // Nameplate
      ctx.font = "bold 11px 'JetBrains Mono', monospace";
      ctx.fillStyle = "#ffffff";
      ctx.textAlign = "center";
      ctx.fillText(label, x, y - 25 + bounce);
    }}

    function drawBuildingInterior() {{
      ctx.fillStyle = "#0b101b";
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      // Floor grid tiles
      ctx.strokeStyle = "#141d30";
      ctx.lineWidth = 1;
      for (let gx = 0; gx < canvas.width; gx += 36) {{
        ctx.beginPath(); ctx.moveTo(gx, 0); ctx.lineTo(gx, canvas.height); ctx.stroke();
      }}
      for (let gy = 0; gy < canvas.height; gy += 36) {{
        ctx.beginPath(); ctx.moveTo(0, gy); ctx.lineTo(canvas.width, gy); ctx.stroke();
      }}

      // Central main corridor carpet
      ctx.fillStyle = "#131c2e";
      ctx.fillRect(35, 255, canvas.width - 70, 150);
      ctx.strokeStyle = "#263554";
      ctx.lineWidth = 2;
      ctx.strokeRect(35, 255, canvas.width - 70, 150);

      // Corridor centerline & directional arrows
      ctx.strokeStyle = "rgba(245, 158, 11, 0.25)";
      ctx.setLineDash([10, 10]);
      ctx.beginPath();
      ctx.moveTo(60, 330);
      ctx.lineTo(canvas.width - 60, 330);
      ctx.stroke();
      ctx.setLineDash([]);

      const mods = getModulesForLevel(state.buildingLevel);

      for (let i = 0; i < Math.min(ROOM_RECTS.length, mods.length); i++) {{
        const r = ROOM_RECTS[i];
        const m = mods[i];
        const cleared = clearedRooms.has(m.id);
        const unlocked = isRoomUnlocked(state.buildingLevel, i);
        const seeded = Boolean(SEEDED_LESSONS[m.id]);
        const isNearby = state.nearbyRoomIndex === i;

        // Room floor
        if (cleared) {{
          ctx.fillStyle = "rgba(16, 185, 129, 0.13)";
        }} else if (unlocked) {{
          ctx.fillStyle = "rgba(245, 158, 11, 0.12)";
        }} else {{
          ctx.fillStyle = "rgba(15, 23, 42, 0.78)";
        }}
        ctx.fillRect(r.x, r.y, r.w, r.h);

        // Room walls
        ctx.strokeStyle = cleared ? "#10b981" : (unlocked ? (isNearby ? "#fbbf24" : "#f59e0b") : "#334155");
        ctx.lineWidth = isNearby ? 4 : 2.5;
        ctx.strokeRect(r.x, r.y, r.w, r.h);

        // Doorway cutout on the corridor side
        const doorW = 54;
        ctx.fillStyle = "#131c2e";
        if (i < 4) {{
          ctx.fillRect(r.doorX - doorW / 2, r.y + r.h - 4, doorW, 8);
        }} else {{
          ctx.fillRect(r.doorX - doorW / 2, r.y - 4, doorW, 8);
        }}

        // Laser gate across door if locked
        if (!unlocked) {{
          ctx.strokeStyle = "#f43f5e";
          ctx.lineWidth = 3;
          ctx.beginPath();
          ctx.moveTo(r.doorX - doorW / 2, r.doorY);
          ctx.lineTo(r.doorX + doorW / 2, r.doorY);
          ctx.stroke();
        }}

        // Room Number Header
        const roomCode = `ROOM ${{state.buildingLevel + 1}}0${{i + 1}}`;
        ctx.fillStyle = cleared ? "#10b981" : (unlocked ? "#f59e0b" : "#64748b");
        ctx.font = "bold 11px 'JetBrains Mono', monospace";
        ctx.textAlign = "left";
        ctx.fillText(roomCode, r.x + 12, r.y + 22);

        // Status Icon top-right
        ctx.textAlign = "right";
        ctx.fillText(cleared ? "★ CLEARED" : (unlocked ? (seeded ? "● LIVE LAB" : "◐ PREVIEW") : "🔒 LOCKED"), r.x + r.w - 12, r.y + 22);

        // Room Title (wrapped 2 lines)
        ctx.fillStyle = unlocked || cleared ? "#f8fafc" : "#94a3b8";
        ctx.font = "bold 13px 'Inter', sans-serif";
        ctx.textAlign = "center";
        const words = m.title.split(" ");
        let line1 = "", line2 = "";
        for (const w of words) {{
          if ((line1 + " " + w).trim().length <= 22) line1 = (line1 + " " + w).trim();
          else line2 = (line2 + " " + w).trim();
        }}
        if (line2.length > 24) line2 = line2.slice(0, 22) + "…";
        const titleY = i < 4 ? r.y + 52 : r.y + 148;
        ctx.fillText(line1, r.x + r.w / 2, titleY);
        if (line2) ctx.fillText(line2, r.x + r.w / 2, titleY + 17);

        // Workstation Desk & Glowing Monitor inside room
        const tx = r.termX;
        const ty = r.termY;
        ctx.fillStyle = "#1e293b";
        ctx.fillRect(tx - 26, ty - 14, 52, 26);
        ctx.strokeStyle = cleared ? "#10b981" : (unlocked ? "#38bdf8" : "#475569");
        ctx.lineWidth = 2;
        ctx.strokeRect(tx - 26, ty - 14, 52, 26);

        // Monitor screen glow
        ctx.fillStyle = cleared ? "#10b981" : (unlocked ? "#38bdf8" : "#334155");
        ctx.fillRect(tx - 16, ty - 9, 32, 14);

        // Prompt bubble when player is inside/near room
        if (isNearby) {{
          ctx.fillStyle = "#f59e0b";
          ctx.fillRect(tx - 78, ty - 42, 156, 22);
          ctx.fillStyle = "#080b11";
          ctx.font = "bold 11px 'JetBrains Mono', monospace";
          ctx.textAlign = "center";
          ctx.fillText("PRESS [E] / CLICK DESK", tx, ty - 27);
        }}
      }}

      // Draw Player Avatar
      drawAvatar(state.player.x, state.player.y, "ASHWIN");
    }}

    function drawCampusOverworld() {{
      ctx.fillStyle = "#09131c";
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      // Campus Courtyard Pathways
      ctx.fillStyle = "#162235";
      ctx.fillRect(60, 310, canvas.width - 120, 48);
      ctx.fillRect(200, 90, 44, 480);
      ctx.fillRect(510, 90, 44, 480);
      ctx.fillRect(825, 90, 44, 480);

      for (const b of CAMPUS_BUILDINGS) {{
        const mods = getModulesForLevel(b.level);
        const done = mods.filter(m => clearedRooms.has(m.id)).length;
        const isNearby = state.nearbyBuildingIndex === b.level;

        ctx.fillStyle = "#131c2e";
        ctx.fillRect(b.x, b.y, b.w, b.h);
        ctx.strokeStyle = isNearby ? "#ffffff" : b.color;
        ctx.lineWidth = isNearby ? 4 : 2.5;
        ctx.strokeRect(b.x, b.y, b.w, b.h);

        // Roof banner
        ctx.fillStyle = b.color;
        ctx.fillRect(b.x, b.y, b.w, 28);
        ctx.fillStyle = "#080b11";
        ctx.font = "bold 11px 'JetBrains Mono', monospace";
        ctx.textAlign = "left";
        ctx.fillText(`BUILDING 0${{b.level}}`, b.x + 10, b.y + 18);
        ctx.textAlign = "right";
        ctx.fillText(`${{done}}/${{mods.length}} ROOMS`, b.x + b.w - 10, b.y + 18);

        ctx.fillStyle = "#f8fafc";
        ctx.font = "bold 16px 'Inter', sans-serif";
        ctx.textAlign = "center";
        ctx.fillText(b.name, b.x + b.w / 2, b.y + 75);

        ctx.fillStyle = "#94a3b8";
        ctx.font = "12px 'Inter', sans-serif";
        ctx.fillText(b.sub, b.x + b.w / 2, b.y + 100);

        ctx.fillStyle = b.color;
        ctx.font = "bold 11px 'JetBrains Mono', monospace";
        ctx.fillText(isNearby ? "▶ PRESS [E] OR CLICK TO ENTER" : "Click to enter building", b.x + b.w / 2, b.y + 145);
      }}

      drawAvatar(state.campusPlayer.x, state.campusPlayer.y, "ASHWIN");
    }}

    function loop() {{
      updateGame();
      if (state.scene === "campus") drawCampusOverworld();
      else drawBuildingInterior();
      requestAnimationFrame(loop);
    }}

    // ROOM WORKSTATION MODAL RENDERER
    function openRoomModal(idx) {{
      const mods = getModulesForLevel(state.buildingLevel);
      const mod = mods[idx];
      if (!mod) return;

      const unlocked = isRoomUnlocked(state.buildingLevel, idx);
      const cleared = clearedRooms.has(mod.id);
      const roomCode = `ROOM ${{state.buildingLevel + 1}}0${{idx + 1}}`;
      state.activeLessonId = mod.id;
      state.activeRoomIdx = idx;
      state.quizAnswers = {{}};

      document.getElementById("ws-room-code").innerText = roomCode;
      const statusEl = document.getElementById("ws-room-status");
      statusEl.innerText = cleared ? "★ ROOM CLEARED" : (unlocked ? "🟢 UNLOCKED" : "🔒 LOCKED (CLEAR PREVIOUS ROOM FIRST)");
      statusEl.className = cleared ? "tag tag-emerald" : (unlocked ? "tag tag-amber" : "tag");

      document.getElementById("ws-title").innerText = mod.title;
      const lesson = SEEDED_LESSONS[mod.id];
      const linkEl = document.getElementById("ws-standalone-link");
      if (lesson) {{
        linkEl.href = `lessons/${{mod.id}}/index.html`;
        linkEl.style.display = "inline-flex";
        renderSeededLessonModal(mod, lesson, roomCode, unlocked, cleared);
      }} else {{
        linkEl.style.display = "none";
        renderPreviewModuleModal(mod, roomCode, unlocked, cleared);
      }}

      document.getElementById("room-modal").classList.add("open");
      switchWsTab("sim");
    }}

    function closeRoomModal() {{
      document.getElementById("room-modal").classList.remove("open");
    }}

    function switchWsTab(tabName) {{
      document.querySelectorAll(".ws-tab").forEach(b => {{
        b.classList.toggle("active", b.getAttribute("data-tab") === tabName);
      }});
      document.querySelectorAll(".ws-pane").forEach(p => p.classList.remove("active"));
      document.getElementById("ws-pane-" + tabName).classList.add("active");
    }}

    function renderSeededLessonModal(mod, lesson, roomCode, unlocked, cleared) {{
      const sp = lesson.story_spine;
      // TAB 1: Interactive Simulator + Story Spine + Sections
      let simWidget = "";
      if (lesson.id === "l0-what-is-an-llm") {{
        simWidget = `
          <div class="quest-card active-target" style="margin-bottom:1.5rem;">
            <div class="spine-label">ROOM 101 INTERACTIVE MECHANISM · NEXT-TOKEN LOOP</div>
            <h3 style="margin:0.2rem 0 0.5rem;font-family:var(--serif);">Tune Temperature & Roll the Next-Token Sampler</h3>
            <div style="display:flex;gap:1rem;align-items:center;flex-wrap:wrap;margin-bottom:0.85rem;">
              <label style="font-family:var(--mono);font-size:0.84rem;">Temperature: <strong id="modal-temp-val" style="color:var(--amber);">1.0</strong></label>
              <input id="modal-temp-slider" type="range" min="0" max="2.0" step="0.1" value="1.0" oninput="updateModalL0Sim()" style="width:200px;accent-color:var(--amber);" />
              <button class="btn btn-primary" onclick="sampleModalL0Token()">Sample & Append Next Token →</button>
              <button class="btn" onclick="resetModalL0Sim()">Reset</button>
            </div>
            <div id="modal-prob-bars" style="margin-bottom:0.75rem;"></div>
            <div style="background:#06080d;padding:0.75rem 1rem;border-radius:8px;border:1px solid var(--line);font-family:var(--mono);font-size:0.86rem;">
              Prompt Context: <strong id="modal-live-ctx" style="color:var(--amber);">the server</strong>
            </div>
          </div>`;
      }} else if (lesson.id === "l0-tokens") {{
        simWidget = `
          <div class="quest-card active-target" style="margin-bottom:1.5rem;">
            <div class="spine-label">ROOM 102 INTERACTIVE MECHANISM · BPE TOKENIZER & FERTILITY INSPECTOR</div>
            <h3 style="margin:0.2rem 0 0.5rem;font-family:var(--serif);">Slice Strings into Subword Token IDs & Check the Cost Multiplier</h3>
            <div style="display:flex;gap:0.5rem;flex-wrap:wrap;margin-bottom:0.85rem;">
              <button class="btn btn-primary" onclick="inspectTokenPreset('strawberry')">"strawberry"</button>
              <button class="btn" onclick="inspectTokenPreset('s t r a w b e r r y')">"s t r a w b e r r y" (Spaced Fix)</button>
              <button class="btn" onclick="inspectTokenPreset('The server responded in 12ms.')">English Prose</button>
              <button class="btn" onclick="inspectTokenPreset('नमस्ते दुनिया')">Hindi ('नमस्ते दुनिया')</button>
              <button class="btn" onclick="inspectTokenPreset('🚀🔥🤖')">Emojis ('🚀🔥🤖')</button>
            </div>
            <div id="modal-token-chips" style="display:flex;gap:0.5rem;flex-wrap:wrap;margin-bottom:0.75rem;"></div>
            <div id="modal-token-stats" style="background:#06080d;padding:0.75rem 1rem;border-radius:8px;border:1px solid var(--line);font-family:var(--mono);font-size:0.84rem;"></div>
          </div>`;
      }}

      const secsHtml = (lesson.sections || []).map((s, i) => `
        <div class="quest-card" style="margin-bottom:1rem;">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.4rem;">
            <h3 style="margin:0;font-family:var(--serif);">${{i + 1}}. ${{s.heading}}</h3>
            <span class="tag tag-amber">${{s.badge || ''}}</span>
          </div>
          <div style="font-size:0.94rem;color:#cbd5e1;white-space:pre-line;">${{s.body_md}}</div>
        </div>
      `).join("");

      document.getElementById("ws-pane-sim").innerHTML = `
        <div style="font-family:var(--serif);font-size:1.15rem;color:var(--amber);font-style:italic;margin-bottom:0.65rem;">“${{lesson.question}}”</div>
        <div class="quest-card" style="border-left:4px solid var(--amber);margin-bottom:1.25rem;">
          <strong>One-Line Takeaway:</strong> ${{lesson.one_line}}
        </div>
        ${{simWidget}}
        <h3 style="font-family:var(--serif);margin-bottom:0.4rem;">The Story Spine</h3>
        <div class="spine-grid">
          <div class="spine-card"><div class="spine-label">The Surprise</div><div style="font-size:0.88rem;">${{sp.surprise}}</div></div>
          <div class="spine-card"><div class="spine-label">What Breaks</div><div style="font-size:0.88rem;">${{sp.broken}}</div></div>
          <div class="spine-card"><div class="spine-label">The Turn</div><div style="font-size:0.88rem;">${{sp.turn}}</div></div>
          <div class="spine-card"><div class="spine-label">Honest Limit</div><div style="font-size:0.88rem;">${{sp.honest_limit}}</div></div>
        </div>
        ${{secsHtml}}
      `;

      // TAB 2: Excalidraw Figures + Jargon Decoder
      const figsHtml = (lesson.figures || []).map(f => `
        <div class="figure-box">
          <img src="lessons/${{lesson.id}}/${{f.id}}.svg" alt="${{f.title}}" style="width:100%;height:auto;display:block;" />
          <div style="display:flex;justify-content:space-between;align-items:center;margin-top:0.65rem;padding-top:0.5rem;border-top:1px dashed #cbd5e1;font-size:0.82rem;color:#475569;">
            <span><strong>${{f.title}}:</strong> ${{f.caption}}</span>
            <a href="lessons/${{lesson.id}}/${{f.id}}.excalidraw" download style="color:#0284c7;font-family:var(--mono);">⬇ .excalidraw</a>
          </div>
        </div>
      `).join("");

      const jargonHtml = (lesson.jargon_decoder || []).map(j => `
        <div class="spine-card">
          <div style="font-weight:700;color:var(--amber);margin-bottom:0.25rem;">${{j.term}}</div>
          <div style="font-size:0.86rem;margin-bottom:0.35rem;">${{j.plain_words}}</div>
          <div style="font-size:0.78rem;color:var(--muted);font-family:var(--mono);">Why you care: ${{j.why_you_care}}</div>
        </div>
      `).join("");

      document.getElementById("ws-pane-diagrams").innerHTML = `
        <h3 style="font-family:var(--serif);margin-top:0;">Hand-Drawn Excalidraw Figures</h3>
        ${{figsHtml}}
        <h3 style="font-family:var(--serif);margin-top:2rem;">Jargon Decoder</h3>
        <div class="spine-grid">${{jargonHtml}}</div>
      `;

      // TAB 3: Lab & Verified Output
      const lab = lesson.lab;
      const accHtml = (lab.acceptance || []).map(a => `
        <div class="spine-card" style="border-left:4px solid var(--emerald);">
          <div class="spine-label" style="color:var(--emerald);">✓ VERIFIED ACCEPTANCE CRITERION</div>
          <div style="font-weight:600;font-size:0.88rem;margin-bottom:0.3rem;">${{a.criterion}}</div>
          <div style="font-family:var(--mono);font-size:0.75rem;color:var(--muted);">Evidence: ${{a.evidence}}</div>
        </div>
      `).join("");

      document.getElementById("ws-pane-lab").innerHTML = `
        <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:0.5rem;margin-bottom:1rem;">
          <div>
            <div class="spine-label">HANDS-ON PYTHON LAB</div>
            <h3 style="margin:0.2rem 0;font-family:var(--serif);">${{lab.title}}</h3>
          </div>
          <a class="btn btn-primary" href="lessons/${{lesson.id}}/${{lab.code_file}}" download>⬇ Download ${{lab.code_file}}</a>
        </div>
        <p style="font-size:0.9rem;color:var(--muted);">${{lab.goal}}</p>
        <div class="spine-grid">${{accHtml}}</div>
        <h4 style="font-family:var(--mono);font-size:0.82rem;color:var(--emerald);">REAL VERIFIED TERMINAL OUTPUT (EXIT 0)</h4>
        <pre><code>${{lab.real_output}}</code></pre>
        <h4 style="font-family:var(--mono);font-size:0.82rem;color:var(--amber);margin-top:1.5rem;">REFERENCE CODE (${{lab.code_file}})</h4>
        <pre><code>${{lesson.code_text.replace(/</g, "&lt;")}}</code></pre>
      `;

      // TAB 4: Gate Challenge (3 questions to unlock next room)
      const questions = lesson.gate_challenge || [];
      const qHtml = questions.map((qObj, qIdx) => {{
        const opts = qObj.options.map((opt, oIdx) => `
          <button class="quiz-option" id="q-${{qIdx}}-opt-${{oIdx}}" onclick="selectQuizOption(${{qIdx}}, ${{oIdx}})">
            ${{opt}}
          </button>
        `).join("");
        return `
          <div class="quest-card" style="margin-bottom:1rem;">
            <div style="font-weight:700;margin-bottom:0.65rem;">${{qObj.q}}</div>
            ${{opts}}
            <div id="q-${{qIdx}}-feedback" style="display:none;margin-top:0.5rem;font-size:0.84rem;padding:0.55rem 0.8rem;border-radius:8px;"></div>
          </div>
        `;
      }}).join("");

      document.getElementById("ws-pane-gate").innerHTML = `
        <div class="quest-card active-target" style="margin-bottom:1.25rem;">
          <div class="spine-label">ROOM GATE VERIFICATION CHALLENGE</div>
          <h3 style="margin:0.2rem 0 0.35rem;font-family:var(--serif);">Pass all 3 Lab Checks to Unlock the Next Room & Mint Your Share Card</h3>
          <p style="margin:0;font-size:0.88rem;color:var(--muted);">
            No skipping by vibes: every answer below comes directly from the mechanism and real lab output in this room.
          </p>
        </div>
        ${{qHtml}}
        <div id="gate-result-banner" style="margin-top:1rem;"></div>
      `;

      // TAB 5: Share Studio
      const sh = lesson.shareable;
      const tweetsHtml = (sh.x_thread || []).map(t => `
        <div class="quest-card" style="display:flex;justify-content:space-between;gap:1rem;align-items:flex-start;">
          <div style="white-space:pre-line;font-size:0.9rem;">${{t}}</div>
          <button class="btn" onclick="navigator.clipboard.writeText(this.previousElementSibling.innerText);this.innerText='Copied!'">Copy</button>
        </div>
      `).join("");

      const igHtml = (sh.instagram_carousel || []).map(s => `
        <div class="ig-slide">
          <div style="font-family:var(--mono);font-size:0.72rem;color:var(--amber);">${{roomCode}} · SLIDE 0${{s.slide}}</div>
          <div>
            <h4 style="font-family:var(--serif);font-size:1.25rem;margin:0.4rem 0;">${{s.headline}}</h4>
            <p style="font-size:0.84rem;color:#cbd5e1;margin:0;white-space:pre-line;">${{s.body}}</p>
          </div>
          <div style="font-family:var(--mono);font-size:0.68rem;color:#94a3b8;border-top:1px solid rgba(255,255,255,0.12);padding-top:0.45rem;display:flex;justify-content:space-between;">
            <span>@ashwinYardi</span><span>Bits University</span>
          </div>
        </div>
      `).join("");

      document.getElementById("ws-pane-share").innerHTML = `
        <div class="share-badge-card">
          <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:0.5rem;margin-bottom:0.6rem;">
            <span class="pixel-tag">${{roomCode}} CLEARED · ACHIEVEMENT CARD</span>
            <span class="tag tag-emerald">BitsByBlocks AI University · Rung ${{lesson.level}}</span>
          </div>
          <h3 style="font-family:var(--serif);font-size:1.65rem;margin:0.3rem 0;">${{lesson.title}}</h3>
          <p style="font-family:var(--serif);font-style:italic;font-size:1.12rem;color:#fde68a;margin:0.5rem 0 0.85rem;">
            “${{sh.the_turn}}”
          </p>
          <div style="font-size:0.84rem;color:#cbd5e1;margin-bottom:0.9rem;">
            <strong>Reel / Voiceover Hook:</strong> ${{sh.reel_hook}}
          </div>
          <div style="display:flex;gap:0.6rem;flex-wrap:wrap;">
            <button class="btn btn-primary" onclick="copyFullThread()">Copy Complete X Thread (${{sh.x_thread.length}} tweets)</button>
            <button class="btn" onclick="copyTurnCard()">Copy 'The Turn' Post</button>
          </div>
        </div>
        <h3 style="font-family:var(--serif);">Ready-to-Post X Thread</h3>
        ${{tweetsHtml}}
        <h3 style="font-family:var(--serif);margin-top:2rem;">4:5 Instagram Carousel Deck</h3>
        <div class="ig-deck">${{igHtml}}</div>
      `;

      if (lesson.id === "l0-what-is-an-llm") updateModalL0Sim();
      if (lesson.id === "l0-tokens") inspectTokenPreset("strawberry");
    }}

    function renderPreviewModuleModal(mod, roomCode, unlocked, cleared) {{
      document.getElementById("ws-pane-sim").innerHTML = `
        <div class="quest-card active-target">
          <div class="spine-label">${{roomCode}} · CURRICULUM BLUEPRINT</div>
          <h3 style="font-family:var(--serif);font-size:1.4rem;margin:0.3rem 0;">${{mod.title}}</h3>
          <p style="color:var(--amber);font-style:italic;font-family:var(--serif);font-size:1.1rem;">“${{mod.question}}”</p>
          <p><strong>What you unlock after clearing this room:</strong> ${{mod.can}}</p>
          <p><strong>Hands-On Lab Spec:</strong> ${{mod.exercise}}</p>
          <p style="font-family:var(--mono);font-size:0.78rem;color:var(--muted);">Jargon covered: ${{(mod.jargon || []).join(", ")}}</p>
        </div>
      `;
      document.getElementById("ws-pane-diagrams").innerHTML = `<p style="color:var(--muted);">Planned figures: ${{(mod.figures || []).join(" · ")}}</p>`;
      document.getElementById("ws-pane-lab").innerHTML = `<p style="color:var(--muted);">Lab exercise: ${{mod.exercise}}</p>`;
      document.getElementById("ws-pane-gate").innerHTML = `<p style="color:var(--muted);">Clear earlier rooms first so AI Coach seeds this room's live lab and gate check.</p>`;
      document.getElementById("ws-pane-share").innerHTML = `<p style="color:var(--muted);">Share Studio unlocks when this room's lab is seeded and verified.</p>`;
    }}

    // INTERACTIVE SIMULATORS INSIDE ROOM MODAL
    const L0_LOGITS = {{
      "the server": {{"crashed": 3.2, "responded": 2.9, "timed": 2.4, "melted": 0.4, "danced": -1.5}},
      "server crashed": {{"because": 3.6, "after": 2.5, "at": 1.8, "quietly": 0.9}},
      "server responded": {{"in": 3.4, "with": 2.8, "after": 1.7, "slowly": 1.1}},
      "server timed": {{"out": 4.5, "at": 1.1, "twice": 0.8}}
    }};
    let modalL0Tokens = ["the", "server"];

    function updateModalL0Sim() {{
      const slider = document.getElementById("modal-temp-slider");
      if (!slider) return;
      const temp = parseFloat(slider.value);
      document.getElementById("modal-temp-val").innerText = temp.toFixed(1);
      const key = modalL0Tokens.slice(-2).join(" ");
      const logits = L0_LOGITS[key] || {{"and": 2.2, "then": 2.0, "stopped": 2.6, "recovered": 2.3}};
      const entries = Object.entries(logits);
      let probs = {{}};
      if (temp <= 0.01) {{
        let best = entries[0][0], bestV = entries[0][1];
        entries.forEach(([k, v]) => {{ if (v > bestV) {{ best = k; bestV = v; }} }});
        entries.forEach(([k]) => probs[k] = (k === best ? 1.0 : 0.0));
      }} else {{
        const scaled = entries.map(([k, v]) => [k, v / temp]);
        const maxL = Math.max(...scaled.map(x => x[1]));
        const exps = scaled.map(([k, v]) => [k, Math.exp(v - maxL)]);
        const sum = exps.reduce((a, b) => a + b[1], 0);
        exps.forEach(([k, e]) => probs[k] = e / sum);
      }}
      const barsEl = document.getElementById("modal-prob-bars");
      barsEl.innerHTML = Object.entries(probs).sort((a, b) => b[1] - a[1]).map(([tok, p]) => {{
        const pct = (p * 100).toFixed(1);
        return `<div style="display:grid;grid-template-columns:100px 75px 1fr 60px;gap:0.6rem;align-items:center;font-family:var(--mono);font-size:0.8rem;margin-bottom:0.35rem;">
          <strong>${{tok}}</strong>
          <span style="color:var(--muted);">logit ${{logits[tok].toFixed(1)}}</span>
          <div style="background:#06080d;height:14px;border-radius:5px;overflow:hidden;border:1px solid var(--line);">
            <div style="background:var(--amber);height:100%;width:${{pct}}%;"></div>
          </div>
          <span style="text-align:right;">${{pct}}%</span>
        </div>`;
      }}).join("");
      document.getElementById("modal-live-ctx").innerText = modalL0Tokens.join(" ");
    }}

    function sampleModalL0Token() {{
      const slider = document.getElementById("modal-temp-slider");
      const temp = parseFloat(slider.value);
      const key = modalL0Tokens.slice(-2).join(" ");
      const logits = L0_LOGITS[key] || {{"and": 2.2, "then": 2.0, "stopped": 2.6, "recovered": 2.3}};
      const entries = Object.entries(logits);
      let probs = {{}};
      if (temp <= 0.01) {{
        let best = entries[0][0], bestV = entries[0][1];
        entries.forEach(([k, v]) => {{ if (v > bestV) {{ best = k; bestV = v; }} }});
        entries.forEach(([k]) => probs[k] = (k === best ? 1.0 : 0.0));
      }} else {{
        const scaled = entries.map(([k, v]) => [k, v / temp]);
        const maxL = Math.max(...scaled.map(x => x[1]));
        const exps = scaled.map(([k, v]) => [k, Math.exp(v - maxL)]);
        const sum = exps.reduce((a, b) => a + b[1], 0);
        exps.forEach(([k, e]) => probs[k] = e / sum);
      }}
      let r = Math.random(), acc = 0, pick = Object.keys(probs)[0];
      for (const [t, p] of Object.entries(probs)) {{
        acc += p;
        if (r <= acc) {{ pick = t; break; }}
      }}
      modalL0Tokens.push(pick);
      updateModalL0Sim();
    }}

    function resetModalL0Sim() {{
      modalL0Tokens = ["the", "server"];
      updateModalL0Sim();
    }}

    const TOKEN_PRESETS = {{
      "strawberry": {{
        pieces: [["str", 496], ["aw", 675], ["berry", 15717]],
        note: "10 chars → 3 tokens (0.30 tok/char). Notice two 'r' letters are locked inside single integer 15717 ('berry')!"
      }},
      "s t r a w b e r r y": {{
        pieces: [["s", 82], [" t", 259], [" r", 436], [" a", 264], [" w", 289], [" b", 293], [" e", 384], [" r", 436], [" r", 436], [" y", 379]],
        note: "Spaced fix: every letter is forced into its own token ID (id=436 appears 3 times), so the model counts 3 'r's with 100% accuracy."
      }},
      "The server responded in 12ms.": {{
        pieces: [["The", 791], [" server", 3585], [" responded", 31574], [" in", 304], [" ", 220], ["12", 717], ["ms", 1294], [".", 13]],
        note: "29 chars → 8 tokens (0.28 tok/char · 1.0x baseline cost & speed)."
      }},
      "नमस्ते दुनिया": {{
        pieces: [["न", 28001], ["म", 44102], ["स", 31902], ["्", 11904], ["त", 29501], ["े", 19822], [" द", 85120], ["ु", 22911], ["न", 28001], ["ि", 18312], ["य", 34112], ["ा", 15209]],
        note: "13 chars → 12 tokens (0.92 tok/char · 3.3x cost & latency multiplier vs English!)."
      }},
      "🚀🔥🤖": {{
        pieces: [["🚀", 9468], ["<0xF0>", 242], ["🔥", 9469], ["<0x9F>", 161], ["🤖", 99812], ["<0x96>", 152]],
        note: "3 chars → 6 tokens (2.00 tok/char · 7.1x cost multiplier due to UTF-8 byte fallback)."
      }}
    }};

    function inspectTokenPreset(key) {{
      const preset = TOKEN_PRESETS[key];
      if (!preset) return;
      const chipsEl = document.getElementById("modal-token-chips");
      const colors = ["#f59e0b", "#38bdf8", "#10b981", "#a855f7", "#f43f5e"];
      chipsEl.innerHTML = preset.pieces.map(([txt, id], i) => {{
        const c = colors[i % colors.length];
        return `<div style="background:var(--bg-card);border:2px solid ${{c}};border-radius:8px;padding:0.35rem 0.7rem;font-family:var(--mono);font-size:0.82rem;">
          <strong>${{txt}}</strong> <span style="color:var(--muted);font-size:0.72rem;">id=${{id}}</span>
        </div>`;
      }}).join("");
      document.getElementById("modal-token-stats").innerText = preset.note;
    }}

    // GATE CHALLENGE CHECKER
    function selectQuizOption(qIdx, oIdx) {{
      const lesson = SEEDED_LESSONS[state.activeLessonId];
      if (!lesson || !lesson.gate_challenge) return;
      const qObj = lesson.gate_challenge[qIdx];
      state.quizAnswers[qIdx] = oIdx;

      qObj.options.forEach((_, i) => {{
        const btn = document.getElementById(`q-${{qIdx}}-opt-${{i}}`);
        btn.classList.remove("selected", "correct", "wrong");
        if (i === oIdx) {{
          btn.classList.add(oIdx === qObj.correct ? "correct" : "wrong");
        }}
      }});

      const fb = document.getElementById(`q-${{qIdx}}-feedback`);
      fb.style.display = "block";
      if (oIdx === qObj.correct) {{
        fb.style.background = "rgba(16, 185, 129, 0.15)";
        fb.style.color = "#10b981";
        fb.innerText = "✓ Correct! " + qObj.explain;
      }} else {{
        fb.style.background = "rgba(244, 63, 94, 0.15)";
        fb.style.color = "#f43f5e";
        fb.innerText = "✗ Not quite — try again. Hint: check the real lab output.";
      }}

      // Check if all 3 are correct
      const allCorrect = lesson.gate_challenge.every((q, idx) => state.quizAnswers[idx] === q.correct);
      const banner = document.getElementById("gate-result-banner");
      if (allCorrect) {{
        clearedRooms.add(lesson.id);
        saveProgress();
        document.getElementById("ws-room-status").innerText = "★ ROOM CLEARED";
        document.getElementById("ws-room-status").className = "tag tag-emerald";
        banner.innerHTML = `
          <div class="share-badge-card" style="margin-top:1rem;">
            <div class="pixel-tag" style="display:inline-block;margin-bottom:0.5rem;">🎉 LEVEL GATE PASSED! NEXT ROOM UNLOCKED!</div>
            <h3 style="margin:0.2rem 0 0.4rem;font-family:var(--serif);">You cleared ${{lesson.title}}!</h3>
            <p style="margin:0 0 0.85rem;font-size:0.9rem;color:#cbd5e1;">
              The laser barrier on the next room door is now open. Grab your shareable X thread or Instagram carousel card before walking to the next room!
            </p>
            <div style="display:flex;gap:0.65rem;flex-wrap:wrap;">
              <button class="btn btn-primary" onclick="switchWsTab('share')">🏆 Open Share Studio Card</button>
              <button class="btn btn-emerald" onclick="closeModalAndWalkNext()">🚶 Walk to Next Room →</button>
            </div>
          </div>
        `;
      }}
    }}

    function closeModalAndWalkNext() {{
      closeRoomModal();
      const nextIdx = (state.activeRoomIdx || 0) + 1;
      const mods = getModulesForLevel(state.buildingLevel);
      if (nextIdx < mods.length) {{
        walkToAndOpenRoom(nextIdx);
      }}
    }}

    function copyFullThread() {{
      const lesson = SEEDED_LESSONS[state.activeLessonId];
      if (!lesson) return;
      navigator.clipboard.writeText((lesson.shareable.x_thread || []).join("\\n\\n"));
      alert("Full X Thread copied to clipboard!");
    }}

    function copyTurnCard() {{
      const lesson = SEEDED_LESSONS[state.activeLessonId];
      if (!lesson) return;
      const txt = `${{lesson.title}} (${{lesson.shareable.notebook_shelf}})\\n\\n"${{lesson.shareable.the_turn}}"\\n\\nhttps://ashwinyardi.github.io/bits-course/`;
      navigator.clipboard.writeText(txt);
      alert("The Turn copied to clipboard!");
    }}

    updateHudAndSidebar();
    requestAnimationFrame(loop);
  </script>
</body>
</html>
"""


def _render_lesson_page(curriculum: dict, lesson: dict, live_ids: set[str], code_text: str) -> str:
    """Render standalone Room Workstation page at lessons/<id>/index.html."""
    lid = lesson["id"]
    spine = lesson["story_spine"]
    sh = lesson["shareable"]
    lab = lesson["lab"]

    figs_by_id = {f["id"]: f for f in lesson.get("figures", [])}
    sections_html = []
    for idx, sec in enumerate(lesson.get("sections", []), 1):
        fig_block = ""
        fid = sec.get("figure_id")
        if fid and fid in figs_by_id:
            fobj = figs_by_id[fid]
            fig_block = (
                f'<div style="background:#fff;color:#1e1e1e;padding:1.15rem;border-radius:12px;margin:1.25rem 0;border:2px solid var(--line);">'
                f'<img src="{_esc(fid)}.svg" alt="{_esc(fobj["title"])}" style="width:100%;height:auto;display:block;" />'
                f'<div style="display:flex;justify-content:space-between;align-items:center;margin-top:0.65rem;padding-top:0.5rem;border-top:1px dashed #cbd5e1;font-size:0.82rem;color:#475569;">'
                f'<span><strong>{_esc(fobj["title"])}:</strong> {_esc(fobj["caption"])}</span>'
                f'<a href="{_esc(fid)}.excalidraw" download style="color:#0284c7;font-family:var(--mono);">⬇ .excalidraw</a>'
                f'</div></div>'
            )
        sections_html.append(
            f'<div style="background:var(--bg-card);border:1px solid var(--line);border-radius:14px;padding:1.5rem;margin-bottom:1.25rem;">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.65rem;">'
            f'<h2 style="margin:0;font-family:var(--serif);font-size:1.35rem;">{idx}. {_esc(sec["heading"])}</h2>'
            f'<span class="tag tag-amber">{_esc(sec.get("badge", ""))}</span>'
            f'</div>'
            f'{_md_to_html(sec["body_md"])}'
            f'{fig_block}'
            f'</div>'
        )

    jargon_rows = "".join(
        f'<tr><td style="padding:0.75rem;border-bottom:1px solid var(--line);"><strong>{_esc(r["term"])}</strong></td>'
        f'<td style="padding:0.75rem;border-bottom:1px solid var(--line);">{_esc(r["plain_words"])}</td>'
        f'<td style="padding:0.75rem;border-bottom:1px solid var(--line);color:var(--muted);">{_esc(r["why_you_care"])}</td></tr>'
        for r in lesson.get("jargon_decoder", [])
    )

    tweets_html = "".join(
        f'<div style="background:var(--bg-card);border:1px solid var(--line);border-radius:10px;padding:1rem;margin-bottom:0.75rem;display:flex;justify-content:space-between;gap:1rem;">'
        f'<div style="white-space:pre-line;">{_esc(t)}</div>'
        f'<button class="btn" onclick="navigator.clipboard.writeText(this.previousElementSibling.innerText);this.innerText=\'Copied!\'">Copy</button>'
        f'</div>'
        for t in sh.get("x_thread", [])
    )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{_esc(lesson["title"])} · Bits University Room Workstation</title>
  <style>{SHARED_CSS}</style>
</head>
<body>
  <header class="hud-bar">
    <a class="hud-brand" href="../../index.html">
      <span class="pixel-tag">← BACK TO 2D CAMPUS</span>
      <span>BitsByBlocks AI University</span>
    </a>
    <div style="display:flex;gap:0.6rem;">
      <a class="btn" href="lesson.json" target="_blank">lesson.json</a>
      <a class="btn btn-primary" href="../../index.html">🎮 Walk Campus & Take Gate Challenge</a>
    </div>
  </header>

  <main style="max-width:920px;margin:0 auto;padding:2rem 1.5rem 5rem;">
    <div style="display:flex;gap:0.5rem;flex-wrap:wrap;margin-bottom:0.75rem;">
      <span class="tag tag-amber">{_esc(sh["notebook_shelf"])}</span>
      <span class="tag tag-cyan">Building {lesson["level"]}: {_esc(lesson["level_name"])}</span>
      <span class="tag tag-emerald">✓ Lab Verified</span>
    </div>
    <h1 style="font-family:var(--serif);font-size:2.4rem;margin:0.2rem 0 0.5rem;">{_esc(lesson["title"])}</h1>
    <div style="font-family:var(--serif);font-style:italic;font-size:1.2rem;color:var(--amber);margin-bottom:1.25rem;">“{_esc(lesson["question"])}”</div>
    <div style="background:var(--bg-card);border-left:4px solid var(--amber);padding:1rem 1.25rem;border-radius:0 10px 10px 0;margin-bottom:2rem;">
      <strong>One-Line Takeaway:</strong> {_esc(lesson["one_line"])}
    </div>

    {"".join(sections_html)}

    <h2 style="font-family:var(--serif);margin-top:2.5rem;">Jargon Decoder</h2>
    <table style="width:100%;border-collapse:collapse;background:var(--bg-card);border:1px solid var(--line);border-radius:10px;overflow:hidden;font-size:0.9rem;">
      <thead><tr style="background:var(--bg-subtle);text-align:left;"><th style="padding:0.75rem;">Term</th><th style="padding:0.75rem;">In Plain Words</th><th style="padding:0.75rem;">Why You Care</th></tr></thead>
      <tbody>{jargon_rows}</tbody>
    </table>

    <h2 style="font-family:var(--serif);margin-top:2.5rem;">Hands-On Lab: {_esc(lab["title"])}</h2>
    <p>{_esc(lab["goal"])}</p>
    <pre style="background:#06080d;padding:1rem;border-radius:10px;border:1px solid var(--line);overflow-x:auto;"><code>{_esc(lab["real_output"])}</code></pre>
    <pre style="background:#06080d;padding:1rem;border-radius:10px;border:1px solid var(--line);overflow-x:auto;margin-top:1rem;"><code>{_esc(code_text)}</code></pre>

    <h2 style="font-family:var(--serif);margin-top:2.5rem;">Share Studio · The Turn & X Thread</h2>
    <div style="background:var(--bg-card);border:2px solid var(--amber);border-radius:12px;padding:1.25rem;margin-bottom:1.25rem;">
      <div style="font-family:var(--mono);font-size:0.72rem;color:var(--amber);">THE NOTEBOOK TURN</div>
      <div style="font-family:var(--serif);font-size:1.25rem;margin:0.35rem 0;">“{_esc(sh["the_turn"])}”</div>
      <div style="font-size:0.85rem;color:var(--muted);"><strong>Reel Hook:</strong> {_esc(sh["reel_hook"])}</div>
    </div>
    {tweets_html}
  </main>
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
    code_by_id: dict[str, str] = {}

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

        code_file = lesson.get("lab", {}).get("code_file", "lab_main.py")
        code_path = ldir / code_file
        code_text = ""
        if code_path.exists():
            shutil.copy2(code_path, out_dir / code_file)
            code_text = code_path.read_text()
        code_by_id[lid] = code_text

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

        (out_dir / "post.md").write_text(_lesson_to_markdown(lesson, fig_files))

    live_ids = set(lessons.keys())
    for lid, lesson in lessons.items():
        out_dir = DIST / "lessons" / lid
        html_str = _render_lesson_page(curriculum, lesson, live_ids, code_by_id.get(lid, ""))
        (out_dir / "index.html").write_text(html_str)

    (DIST / "index.html").write_text(_render_university_index(curriculum, lessons, code_by_id))

    docs = ROOT / "docs"
    if docs.exists():
        shutil.rmtree(docs)
    shutil.copytree(DIST, docs)
    print(f"Built Bits University RPG in {DIST} and {docs} with {len(lessons)} seeded rooms across {len(curriculum['modules'])} total rooms.")


if __name__ == "__main__":
    build_site()
