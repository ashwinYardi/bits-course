"""Build the BitsByBlocks 3D Isometric Sunlit AI University Campus & Interactive Field Guide.

Produces a complete static site in `dist/` and `docs/`:
- `index.html` — Sunlit 3D Isometric University Campus with:
  1. South Entrance Security Gate & Guard Booth (Officer Rajan's Basic Entry Check: `l0-what-is-an-llm` lifts the red/white boom barrier)
  2. West Campus Parking Lot & Token Chopper Kiosk (`l0-tokens`)
  3. Campus Cafeteria & Chai Terrace (`l0-embeddings` — 4D meaning floor map)
  4. Central Quad Lawn & Fountain (`l0-context-window` — 24-word fixed lunch tray & Lost-in-the-Middle U-curve)
  5. 6 3D Isometric Academic Halls (Hall 0 through Hall 5) with walkable interior classrooms for all 36 modules.
- `lessons/<id>/index.html` — Warm paper editorial Chapter Book with Feynman-style 12-year-old-friendly chapters, inline hand-drawn Excalidraw figures, interactive mechanism playground, runnable Python lab, Gate Test, and Share Studio.
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
            "q": "1. Officer Rajan's Entry Check: After the prompt 'the server', the raw scores are crashed=3.2 and responded=2.9. What happens when you turn the Temperature dial down from 1.0 to 0.2?",
            "options": [
                "The model rewrites its hard drive so it remembers 'crashed' forever.",
                "Softmax sharpens the gap: 'crashed' jumps from 44.2% to 80.6% chance on the weighted die.",
                "The chance splits 50/50 between 'crashed' and 'responded'."
            ],
            "correct": 1,
            "explain": "Dividing scores by a small temperature (0.2) stretches the gap between the top score and runner-up before turning them into percentages."
        },
        {
            "q": "2. Why did rolling the relay game 5 times at Temperature 0.0 give 1 identical sentence, while Temperature 1.0 gave 5 completely different stories?",
            "options": [
                "At Temp 1.0, as soon as one different word is picked and glued onto the prompt, it changes the input for every word after it.",
                "Temperature 1.0 shuffles the user's prompt words into random order.",
                "The model connects to Google Search whenever Temperature is above 0."
            ],
            "correct": 0,
            "explain": "Every word the model picks gets taped onto the end of the prompt — so one different roll on word #3 branches the entire rest of the sentence!"
        },
        {
            "q": "3. The Snowball Trap: Why should you never ask an AI to 'Answer YES or NO on line 1, then explain why on line 2'?",
            "options": [
                "Because capital letters cost twice as much money.",
                "Because the AI has no backspace key: once it blurts out 'YES' on word 1, 'YES' is glued onto its prompt and it is forced to invent an excuse for it.",
                "Because the scoreboard cannot score two-letter words."
            ],
            "correct": 1,
            "explain": "Always ask the AI to think step-by-step FIRST and write the final YES/NO verdict on the very last line."
        }
    ],
    "l0-tokens": [
        {
            "q": "1. Parking Lot Barcode Check: Why does a giant AI struggle to count the three 'r's in 'strawberry'?",
            "options": [
                "The Token Chopper glues common letter chunks into single barcode numbers: [496, 675, 15717] ('str', 'aw', 'berry'), hiding two 'r's inside barcode 15717.",
                "The letter 'r' is deleted by the keyboard before sending.",
                "Computers cannot count past the number 2."
            ],
            "correct": 0,
            "explain": "The AI never sees the letters 'b-e-r-r-y' — it only sees the single sealed number 15717. Adding spaces ('s t r a w b e r r y') forces every letter into its own barcode!"
        },
        {
            "q": "2. In our Parking Lot lab, how many token barcodes did Hindi ('नमस्ते दुनिया') need per character compared to English?",
            "options": [
                "Hindi used half as many tokens as English.",
                "Hindi and English had the exact same 0.28 tokens/char ratio.",
                "Hindi needed 0.92 tokens/char vs English 0.28 tokens/char — a 3.3x price and speed penalty!"
            ],
            "correct": 2,
            "explain": "Because the BPE Lego-gluing game practiced mostly on English text, Hindi words get chopped into tiny byte crumbs."
        },
        {
            "q": "3. How does the Byte-Pair Encoding (BPE) Lego game invent its 100,000-piece vocabulary?",
            "options": [
                "Grammar teachers type in a dictionary of prefixes and suffixes by hand.",
                "It starts with 256 raw byte blocks and repeatedly glues the most common side-by-side pair into a brand-new block.",
                "It picks 100,000 random words from a rhyming dictionary."
            ],
            "correct": 1,
            "explain": "In our 30-line Python lab, just 8 rounds of gluing the most frequent neighbor pair shrunk 39 raw blocks down to 11 chunks!"
        }
    ],
    "l0-embeddings": [
        {
            "q": "1. Campus Cafeteria Check: Why doesn't an AI get confused even though Token #40,000 ('coffee') is numerically right next to Token #40,001 ('coffin')?",
            "options": [
                "Because the AI sorts words alphabetically before reading.",
                "Because a Token ID is just a coat-check ticket; the AI immediately trades it for an Embedding — a list of GPS coordinates on the Meaning Map.",
                "Because 'coffin' is deleted from the dictionary."
            ],
            "correct": 1,
            "explain": "Barcode numbers have zero meaning. The embedding table turns each barcode into coordinates (like Hot Drink, Spicy, Tech, Royal) where similar ideas sit at the same cafeteria table."
        },
        {
            "q": "2. In our Cafeteria GPS lab, what was the Cosine Similarity (flashlight angle score) between masala_chai and filter_coffee vs masala_chai and kubernetes?",
            "options": [
                "masala_chai & filter_coffee scored +0.9924 (almost identical direction), while masala_chai & kubernetes scored +0.1006 (unrelated).",
                "Both pairs scored 0.5000.",
                "masala_chai & kubernetes scored +0.9924 because developers drink chai while coding."
            ],
            "correct": 0,
            "explain": "Cosine similarity measures the angle between two coordinate arrows: +1.0 means pointing the exact same way in meaning space."
        },
        {
            "q": "3. When we ran vector arithmetic `king - man + woman` on our 4D Cafeteria map, which word landed at the closest table (and what is the honest trap with cosine similarity)?",
            "options": [
                "It landed on 'queen' (0.9854), and the trap is that opposites like 'boiling chai' and 'iced chai' ALSO sit close together because they share the same topic table!",
                "It landed on 'kubernetes', and cosine similarity never makes mistakes.",
                "You cannot add or subtract word coordinates."
            ],
            "correct": 0,
            "explain": "Subtracting 'man' and adding 'woman' walks across the gender axis to 'queen' (0.9854), while hot and cold drinks still cluster together because they share the drink context."
        }
    ],
    "l0-context-window": [
        {
            "q": "1. Quad Lunch Tray Check: Why does the AI act like it 'remembers' your name on Turn 2 of a chat even though its brain resets to zero after every single response?",
            "options": [
                "It secretly writes your name onto its GPU hard drive.",
                "The chat app silently re-pastes your ENTIRE conversation from Turn 1 onto the tray and sends the whole script back to the AI every turn.",
                "It recognizes your typing speed."
            ],
            "correct": 1,
            "explain": "An LLM is an Amnesia Chef: it has zero memory between turns unless the app re-sends the whole transcript on the lunch tray."
        },
        {
            "q": "2. In our 24-word Lunch Tray lab, why did the AI forget the secret locker code `7492` by Turn 4?",
            "options": [
                "Because the tray only holds 24 words: when the conversation hit 34 words, the oldest 10 words at the left edge slid off into the trash.",
                "Because 7492 is an even number.",
                "Because the user asked nicely to delete it."
            ],
            "correct": 0,
            "explain": "Once old words exceed the context window limit and fall off the left edge of the tray, the model literally never receives them."
        },
        {
            "q": "3. According to the 'Lost in the Middle' U-curve we proved in the lab, where should you place your most important rules and facts on a giant prompt tray?",
            "options": [
                "Buried right in the middle (Chunk 5 or 6 out of 10), where recall was 38.7%.",
                "At the very beginning (Chunk 1) or the very end (Chunk 10), where attention recall was 93.0%!",
                "It doesn't matter; every spot on a 100,000-token tray gets equal attention."
            ],
            "correct": 1,
            "explain": "Attention follows a U-shaped curve: 93.0% recall at the start and end vs 38.7% in the soggy middle. Always put key facts and instructions at the top or bottom!"
        }
    ]
}


SHARED_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,600;0,9..144,700;0,9..144,800;1,9..144,400&family=JetBrains+Mono:wght@400;600;700;800&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

:root {
  --paper: #fbf8f1;
  --paper-card: #ffffff;
  --paper-warm: #f3ece0;
  --paper-deep: #e8decb;
  --ink: #1c1917;
  --ink-soft: #44403c;
  --muted: #78716c;
  --line: #d6cbb9;
  --line-strong: #b8a992;
  --terracotta: #d94e1f;
  --terracotta-soft: #fde8df;
  --amber: #d97706;
  --amber-soft: #fef3c7;
  --meadow: #15803d;
  --meadow-soft: #dcfce7;
  --sky: #0369a1;
  --sky-soft: #e0f2fe;
  --berry: #7e22ce;
  --berry-soft: #f3e8ff;
  --sans: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
  --serif: 'Fraunces', Georgia, serif;
  --mono: 'JetBrains Mono', monospace;
}

* { box-sizing: border-box; }

body {
  margin: 0;
  background: var(--paper);
  color: var(--ink);
  font-family: var(--sans);
  line-height: 1.65;
  overflow-x: hidden;
}

a { color: var(--terracotta); text-decoration: none; font-weight: 600; }
a:hover { text-decoration: underline; }

.top-nav {
  position: sticky;
  top: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.65rem 1.4rem;
  background: rgba(251, 248, 241, 0.94);
  backdrop-filter: blur(10px);
  border-bottom: 2px solid var(--line);
  gap: 1rem;
  flex-wrap: wrap;
}

.brand-cluster {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.crest-badge {
  background: var(--terracotta);
  color: #fff;
  font-family: var(--serif);
  font-weight: 800;
  font-size: 0.85rem;
  padding: 0.32rem 0.75rem;
  border-radius: 8px;
  border: 2px solid #9a3412;
  box-shadow: 0 2px 0 #9a3412;
  letter-spacing: 0.01em;
}

.brand-title {
  font-family: var(--serif);
  font-weight: 800;
  font-size: 1.15rem;
  color: var(--ink);
}

.brand-sub {
  font-size: 0.78rem;
  color: var(--muted);
  font-weight: 500;
}

.nav-pills {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  flex-wrap: wrap;
}

.stat-chip {
  background: var(--paper-card);
  border: 2px solid var(--line);
  padding: 0.28rem 0.75rem;
  border-radius: 999px;
  font-family: var(--mono);
  font-size: 0.76rem;
  font-weight: 700;
  color: var(--ink-soft);
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  box-shadow: 0 2px 0 rgba(0,0,0,0.04);
}

.btn {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  background: var(--paper-card);
  color: var(--ink);
  border: 2px solid var(--line-strong);
  padding: 0.45rem 0.95rem;
  border-radius: 10px;
  font-size: 0.83rem;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.14s ease;
  font-family: var(--sans);
  box-shadow: 0 2px 0 var(--line-strong);
}

.btn:hover {
  transform: translateY(-1px);
  border-color: var(--ink);
  text-decoration: none;
}

.btn-primary {
  background: var(--terracotta);
  color: #ffffff;
  border-color: #9a3412;
  box-shadow: 0 3px 0 #9a3412;
}

.btn-primary:hover {
  background: #ea580c;
  color: #ffffff;
}

.btn-meadow {
  background: var(--meadow);
  color: #ffffff;
  border-color: #14532d;
  box-shadow: 0 3px 0 #14532d;
}

.btn-meadow:hover {
  background: #16a34a;
  color: #ffffff;
}

.tag {
  font-family: var(--mono);
  font-size: 0.72rem;
  font-weight: 700;
  padding: 0.2rem 0.65rem;
  border-radius: 999px;
  background: var(--paper-warm);
  border: 1.5px solid var(--line);
  color: var(--ink-soft);
}

.tag-terracotta { background: var(--terracotta-soft); color: var(--terracotta); border-color: #fDBA74; }
.tag-meadow { background: var(--meadow-soft); color: var(--meadow); border-color: #86efac; }
.tag-sky { background: var(--sky-soft); color: var(--sky); border-color: #7dd3fc; }
.tag-amber { background: var(--amber-soft); color: #b45309; border-color: #fcd34d; }
"""


def _render_university_index(curriculum: dict, lessons: dict[str, dict], code_by_id: dict[str, str]) -> str:
    """Render the Sunlit 3D Isometric AI University Campus & Interactive Field Guide."""
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
  <title>BitsByBlocks AI University · 3D Isometric Campus & Field Guide</title>
  <style>
    {SHARED_CSS}
    .campus-layout {{
      display: grid;
      grid-template-columns: 1fr 390px;
      height: calc(100vh - 60px);
      overflow: hidden;
    }}
    @media (max-width: 1100px) {{
      .campus-layout {{
        grid-template-columns: 1fr;
        height: auto;
        overflow: visible;
      }}
    }}
    .map-stage {{
      position: relative;
      background: linear-gradient(180deg, #bae6fd 0%, #e0f2fe 24%, #d9f99d 24%, #84cc16 100%);
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 0.75rem;
      overflow: hidden;
      user-select: none;
    }}
    #campus-canvas {{
      width: 100%;
      max-width: 1120px;
      aspect-ratio: 16 / 10;
      border-radius: 18px;
      border: 4px solid #fff;
      box-shadow: 0 22px 50px rgba(28, 25, 23, 0.22), 0 0 0 2px var(--line-strong);
      cursor: pointer;
      background: #84cc16;
    }}
    .map-hud-top {{
      position: absolute;
      top: 1.25rem;
      left: 1.5rem;
      right: 1.5rem;
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      pointer-events: none;
      gap: 0.75rem;
      flex-wrap: wrap;
    }}
    .map-hud-top > * {{
      pointer-events: auto;
    }}
    .place-placard {{
      background: rgba(255, 253, 248, 0.96);
      border: 2.5px solid var(--ink);
      padding: 0.55rem 1rem;
      border-radius: 14px;
      box-shadow: 0 6px 0 var(--ink);
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }}
    .place-icon {{
      font-size: 1.45rem;
    }}
    .place-title {{
      font-family: var(--serif);
      font-weight: 800;
      font-size: 1rem;
      color: var(--ink);
      line-height: 1.15;
    }}
    .place-sub {{
      font-size: 0.76rem;
      color: var(--muted);
      font-weight: 600;
    }}
    .map-controls-bar {{
      position: absolute;
      bottom: 1.25rem;
      left: 50%;
      transform: translateX(-50%);
      background: rgba(255, 253, 248, 0.96);
      border: 2px solid var(--ink);
      box-shadow: 0 4px 0 var(--ink);
      padding: 0.45rem 1.1rem;
      border-radius: 999px;
      font-size: 0.79rem;
      font-weight: 700;
      color: var(--ink);
      display: flex;
      align-items: center;
      gap: 1rem;
      white-space: nowrap;
    }}
    .kbd {{
      background: var(--paper-warm);
      border: 1.5px solid var(--ink);
      box-shadow: 0 2px 0 var(--ink);
      border-radius: 5px;
      padding: 0.1rem 0.42rem;
      font-family: var(--mono);
      font-size: 0.72rem;
    }}
    .guide-sidebar {{
      background: var(--paper);
      border-left: 2px solid var(--line);
      display: flex;
      flex-direction: column;
      height: 100%;
      overflow-y: auto;
      padding: 1.15rem;
    }}
    .npc-dialogue-box {{
      background: #fffdf9;
      border: 2.5px solid var(--ink);
      box-shadow: 0 5px 0 var(--ink);
      border-radius: 14px;
      padding: 0.95rem 1rem;
      margin-bottom: 1.1rem;
      position: relative;
    }}
    .npc-header {{
      display: flex;
      align-items: center;
      gap: 0.6rem;
      margin-bottom: 0.4rem;
    }}
    .npc-avatar-badge {{
      width: 36px;
      height: 36px;
      border-radius: 10px;
      background: var(--amber-soft);
      border: 2px solid var(--ink);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 1.2rem;
      flex-shrink: 0;
    }}
    .npc-name {{
      font-family: var(--serif);
      font-weight: 800;
      font-size: 0.95rem;
    }}
    .npc-role {{
      font-family: var(--mono);
      font-size: 0.68rem;
      color: var(--terracotta);
      font-weight: 700;
    }}
    .checkpoint-list {{
      display: flex;
      flex-direction: column;
      gap: 0.65rem;
    }}
    .checkpoint-card {{
      background: var(--paper-card);
      border: 2px solid var(--line-strong);
      border-radius: 12px;
      padding: 0.8rem 0.95rem;
      cursor: pointer;
      transition: all 0.15s ease;
      position: relative;
    }}
    .checkpoint-card:hover {{
      border-color: var(--ink);
      transform: translateY(-2px);
      box-shadow: 0 4px 0 var(--line-strong);
    }}
    .checkpoint-card.active-stop {{
      border: 2.5px solid var(--terracotta);
      background: #fffaf5;
      box-shadow: 0 4px 0 var(--terracotta);
    }}
    .checkpoint-card.cleared-stop {{
      border-color: var(--meadow);
      background: #f7fee7;
    }}
    /* Editorial Chapter Book Modal */
    .book-modal {{
      position: fixed;
      inset: 0;
      z-index: 250;
      background: rgba(28, 25, 23, 0.62);
      backdrop-filter: blur(6px);
      display: none;
      align-items: center;
      justify-content: center;
      padding: 1.25rem;
    }}
    .book-modal.open {{
      display: flex;
    }}
    .book-sheet {{
      background: var(--paper);
      border: 3px solid var(--ink);
      box-shadow: 0 14px 0 var(--ink), 0 30px 70px rgba(0,0,0,0.4);
      border-radius: 20px;
      width: 100%;
      max-width: 1080px;
      height: 90vh;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }}
    .book-header {{
      background: var(--paper-warm);
      padding: 0.9rem 1.5rem;
      border-bottom: 2px solid var(--line-strong);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 1rem;
      flex-wrap: wrap;
    }}
    .book-tabs {{
      display: flex;
      gap: 0.45rem;
      padding: 0.6rem 1.5rem;
      background: #f7f2e7;
      border-bottom: 2px solid var(--line);
      overflow-x: auto;
    }}
    .book-tab {{
      background: transparent;
      border: 2px solid transparent;
      color: var(--ink-soft);
      font-family: var(--sans);
      font-size: 0.84rem;
      font-weight: 700;
      padding: 0.42rem 0.95rem;
      border-radius: 10px;
      cursor: pointer;
    }}
    .book-tab.active {{
      background: var(--paper-card);
      color: var(--terracotta);
      border-color: var(--ink);
      box-shadow: 0 2px 0 var(--ink);
    }}
    .book-body {{
      flex: 1;
      overflow-y: auto;
      padding: 1.75rem 2.25rem 3rem;
    }}
    .book-pane {{
      display: none;
      max-width: 820px;
      margin: 0 auto;
    }}
    .book-pane.active {{
      display: block;
    }}
    .chapter-card {{
      background: var(--paper-card);
      border: 2px solid var(--line-strong);
      border-radius: 16px;
      padding: 1.5rem 1.75rem;
      margin-bottom: 1.5rem;
      box-shadow: 0 4px 0 rgba(28, 25, 23, 0.06);
    }}
    .chapter-number {{
      font-family: var(--mono);
      font-size: 0.74rem;
      font-weight: 800;
      color: var(--terracotta);
      text-transform: uppercase;
      letter-spacing: 0.06em;
    }}
    .chapter-heading {{
      font-family: var(--serif);
      font-size: 1.45rem;
      font-weight: 800;
      margin: 0.25rem 0 0.85rem;
      color: var(--ink);
    }}
    .chapter-prose {{
      font-size: 1.03rem;
      color: var(--ink-soft);
      line-height: 1.75;
    }}
    .chapter-prose p {{
      margin: 0 0 0.9rem;
    }}
    .chapter-prose code {{
      background: var(--paper-warm);
      padding: 0.15rem 0.4rem;
      border-radius: 5px;
      font-family: var(--mono);
      font-size: 0.88em;
      color: #9a3412;
      border: 1px solid var(--line);
    }}
    .inline-figure {{
      background: #ffffff;
      border: 2.5px solid var(--ink);
      box-shadow: 0 6px 0 var(--line-strong);
      border-radius: 14px;
      padding: 1.1rem;
      margin: 1.35rem 0 0.4rem;
    }}
    .playground-box {{
      background: #fffbeb;
      border: 2.5px solid var(--ink);
      box-shadow: 0 6px 0 var(--ink);
      border-radius: 16px;
      padding: 1.35rem 1.5rem;
      margin-bottom: 1.75rem;
    }}
    .spine-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 0.85rem;
      margin: 1rem 0 1.5rem;
    }}
    .spine-card {{
      background: var(--paper-card);
      border: 2px solid var(--line-strong);
      border-radius: 12px;
      padding: 0.9rem 1rem;
    }}
    .spine-label {{
      font-family: var(--mono);
      font-size: 0.7rem;
      font-weight: 800;
      text-transform: uppercase;
      color: var(--terracotta);
      letter-spacing: 0.05em;
      margin-bottom: 0.25rem;
    }}
    .quiz-option {{
      display: block;
      width: 100%;
      text-align: left;
      background: var(--paper-card);
      border: 2px solid var(--line-strong);
      color: var(--ink);
      padding: 0.8rem 1rem;
      border-radius: 10px;
      margin-bottom: 0.55rem;
      cursor: pointer;
      font-family: var(--sans);
      font-size: 0.92rem;
      font-weight: 600;
      transition: all 0.12s;
    }}
    .quiz-option:hover {{
      border-color: var(--ink);
      background: var(--paper-warm);
    }}
    .quiz-option.correct {{
      border-color: var(--meadow);
      background: var(--meadow-soft);
      color: #14532d;
    }}
    .quiz-option.wrong {{
      border-color: #dc2626;
      background: #fee2e2;
      color: #7f1d1d;
    }}
    pre {{
      background: #1c1917;
      color: #f5f5f4;
      padding: 1.1rem 1.25rem;
      border-radius: 12px;
      border: 2px solid var(--ink);
      overflow-x: auto;
      font-family: var(--mono);
      font-size: 0.82rem;
      line-height: 1.55;
    }}
    .ig-deck {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
      gap: 1rem;
      margin-top: 1rem;
    }}
    .ig-slide {{
      aspect-ratio: 4 / 5;
      background: linear-gradient(155deg, #fffbeb 0%, #fde8df 100%);
      border: 2.5px solid var(--ink);
      box-shadow: 0 5px 0 var(--ink);
      border-radius: 14px;
      padding: 1.1rem;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }}
  </style>
</head>
<body>
  <header class="top-nav">
    <div class="brand-cluster">
      <span class="crest-badge">BITS UNIVERSITY</span>
      <div>
        <div class="brand-title">BitsByBlocks 3D AI Campus</div>
        <div class="brand-sub">Walk the Campus · Clear the Guard Gate · Run Real Labs</div>
      </div>
    </div>
    <div class="nav-pills">
      <div class="stat-chip">
        <span>🚧 Security Gate:</span>
        <strong id="hud-gate-state" style="color:var(--terracotta);">CLOSED</strong>
      </div>
      <div class="stat-chip">
        <span>⭐ Checkpoints Cleared:</span>
        <strong id="hud-cleared-count">0 / 36</strong>
      </div>
      <button class="btn" onclick="switchScene('campus')">🌳 3D Campus Map</button>
      <button class="btn btn-primary" onclick="openActiveCheckpoint()">📖 Open Current Chapter & Test</button>
    </div>
  </header>

  <div class="campus-layout">
    <!-- LEFT: 3D ISOMETRIC CAMPUS & HALL FLOORPLAN CANVAS -->
    <div class="map-stage">
      <div class="map-hud-top">
        <div class="place-placard">
          <div class="place-icon" id="placard-icon">🚧</div>
          <div>
            <div class="place-title" id="placard-title">South Security Gate & Guard Booth</div>
            <div class="place-sub" id="placard-sub">Pass Officer Rajan's 3-question entry test to lift the boom barrier!</div>
          </div>
        </div>
        <div style="display:flex;gap:0.5rem;flex-wrap:wrap;">
          <button class="btn" id="btn-back-campus" style="display:none;" onclick="switchScene('campus')">← Exit Hall to 3D Campus</button>
          <button class="btn btn-meadow" onclick="walkToNextTarget()">🚶 Walk to Next Stop →</button>
        </div>
      </div>

      <canvas id="campus-canvas" width="1120" height="700"></canvas>

      <div class="map-controls-bar">
        <span><span class="kbd">Click</span> any 3D Landmark or <span class="kbd">W</span><span class="kbd">A</span><span class="kbd">S</span><span class="kbd">D</span> / <span class="kbd">Arrows</span> to walk</span>
        <span>·</span>
        <span>Press <span class="kbd">E</span> or <span class="kbd">Enter</span> to talk & open Chapter Book</span>
      </div>
    </div>

    <!-- RIGHT: CAMPUS FIELD GUIDE & CHECKPOINT LIST -->
    <aside class="guide-sidebar">
      <div class="npc-dialogue-box" id="npc-box">
        <div class="npc-header">
          <div class="npc-avatar-badge" id="npc-icon">👮🏽‍♂️</div>
          <div>
            <div class="npc-name" id="npc-name">Officer Rajan · Chief of Campus Security</div>
            <div class="npc-role" id="npc-role">SOUTH ENTRANCE BOOM GATE</div>
          </div>
        </div>
        <div style="font-size:0.86rem;color:var(--ink-soft);" id="npc-speech">
          “Hold up, Ashwin! Nobody drives onto the Bits University quad thinking an AI is a tiny brain in a jar. Read Chapter 1 and pass my 3-question Basic Check to lift this red-and-white boom barrier!”
        </div>
        <div style="margin-top:0.75rem;display:flex;gap:0.5rem;flex-wrap:wrap;">
          <button class="btn btn-primary" style="width:100%;justify-content:center;" id="npc-cta-btn" onclick="openActiveCheckpoint()">
            📖 Open Chapter 1 & Take Gate Test
          </button>
        </div>
      </div>

      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.55rem;">
        <span style="font-family:var(--mono);font-size:0.73rem;font-weight:800;color:var(--muted);text-transform:uppercase;" id="sidebar-list-heading">
          CAMPUS LANDMARKS & ACADEMIC HALLS
        </span>
        <span class="tag tag-amber" id="sidebar-progress-pill">4 Live Labs Ready</span>
      </div>

      <div class="checkpoint-list" id="checkpoint-list"></div>
    </aside>
  </div>

  <!-- CHAPTER BOOK & GATE TEST MODAL -->
  <div class="book-modal" id="book-modal">
    <div class="book-sheet">
      <div class="book-header">
        <div>
          <div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.2rem;">
            <span class="tag tag-terracotta" id="bk-location-tag">CHECKPOINT 01 · SECURITY GATE</span>
            <span class="tag tag-meadow" id="bk-status-tag">🟢 UNLOCKED</span>
          </div>
          <h2 id="bk-title" style="margin:0;font-family:var(--serif);font-size:1.5rem;">What an LLM Actually Does</h2>
        </div>
        <div style="display:flex;gap:0.55rem;align-items:center;">
          <a id="bk-standalone-link" class="btn" href="#" target="_blank">↗ Full Page View</a>
          <button class="btn" onclick="closeBookModal()">✕ Back to Campus (Esc)</button>
        </div>
      </div>

      <div class="book-tabs">
        <button class="book-tab active" data-tab="story" onclick="switchBookTab('story')">1. Illustrated Story & Playground</button>
        <button class="book-tab" data-tab="lab" onclick="switchBookTab('lab')">2. Runnable Python Lab (Verified)</button>
        <button class="book-tab" data-tab="gate" onclick="switchBookTab('gate')">3. Checkpoint Gate Test (Unlock Next)</button>
        <button class="book-tab" data-tab="share" onclick="switchBookTab('share')">4. Share Studio (X & IG)</button>
      </div>

      <div class="book-body">
        <div class="book-pane active" id="bk-pane-story"></div>
        <div class="book-pane" id="bk-pane-lab"></div>
        <div class="book-pane" id="bk-pane-gate"></div>
        <div class="book-pane" id="bk-pane-share"></div>
      </div>
    </div>
  </div>

  <script>
    const CURRICULUM = {curriculum_json};
    const SEEDED_LESSONS = {lessons_json};

    const STORAGE_KEY = "bits_uni_cleared_v3";
    let clearedIds = new Set(JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]"));

    function saveProgress() {{
      localStorage.setItem(STORAGE_KEY, JSON.stringify([...clearedIds]));
      refreshHudAndSidebar();
    }}

    function isGateOpen() {{
      return clearedIds.has("l0-what-is-an-llm");
    }}

    // 4 Outdoor Campus Checkpoints for the 4 live Rung-0 lessons + 6 3D Academic Halls
    const OUTDOOR_LANDMARKS = [
      {{
        id: "l0-what-is-an-llm",
        kind: "checkpoint",
        num: "STOP 01",
        name: "Entrance Security Gate",
        landmark: "Guard Booth & Boom Barrier",
        icon: "🚧",
        npcName: "Officer Rajan · Campus Security Chief",
        npcIcon: "👮🏽‍♂️",
        npcSpeech: "“Stop right at the red-and-white barrier! Before I let you onto campus, prove you know how the world's fastest one-word relay game works — and why Temperature changes the dice roll.”",
        x: 520, y: 585, radius: 68
      }},
      {{
        id: "l0-tokens",
        kind: "checkpoint",
        num: "STOP 02",
        name: "Campus Parking Lot",
        landmark: "West Lot & Barcode Chopper Kiosk",
        icon: "🅿️",
        npcName: "Maya · Parking & Barcode Engineer",
        npcIcon: "👷🏽‍♀️",
        npcSpeech: "“Welcome inside the gate! Look at how cars park in numbered bays. An AI chops every sentence into numbered Lego barcodes the exact same way — which is why 'strawberry' hides its r's and Hindi costs 3.3x more!”",
        x: 205, y: 455, radius: 75
      }},
      {{
        id: "l0-embeddings",
        kind: "checkpoint",
        num: "STOP 03",
        name: "Campus Cafeteria & Chai Terrace",
        landmark: "Umbrella Patio & 4D Meaning Map",
        icon: "☕",
        npcName: "Chef Kabir · Chai Terrace Host",
        npcIcon: "🧑🏽‍🍳",
        npcSpeech: "“Grab a masala chai! Notice how masala chai and filter coffee sit at the same table, while Kubernetes sits across the room? That's Embeddings: turning dull barcode numbers into GPS coordinates on a Meaning Map.”",
        x: 345, y: 295, radius: 75
      }},
      {{
        id: "l0-context-window",
        kind: "checkpoint",
        num: "STOP 04",
        name: "Central Quad & Fountain",
        landmark: "Great Lawn & Fixed Lunch Tray",
        icon: "⛲",
        npcName: "Prof. Meera · Quad Bench Mentor",
        npcIcon: "👩🏽‍🏫",
        npcSpeech: "“Sit by the fountain! Every AI is an Amnesia Chef with a fixed-size 24-word lunch tray. When new words squeeze on, old facts fall off the left edge — and anything buried in the middle gets ignored!”",
        x: 545, y: 345, radius: 75
      }}
    ];

    const ACADEMIC_HALLS = [
      {{ level: 0, code: "HALL 0", name: "Foundations Hall", sub: "Intuition, Eval & First Call", x: 760, y: 470, w: 120, d: 70, h: 52, roof: "#d94e1f", wallL: "#fff7ed", wallR: "#fed7aa" }},
      {{ level: 1, code: "HALL 1", name: "Prompt & Retrieval Hall", sub: "RAG, Vectors & Chunking", x: 935, y: 470, w: 120, d: 70, h: 52, roof: "#0284c7", wallL: "#f0f9ff", wallR: "#bae6fd" }},
      {{ level: 2, code: "HALL 2", name: "Attention Conservatory", sub: "Transformers & KV Cache", x: 760, y: 280, w: 120, d: 70, h: 56, roof: "#15803d", wallL: "#f0fdf4", wallR: "#bbf7d0" }},
      {{ level: 3, code: "HALL 3", name: "Agent Robotics Wing", sub: "Tool Loops, MCP & Memory", x: 935, y: 280, w: 120, d: 70, h: 56, roof: "#7e22ce", wallL: "#faf5ff", wallR: "#e9d5ff" }},
      {{ level: 4, code: "HALL 4", name: "Fine-Tuning Foundry", sub: "LoRA, DPO & GRPO", x: 645, y: 125, w: 130, d: 72, h: 60, roof: "#b45309", wallL: "#fffbeb", wallR: "#fde68a" }},
      {{ level: 5, code: "HALL 5", name: "Frontier Observatory", sub: "MoE, Speculative & Prod", x: 885, y: 125, w: 135, d: 72, h: 64, roof: "#be123c", wallL: "#fff1f2", wallR: "#fecdd3" }}
    ];

    const HALL_ROOMS = [
      {{ idx: 0, x: 75,  y: 75,  w: 220, h: 175, doorX: 185, doorY: 250 }},
      {{ idx: 1, x: 325, y: 75,  w: 220, h: 175, doorX: 435, doorY: 250 }},
      {{ idx: 2, x: 575, y: 75,  w: 220, h: 175, doorX: 685, doorY: 250 }},
      {{ idx: 3, x: 825, y: 75,  w: 220, h: 175, doorX: 935, doorY: 250 }},
      {{ idx: 4, x: 75,  y: 425, w: 220, h: 175, doorX: 185, doorY: 425 }},
      {{ idx: 5, x: 325, y: 425, w: 220, h: 175, doorX: 435, doorY: 425 }},
      {{ idx: 6, x: 575, y: 425, w: 220, h: 175, doorX: 685, doorY: 425 }},
      {{ idx: 7, x: 825, y: 425, w: 220, h: 175, doorX: 935, doorY: 425 }}
    ];

    const state = {{
      scene: "campus", // "campus" | "hall"
      hallLevel: 0,
      activeStopId: "l0-what-is-an-llm",
      player: {{
        x: 520,
        y: 648,
        targetX: null,
        targetY: null,
        speed: 4.5,
        frame: 0,
        pendingAction: null
      }},
      hallPlayer: {{
        x: 185,
        y: 335,
        targetX: null,
        targetY: null,
        frame: 0,
        pendingRoomIdx: null
      }},
      keys: {{}},
      quizAnswers: {{}},
      tick: 0
    }};

    function getModulesForLevel(lvl) {{
      return CURRICULUM.modules.filter(m => m.level === lvl);
    }}

    function isModuleUnlocked(modId) {{
      if (modId === "l0-what-is-an-llm") return true;
      if (!isGateOpen()) return false;
      const allMods = CURRICULUM.modules;
      const idx = allMods.findIndex(m => m.id === modId);
      if (idx <= 0) return true;
      return clearedIds.has(allMods[idx - 1].id);
    }}

    function switchScene(sceneName, hallLvl) {{
      state.scene = sceneName;
      if (typeof hallLvl === "number") {{
        state.hallLevel = hallLvl;
        state.hallPlayer.x = 185;
        state.hallPlayer.y = 335;
        state.hallPlayer.targetX = null;
        state.hallPlayer.targetY = null;
      }}
      document.getElementById("btn-back-campus").style.display = sceneName === "hall" ? "inline-flex" : "none";
      refreshHudAndSidebar();
    }}

    function selectOutdoorStop(stopId, openImmediately = true) {{
      const stop = OUTDOOR_LANDMARKS.find(s => s.id === stopId);
      if (!stop) return;
      if (stopId !== "l0-what-is-an-llm" && !isGateOpen()) {{
        // Walk up to the closed boom barrier and prompt Officer Rajan
        state.activeStopId = "l0-what-is-an-llm";
        state.player.targetX = 520;
        state.player.targetY = 615;
        state.player.pendingAction = () => openLessonBook("l0-what-is-an-llm");
        refreshHudAndSidebar();
        return;
      }}
      state.scene = "campus";
      state.activeStopId = stopId;
      state.player.targetX = stop.x;
      state.player.targetY = stop.y + 18;
      state.player.pendingAction = openImmediately ? () => openLessonBook(stopId) : null;
      refreshHudAndSidebar();
    }}

    function walkToNextTarget() {{
      if (!isGateOpen()) {{
        selectOutdoorStop("l0-what-is-an-llm", true);
        return;
      }}
      for (const s of OUTDOOR_LANDMARKS) {{
        if (!clearedIds.has(s.id)) {{
          selectOutdoorStop(s.id, true);
          return;
        }}
      }}
      switchScene("hall", 0);
    }}

    function openActiveCheckpoint() {{
      openLessonBook(state.activeStopId || "l0-what-is-an-llm");
    }}

    function refreshHudAndSidebar() {{
      const gateEl = document.getElementById("hud-gate-state");
      if (isGateOpen()) {{
        gateEl.innerText = "OPEN (BOOM LIFTED)";
        gateEl.style.color = "var(--meadow)";
      }} else {{
        gateEl.innerText = "LOCKED (PASS GUARD CHECK)";
        gateEl.style.color = "var(--terracotta)";
      }}
      document.getElementById("hud-cleared-count").innerText = `${{clearedIds.size}} / ${{CURRICULUM.modules.length}}`;

      const activeOutdoor = OUTDOOR_LANDMARKS.find(s => s.id === state.activeStopId) || OUTDOOR_LANDMARKS[0];
      if (state.scene === "campus") {{
        document.getElementById("placard-icon").innerText = activeOutdoor.icon;
        document.getElementById("placard-title").innerText = `${{activeOutdoor.name}} · ${{activeOutdoor.landmark}}`;
        document.getElementById("placard-sub").innerText = activeOutdoor.npcName;

        document.getElementById("npc-icon").innerText = activeOutdoor.npcIcon;
        document.getElementById("npc-name").innerText = activeOutdoor.npcName;
        document.getElementById("npc-role").innerText = `${{activeOutdoor.num}} · ${{activeOutdoor.name.toUpperCase()}}`;
        document.getElementById("npc-speech").innerText = activeOutdoor.npcSpeech;
        const mod = CURRICULUM.modules.find(m => m.id === activeOutdoor.id);
        document.getElementById("npc-cta-btn").innerText = `📖 Open '${{mod ? mod.title : activeOutdoor.name}}' & Gate Test`;
      }} else {{
        const h = ACADEMIC_HALLS[state.hallLevel];
        document.getElementById("placard-icon").innerText = "🏛️";
        document.getElementById("placard-title").innerText = `${{h.code}}: ${{h.name}} (Interior Classrooms)`;
        document.getElementById("placard-sub").innerText = "Click any classroom desk to open its chapter & lab";
      }}

      const listEl = document.getElementById("checkpoint-list");
      let html = "";

      if (state.scene === "campus") {{
        document.getElementById("sidebar-list-heading").innerText = "OUTDOOR CAMPUS CHECKPOINTS & HALLS";
        for (const s of OUTDOOR_LANDMARKS) {{
          const mod = CURRICULUM.modules.find(m => m.id === s.id);
          const cleared = clearedIds.has(s.id);
          const unlocked = isModuleUnlocked(s.id);
          const active = state.activeStopId === s.id;
          html += `
            <div class="checkpoint-card ${{active ? 'active-stop' : ''}} ${{cleared ? 'cleared-stop' : ''}}" onclick="selectOutdoorStop('${{s.id}}', true)">
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.2rem;">
                <span style="font-family:var(--mono);font-size:0.71rem;font-weight:800;color:var(--terracotta);">${{s.icon}} ${{s.num}} · ${{s.name}}</span>
                <span class="tag ${{cleared ? 'tag-meadow' : (unlocked ? 'tag-amber' : '')}}">
                  ${{cleared ? '✓ CLEARED' : (unlocked ? '● LIVE LAB' : '🔒 GATE LOCKED')}}
                </span>
              </div>
              <div style="font-family:var(--serif);font-weight:800;font-size:0.98rem;">${{mod ? mod.title : s.name}}</div>
              <div style="font-size:0.78rem;color:var(--muted);margin-top:0.15rem;">${{mod ? mod.question : ''}}</div>
            </div>
          `;
        }}

        for (const h of ACADEMIC_HALLS) {{
          const mods = getModulesForLevel(h.level);
          const done = mods.filter(m => clearedIds.has(m.id)).length;
          html += `
            <div class="checkpoint-card" onclick="switchScene('hall', ${{h.level}})">
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.2rem;">
                <span style="font-family:var(--mono);font-size:0.71rem;font-weight:800;color:var(--sky);">🏛️ ${{h.code}} · 3D ACADEMIC HALL</span>
                <span class="tag tag-sky">${{done}}/${{mods.length}} Rooms</span>
              </div>
              <div style="font-family:var(--serif);font-weight:800;font-size:0.96rem;">${{h.name}}</div>
              <div style="font-size:0.77rem;color:var(--muted);">${{h.sub}} — Click to enter hall classrooms →</div>
            </div>
          `;
        }}
      }} else {{
        const h = ACADEMIC_HALLS[state.hallLevel];
        document.getElementById("sidebar-list-heading").innerText = `${{h.code}} CLASSROOMS (${{h.name.toUpperCase()}})`;
        const mods = getModulesForLevel(state.hallLevel);
        mods.forEach((m, idx) => {{
          const cleared = clearedIds.has(m.id);
          const seeded = Boolean(SEEDED_LESSONS[m.id]);
          const unlocked = isModuleUnlocked(m.id);
          html += `
            <div class="checkpoint-card ${{state.activeStopId === m.id ? 'active-stop' : ''}} ${{cleared ? 'cleared-stop' : ''}}" onclick="walkToHallRoom(${{idx}})">
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.2rem;">
                <span style="font-family:var(--mono);font-size:0.71rem;font-weight:800;">ROOM ${{state.hallLevel + 1}}0${{idx + 1}}</span>
                <span class="tag ${{cleared ? 'tag-meadow' : (seeded ? 'tag-amber' : '')}}">
                  ${{cleared ? '✓ CLEARED' : (seeded ? '● LIVE LAB' : '◐ SYLLABUS')}}
                </span>
              </div>
              <div style="font-family:var(--serif);font-weight:800;font-size:0.96rem;">${{m.title}}</div>
              <div style="font-size:0.77rem;color:var(--muted);">${{m.question}}</div>
            </div>
          `;
        }});
      }}
      listEl.innerHTML = html;
    }}

    function walkToHallRoom(roomIdx) {{
      const mods = getModulesForLevel(state.hallLevel);
      const mod = mods[roomIdx];
      if (!mod) return;
      state.activeStopId = mod.id;
      const r = HALL_ROOMS[roomIdx];
      if (r) {{
        state.hallPlayer.targetX = r.x + r.w / 2;
        state.hallPlayer.targetY = r.y + r.h / 2;
        state.hallPlayer.pendingRoomIdx = roomIdx;
      }} else {{
        openLessonBook(mod.id);
      }}
      refreshHudAndSidebar();
    }}

    // =========================================================================
    // 3D ISOMETRIC DRAWING PRIMITIVES (SUNLIT ARCHITECTURAL CAMPUS)
    // =========================================================================
    const canvas = document.getElementById("campus-canvas");
    const ctx = canvas.getContext("2d");

    // Draw an extruded 3D block with top roof, left facade, right facade, and drop shadow
    function drawIsoBox(cx, cy, w, d, h, topColor, leftColor, rightColor, strokeColor = "#1c1917") {{
      const hw = w / 2;
      const hd = d / 2;
      // Ground shadow
      ctx.fillStyle = "rgba(28, 25, 23, 0.18)";
      ctx.beginPath();
      ctx.moveTo(cx, cy + hd + 8);
      ctx.lineTo(cx + hw + 14, cy + 8);
      ctx.lineTo(cx, cy - hd + 8);
      ctx.lineTo(cx - hw + 6, cy + 8);
      ctx.closePath();
      ctx.fill();

      // Left wall
      ctx.fillStyle = leftColor;
      ctx.beginPath();
      ctx.moveTo(cx - hw, cy);
      ctx.lineTo(cx, cy + hd);
      ctx.lineTo(cx, cy + hd - h);
      ctx.lineTo(cx - hw, cy - h);
      ctx.closePath();
      ctx.fill();
      ctx.strokeStyle = strokeColor;
      ctx.lineWidth = 1.8;
      ctx.stroke();

      // Right wall
      ctx.fillStyle = rightColor;
      ctx.beginPath();
      ctx.moveTo(cx, cy + hd);
      ctx.lineTo(cx + hw, cy);
      ctx.lineTo(cx + hw, cy - h);
      ctx.lineTo(cx, cy + hd - h);
      ctx.closePath();
      ctx.fill();
      ctx.stroke();

      // Pitched or flat roof top
      ctx.fillStyle = topColor;
      ctx.beginPath();
      ctx.moveTo(cx, cy - hd - h);
      ctx.lineTo(cx + hw, cy - h);
      ctx.lineTo(cx, cy + hd - h);
      ctx.lineTo(cx - hw, cy - h);
      ctx.closePath();
      ctx.fill();
      ctx.stroke();
    }}

    function drawTree3D(x, y, scale = 1.0) {{
      const sway = Math.sin(state.tick * 0.03 + x) * 1.8;
      // Shadow
      ctx.fillStyle = "rgba(20, 83, 45, 0.22)";
      ctx.beginPath();
      ctx.ellipse(x + 6, y + 6, 16 * scale, 8 * scale, 0, 0, Math.PI * 2);
      ctx.fill();
      // Trunk
      ctx.fillStyle = "#78350f";
      ctx.fillRect(x - 3 * scale, y - 14 * scale, 6 * scale, 16 * scale);
      // 3 layered sunlit foliage spheres
      ctx.fillStyle = "#15803d";
      ctx.beginPath();
      ctx.arc(x + sway, y - 20 * scale, 15 * scale, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = "#22c55e";
      ctx.beginPath();
      ctx.arc(x - 4 * scale + sway, y - 24 * scale, 12 * scale, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = "#86efac";
      ctx.beginPath();
      ctx.arc(x - 6 * scale + sway, y - 27 * scale, 6 * scale, 0, Math.PI * 2);
      ctx.fill();
    }}

    function drawCar3D(x, y, bodyColor, roofColor, label) {{
      drawIsoBox(x, y, 44, 24, 11, bodyColor, bodyColor, "#1e293b");
      drawIsoBox(x, y - 9, 26, 16, 8, roofColor, "#e2e8f0", "#cbd5e1");
      if (label) {{
        ctx.font = "bold 9px 'JetBrains Mono', monospace";
        ctx.fillStyle = "#1c1917";
        ctx.textAlign = "center";
        ctx.fillText(label, x, y - 26);
      }}
    }}

    function drawUmbrellaTable(x, y, color1) {{
      // Table shadow
      ctx.fillStyle = "rgba(28,25,23,0.18)";
      ctx.beginPath();
      ctx.ellipse(x, y + 6, 18, 9, 0, 0, Math.PI * 2);
      ctx.fill();
      // Table top
      ctx.fillStyle = "#fef3c7";
      ctx.strokeStyle = "#1c1917";
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.ellipse(x, y, 16, 8, 0, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
      // Pole
      ctx.strokeStyle = "#44403c";
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(x, y);
      ctx.lineTo(x, y - 20);
      ctx.stroke();
      // Striped umbrella canopy
      ctx.fillStyle = color1;
      ctx.beginPath();
      ctx.ellipse(x, y - 20, 20, 10, 0, 0, Math.PI * 2);
      ctx.fill();
      ctx.strokeStyle = "#1c1917";
      ctx.lineWidth = 1.5;
      ctx.stroke();
    }}

    function drawWaypointPin(x, y, numTxt, titleTxt, cleared, unlocked, isActive) {{
      const floatY = Math.sin(state.tick * 0.07 + x) * 3.5;
      const py = y + floatY;

      // Pill background
      const bg = cleared ? "#15803d" : (unlocked ? (isActive ? "#d94e1f" : "#d97706") : "#57534e");
      ctx.font = "bold 11px 'Plus Jakarta Sans', sans-serif";
      const tw = Math.max(ctx.measureText(titleTxt).width + 26, 130);
      const bx = x - tw / 2;
      const by = py - 36;

      // Shadow
      ctx.fillStyle = "rgba(28, 25, 23, 0.3)";
      ctx.beginPath();
      ctx.roundRect(bx + 2, by + 3, tw, 30, 8);
      ctx.fill();

      // Main sign
      ctx.fillStyle = "#fffdf8";
      ctx.strokeStyle = "#1c1917";
      ctx.lineWidth = isActive ? 3 : 2;
      ctx.beginPath();
      ctx.roundRect(bx, by, tw, 30, 8);
      ctx.fill();
      ctx.stroke();

      // Top color bar
      ctx.fillStyle = bg;
      ctx.beginPath();
      ctx.roundRect(bx, by, tw, 12, [8, 8, 0, 0]);
      ctx.fill();

      ctx.font = "bold 8.5px 'JetBrains Mono', monospace";
      ctx.fillStyle = "#ffffff";
      ctx.textAlign = "center";
      ctx.fillText(cleared ? `✓ ${{numTxt}} CLEARED` : (unlocked ? `★ ${{numTxt}}` : `🔒 ${{numTxt}}`), x, by + 9);

      ctx.font = "bold 11px 'Plus Jakarta Sans', sans-serif";
      ctx.fillStyle = "#1c1917";
      ctx.fillText(titleTxt, x, by + 24);
    }}

    function drawAvatar3D(x, y, name, hoodieColor = "#d94e1f", hatIcon = "") {{
      const bounce = Math.abs(Math.sin(state.player.frame)) * 3;
      // Ground shadow
      ctx.fillStyle = "rgba(28, 25, 23, 0.28)";
      ctx.beginPath();
      ctx.ellipse(x, y + 12, 13, 6, 0, 0, Math.PI * 2);
      ctx.fill();

      // Legs
      ctx.fillStyle = "#1e293b";
      ctx.fillRect(x - 6, y + 2 - bounce, 5, 10);
      ctx.fillRect(x + 1, y + 2 - bounce, 5, 10);

      // Torso / Hoodie
      ctx.fillStyle = hoodieColor;
      ctx.strokeStyle = "#1c1917";
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.roundRect(x - 10, y - 13 - bounce, 20, 17, 5);
      ctx.fill();
      ctx.stroke();

      // Head
      ctx.fillStyle = "#fed7aa";
      ctx.beginPath();
      ctx.arc(x, y - 21 - bounce, 9, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();

      // Hair / Cap
      ctx.fillStyle = "#1c1917";
      ctx.beginPath();
      ctx.arc(x, y - 24 - bounce, 9, Math.PI, Math.PI * 2);
      ctx.fill();

      // Eyes
      ctx.fillStyle = "#1c1917";
      ctx.fillRect(x - 4, y - 22 - bounce, 2.5, 3);
      ctx.fillRect(x + 2, y - 22 - bounce, 2.5, 3);

      // Floating Nameplate
      ctx.font = "bold 10px 'JetBrains Mono', monospace";
      const nw = ctx.measureText(name).width + 12;
      ctx.fillStyle = "#1c1917";
      ctx.beginPath();
      ctx.roundRect(x - nw / 2, y - 46 - bounce, nw, 15, 4);
      ctx.fill();
      ctx.fillStyle = "#fffdf8";
      ctx.textAlign = "center";
      ctx.fillText(name, x, y - 35 - bounce);
    }}

    function drawCampus3D() {{
      // 1. Sunlit Sky & Horizon Hills
      const skyGrad = ctx.createLinearGradient(0, 0, 0, 145);
      skyGrad.addColorStop(0, "#7dd3fc");
      skyGrad.addColorStop(1, "#e0f2fe");
      ctx.fillStyle = skyGrad;
      ctx.fillRect(0, 0, canvas.width, 145);

      // Distant rolling hills
      ctx.fillStyle = "#a3e635";
      ctx.beginPath();
      ctx.moveTo(0, 145);
      ctx.quadraticCurveTo(240, 88, 520, 130);
      ctx.quadraticCurveTo(840, 82, 1120, 135);
      ctx.lineTo(1120, 700);
      ctx.lineTo(0, 700);
      ctx.closePath();
      ctx.fill();

      // Main campus meadow lawn
      const lawnGrad = ctx.createLinearGradient(0, 130, 0, 700);
      lawnGrad.addColorStop(0, "#a3e635");
      lawnGrad.addColorStop(0.5, "#84cc16");
      lawnGrad.addColorStop(1, "#65a30d");
      ctx.fillStyle = lawnGrad;
      ctx.fillRect(0, 130, canvas.width, 570);

      // Isometric decorative lawn grid lines
      ctx.strokeStyle = "rgba(255, 255, 255, 0.14)";
      ctx.lineWidth = 1;
      for (let i = -700; i < 1600; i += 90) {{
        ctx.beginPath();
        ctx.moveTo(i, 130);
        ctx.lineTo(i + 550, 700);
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(i + 550, 130);
        ctx.lineTo(i, 700);
        ctx.stroke();
      }}

      // 2. Sandstone Campus Walkways & Main Entry Road
      // South Entrance Asphalt Driveway (leads up through Security Gate)
      ctx.fillStyle = "#475569";
      ctx.fillRect(475, 525, 90, 175);
      ctx.strokeStyle = "#f8fafc";
      ctx.lineWidth = 2;
      ctx.setLineDash([10, 10]);
      ctx.beginPath();
      ctx.moveTo(520, 535);
      ctx.lineTo(520, 695);
      ctx.stroke();
      ctx.setLineDash([]);

      // Warm sandstone pedestrian avenues connecting Gate -> Parking -> Cafeteria -> Quad -> Academic Halls
      ctx.fillStyle = "#f5ebe0";
      ctx.strokeStyle = "#d6cbb9";
      ctx.lineWidth = 3;
      // Central North-South Grand Spine
      ctx.beginPath();
      ctx.roundRect(492, 185, 56, 355, 16);
      ctx.fill();
      ctx.stroke();
      // West Branch to Parking Lot & Cafeteria
      ctx.beginPath();
      ctx.roundRect(190, 435, 330, 42, 12);
      ctx.fill();
      ctx.stroke();
      ctx.beginPath();
      ctx.roundRect(325, 275, 210, 42, 12);
      ctx.fill();
      ctx.stroke();
      // East Branch to Academic Halls
      ctx.beginPath();
      ctx.roundRect(520, 445, 440, 42, 12);
      ctx.fill();
      ctx.stroke();
      ctx.beginPath();
      ctx.roundRect(520, 265, 440, 42, 12);
      ctx.fill();
      ctx.stroke();
      ctx.beginPath();
      ctx.roundRect(520, 145, 410, 36, 12);
      ctx.fill();
      ctx.stroke();

      // Perimeter Campus Brick Wall at South Gate
      ctx.fillStyle = "#9a3412";
      ctx.fillRect(40, 608, 425, 16);
      ctx.fillRect(575, 608, 505, 16);
      ctx.fillStyle = "#fed7aa";
      ctx.fillRect(40, 604, 425, 4);
      ctx.fillRect(575, 604, 505, 4);

      // =====================================================================
      // LANDMARK 2: WEST CAMPUS PARKING LOT (l0-tokens)
      // =====================================================================
      ctx.save();
      // Asphalt lot pad
      ctx.fillStyle = "#334155";
      ctx.strokeStyle = "#cbd5e1";
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.roundRect(65, 375, 235, 155, 14);
      ctx.fill();
      ctx.stroke();

      // Painted parking bay dividers
      ctx.strokeStyle = "#fde047";
      ctx.lineWidth = 2;
      for (let bx = 105; bx <= 255; bx += 50) {{
        ctx.beginPath();
        ctx.moveTo(bx, 385);
        ctx.lineTo(bx, 445);
        ctx.stroke();
      }}
      // Parked 3D Isometric Token Cars with Subword Barcode plates!
      drawCar3D(130, 420, "#ef4444", "#fecaca", '"str" #496');
      drawCar3D(180, 420, "#3b82f6", "#bfdbfe", '"aw" #675');
      drawCar3D(232, 420, "#10b981", "#a7f3d0", '"berry" #15717');

      // Token Chopper Kiosk Booth
      drawIsoBox(115, 495, 58, 36, 34, "#0284c7", "#f0f9ff", "#bae6fd");
      drawAvatar3D(165, 505, "MAYA (TOKENS)", "#0284c7");
      ctx.restore();

      // =====================================================================
      // LANDMARK 3: CAMPUS CAFETERIA & CHAI TERRACE (l0-embeddings)
      // =====================================================================
      ctx.save();
      // Wooden sun-deck patio
      ctx.fillStyle = "#fed7aa";
      ctx.strokeStyle = "#c2410c";
      ctx.lineWidth = 2.5;
      ctx.beginPath();
      ctx.roundRect(225, 200, 235, 135, 16);
      ctx.fill();
      ctx.stroke();

      // 3D Isometric Cafeteria Pavilion Building
      drawIsoBox(295, 245, 96, 56, 44, "#ea580c", "#fff7ed", "#fdba74");
      // Striped awning badge
      ctx.font = "bold 9.5px 'JetBrains Mono', monospace";
      ctx.fillStyle = "#9a3412";
      ctx.textAlign = "center";
      ctx.fillText("CHAI & EMBEDDINGS CAFE", 345, 323);

      // Outdoor Umbrella Tables (Meaning clusters!)
      drawUmbrellaTable(385, 235, "#ef4444");
      drawUmbrellaTable(425, 265, "#f59e0b");
      drawUmbrellaTable(375, 290, "#10b981");
      drawAvatar3D(330, 295, "CHEF KABIR", "#ea580c");
      ctx.restore();

      // =====================================================================
      // LANDMARK 4: CENTRAL QUAD LAWN & FOUNTAIN (l0-context-window)
      // =====================================================================
      ctx.save();
      // Circular stone plaza
      ctx.fillStyle = "#e7e5e4";
      ctx.strokeStyle = "#a8a29e";
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.ellipse(520, 340, 82, 48, 0, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();

      // Animated Water Fountain Basin
      ctx.fillStyle = "#0ea5e9";
      ctx.strokeStyle = "#1c1917";
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.ellipse(520, 338, 46, 26, 0, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();

      // Rippling water rings
      const ripple = (state.tick % 40) / 40;
      ctx.strokeStyle = `rgba(255, 255, 255, ${{1 - ripple}})`;
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.ellipse(520, 338, 12 + ripple * 30, 6 + ripple * 16, 0, 0, Math.PI * 2);
      ctx.stroke();

      // Fountain center spire
      drawIsoBox(520, 338, 20, 14, 22, "#38bdf8", "#f8fafc", "#cbd5e1");
      drawAvatar3D(578, 355, "PROF. MEERA", "#7e22ce");
      ctx.restore();

      // =====================================================================
      // 6 3D ISOMETRIC ACADEMIC HALLS (EAST & NORTH CAMPUS)
      // =====================================================================
      for (const h of ACADEMIC_HALLS) {{
        const mods = getModulesForLevel(h.level);
        const done = mods.filter(m => clearedIds.has(m.id)).length;
        drawIsoBox(h.x, h.y, h.w, h.d, h.h, h.roof, h.wallL, h.wallR);

        // Windows on left & right 3D facades
        ctx.fillStyle = "#38bdf8";
        for (let wy = h.y - h.h + 14; wy < h.y - 6; wy += 16) {{
          ctx.fillRect(h.x - h.w / 3, wy, 8, 9);
          ctx.fillRect(h.x - h.w / 6, wy + 5, 8, 9);
          ctx.fillRect(h.x + h.w / 8, wy + 5, 8, 9);
          ctx.fillRect(h.x + h.w / 3 - 8, wy, 8, 9);
        }}

        // Hall Crest Sign above roof
        const signY = h.y - h.d / 2 - h.h - 24;
        ctx.fillStyle = "#fffdf8";
        ctx.strokeStyle = "#1c1917";
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.roundRect(h.x - 74, signY, 148, 28, 7);
        ctx.fill();
        ctx.stroke();

        ctx.fillStyle = h.roof;
        ctx.font = "bold 9px 'JetBrains Mono', monospace";
        ctx.textAlign = "center";
        ctx.fillText(`${{h.code}} · ${{done}}/${{mods.length}} ROOMS`, h.x, signY + 11);

        ctx.fillStyle = "#1c1917";
        ctx.font = "bold 10.5px 'Plus Jakarta Sans', sans-serif";
        ctx.fillText(h.name, h.x, signY + 23);
      }}

      // =====================================================================
      // LANDMARK 1: SOUTH SECURITY GATE & GUARD BOOTH (l0-what-is-an-llm)
      // =====================================================================
      ctx.save();
      // 3D Guard Booth on West side of gate
      drawIsoBox(442, 585, 58, 38, 42, "#d94e1f", "#fffbeb", "#fde68a");
      // Guard window
      ctx.fillStyle = "#38bdf8";
      ctx.fillRect(450, 560, 14, 12);

      // Boom Barrier Post
      ctx.fillStyle = "#dc2626";
      ctx.strokeStyle = "#1c1917";
      ctx.lineWidth = 2;
      ctx.fillRect(468, 578, 12, 24);
      ctx.strokeRect(468, 578, 12, 24);

      // Red-and-White Boom Barrier Arm (Closed horizontal vs Open raised!)
      ctx.save();
      ctx.translate(474, 584);
      if (isGateOpen()) {{
        ctx.rotate(-1.22); // Lifted open!
      }}
      // Draw striped arm
      for (let seg = 0; seg < 6; seg++) {{
        ctx.fillStyle = seg % 2 === 0 ? "#ef4444" : "#ffffff";
        ctx.fillRect(seg * 16, -4, 16, 8);
        ctx.strokeStyle = "#1c1917";
        ctx.lineWidth = 1.5;
        ctx.strokeRect(seg * 16, -4, 16, 8);
      }}
      ctx.restore();

      // Security Guard Officer Rajan NPC
      drawAvatar3D(492, 575, "OFFICER RAJAN", "#1e3a8a");
      ctx.restore();

      // 3D Campus Trees around quad and walkways
      const treeCoords = [
        [95, 195], [155, 240], [85, 585], [375, 555],
        [635, 560], [645, 395], [645, 235], [440, 155],
        [1065, 570], [1070, 365], [1070, 185]
      ];
      for (const [tx, ty] of treeCoords) {{
        drawTree3D(tx, ty, 0.95);
      }}

      // Floating Waypoint Pins for the 4 Outdoor Live Checkpoints
      for (const s of OUTDOOR_LANDMARKS) {{
        const cleared = clearedIds.has(s.id);
        const unlocked = isModuleUnlocked(s.id);
        const isActive = state.activeStopId === s.id;
        drawWaypointPin(s.x, s.y - 45, s.num, s.name, cleared, unlocked, isActive);
      }}

      // Draw Ashwin Player Avatar
      drawAvatar3D(state.player.x, state.player.y, "ASHWIN (YOU)", "#d94e1f");
    }}

    function drawHallInterior3D() {{
      const h = ACADEMIC_HALLS[state.hallLevel];
      // Warm sunlit oak classroom floor
      ctx.fillStyle = "#f5ebe0";
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      // Subtle architectural tile grid
      ctx.strokeStyle = "#e7dacB";
      ctx.lineWidth = 1;
      for (let gx = 0; gx < canvas.width; gx += 40) {{
        ctx.beginPath(); ctx.moveTo(gx, 0); ctx.lineTo(gx, canvas.height); ctx.stroke();
      }}
      for (let gy = 0; gy < canvas.height; gy += 40) {{
        ctx.beginPath(); ctx.moveTo(0, gy); ctx.lineTo(canvas.width, gy); ctx.stroke();
      }}

      // Central sunlit hallway runner
      ctx.fillStyle = "#e6ccb2";
      ctx.strokeStyle = "#b08968";
      ctx.lineWidth = 3;
      ctx.fillRect(45, 270, canvas.width - 90, 135);
      ctx.strokeRect(45, 270, canvas.width - 90, 135);

      ctx.font = "bold 13px 'Fraunces', serif";
      ctx.fillStyle = "#7f5539";
      ctx.textAlign = "center";
      ctx.fillText(`${{h.code}} · ${{h.name.toUpperCase()}} CORRIDOR (CLICK ANY CLASSROOM TO OPEN CHAPTER)`, canvas.width / 2, 342);

      const mods = getModulesForLevel(state.hallLevel);
      for (let i = 0; i < Math.min(HALL_ROOMS.length, mods.length); i++) {{
        const r = HALL_ROOMS[i];
        const m = mods[i];
        const cleared = clearedIds.has(m.id);
        const seeded = Boolean(SEEDED_LESSONS[m.id]);
        const unlocked = isModuleUnlocked(m.id);

        // Classroom card floor
        ctx.fillStyle = cleared ? "#f0fdf4" : (seeded ? "#fffbeb" : "#ffffff");
        ctx.strokeStyle = cleared ? "#15803d" : (seeded ? "#d94e1f" : "#a8a29e");
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.roundRect(r.x, r.y, r.w, r.h, 14);
        ctx.fill();
        ctx.stroke();

        // Top classroom banner
        ctx.fillStyle = cleared ? "#15803d" : (seeded ? "#d94e1f" : "#78716c");
        ctx.beginPath();
        ctx.roundRect(r.x, r.y, r.w, 28, [14, 14, 0, 0]);
        ctx.fill();

        ctx.font = "bold 10px 'JetBrains Mono', monospace";
        ctx.fillStyle = "#ffffff";
        ctx.textAlign = "left";
        ctx.fillText(`ROOM ${{state.hallLevel + 1}}0${{i + 1}}`, r.x + 12, r.y + 18);
        ctx.textAlign = "right";
        ctx.fillText(cleared ? "✓ CLEARED" : (seeded ? "★ LIVE LAB" : "SYLLABUS"), r.x + r.w - 12, r.y + 18);

        // Room title
        ctx.fillStyle = "#1c1917";
        ctx.font = "bold 13px 'Fraunces', serif";
        ctx.textAlign = "center";
        const words = m.title.split(" ");
        let l1 = "", l2 = "";
        for (const w of words) {{
          if ((l1 + " " + w).trim().length <= 22) l1 = (l1 + " " + w).trim();
          else l2 = (l2 + " " + w).trim();
        }}
        ctx.fillText(l1, r.x + r.w / 2, r.y + 62);
        if (l2) ctx.fillText(l2, r.x + r.w / 2, r.y + 80);

        // 3D Lab Desk inside classroom
        drawIsoBox(r.x + r.w / 2, r.y + 132, 64, 34, 18, "#d97706", "#fef3c7", "#fde68a");
      }}

      drawAvatar3D(state.hallPlayer.x, state.hallPlayer.y, "ASHWIN (YOU)", "#d94e1f");
    }}

    // =========================================================================
    // GAME LOOP & INPUT HANDLING
    // =========================================================================
    window.addEventListener("keydown", e => {{
      if (document.getElementById("book-modal").classList.contains("open")) {{
        if (e.key === "Escape") closeBookModal();
        return;
      }}
      state.keys[e.key.toLowerCase()] = true;
      if (["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", " "].includes(e.key)) {{
        e.preventDefault();
      }}
      if (e.key.toLowerCase() === "e" || e.key === "Enter") {{
        openActiveCheckpoint();
      }}
    }});

    window.addEventListener("keyup", e => {{
      state.keys[e.key.toLowerCase()] = false;
    }});

    canvas.addEventListener("click", e => {{
      const rect = canvas.getBoundingClientRect();
      const cx = (e.clientX - rect.left) * (canvas.width / rect.width);
      const cy = (e.clientY - rect.top) * (canvas.height / rect.height);

      if (state.scene === "campus") {{
        // 1. Check outdoor checkpoints
        for (const s of OUTDOOR_LANDMARKS) {{
          if (Math.hypot(cx - s.x, cy - (s.y - 15)) < s.radius) {{
            selectOutdoorStop(s.id, true);
            return;
          }}
        }}
        // 2. Check 3D Academic Halls
        for (const h of ACADEMIC_HALLS) {{
          if (cx >= h.x - h.w / 2 - 15 && cx <= h.x + h.w / 2 + 15 &&
              cy >= h.y - h.h - h.d / 2 - 25 && cy <= h.y + h.d / 2 + 15) {{
            if (!isGateOpen()) {{
              selectOutdoorStop("l0-what-is-an-llm", true);
              return;
            }}
            switchScene("hall", h.level);
            return;
          }}
        }}
        // Otherwise walk Ashwin there (respecting the closed boom gate!)
        if (!isGateOpen() && cy < 575) {{
          selectOutdoorStop("l0-what-is-an-llm", true);
          return;
        }}
        state.player.targetX = cx;
        state.player.targetY = cy;
        state.player.pendingAction = null;
      }} else {{
        const mods = getModulesForLevel(state.hallLevel);
        for (let i = 0; i < Math.min(HALL_ROOMS.length, mods.length); i++) {{
          const r = HALL_ROOMS[i];
          if (cx >= r.x && cx <= r.x + r.w && cy >= r.y && cy <= r.y + r.h) {{
            walkToHallRoom(i);
            return;
          }}
        }}
        state.hallPlayer.targetX = cx;
        state.hallPlayer.targetY = cy;
      }}
    }});

    function updateLoop() {{
      state.tick += 1;
      let dx = 0, dy = 0;
      if (state.keys["w"] || state.keys["arrowup"]) dy -= 1;
      if (state.keys["s"] || state.keys["arrowdown"]) dy += 1;
      if (state.keys["a"] || state.keys["arrowleft"]) dx -= 1;
      if (state.keys["d"] || state.keys["arrowright"]) dx += 1;

      const p = state.scene === "campus" ? state.player : state.hallPlayer;

      if (dx !== 0 || dy !== 0) {{
        p.targetX = null;
        p.targetY = null;
        p.pendingAction = null;
        p.pendingRoomIdx = null;
        const len = Math.hypot(dx, dy);
        let nx = p.x + (dx / len) * state.player.speed;
        let ny = p.y + (dy / len) * state.player.speed;
        if (state.scene === "campus" && !isGateOpen() && ny < 588) {{
          ny = 588;
        }}
        p.x = Math.max(45, Math.min(canvas.width - 45, nx));
        p.y = Math.max(95, Math.min(canvas.height - 30, ny));
        state.player.frame += 0.22;
      }} else if (p.targetX !== null && p.targetY !== null) {{
        const tx = p.targetX - p.x;
        const ty = p.targetY - p.y;
        const dist = Math.hypot(tx, ty);
        if (dist <= state.player.speed * 1.3) {{
          p.x = p.targetX;
          p.y = p.targetY;
          p.targetX = null;
          p.targetY = null;
          if (state.scene === "campus" && p.pendingAction) {{
            const fn = p.pendingAction;
            p.pendingAction = null;
            fn();
          }} else if (state.scene === "hall" && p.pendingRoomIdx !== null && p.pendingRoomIdx !== undefined) {{
            const idx = p.pendingRoomIdx;
            p.pendingRoomIdx = null;
            const mods = getModulesForLevel(state.hallLevel);
            if (mods[idx]) openLessonBook(mods[idx].id);
          }}
        }} else {{
          p.x += (tx / dist) * state.player.speed * 1.25;
          p.y += (ty / dist) * state.player.speed * 1.25;
          state.player.frame += 0.25;
        }}
      }}

      // Check proximity to outdoor landmarks
      if (state.scene === "campus") {{
        for (const s of OUTDOOR_LANDMARKS) {{
          if (Math.hypot(state.player.x - s.x, state.player.y - s.y) < 62) {{
            if (state.activeStopId !== s.id) {{
              state.activeStopId = s.id;
              refreshHudAndSidebar();
            }}
            break;
          }}
        }}
      }}
    }}

    function gameFrame() {{
      updateLoop();
      if (state.scene === "campus") drawCampus3D();
      else drawHallInterior3D();
      requestAnimationFrame(gameFrame);
    }}

    // =========================================================================
    // EDITORIAL CHAPTER BOOK & INTERACTIVE PLAYGROUNDS
    // =========================================================================
    function openLessonBook(lessonId) {{
      state.activeStopId = lessonId;
      state.quizAnswers = {{}};
      refreshHudAndSidebar();

      const mod = CURRICULUM.modules.find(m => m.id === lessonId);
      const lesson = SEEDED_LESSONS[lessonId];
      const stop = OUTDOOR_LANDMARKS.find(s => s.id === lessonId);
      const cleared = clearedIds.has(lessonId);
      const unlocked = isModuleUnlocked(lessonId);

      document.getElementById("bk-location-tag").innerText = stop
        ? `${{stop.icon}} ${{stop.num}} · ${{stop.name.toUpperCase()}}`
        : `🏛️ HALL ${{mod ? mod.level : 0}} CLASSROOM`;

      const stTag = document.getElementById("bk-status-tag");
      stTag.innerText = cleared ? "✓ CHECKPOINT CLEARED" : (unlocked ? "🟢 READY TO CLEAR" : "🔒 CLEAR PREVIOUS STOP FIRST");
      stTag.className = cleared ? "tag tag-meadow" : (unlocked ? "tag tag-amber" : "tag");

      document.getElementById("bk-title").innerText = mod ? mod.title : lessonId;
      const linkEl = document.getElementById("bk-standalone-link");

      if (lesson) {{
        linkEl.href = `lessons/${{lesson.id}}/index.html`;
        linkEl.style.display = "inline-flex";
        renderSeededLessonBook(mod, lesson, stop, unlocked, cleared);
      }} else {{
        linkEl.style.display = "none";
        renderSyllabusPreviewBook(mod, unlocked, cleared);
      }}

      document.getElementById("book-modal").classList.add("open");
      switchBookTab("story");
    }}

    function closeBookModal() {{
      document.getElementById("book-modal").classList.remove("open");
    }}

    function switchBookTab(tabName) {{
      document.querySelectorAll(".book-tab").forEach(b => {{
        b.classList.toggle("active", b.getAttribute("data-tab") === tabName);
      }});
      document.querySelectorAll(".book-pane").forEach(p => p.classList.remove("active"));
      document.getElementById("bk-pane-" + tabName).classList.add("active");
    }}

    function formatSimpleMarkdown(text) {{
      if (!text) return "";
      const paras = text.trim().split(/\\n\\n+/);
      return paras.map(p => {{
        let h = p
          .replace(/&/g, "&amp;")
          .replace(/</g, "&lt;")
          .replace(/>/g, "&gt;")
          .replace(/`([^`]+)`/g, "<code>$1</code>")
          .replace(/\\*\\*([^*]+)\\*\\*/g, "<strong>$1</strong>")
          .replace(/\\*([^*]+)\\*/g, "<em>$1</em>");
        return `<p>${{h}}</p>`;
      }}).join("");
    }}

    function buildInteractivePlayground(lessonId) {{
      if (lessonId === "l0-what-is-an-llm") {{
        return `
          <div class="playground-box">
            <div class="spine-label">🎲 INTERACTIVE GUARD BOOTH SIMULATOR · TEMPERATURE & THE WEIGHTED DIE</div>
            <h3 style="margin:0.2rem 0 0.5rem;font-family:var(--serif);font-size:1.3rem;">Slide the Temperature Dial & Roll the Next Word</h3>
            <p style="margin:0 0 0.9rem;font-size:0.9rem;color:var(--ink-soft);">
              Watch what happens to the scoreboard after <code>"the server"</code> (` + "`crashed=3.2`" + ` vs ` + "`responded=2.9`" + `). Lowering Temperature to <strong>0.2</strong> makes the top word almost guaranteed; raising it to <strong>1.5</strong> flattens the bars so weird words can win!
            </p>
            <div style="display:flex;gap:0.85rem;align-items:center;flex-wrap:wrap;margin-bottom:0.9rem;">
              <label style="font-family:var(--mono);font-size:0.86rem;font-weight:700;">
                Temperature: <strong id="sim-l0-temp-val" style="color:var(--terracotta);">1.0</strong>
              </label>
              <input id="sim-l0-temp" type="range" min="0" max="2.0" step="0.1" value="1.0" oninput="updateL0Sim()" style="width:200px;accent-color:var(--terracotta);" />
              <button class="btn btn-primary" onclick="rollL0NextWord()">🎲 Roll & Glue Next Word →</button>
              <button class="btn" onclick="resetL0Sim()">↺ Reset</button>
            </div>
            <div id="sim-l0-bars" style="margin-bottom:0.85rem;"></div>
            <div style="background:#fffdf8;padding:0.75rem 1rem;border-radius:10px;border:2px solid var(--ink);font-family:var(--mono);font-size:0.88rem;">
              Current Relay Sentence: <strong id="sim-l0-sentence" style="color:var(--terracotta);">the server</strong>
            </div>
          </div>
        `;
      }}
      if (lessonId === "l0-tokens") {{
        return `
          <div class="playground-box">
            <div class="spine-label">🅿️ INTERACTIVE PARKING LOT CHOPPER · BPE BARCODES & THE HINDI TAX</div>
            <h3 style="margin:0.2rem 0 0.5rem;font-family:var(--serif);font-size:1.3rem;">Click Any Phrase to Chop It Into Token Barcodes</h3>
            <p style="margin:0 0 0.85rem;font-size:0.9rem;color:var(--ink-soft);">
              See why <code>"strawberry"</code> hides two <code>r</code>'s inside barcode <code>#15717</code>, why adding spaces fixes letter counting immediately, and why Hindi pays a <strong>3.3x token tax</strong>.
            </p>
            <div style="display:flex;gap:0.5rem;flex-wrap:wrap;margin-bottom:0.9rem;">
              <button class="btn btn-primary" onclick="inspectTokenPreset('strawberry')">🍓 "strawberry"</button>
              <button class="btn" onclick="inspectTokenPreset('s t r a w b e r r y')">✨ "s t r a w b e r r y" (Spaced Fix)</button>
              <button class="btn" onclick="inspectTokenPreset('The server responded in 12ms.')">🇬🇧 English Sentence</button>
              <button class="btn" onclick="inspectTokenPreset('नमस्ते दुनिया')">🇮🇳 Hindi ('नमस्ते दुनिया')</button>
              <button class="btn" onclick="inspectTokenPreset('🚀🔥🤖')">🚀 Emojis ('🚀🔥🤖')</button>
            </div>
            <div id="sim-tok-chips" style="display:flex;gap:0.5rem;flex-wrap:wrap;margin-bottom:0.8rem;"></div>
            <div id="sim-tok-note" style="background:#fffdf8;padding:0.75rem 1rem;border-radius:10px;border:2px solid var(--ink);font-family:var(--mono);font-size:0.84rem;"></div>
          </div>
        `;
      }}
      if (lessonId === "l0-embeddings") {{
        return `
          <div class="playground-box">
            <div class="spine-label">☕ INTERACTIVE CAFETERIA MEANING MAP · 4D EMBEDDING GPS</div>
            <h3 style="margin:0.2rem 0 0.5rem;font-family:var(--serif);font-size:1.3rem;">Compare Any Item Against Masala Chai or Run Vector Math</h3>
            <p style="margin:0 0 0.85rem;font-size:0.9rem;color:var(--ink-soft);">
              Every item has 4 coordinates: <code>[Hot_Drink, Spicy_Indian, Tech_Code, Royalty]</code>. Click an item to measure its flashlight angle (Cosine Similarity) with <strong>masala_chai</strong>!
            </p>
            <div style="display:flex;gap:0.5rem;flex-wrap:wrap;margin-bottom:0.85rem;">
              <button class="btn btn-primary" onclick="inspectEmbeddingItem('filter_coffee')">☕ filter_coffee</button>
              <button class="btn" onclick="inspectEmbeddingItem('iced_chai')">🧊 iced_chai (Opposite Trap!)</button>
              <button class="btn" onclick="inspectEmbeddingItem('samosa')">🥟 samosa</button>
              <button class="btn" onclick="inspectEmbeddingItem('kubernetes')">☸️ kubernetes</button>
              <button class="btn btn-meadow" onclick="inspectEmbeddingItem('king_math')">👑 Run king - man + woman</button>
            </div>
            <div id="sim-emb-output" style="background:#fffdf8;padding:0.85rem 1rem;border-radius:10px;border:2px solid var(--ink);font-family:var(--mono);font-size:0.84rem;"></div>
          </div>
        `;
      }}
      if (lessonId === "l0-context-window") {{
        return `
          <div class="playground-box">
            <div class="spine-label">⛲ INTERACTIVE QUAD LUNCH TRAY · SLIDING WINDOW & U-CURVE</div>
            <h3 style="margin:0.2rem 0 0.5rem;font-family:var(--serif);font-size:1.3rem;">Watch Turn 1's Secret Code Fall Off the 24-Word Lunch Tray</h3>
            <p style="margin:0 0 0.85rem;font-size:0.9rem;color:var(--ink-soft);">
              Click through Turns 1 → 4 on our 24-word tray, or test where to hide the locker code <code>7492</code> on a 10-chunk tray!
            </p>
            <div style="display:flex;gap:0.5rem;flex-wrap:wrap;margin-bottom:0.85rem;">
              <button class="btn btn-primary" onclick="inspectTrayStep(1)">Turn 1 (8/24 words)</button>
              <button class="btn" onclick="inspectTrayStep(2)">Turn 2 (16/24 words)</button>
              <button class="btn" onclick="inspectTrayStep(3)">Turn 3 (24/24 FULL!)</button>
              <button class="btn" onclick="inspectTrayStep(4)">Turn 4 (Overflow! 7492 Dropped)</button>
              <button class="btn btn-meadow" onclick="inspectTrayStep(5)">📉 Show Lost-in-the-Middle U-Curve</button>
            </div>
            <div id="sim-ctx-output" style="background:#fffdf8;padding:0.85rem 1rem;border-radius:10px;border:2px solid var(--ink);font-family:var(--mono);font-size:0.84rem;"></div>
          </div>
        `;
      }}
      return "";
    }}

    function renderSeededLessonBook(mod, lesson, stop, unlocked, cleared) {{
      const sp = lesson.story_spine;
      const figsById = {{}};
      (lesson.figures || []).forEach(f => {{ figsById[f.id] = f; }});

      const chaptersHtml = (lesson.sections || []).map((sec, idx) => {{
        let figHtml = "";
        if (sec.figure_id && figsById[sec.figure_id]) {{
          const f = figsById[sec.figure_id];
          figHtml = `
            <div class="inline-figure">
              <img src="lessons/${{lesson.id}}/${{f.id}}.svg" alt="${{f.title}}" style="width:100%;height:auto;display:block;" />
              <div style="display:flex;justify-content:space-between;align-items:center;margin-top:0.65rem;padding-top:0.5rem;border-top:1.5px dashed var(--line-strong);font-size:0.81rem;color:var(--ink-soft);flex-wrap:wrap;gap:0.5rem;">
                <span><strong>📐 ${{f.title}}:</strong> ${{f.caption}}</span>
                <a href="lessons/${{lesson.id}}/${{f.id}}.excalidraw" download style="font-family:var(--mono);">⬇ .excalidraw</a>
              </div>
            </div>
          `;
        }}
        return `
          <article class="chapter-card">
            <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:0.5rem;">
              <span class="chapter-number">CHAPTER 0${{idx + 1}}</span>
              <span class="tag tag-amber">${{sec.badge || ''}}</span>
            </div>
            <h3 class="chapter-heading">${{sec.heading}}</h3>
            <div class="chapter-prose">${{formatSimpleMarkdown(sec.body_md)}}</div>
            ${{figHtml}}
          </article>
        `;
      }}).join("");

      const jargonHtml = (lesson.jargon_decoder || []).map(j => `
        <div class="spine-card">
          <div style="font-family:var(--serif);font-weight:800;font-size:1.05rem;color:var(--terracotta);margin-bottom:0.25rem;">${{j.term}}</div>
          <div style="font-size:0.88rem;color:var(--ink);margin-bottom:0.35rem;"><strong>In plain words:</strong> ${{j.plain_words}}</div>
          <div style="font-size:0.78rem;color:var(--muted);font-family:var(--mono);">Why you care: ${{j.why_you_care}}</div>
        </div>
      `).join("");

      document.getElementById("bk-pane-story").innerHTML = `
        <div style="background:var(--paper-warm);border:2.5px solid var(--ink);box-shadow:0 5px 0 var(--ink);border-radius:16px;padding:1.25rem 1.5rem;margin-bottom:1.5rem;">
          <div style="font-family:var(--serif);font-size:1.25rem;font-style:italic;color:var(--terracotta);margin-bottom:0.35rem;">
            “${{lesson.question}}”
          </div>
          <div style="font-size:1rem;color:var(--ink);">
            <strong>The One-Line Picture:</strong> ${{lesson.one_line}}
          </div>
        </div>

        ${{buildInteractivePlayground(lesson.id)}}

        ${{chaptersHtml}}

        <h3 style="font-family:var(--serif);font-size:1.35rem;margin:2rem 0 0.5rem;">Plain-English Jargon Decoder</h3>
        <div class="spine-grid">${{jargonHtml}}</div>

        <h3 style="font-family:var(--serif);font-size:1.35rem;margin:2rem 0 0.5rem;">The 4-Beat Pocket Summary</h3>
        <div class="spine-grid">
          <div class="spine-card"><div class="spine-label">1. The Surprise</div><div style="font-size:0.9rem;">${{sp.surprise}}</div></div>
          <div class="spine-card"><div class="spine-label">2. What Breaks</div><div style="font-size:0.9rem;">${{sp.broken}}</div></div>
          <div class="spine-card"><div class="spine-label">3. The Turn</div><div style="font-size:0.9rem;">${{sp.turn}}</div></div>
          <div class="spine-card"><div class="spine-label">4. Honest Limit</div><div style="font-size:0.9rem;">${{sp.honest_limit}}</div></div>
        </div>

        <div style="text-align:center;margin-top:1.75rem;">
          <button class="btn btn-primary" style="font-size:0.95rem;padding:0.7rem 1.5rem;" onclick="switchBookTab('gate')">
            🚧 Ready? Take the 3-Question Checkpoint Gate Test →
          </button>
        </div>
      `;

      // TAB 2: RUNNABLE PYTHON LAB
      const lab = lesson.lab;
      const accHtml = (lab.acceptance || []).map(a => `
        <div class="spine-card" style="border-left:5px solid var(--meadow);">
          <div class="spine-label" style="color:var(--meadow);">✓ VERIFIED ACCEPTANCE CHECK</div>
          <div style="font-weight:700;font-size:0.9rem;margin-bottom:0.25rem;">${{a.criterion}}</div>
          <div style="font-family:var(--mono);font-size:0.76rem;color:var(--muted);">Proof: ${{a.evidence}}</div>
        </div>
      `).join("");

      document.getElementById("bk-pane-lab").innerHTML = `
        <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:0.75rem;margin-bottom:1rem;">
          <div>
            <div class="spine-label">PURE PYTHON HANDS-ON LAB (ZERO API KEYS)</div>
            <h3 style="margin:0.2rem 0;font-family:var(--serif);font-size:1.45rem;">${{lab.title}}</h3>
          </div>
          <a class="btn btn-primary" href="lessons/${{lesson.id}}/${{lab.code_file}}" download>⬇ Download ${{lab.code_file}}</a>
        </div>
        <p style="font-size:0.95rem;color:var(--ink-soft);">${{lab.goal}}</p>
        <div class="spine-grid">${{accHtml}}</div>
        <h4 style="font-family:var(--mono);font-size:0.82rem;color:var(--meadow);margin-top:1.5rem;">REAL VERIFIED TERMINAL OUTPUT (EXIT CODE 0)</h4>
        <pre><code>${{lab.real_output}}</code></pre>
        <h4 style="font-family:var(--mono);font-size:0.82rem;color:var(--terracotta);margin-top:1.5rem;">COMPLETE SOURCE CODE (${{lab.code_file}})</h4>
        <pre><code>${{(lesson.code_text || "").replace(/</g, "&lt;")}}</code></pre>
      `;

      // TAB 3: GATE TEST
      const questions = lesson.gate_challenge || [];
      const qHtml = questions.map((qObj, qIdx) => {{
        const opts = qObj.options.map((opt, oIdx) => `
          <button class="quiz-option" id="q-${{qIdx}}-opt-${{oIdx}}" onclick="selectQuizAnswer(${{qIdx}}, ${{oIdx}})">
            ${{opt}}
          </button>
        `).join("");
        return `
          <div class="chapter-card" style="padding:1.2rem 1.4rem;margin-bottom:1rem;">
            <div style="font-weight:800;font-size:0.98rem;margin-bottom:0.75rem;">${{qObj.q}}</div>
            ${{opts}}
            <div id="q-${{qIdx}}-feedback" style="display:none;margin-top:0.55rem;font-size:0.86rem;font-weight:600;padding:0.6rem 0.85rem;border-radius:8px;"></div>
          </div>
        `;
      }}).join("");

      document.getElementById("bk-pane-gate").innerHTML = `
        <div class="playground-box" style="margin-bottom:1.25rem;">
          <div class="spine-label">🚧 CAMPUS CHECKPOINT GATE TEST</div>
          <h3 style="margin:0.2rem 0 0.35rem;font-family:var(--serif);font-size:1.35rem;">
            Answer All 3 Questions to Lift the Barrier & Unlock the Next Campus Landmark
          </h3>
          <p style="margin:0;font-size:0.9rem;color:var(--ink-soft);">
            Every answer comes straight from the chapters and the Python lab output you just explored.
          </p>
        </div>
        ${{qHtml}}
        <div id="gate-success-banner" style="margin-top:1rem;"></div>
      `;

      // TAB 4: SHARE STUDIO
      const sh = lesson.shareable;
      const tweetsHtml = (sh.x_thread || []).map(t => `
        <div class="chapter-card" style="padding:1rem 1.25rem;margin-bottom:0.75rem;display:flex;justify-content:space-between;gap:1rem;align-items:flex-start;">
          <div style="white-space:pre-line;font-size:0.92rem;">${{t}}</div>
          <button class="btn" onclick="navigator.clipboard.writeText(this.previousElementSibling.innerText);this.innerText='Copied!'">Copy</button>
        </div>
      `).join("");

      const igHtml = (sh.instagram_carousel || []).map(s => `
        <div class="ig-slide">
          <div style="font-family:var(--mono);font-size:0.72rem;font-weight:800;color:var(--terracotta);">SLIDE 0${{s.slide}} · ${{sh.notebook_shelf}}</div>
          <div>
            <h4 style="font-family:var(--serif);font-size:1.18rem;margin:0.35rem 0;color:var(--ink);">${{s.headline}}</h4>
            <p style="font-size:0.83rem;color:var(--ink-soft);margin:0;white-space:pre-line;">${{s.body}}</p>
          </div>
          <div style="font-family:var(--mono);font-size:0.68rem;color:var(--muted);border-top:1.5px solid var(--line-strong);padding-top:0.4rem;display:flex;justify-content:space-between;">
            <span>@ashwinYardi</span><span>Bits University</span>
          </div>
        </div>
      `).join("");

      document.getElementById("bk-pane-share").innerHTML = `
        <div class="playground-box">
          <div class="spine-label">🏆 SHAREABLE FIELD NOTE · ${{sh.notebook_shelf}}</div>
          <h3 style="font-family:var(--serif);font-size:1.5rem;margin:0.25rem 0;">${{lesson.title}}</h3>
          <p style="font-family:var(--serif);font-style:italic;font-size:1.15rem;color:var(--terracotta);margin:0.5rem 0 0.85rem;">
            “${{sh.the_turn}}”
          </p>
          <div style="font-size:0.88rem;color:var(--ink-soft);margin-bottom:0.95rem;">
            <strong>60-Second Reel / Short Hook:</strong> ${{sh.reel_hook}}
          </div>
          <div style="display:flex;gap:0.65rem;flex-wrap:wrap;">
            <button class="btn btn-primary" onclick="copyFullXThread()">📋 Copy Complete X Thread (${{sh.x_thread.length}} posts)</button>
            <button class="btn" onclick="copyTurnQuote()">📋 Copy 'The Turn' Quote</button>
          </div>
        </div>
        <h3 style="font-family:var(--serif);">Ready-to-Post X Thread</h3>
        ${{tweetsHtml}}
        <h3 style="font-family:var(--serif);margin-top:2rem;">4:5 Instagram Carousel Deck</h3>
        <div class="ig-deck">${{igHtml}}</div>
      `;

      // Initialize interactive playground defaults
      if (lesson.id === "l0-what-is-an-llm") updateL0Sim();
      if (lesson.id === "l0-tokens") inspectTokenPreset("strawberry");
      if (lesson.id === "l0-embeddings") inspectEmbeddingItem("filter_coffee");
      if (lesson.id === "l0-context-window") inspectTrayStep(1);
    }}

    function renderSyllabusPreviewBook(mod, unlocked, cleared) {{
      if (!mod) return;
      document.getElementById("bk-pane-story").innerHTML = `
        <div class="chapter-card">
          <div class="chapter-number">CURRICULUM MODULE SPECIFICATION · RUNG ${{mod.level}}</div>
          <h3 class="chapter-heading">${{mod.title}}</h3>
          <p style="font-family:var(--serif);font-style:italic;font-size:1.15rem;color:var(--terracotta);">“${{mod.question}}”</p>
          <p><strong>What you can do after clearing this room:</strong> ${{mod.can}}</p>
          <p><strong>Hands-on Lab Blueprint:</strong> ${{mod.exercise}}</p>
          <p style="font-family:var(--mono);font-size:0.82rem;color:var(--muted);">Jargon decoded in this room: ${{(mod.jargon || []).join(", ")}}</p>
        </div>
      `;
      document.getElementById("bk-pane-lab").innerHTML = `<div class="chapter-card"><p>Lab specification: ${{mod.exercise}}</p></div>`;
      document.getElementById("bk-pane-gate").innerHTML = `<div class="chapter-card"><p>Clear the 4 outdoor Rung 0 campus checkpoints first to unlock this hall classroom!</p></div>`;
      document.getElementById("bk-pane-share").innerHTML = `<div class="chapter-card"><p>Share cards mint as soon as this classroom's lab is completed.</p></div>`;
    }}

    // =========================================================================
    // 4 LIVE INTERACTIVE MECHANISM PLAYGROUNDS
    // =========================================================================
    const L0_LOGITS = {{
      "the server": {{"crashed": 3.2, "responded": 2.9, "timed": 2.4, "melted": 0.4, "danced": -1.5}},
      "server crashed": {{"because": 3.6, "after": 2.5, "at": 1.8, "quietly": 0.9}},
      "server responded": {{"in": 3.4, "with": 2.8, "after": 1.7, "slowly": 1.1}},
      "server timed": {{"out": 4.5, "at": 1.1, "twice": 0.8}}
    }};
    let simL0Words = ["the", "server"];

    function updateL0Sim() {{
      const slider = document.getElementById("sim-l0-temp");
      if (!slider) return;
      const temp = parseFloat(slider.value);
      document.getElementById("sim-l0-temp-val").innerText = temp.toFixed(1);
      const key = simL0Words.slice(-2).join(" ");
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
      const barsEl = document.getElementById("sim-l0-bars");
      barsEl.innerHTML = Object.entries(probs).sort((a, b) => b[1] - a[1]).map(([tok, p]) => {{
        const pct = (p * 100).toFixed(1);
        return `<div style="display:grid;grid-template-columns:105px 80px 1fr 62px;gap:0.6rem;align-items:center;font-family:var(--mono);font-size:0.81rem;margin-bottom:0.35rem;">
          <strong>${{tok}}</strong>
          <span style="color:var(--muted);">score ${{logits[tok].toFixed(1)}}</span>
          <div style="background:#fffdf8;height:15px;border-radius:6px;overflow:hidden;border:1.5px solid var(--ink);">
            <div style="background:var(--terracotta);height:100%;width:${{pct}}%;"></div>
          </div>
          <span style="text-align:right;font-weight:700;">${{pct}}%</span>
        </div>`;
      }}).join("");
      document.getElementById("sim-l0-sentence").innerText = simL0Words.join(" ");
    }}

    function rollL0NextWord() {{
      const slider = document.getElementById("sim-l0-temp");
      const temp = parseFloat(slider.value);
      const key = simL0Words.slice(-2).join(" ");
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
      simL0Words.push(pick);
      updateL0Sim();
    }}

    function resetL0Sim() {{
      simL0Words = ["the", "server"];
      updateL0Sim();
    }}

    const TOKEN_PRESETS = {{
      "strawberry": {{
        pieces: [["str", 496], ["aw", 675], ["berry", 15717]],
        note: "10 letters → 3 barcodes (0.30 tokens/char). Look at barcode #15717 ('berry'): two 'r' letters are locked inside a single number!"
      }},
      "s t r a w b e r r y": {{
        pieces: [["s", 82], [" t", 259], [" r", 436], [" a", 264], [" w", 289], [" b", 293], [" e", 384], [" r", 436], [" r", 436], [" y", 379]],
        note: "Spaced Trick: Every letter gets its own barcode! Barcode #436 (' r') appears 3 separate times, so the AI counts 3 'r's easily."
      }},
      "The server responded in 12ms.": {{
        pieces: [["The", 791], [" server", 3585], [" responded", 31574], [" in", 304], [" ", 220], ["12", 717], ["ms", 1294], [".", 13]],
        note: "29 chars → 8 barcodes (0.28 tokens/char · 1.0x baseline cost & speed)."
      }},
      "नमस्ते दुनिया": {{
        pieces: [["न", 28001], ["म", 44102], ["स", 31902], ["्", 11904], ["त", 29501], ["े", 19822], [" द", 85120], ["ु", 22911], ["न", 28001], ["ि", 18312], ["य", 34112], ["ा", 15209]],
        note: "13 chars → 12 barcodes (0.92 tokens/char · 3.3x cost and speed penalty compared to English!)."
      }},
      "🚀🔥🤖": {{
        pieces: [["🚀", 9468], ["<0xF0>", 242], ["🔥", 9469], ["<0x9F>", 161], ["🤖", 99812], ["<0x96>", 152]],
        note: "3 emojis → 6 byte-fallback barcodes (2.00 tokens/char · 7.1x multiplier!)."
      }}
    }};

    function inspectTokenPreset(key) {{
      const preset = TOKEN_PRESETS[key];
      if (!preset) return;
      const chipsEl = document.getElementById("sim-tok-chips");
      if (!chipsEl) return;
      const colors = ["#d94e1f", "#0284c7", "#15803d", "#7e22ce", "#b45309"];
      chipsEl.innerHTML = preset.pieces.map(([txt, id], i) => {{
        const c = colors[i % colors.length];
        return `<div style="background:#fffdf8;border:2.5px solid ${{c}};border-radius:10px;padding:0.35rem 0.75rem;font-family:var(--mono);font-size:0.84rem;box-shadow:0 3px 0 ${{c}};">
          <strong>"${{txt}}"</strong> <span style="color:var(--muted);font-size:0.74rem;">#${{id}}</span>
        </div>`;
      }}).join("");
      document.getElementById("sim-tok-note").innerText = preset.note;
    }}

    function inspectEmbeddingItem(key) {{
      const el = document.getElementById("sim-emb-output");
      if (!el) return;
      const notes = {{
        "filter_coffee": "masala_chai [0.95, 0.90, 0.05, 0.10] vs filter_coffee [0.90, 0.80, 0.05, 0.05]\\n→ Cosine Similarity = +0.9924 (Sitting at the exact same Cafeteria Hot-Drinks table!)",
        "iced_chai": "masala_chai [0.95, 0.90, 0.05, 0.10] vs iced_chai [0.75, 0.85, 0.05, 0.05]\\n→ Cosine Similarity = +0.9939 (THE TRAP: Even though hot & cold are opposites, they sit at the same Chai table!)",
        "samosa": "masala_chai [0.95, 0.90, 0.05, 0.10] vs samosa [0.20, 0.95, 0.05, 0.05]\\n→ Cosine Similarity = +0.7995 (Close neighbors on the Spicy Indian Snacks axis).",
        "kubernetes": "masala_chai [0.95, 0.90, 0.05, 0.10] vs kubernetes [0.05, 0.05, 0.98, 0.05]\\n→ Cosine Similarity = +0.1006 (Pointing 84° away in the Tech & Cloud corner of the cafeteria).",
        "king_math": "Vector Walk: king [0.10, 0.15, 0.05, 0.95] - man [0.10, 0.10, 0.10, 0.20] + woman [0.15, 0.15, 0.10, 0.25]\\n→ Target Vector = [0.15, 0.20, 0.05, 1.00]\\n→ Closest Neighbor = queen [0.15, 0.20, 0.05, 0.92] with Cosine Similarity +0.9854!"
      }};
      el.innerText = notes[key] || "";
    }}

    function inspectTrayStep(step) {{
      const el = document.getElementById("sim-ctx-output");
      if (!el) return;
      const steps = {{
        1: "TURN 1 (8 / 24 words on tray · 0 dropped):\\n[User: Remember secret locker code 7492 for tomorrow.]\\n→ Locker code '7492' on tray? YES ✅",
        2: "TURN 2 (16 / 24 words on tray · 0 dropped):\\n[User: Remember secret locker code 7492 for tomorrow. AI: Got it, I saved your locker code.]\\n→ Locker code '7492' on tray? YES ✅",
        3: "TURN 3 (24 / 24 words on tray · TRAY 100% FULL):\\n[User: Remember secret locker code 7492 for tomorrow. AI: Got it, I saved your locker code. User: Also pack two masala dosa boxes please.]\\n→ Locker code '7492' on tray? YES ✅ (Right on the left edge!)",
        4: "TURN 4 (34 total words → 10 oldest words DROPPED off left edge!):\\nDropped into trash: 'User: Remember secret locker code 7492 for tomorrow. AI: Got'\\nRemaining on tray: [it, I saved your locker code. User: Also pack two masala dosa boxes please. AI: Packed two masala dosa boxes for lunch today!]\\n→ Locker code '7492' on tray? NO ❌ (Vanished!)",
        5: "LOST-IN-THE-MIDDLE U-CURVE (10-Chunk Tray Recall):\\nChunk 1 (Top edge):    93.0% ███████████████████\\nChunk 3 (Upper-mid):   51.0% ██████████\\nChunk 6 (Dead middle): 38.7% ████████  <-- DANGER ZONE!\\nChunk 10 (Bottom end): 93.0% ███████████████████"
      }};
      el.innerText = steps[step] || "";
    }}

    // =========================================================================
    // GATE QUIZ VERIFICATION (LIFTS THE SECURITY BOOM BARRIER!)
    // =========================================================================
    function selectQuizAnswer(qIdx, oIdx) {{
      const lesson = SEEDED_LESSONS[state.activeStopId];
      if (!lesson || !lesson.gate_challenge) return;
      const qObj = lesson.gate_challenge[qIdx];
      state.quizAnswers[qIdx] = oIdx;

      qObj.options.forEach((_, i) => {{
        const btn = document.getElementById(`q-${{qIdx}}-opt-${{i}}`);
        btn.classList.remove("correct", "wrong");
        if (i === oIdx) {{
          btn.classList.add(oIdx === qObj.correct ? "correct" : "wrong");
        }}
      }});

      const fb = document.getElementById(`q-${{qIdx}}-feedback`);
      fb.style.display = "block";
      if (oIdx === qObj.correct) {{
        fb.style.background = "var(--meadow-soft)";
        fb.style.color = "#14532d";
        fb.innerText = "✓ Spot on! " + qObj.explain;
      }} else {{
        fb.style.background = "#fee2e2";
        fb.style.color = "#7f1d1d";
        fb.innerText = "✗ Not quite — check the story or lab output and try another choice!";
      }}

      const allCorrect = lesson.gate_challenge.every((q, idx) => state.quizAnswers[idx] === q.correct);
      const banner = document.getElementById("gate-success-banner");
      if (allCorrect) {{
        clearedIds.add(lesson.id);
        saveProgress();
        document.getElementById("bk-status-tag").innerText = "✓ CHECKPOINT CLEARED";
        document.getElementById("bk-status-tag").className = "tag tag-meadow";

        const isFirstGate = lesson.id === "l0-what-is-an-llm";
        banner.innerHTML = `
          <div class="playground-box" style="background:var(--meadow-soft);border-color:var(--meadow);margin-top:1rem;">
            <div class="spine-label" style="color:var(--meadow);">🎉 CHECKPOINT PASSED!</div>
            <h3 style="margin:0.2rem 0 0.4rem;font-family:var(--serif);font-size:1.4rem;color:#14532d;">
              ${{isFirstGate ? "🚧 Officer Rajan Lifted the Campus Boom Barrier!" : "★ You Cleared " + lesson.title + "!"}}
            </h3>
            <p style="margin:0 0 0.9rem;font-size:0.92rem;color:#14532d;">
              ${{isFirstGate
                ? "The South Entrance Security Gate is now wide open! You can walk into the Campus Parking Lot, the Chai Cafeteria, the Central Quad Fountain, and all 6 Academic Halls."
                : "Your campus progress is saved and the next stop on the Bits University map is unlocked!"}}
            </p>
            <div style="display:flex;gap:0.65rem;flex-wrap:wrap;">
              <button class="btn btn-meadow" onclick="closeBookAndWalkNext()">🚶 Walk to Next Campus Landmark →</button>
              <button class="btn" onclick="switchBookTab('share')">🏆 Grab Shareable X Thread & IG Carousel</button>
            </div>
          </div>
        `;
      }}
    }}

    function closeBookAndWalkNext() {{
      closeBookModal();
      walkToNextTarget();
    }}

    function copyFullXThread() {{
      const lesson = SEEDED_LESSONS[state.activeStopId];
      if (!lesson) return;
      navigator.clipboard.writeText((lesson.shareable.x_thread || []).join("\\n\\n"));
      alert("Complete X Thread copied to clipboard!");
    }}

    function copyTurnQuote() {{
      const lesson = SEEDED_LESSONS[state.activeStopId];
      if (!lesson) return;
      const txt = `${{lesson.title}} (${{lesson.shareable.notebook_shelf}})\\n\\n"${{lesson.shareable.the_turn}}"\\n\\nhttps://ashwinyardi.github.io/bits-course/`;
      navigator.clipboard.writeText(txt);
      alert("The Turn copied to clipboard!");
    }}

    refreshHudAndSidebar();
    requestAnimationFrame(gameFrame);
  </script>
</body>
</html>
"""


def _render_lesson_page(curriculum: dict, lesson: dict, live_ids: set[str], code_text: str) -> str:
    """Render standalone warm-paper Chapter Book page at lessons/<id>/index.html."""
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
                f'<div style="background:#fff;border:2.5px solid var(--ink);box-shadow:0 5px 0 var(--line-strong);padding:1.15rem;border-radius:14px;margin:1.35rem 0 0.4rem;">'
                f'<img src="{_esc(fid)}.svg" alt="{_esc(fobj["title"])}" style="width:100%;height:auto;display:block;" />'
                f'<div style="display:flex;justify-content:space-between;align-items:center;margin-top:0.65rem;padding-top:0.5rem;border-top:1.5px dashed var(--line-strong);font-size:0.82rem;color:var(--ink-soft);">'
                f'<span><strong>📐 {_esc(fobj["title"])}:</strong> {_esc(fobj["caption"])}</span>'
                f'<a href="{_esc(fid)}.excalidraw" download style="font-family:var(--mono);">⬇ .excalidraw</a>'
                f'</div></div>'
            )
        sections_html.append(
            f'<article style="background:var(--paper-card);border:2px solid var(--line-strong);border-radius:16px;padding:1.5rem 1.75rem;margin-bottom:1.5rem;">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.4rem;">'
            f'<span style="font-family:var(--mono);font-size:0.74rem;font-weight:800;color:var(--terracotta);">CHAPTER 0{idx}</span>'
            f'<span class="tag tag-amber">{_esc(sec.get("badge", ""))}</span>'
            f'</div>'
            f'<h2 style="margin:0.1rem 0 0.85rem;font-family:var(--serif);font-size:1.45rem;">{_esc(sec["heading"])}</h2>'
            f'<div style="font-size:1.02rem;color:var(--ink-soft);">{_md_to_html(sec["body_md"])}</div>'
            f'{fig_block}'
            f'</article>'
        )

    jargon_rows = "".join(
        f'<tr><td style="padding:0.8rem;border-bottom:1.5px solid var(--line);"><strong>{_esc(r["term"])}</strong></td>'
        f'<td style="padding:0.8rem;border-bottom:1.5px solid var(--line);">{_esc(r["plain_words"])}</td>'
        f'<td style="padding:0.8rem;border-bottom:1.5px solid var(--line);color:var(--muted);">{_esc(r["why_you_care"])}</td></tr>'
        for r in lesson.get("jargon_decoder", [])
    )

    tweets_html = "".join(
        f'<div style="background:var(--paper-card);border:2px solid var(--line-strong);border-radius:12px;padding:1rem 1.25rem;margin-bottom:0.75rem;display:flex;justify-content:space-between;gap:1rem;">'
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
  <title>{_esc(lesson["title"])} · Bits University Field Guide</title>
  <style>{SHARED_CSS}</style>
</head>
<body>
  <header class="top-nav">
    <div class="brand-cluster">
      <a class="crest-badge" href="../../index.html">← 3D CAMPUS MAP</a>
      <div>
        <div class="brand-title">{_esc(lesson["title"])}</div>
        <div class="brand-sub">BitsByBlocks AI University · Rung {lesson["level"]}: {_esc(lesson["level_name"])}</div>
      </div>
    </div>
    <div style="display:flex;gap:0.6rem;">
      <a class="btn" href="lesson.json" target="_blank">lesson.json</a>
      <a class="btn btn-primary" href="../../index.html">🎮 Walk 3D Campus & Take Gate Test</a>
    </div>
  </header>

  <main style="max-width:860px;margin:0 auto;padding:2rem 1.5rem 5rem;">
    <div style="display:flex;gap:0.5rem;flex-wrap:wrap;margin-bottom:0.75rem;">
      <span class="tag tag-terracotta">{_esc(sh["notebook_shelf"])}</span>
      <span class="tag tag-sky">Hall {lesson["level"]}: {_esc(lesson["level_name"])}</span>
      <span class="tag tag-meadow">✓ Python Lab Verified</span>
    </div>
    <h1 style="font-family:var(--serif);font-size:2.4rem;margin:0.2rem 0 0.5rem;">{_esc(lesson["title"])}</h1>
    <div style="font-family:var(--serif);font-style:italic;font-size:1.25rem;color:var(--terracotta);margin-bottom:1.25rem;">“{_esc(lesson["question"])}”</div>
    <div style="background:var(--paper-warm);border:2.5px solid var(--ink);box-shadow:0 5px 0 var(--ink);padding:1rem 1.35rem;border-radius:14px;margin-bottom:2rem;">
      <strong>In One Line:</strong> {_esc(lesson["one_line"])}
    </div>

    {"".join(sections_html)}

    <h2 style="font-family:var(--serif);margin-top:2.5rem;">Plain-English Jargon Decoder</h2>
    <table style="width:100%;border-collapse:collapse;background:var(--paper-card);border:2px solid var(--line-strong);border-radius:12px;overflow:hidden;font-size:0.92rem;">
      <thead><tr style="background:var(--paper-warm);text-align:left;"><th style="padding:0.8rem;">Term</th><th style="padding:0.8rem;">In Plain Words</th><th style="padding:0.8rem;">Why You Care</th></tr></thead>
      <tbody>{jargon_rows}</tbody>
    </table>

    <h2 style="font-family:var(--serif);margin-top:2.5rem;">Hands-On Python Lab: {_esc(lab["title"])}</h2>
    <p>{_esc(lab["goal"])}</p>
    <pre style="background:#1c1917;color:#f5f5f4;padding:1.1rem;border-radius:12px;border:2px solid var(--ink);overflow-x:auto;"><code>{_esc(lab["real_output"])}</code></pre>
    <pre style="background:#1c1917;color:#f5f5f4;padding:1.1rem;border-radius:12px;border:2px solid var(--ink);overflow-x:auto;margin-top:1rem;"><code>{_esc(code_text)}</code></pre>

    <h2 style="font-family:var(--serif);margin-top:2.5rem;">Share Studio · The Turn & X Thread</h2>
    <div style="background:var(--paper-warm);border:2.5px solid var(--ink);box-shadow:0 5px 0 var(--ink);border-radius:14px;padding:1.25rem;margin-bottom:1.25rem;">
      <div style="font-family:var(--mono);font-size:0.72rem;font-weight:800;color:var(--terracotta);">THE NOTEBOOK TURN</div>
      <div style="font-family:var(--serif);font-size:1.3rem;margin:0.35rem 0;">“{_esc(sh["the_turn"])}”</div>
      <div style="font-size:0.88rem;color:var(--ink-soft);"><strong>Reel Hook:</strong> {_esc(sh["reel_hook"])}</div>
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
    print(f"Built Bits University 3D Campus in {DIST} and {docs} with {len(lessons)} seeded lessons across {len(curriculum['modules'])} total modules.")


if __name__ == "__main__":
    build_site()
