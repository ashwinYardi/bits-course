"""Build the BitsByBlocks 3D Isometric AI University RPG & Living Story Adventure.

Produces a complete static site in `dist/` and `docs/`:
- `index.html` — Full-Viewport 3D Isometric University World with:
  * High-DPI Retina 3D architectural rendering (zero blurry/overlapping canvas text)
  * HTML DOM 3D-projected floating pins & proximity action buttons ("👋 Talk to Officer Rajan [E]")
  * Dean Andrej Karpathy Hologram Arrival Cutscene & Lore (why this living, self-expanding AI University exists)
  * Branching RPG Typewriter Dialogue Stage when approaching NPCs ("I already know this — quiz me!" vs "Wait, teach me the secret first!")
  * Story-first Illustrated Field Guide Drawer (clean, breathable narrative flow — no wall of nested boxes)
- `lessons/<id>/index.html` — Standalone Illustrated Field Guide page for each module.
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
            "explain": "In our Python lab, after regex pre-tokenization, just 8 BPE merge rounds shrunk 42 raw byte blocks down to 14 chunks (33.3% of the original length)!"
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
                "masala_chai & filter_coffee scored +0.9858 (9.7° apart — same hot-drink table), while masala_chai & kubernetes scored +0.0322 (88.2° — nearly perpendicular).",
                "Both pairs scored 0.5000.",
                "masala_chai & kubernetes scored +0.9858 because developers drink chai while coding."
            ],
            "correct": 0,
            "explain": "Cosine similarity measures the angle between two coordinate arrows: +0.9858 (9.7°) points almost the exact same way, while +0.0322 (88.2°) is nearly orthogonal."
        },
        {
            "q": "3. When we ran vector arithmetic `king - man + woman` in our lab, which word landed at the closest table (and what is the Antonym Trap with cosine similarity)?",
            "options": [
                "It landed on 'queen' (+1.0000 exact direction match), and the trap is that opposites like 'masala_chai' and 'iced_chai' still score +0.8234 (34.6°) because they share the same drink context!",
                "It landed on 'kubernetes', and cosine similarity never makes mistakes.",
                "You cannot add or subtract word coordinates."
            ],
            "correct": 0,
            "explain": "Subtracting 'man' and adding 'woman' walks cleanly across the gender axis to 'queen' (+1.0000), while hot and cold drinks still cluster at +0.8234 because distributional embeddings group co-occurring topics — even opposites."
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
@import url('https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible:ital,wght@0,400;0,700;1,400&family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,700;12..96,800&family=IBM+Plex+Mono:wght@400;600;700&display=swap');

:root {
  /* Better-Colors Primitive Ramps (Neutral Slate-Mist, Terracotta Accent, Pine Status) */
  --slate-50: #f6f8f7;
  --slate-100: #ebf0ed;
  --slate-200: #d8e1dc;
  --slate-300: #b8c6be;
  --slate-600: #4b5b53;
  --slate-700: #2e3b34;
  --slate-900: #141d18;
  --clay-100: #faeae4;
  --clay-600: #a93b1f;
  --clay-700: #882d16;
  --pine-100: #e6f4ec;
  --pine-700: #1f6a44;

  /* Semantic Role Tokens */
  --paper: var(--slate-50);
  --paper-card: #ffffff;
  --paper-warm: var(--slate-100);
  --paper-deep: var(--slate-200);
  --ink: var(--slate-900);
  --ink-soft: var(--slate-700);
  --muted: var(--slate-600);
  --line: var(--slate-200);
  --line-strong: var(--slate-300);
  --color-accent-solid: var(--clay-600);
  --color-accent-hover: var(--clay-700);
  --color-accent-soft: var(--clay-100);
  --color-status-open: var(--pine-700);
  --color-status-open-soft: var(--pine-100);
  --terracotta: var(--color-accent-solid);
  --terracotta-soft: var(--color-accent-soft);
  --amber: #8a5a18;
  --amber-soft: #f7eedc;
  --meadow: var(--color-status-open);
  --meadow-soft: var(--color-status-open-soft);
  --sky: #335c73;
  --sky-soft: #e6eff4;
  --berry: #5c4d6b;
  --berry-soft: #efebf4;
  --shadow-ring: 0 0 0 1px rgba(20, 29, 24, 0.08), 0 4px 10px -2px rgba(20, 29, 24, 0.10), 0 12px 24px -6px rgba(20, 29, 24, 0.08);
  --shadow-ring-sm: 0 0 0 1px rgba(20, 29, 24, 0.09), 0 2px 6px -1px rgba(20, 29, 24, 0.08);
  --sans: 'Atkinson Hyperlegible', -apple-system, BlinkMacSystemFont, sans-serif;
  --serif: 'Bricolage Grotesque', Georgia, serif;
  --mono: 'IBM Plex Mono', monospace;
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

a { color: var(--terracotta); text-decoration: none; font-weight: 700; }
a:hover { text-decoration: underline; }

.top-nav {
  position: sticky;
  top: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.65rem 1.4rem;
  background: rgba(242, 247, 244, 0.95);
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
  border: 2px solid #7c2d12;
  box-shadow: 0 2px 0 #7c2d12;
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
  font-weight: 700;
}

.nav-pills {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  flex-wrap: wrap;
}

.stat-chip {
  background: var(--paper-card);
  border: 2px solid var(--line-strong);
  padding: 0.28rem 0.75rem;
  border-radius: 999px;
  font-family: var(--mono);
  font-size: 0.78rem;
  font-weight: 700;
  color: var(--ink-soft);
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
}

.btn {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  background: var(--paper-card);
  color: var(--ink);
  border: 2px solid var(--ink);
  padding: 0.5rem 1rem;
  border-radius: 10px;
  font-size: 0.85rem;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.14s ease;
  font-family: var(--sans);
  box-shadow: 0 2px 0 var(--ink);
}

.btn:hover {
  transform: translateY(-1px);
  background: var(--paper-warm);
  text-decoration: none;
}

.btn-primary {
  background: var(--terracotta);
  color: #ffffff;
  border-color: #7c2d12;
  box-shadow: 0 3px 0 #7c2d12;
}

.btn-primary:hover {
  background: #7c2d12;
  color: #ffffff;
}

.btn-meadow {
  background: var(--meadow);
  color: #ffffff;
  border-color: #052e16;
  box-shadow: 0 3px 0 #052e16;
}

.btn-meadow:hover {
  background: #166534;
  color: #ffffff;
}

.tag {
  font-family: var(--mono);
  font-size: 0.78rem;
  font-weight: 700;
  padding: 0.2rem 0.65rem;
  border-radius: 999px;
  background: var(--paper-warm);
  border: 1.5px solid var(--line-strong);
  color: var(--ink-soft);
}

.tag-terracotta { background: var(--terracotta-soft); color: var(--terracotta); border-color: #fca5a5; }
.tag-meadow { background: var(--meadow-soft); color: var(--meadow); border-color: #86efac; }
.tag-sky { background: var(--sky-soft); color: var(--sky); border-color: #7dd3fc; }
.tag-amber { background: var(--amber-soft); color: #78350f; border-color: #fcd34d; }
"""


def _render_university_index(curriculum: dict, lessons: dict[str, dict], code_by_id: dict[str, str]) -> str:
    """Render the Full-Screen 3D Isometric AI University Adventure with Zero Top Navbar, Thin Floating Pills & 3D Karpathy Calls."""
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
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
  <title>BitsByBlocks AI University · The Living 3D AI RPG</title>
  <style>
    {SHARED_CSS}
    html, body {{
      margin: 0;
      padding: 0;
      width: 100%;
      height: 100dvh;
      overflow: hidden;
      -webkit-font-smoothing: antialiased;
      -moz-osx-font-smoothing: grayscale;
    }}
    /* FULL-BLEED 100DVH 3D WORLD STAGE (NO TOP NAVBAR BAR!) */
    .world-viewport {{
      position: fixed;
      inset: 0;
      width: 100%;
      height: 100dvh;
      background: #dce8ee;
      overflow: hidden;
      user-select: none;
    }}
    #campus-canvas {{
      width: 100%;
      height: 100%;
      display: block;
      cursor: pointer;
    }}

    /* JAKUB KREHEL STAGED MOTION & CONCENTRIC SURFACES */
    @keyframes stageEnter {{
      from {{
        opacity: 0;
        transform: translateY(10px);
        filter: blur(4px);
      }}
      to {{
        opacity: 1;
        transform: translateY(0);
        filter: blur(0px);
      }}
    }}
    @media (prefers-reduced-motion: reduce) {{
      @keyframes stageEnter {{
        from {{ opacity: 0; }}
        to {{ opacity: 1; }}
      }}
    }}

    /* THIN MINIMAL FLOATING TOP INDICATORS (ZERO NAVBAR BACKGROUND BAR!) */
    .hud-top-bar {{
      position: absolute;
      top: 0.75rem;
      left: 1rem;
      right: 1rem;
      z-index: 40;
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      pointer-events: none;
      gap: 0.75rem;
      flex-wrap: wrap;
    }}
    .hud-left-cluster, .hud-right-cluster {{
      display: flex;
      align-items: center;
      gap: 0.45rem;
      flex-wrap: wrap;
      pointer-events: auto;
    }}
    .thin-pill {{
      display: inline-flex;
      align-items: center;
      gap: 0.38rem;
      background: rgba(255, 255, 255, 0.94);
      color: var(--ink);
      border: 1px solid rgba(20, 29, 24, 0.14);
      border-radius: 999px;
      min-height: 32px;
      padding: 0.34rem 0.76rem;
      font-family: var(--mono);
      font-size: 0.76rem;
      line-height: 1.2;
      font-weight: 700;
      font-variant-numeric: tabular-nums;
      box-shadow: var(--shadow-ring-sm);
      white-space: nowrap;
      animation: stageEnter 260ms cubic-bezier(0.22, 1, 0.36, 1) both;
    }}
    .thin-pill-brand {{
      background: var(--ink);
      color: #ffffff;
      border-color: var(--ink);
      font-family: var(--serif);
      font-weight: 800;
      letter-spacing: 0.01em;
    }}
    .thin-btn {{
      display: inline-flex;
      align-items: center;
      gap: 0.38rem;
      background: rgba(255, 255, 255, 0.96);
      color: var(--ink);
      border: 1px solid rgba(20, 29, 24, 0.16);
      border-radius: 999px;
      min-height: 32px;
      padding: 0.34rem 0.76rem 0.34rem 0.84rem;
      font-family: var(--sans);
      font-size: 0.78rem;
      line-height: 1.2;
      font-weight: 700;
      font-variant-numeric: tabular-nums;
      cursor: pointer;
      box-shadow: var(--shadow-ring-sm);
      transition: transform 140ms cubic-bezier(0.22, 1, 0.36, 1), background-color 140ms ease-out;
      animation: stageEnter 260ms cubic-bezier(0.22, 1, 0.36, 1) both;
    }}
    @media (hover: hover) {{
      .thin-btn:hover {{
        background: var(--paper-warm);
        transform: translateY(-1px);
      }}
    }}
    .thin-btn:active {{
      transform: scale(0.98) translateY(1px);
    }}
    /* BETTER-COLORS: Fill exactly ONE primary action per view */
    .thin-btn-primary {{
      background: var(--color-accent-solid);
      color: #ffffff;
      border-color: var(--color-accent-hover);
      box-shadow: 0 0 0 1px rgba(136, 45, 22, 0.22), 0 4px 12px -2px rgba(20, 29, 24, 0.18);
    }}
    @media (hover: hover) {{
      .thin-btn-primary:hover {{
        background: var(--color-accent-hover);
        color: #ffffff;
      }}
    }}
    .thin-btn-meadow {{
      background: var(--color-accent-solid);
      color: #ffffff;
      border-color: var(--color-accent-hover);
      box-shadow: 0 0 0 1px rgba(136, 45, 22, 0.22), 0 4px 12px -2px rgba(20, 29, 24, 0.18);
    }}
    @media (hover: hover) {{
      .thin-btn-meadow:hover {{
        background: var(--color-accent-hover);
        color: #ffffff;
      }}
    }}

    /* COMPACT FLOATING MISSION STRIP (TUCKED IN TOP-LEFT SKY SAFE ZONE) */
    .quest-strip {{
      position: absolute;
      top: 3.4rem;
      left: 1rem;
      z-index: 30;
      background: rgba(255, 255, 255, 0.94);
      border: 1px solid rgba(20, 29, 24, 0.14);
      border-radius: 12px;
      padding: 0.36rem 0.78rem;
      box-shadow: var(--shadow-ring-sm);
      max-width: 340px;
      pointer-events: auto;
      animation: stageEnter 300ms 80ms cubic-bezier(0.22, 1, 0.36, 1) both;
    }}
    .quest-kicker {{
      font-family: var(--mono);
      font-size: 0.76rem;
      font-weight: 700;
      color: var(--color-accent-solid);
      text-transform: uppercase;
      letter-spacing: 0.04em;
      font-variant-numeric: tabular-nums;
    }}
    .quest-headline {{
      font-family: var(--serif);
      font-weight: 800;
      font-size: 0.88rem;
      color: var(--ink);
      line-height: 1.35;
      margin: 0.06rem 0 0;
      text-wrap: balance;
    }}

    /* 3D KARPATHY INCOMING CALL COMMUNICATOR (ANCHORED BOTTOM-LEFT OPEN LAWN — ZERO BUILDING OVERLAP!) */
    .karpathy-call-toast {{
      position: absolute;
      bottom: 0.85rem;
      left: 1rem;
      z-index: 65;
      width: 344px;
      background: #ffffff;
      border: 1px solid rgba(20, 29, 24, 0.14);
      border-radius: 18px; /* outerRadius = innerRadius(12px) + padding(6px) */
      padding: 6px;
      box-shadow: var(--shadow-ring);
      transform-origin: bottom left;
      display: none;
      animation: stageEnter 280ms cubic-bezier(0.22, 1, 0.36, 1) both;
    }}
    .karpathy-call-toast.open {{
      display: block;
    }}
    .karpathy-call-inner {{
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 0.52rem 0.66rem;
    }}
    .karpathy-call-top {{
      display: flex;
      align-items: center;
      gap: 0.6rem;
    }}
    #karpathy-avatar-canvas {{
      width: 46px;
      height: 46px;
      border-radius: 10px;
      background: #e6eff4;
      border: 1px solid var(--line-strong);
      flex-shrink: 0;
    }}
    .call-wave {{
      display: inline-flex;
      align-items: center;
      gap: 2px;
      height: 12px;
    }}
    .call-wave span {{
      display: inline-block;
      width: 2.5px;
      height: 10px;
      background: var(--color-status-open);
      border-radius: 2px;
      animation: wavePulse 0.8s infinite ease-in-out;
    }}
    .call-wave span:nth-child(2) {{ animation-delay: 0.15s; height: 12px; }}
    .call-wave span:nth-child(3) {{ animation-delay: 0.3s; height: 7px; }}
    .call-wave span:nth-child(4) {{ animation-delay: 0.45s; height: 11px; }}
    @keyframes wavePulse {{
      0%, 100% {{ transform: scaleY(0.45); }}
      50% {{ transform: scaleY(1); }}
    }}

    /* CRISP HTML 3D-PROJECTED FLOATING PINS (ZERO OVERLAP, REFINED RING SHADOWS) */
    .pins-layer {{
      position: absolute;
      inset: 0;
      pointer-events: none;
      overflow: hidden;
    }}
    .world-pin {{
      position: absolute;
      transform: translate(-50%, -100%);
      pointer-events: auto;
      background: rgba(255, 255, 255, 0.95);
      border: 1px solid rgba(20, 29, 24, 0.16);
      border-radius: 999px;
      padding: 0.18rem 0.56rem 0.18rem 0.24rem;
      box-shadow: var(--shadow-ring-sm);
      cursor: pointer;
      transition: transform 140ms cubic-bezier(0.22, 1, 0.36, 1), opacity 140ms ease-out, background-color 140ms ease-out;
      display: flex;
      align-items: center;
      gap: 0.34rem;
      white-space: nowrap;
      font-variant-numeric: tabular-nums;
    }}
    .world-pin.pin-hidden-by-prox {{
      opacity: 0;
      pointer-events: none;
    }}
    @media (hover: hover) {{
      .world-pin:hover {{
        transform: translate(-50%, -106%) scale(1.03);
        background: #ffffff;
      }}
    }}
    .world-pin.pin-active {{
      border-color: var(--color-accent-solid);
      background: #ffffff;
      box-shadow: 0 0 0 1px var(--color-accent-solid), 0 6px 16px -4px rgba(20, 29, 24, 0.16);
    }}
    .world-pin.pin-cleared {{
      border-color: var(--color-status-open);
      background: var(--color-status-open-soft);
    }}
    .world-pin.pin-locked {{
      background: rgba(246, 248, 247, 0.94);
    }}
    .pin-badge {{
      font-family: var(--mono);
      font-size: 0.76rem;
      font-weight: 700;
      padding: 0.06rem 0.38rem;
      border-radius: 999px;
      background: var(--color-accent-solid);
      color: #ffffff;
    }}
    .world-pin.pin-cleared .pin-badge {{
      background: var(--color-status-open);
    }}
    .world-pin.pin-locked .pin-badge {{
      background: var(--muted);
    }}
    .world-pin.pin-hall .pin-badge {{
      background: var(--ink-soft);
    }}
    .pin-label {{
      font-family: var(--serif);
      font-weight: 800;
      font-size: 0.78rem;
      color: var(--ink);
    }}

    /* FLOATING PROXIMITY ACTION PROMPT (REPLACES NEARBY PIN — ZERO COLLISION!) */
    .proximity-action-btn {{
      position: absolute;
      transform: translate(-50%, -100%);
      pointer-events: auto;
      background: var(--color-accent-solid);
      color: #ffffff;
      border: 1.5px solid #ffffff;
      border-radius: 999px;
      padding: 0.38rem 0.88rem;
      font-family: var(--serif);
      font-size: 0.84rem;
      font-weight: 800;
      box-shadow: 0 0 0 1px rgba(136, 45, 22, 0.3), 0 8px 20px -4px rgba(20, 29, 24, 0.28);
      cursor: pointer;
      display: none;
      align-items: center;
      gap: 0.38rem;
      white-space: nowrap;
      z-index: 35;
      animation: pulseBounce 1.5s infinite ease-in-out;
    }}
    @keyframes pulseBounce {{
      0%, 100% {{ transform: translate(-50%, -100%); }}
      50% {{ transform: translate(-50%, -108%); }}
    }}

    /* THIN BOTTOM CONTROLS HINT PILL (SHIFTED RIGHT OF BOTTOM-LEFT CALL TOAST ON NARROWER SCREENS) */
    .controls-pill {{
      position: absolute;
      bottom: 0.85rem;
      left: 52%;
      transform: translateX(-50%);
      z-index: 25;
      background: rgba(255, 255, 255, 0.94);
      border: 1px solid rgba(20, 29, 24, 0.14);
      border-radius: 999px;
      padding: 0.26rem 0.82rem;
      font-size: 0.76rem;
      font-weight: 700;
      color: var(--ink);
      box-shadow: var(--shadow-ring-sm);
      display: flex;
      align-items: center;
      gap: 0.55rem;
      white-space: nowrap;
    }}
    .kbd {{
      background: var(--paper-warm);
      border: 1px solid var(--line-strong);
      border-radius: 5px;
      padding: 0.04rem 0.34rem;
      font-family: var(--mono);
      font-size: 0.76rem;
    }}

    /* RPG TYPEWRITER DIALOGUE STAGE (With Live 3D Character Caricature Canvas!) */
    .rpg-dialogue-backdrop {{
      position: absolute;
      inset: 0;
      z-index: 80;
      background: rgba(17, 28, 22, 0.26);
      display: none;
      align-items: flex-end;
      justify-content: center;
      padding: 1.25rem;
    }}
    .rpg-dialogue-backdrop.open {{
      display: flex;
    }}
    .rpg-dialogue-stage {{
      width: 100%;
      max-width: 850px;
      background: #ffffff;
      border: 2.5px solid var(--ink);
      border-radius: 22px; /* outerRadius = 14px + 8px */
      box-shadow: var(--shadow-ring), 0 20px 48px rgba(20, 29, 24, 0.22);
      padding: 1.15rem 1.35rem;
      display: grid;
      grid-template-columns: 96px 1fr;
      gap: 1.15rem;
      align-items: start;
      position: relative;
      transform-origin: bottom center;
      animation: stageEnter 260ms cubic-bezier(0.22, 1, 0.36, 1) both;
    }}
    @media (max-width: 640px) {{
      .rpg-dialogue-stage {{
        grid-template-columns: 1fr;
      }}
    }}
    .rpg-portrait-wrap {{
      width: 96px;
      height: 96px;
      border-radius: 14px;
      background: var(--amber-soft);
      border: 2px solid var(--ink);
      box-shadow: 0 2px 0 var(--ink);
      overflow: hidden;
      display: flex;
      align-items: center;
      justify-content: center;
      position: relative;
    }}
    #rpg-portrait-canvas {{
      width: 96px;
      height: 96px;
      display: block;
    }}
    .rpg-speaker-bar {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 0.65rem;
      flex-wrap: wrap;
      margin-bottom: 0.3rem;
    }}
    .rpg-speaker-name {{
      font-family: var(--serif);
      font-weight: 800;
      font-size: 1.15rem;
      color: var(--ink);
    }}
    .rpg-speaker-role {{
      font-family: var(--mono);
      font-size: 0.76rem;
      font-weight: 700;
      color: var(--terracotta);
      background: var(--terracotta-soft);
      padding: 0.14rem 0.58rem;
      border-radius: 999px;
    }}
    .rpg-speech-text {{
      font-size: 1.02rem;
      color: var(--ink);
      line-height: 1.62;
      min-height: 3.8rem;
      margin-bottom: 0.85rem;
      text-wrap: pretty;
      max-width: 68ch;
    }}
    .rpg-choices {{
      display: flex;
      flex-direction: column;
      gap: 0.48rem;
    }}
    .rpg-choice-btn {{
      text-align: left;
      background: var(--paper);
      border: 2px solid var(--ink);
      border-radius: 12px;
      padding: 0.62rem 0.85rem 0.62rem 0.95rem;
      font-family: var(--sans);
      font-size: 0.92rem;
      font-weight: 700;
      color: var(--ink);
      cursor: pointer;
      transition: transform 140ms cubic-bezier(0.22, 1, 0.36, 1), background-color 140ms ease-out;
      display: flex;
      align-items: center;
      justify-content: space-between;
      box-shadow: 0 2px 0 var(--ink);
    }}
    @media (hover: hover) {{
      .rpg-choice-btn:hover {{
        background: var(--amber-soft);
        transform: translateX(3px);
      }}
    }}
    .rpg-choice-btn.choice-primary {{
      background: var(--terracotta);
      color: #ffffff;
      border-color: #7c2d12;
      box-shadow: 0 2px 0 #7c2d12;
    }}
    @media (hover: hover) {{
      .rpg-choice-btn.choice-primary:hover {{
        background: #7c2d12;
        color: #ffffff;
      }}
    }}

    /* CLEAN, EDITORIAL STORY BOOK MODAL */
    .book-modal {{
      position: fixed;
      inset: 0;
      z-index: 200;
      background: rgba(17, 28, 22, 0.54);
      backdrop-filter: blur(6px);
      display: none;
      align-items: center;
      justify-content: center;
      padding: 1.15rem;
      overscroll-behavior: contain;
    }}
    .book-modal.open {{
      display: flex;
    }}
    .book-sheet {{
      background: #ffffff;
      border: 2.5px solid var(--ink);
      box-shadow: var(--shadow-ring), 0 24px 60px rgba(20, 29, 24, 0.26);
      border-radius: 22px;
      width: 100%;
      max-width: 1020px;
      height: 90vh;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      animation: stageEnter 260ms cubic-bezier(0.22, 1, 0.36, 1) both;
    }}
    .book-header {{
      background: var(--paper);
      padding: 0.9rem 1.5rem;
      border-bottom: 2px solid var(--line);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 1rem;
      flex-wrap: wrap;
    }}
    .book-tabs {{
      display: flex;
      gap: 0.45rem;
      padding: 0.55rem 1.5rem;
      background: var(--paper-warm);
      border-bottom: 2px solid var(--line);
      overflow-x: auto;
    }}
    .book-tab {{
      background: transparent;
      border: 2px solid transparent;
      color: var(--ink-soft);
      font-family: var(--sans);
      font-size: 0.86rem;
      font-weight: 700;
      padding: 0.4rem 0.9rem;
      border-radius: 10px;
      cursor: pointer;
    }}
    .book-tab.active {{
      background: #ffffff;
      color: var(--terracotta);
      border-color: var(--ink);
      box-shadow: 0 2px 0 var(--ink);
    }}
    .book-body {{
      flex: 1;
      overflow-y: auto;
      overscroll-behavior: contain;
      padding: 2rem 2.25rem 3.5rem;
    }}
    .book-pane {{
      display: none;
      max-width: 720px;
      margin: 0 auto;
    }}
    .book-pane.active {{
      display: block;
    }}
    .story-section {{
      padding: 1.65rem 0;
      border-bottom: 2px dashed var(--line);
    }}
    .story-section:last-of-type {{
      border-bottom: none;
    }}
    .chapter-kicker {{
      font-family: var(--mono);
      font-size: 0.78rem;
      font-weight: 700;
      color: var(--terracotta);
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}
    .chapter-heading {{
      font-family: var(--serif);
      font-size: 1.6rem;
      font-weight: 800;
      line-height: 1.35;
      margin: 0.25rem 0 0.85rem;
      color: var(--ink);
      text-wrap: balance;
    }}
    .chapter-prose {{
      font-size: 1.06rem;
      color: var(--ink-soft);
      line-height: 1.75;
      text-wrap: pretty;
    }}
    .chapter-prose p {{
      margin: 0 0 1rem;
    }}
    .chapter-prose code {{
      background: var(--paper);
      padding: 0.14rem 0.42rem;
      border-radius: 6px;
      font-family: var(--mono);
      font-size: 0.88em;
      color: var(--terracotta);
      border: 1px solid var(--line-strong);
    }}
    .book-progress-track {{
      height: 4px;
      width: 100%;
      background: var(--paper-warm);
      overflow: hidden;
      flex-shrink: 0;
    }}
    .book-progress-bar {{
      height: 100%;
      width: 0%;
      background: var(--terracotta);
      transition: width 80ms linear;
    }}
    .chapter-toc {{
      display: flex;
      gap: 0.45rem;
      flex-wrap: wrap;
      margin: 0 0 1.4rem;
      padding: 0.65rem 0.8rem;
      background: var(--paper);
      border: 1.5px solid var(--line);
      border-radius: 12px;
      align-items: center;
    }}
    .toc-chip {{
      display: inline-flex;
      align-items: center;
      gap: 0.3rem;
      padding: 0.36rem 0.72rem;
      border-radius: 999px;
      border: 1.5px solid var(--line-strong);
      background: #ffffff;
      color: var(--ink-soft);
      font-family: var(--mono);
      font-size: 0.76rem;
      font-weight: 700;
      cursor: pointer;
      text-decoration: none;
      transition: border-color 120ms ease-out, color 120ms ease-out, background-color 120ms ease-out;
    }}
    @media (hover: hover) {{
      .toc-chip:hover {{
        border-color: var(--terracotta);
        color: var(--terracotta);
        background: var(--paper-warm);
      }}
    }}
    .callout-grid {{
      display: grid;
      grid-template-columns: 1fr;
      gap: 0.75rem;
      margin: 1.15rem 0 0.35rem;
    }}
    .callout-box {{
      border-radius: 12px;
      padding: 0.9rem 1.1rem;
      font-size: 0.93rem;
      line-height: 1.62;
    }}
    .callout-expert {{
      background: #f2f6f9;
      border: 1.5px solid #b4ccd9;
      color: #1c2e38;
    }}
    .callout-trap {{
      background: #fdf4ee;
      border: 1.5px solid #e2baa7;
      color: #3a1d15;
    }}
    .callout-title {{
      font-family: var(--mono);
      font-size: 0.76rem;
      font-weight: 700;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      margin-bottom: 0.32rem;
      display: flex;
      align-items: center;
      gap: 0.4rem;
    }}
    .callout-expert .callout-title {{ color: #264d60; }}
    .callout-trap .callout-title {{ color: #8c331c; }}
    .chapter-prose ul, .chapter-prose ol {{
      margin: 0.55rem 0 1rem;
      padding-left: 1.35rem;
    }}
    .chapter-prose li {{
      margin-bottom: 0.42rem;
    }}
    .sim-input {{
      flex: 1;
      min-width: 210px;
      padding: 0.48rem 0.78rem;
      border-radius: 10px;
      border: 1.5px solid var(--line-strong);
      background: #ffffff;
      color: var(--ink);
      font-family: var(--mono);
      font-size: 0.84rem;
    }}
    .sim-input:focus {{
      outline: 2px solid var(--terracotta);
      outline-offset: 1px;
    }}
    .tray-slot-grid {{
      display: flex;
      flex-wrap: wrap;
      gap: 0.35rem;
      margin-top: 0.55rem;
    }}
    .tray-word {{
      display: inline-flex;
      align-items: center;
      padding: 0.24rem 0.5rem;
      border-radius: 7px;
      font-family: var(--mono);
      font-size: 0.78rem;
      font-weight: 600;
      border: 1.5px solid var(--line-strong);
      background: #ffffff;
      color: var(--ink);
    }}
    .tray-word.secret {{
      background: #fef3c7;
      border-color: #b45309;
      color: #78350f;
      font-weight: 800;
    }}
    .tray-word.dropped {{
      background: #fee2e2;
      border-color: #dc2626;
      color: #7f1d1d;
      text-decoration: line-through;
      opacity: 0.85;
    }}
    .inline-figure {{
      background: #fbfaf7;
      border: 1.5px solid var(--line-strong);
      box-shadow: 0 6px 20px rgba(24, 34, 29, 0.06);
      border-radius: 16px;
      padding: 1.1rem;
      margin: 1.35rem 0 0.65rem;
    }}
    .playground-band {{
      background: var(--paper);
      border: 2px solid var(--ink);
      box-shadow: 0 3px 0 var(--ink), 0 10px 24px rgba(17, 28, 22, 0.08);
      border-radius: 18px;
      padding: 1.35rem 1.5rem;
      margin: 1.35rem 0 1.85rem;
    }}
    .quiz-option {{
      display: block;
      width: 100%;
      text-align: left;
      background: var(--paper);
      border: 2px solid var(--line-strong);
      color: var(--ink);
      padding: 0.85rem 1.05rem;
      border-radius: 12px;
      margin-bottom: 0.6rem;
      cursor: pointer;
      font-family: var(--sans);
      font-size: 0.95rem;
      font-weight: 700;
      transition: border-color 120ms ease-out, background-color 120ms ease-out;
    }}
    @media (hover: hover) {{
      .quiz-option:hover {{
        border-color: var(--ink);
        background: var(--paper-warm);
      }}
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
      background: #111c16;
      color: #f2f7f4;
      padding: 1.15rem 1.3rem;
      border-radius: 14px;
      border: 2px solid var(--ink);
      overflow-x: auto;
      font-family: var(--mono);
      font-size: 0.84rem;
      line-height: 1.6;
    }}
    .jargon-table {{
      width: 100%;
      border-collapse: collapse;
      margin: 1rem 0 2rem;
      font-size: 0.94rem;
    }}
    .jargon-table th, .jargon-table td {{
      padding: 0.8rem 0.95rem;
      border-bottom: 1.5px solid var(--line);
      text-align: left;
      vertical-align: top;
    }}
    .jargon-table th {{
      background: var(--paper);
      font-family: var(--mono);
      font-size: 0.78rem;
      text-transform: uppercase;
      color: var(--ink-soft);
    }}
    .ig-deck {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
      gap: 1rem;
      margin-top: 1rem;
    }}
    .ig-slide {{
      aspect-ratio: 4 / 5;
      background: var(--paper);
      border: 2px solid var(--ink);
      box-shadow: 0 3px 0 var(--ink), 0 8px 20px rgba(17,28,22,0.10);
      border-radius: 16px;
      padding: 1.1rem;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }}

    /* SLIDE-OVER SYLLABUS TELEPORTER DRAWER */
    .map-drawer-backdrop {{
      position: fixed;
      inset: 0;
      z-index: 150;
      background: rgba(17, 28, 22, 0.42);
      display: none;
      justify-content: flex-end;
      overscroll-behavior: contain;
    }}
    .map-drawer-backdrop.open {{
      display: flex;
    }}
    .map-drawer {{
      width: 100%;
      max-width: 410px;
      background: var(--paper);
      border-left: 2.5px solid var(--ink);
      height: 100%;
      padding: 1.25rem;
      overflow-y: auto;
      overscroll-behavior: contain;
      display: flex;
      flex-direction: column;
      gap: 0.7rem;
    }}
    .teleport-row {{
      background: #ffffff;
      border: 1.5px solid var(--line-strong);
      border-radius: 12px;
      padding: 0.7rem 0.9rem;
      cursor: pointer;
      transition: transform 120ms ease-out, border-color 120ms ease-out;
    }}
    @media (hover: hover) {{
      .teleport-row:hover {{
        border-color: var(--ink);
        transform: translateX(-3px);
      }}
    }}
  </style>
</head>
<body>
  <!-- FULL-BLEED 100VH 3D ISOMETRIC WORLD (NO TOP NAVBAR!) -->
  <div class="world-viewport" id="world-viewport">
    <canvas id="campus-canvas" width="1280" height="760"></canvas>

    <!-- CRISP HTML OVERLAY PINS & PROXIMITY INTERACTION BUTTON -->
    <div class="pins-layer" id="pins-layer"></div>
    <button class="proximity-action-btn" id="proximity-btn" onclick="triggerNearbyInteraction()"></button>

    <!-- THIN MINIMAL FLOATING TOP INDICATORS & BUTTONS (Zero Navbar Background!) -->
    <div class="hud-top-bar">
      <div class="hud-left-cluster">
        <span class="thin-pill thin-pill-brand">BITS UNIVERSITY · 2032</span>
        <span class="thin-pill">
          <span>🚧 Gate:</span>
          <strong id="hud-gate-state" style="color:var(--terracotta);">LOCKED</strong>
        </span>
        <span class="thin-pill">
          <span>⭐</span>
          <strong id="hud-cleared-count">0 / 49</strong>
        </span>
      </div>
      <div class="hud-right-cluster">
        <button class="thin-btn" id="btn-exit-hall" style="display:none;" onclick="switchScene('campus')">← Exit Hall</button>
        <button class="thin-btn" onclick="triggerKarpathyCall('manual')">📞 Call Karpathy (3D)</button>
        <button class="thin-btn thin-btn-meadow" onclick="walkToCurrentQuest()">🚶 Walk to Mission →</button>
        <button class="thin-btn" onclick="toggleTeleportDrawer(true)">🗺️ Map (49)</button>
      </div>
    </div>

    <!-- COMPACT FLOATING MISSION STRIP -->
    <div class="quest-strip">
      <div class="quest-kicker" id="quest-kicker">🎯 SOUTH GATE APPROACH</div>
      <div class="quest-headline" id="quest-headline">Walk up the tree-lined road toward the South Gate</div>
    </div>

    <!-- 3D KARPATHY INCOMING CALL COMMUNICATOR TOAST -->
    <div class="karpathy-call-toast" id="karpathy-call-toast">
      <div class="karpathy-call-inner">
        <div class="karpathy-call-top">
          <canvas id="karpathy-avatar-canvas" width="104" height="104"></canvas>
          <div style="flex:1;min-width:0;">
            <div style="display:flex;align-items:center;justify-content:space-between;gap:0.35rem;">
              <span style="font-family:var(--mono);font-size:0.76rem;font-weight:700;color:var(--meadow);" id="karpathy-call-status">📲 INCOMING 3D CALL</span>
              <div class="call-wave"><span></span><span></span><span></span><span></span></div>
            </div>
            <div style="font-family:var(--serif);font-weight:800;font-size:1rem;color:var(--ink);line-height:1.35;">Andrej Karpathy</div>
            <div style="font-size:0.76rem;color:var(--muted);font-weight:700;">Founder · Pocket Communicator</div>
          </div>
        </div>
        <p id="karpathy-call-preview" style="margin:0.35rem 0 0.45rem;font-size:0.8rem;color:var(--ink-soft);line-height:1.4;text-wrap:pretty;">
          “Yo Ashwin! I dropped you a pin outside our secret self-expanding AI campus. Walk right up the South Road and head inside!”
        </p>
        <div style="display:flex;gap:0.45rem;">
          <button class="thin-btn thin-btn-primary" style="flex:1;justify-content:center;" id="karpathy-call-action-btn" onclick="acceptKarpathyCall()">
            📡 Answer & Walk Up Road →
          </button>
          <button class="thin-btn" onclick="dismissKarpathyToast()">✕</button>
        </div>
      </div>
    </div>

    <!-- THIN BOTTOM CONTROLS HINT -->
    <div class="controls-pill">
      <span><span class="kbd">Click</span> ground or <span class="kbd">W</span><span class="kbd">A</span><span class="kbd">S</span><span class="kbd">D</span> / <span class="kbd">Arrows</span> to walk</span>
      <span>·</span>
      <span>Press <span class="kbd">E</span> near a character</span>
    </div>

    <!-- RPG TYPEWRITER DIALOGUE STAGE (With Live 3D Character Caricature!) -->
    <div class="rpg-dialogue-backdrop" id="rpg-dialogue-backdrop">
      <div class="rpg-dialogue-stage">
        <div class="rpg-portrait-wrap">
          <canvas id="rpg-portrait-canvas" width="192" height="192"></canvas>
        </div>
        <div>
          <div class="rpg-speaker-bar">
            <span class="rpg-speaker-name" id="rpg-speaker-name">Officer Rajan</span>
            <span class="rpg-speaker-role" id="rpg-speaker-role">CHIEF OF CAMPUS SECURITY · SOUTH GATE</span>
          </div>
          <div class="rpg-speech-text" id="rpg-speech-text"></div>
          <div class="rpg-choices" id="rpg-choices"></div>
        </div>
      </div>
    </div>
  </div>

  <!-- STORY-FIRST ILLUSTRATED CHAPTER BOOK MODAL -->
  <div class="book-modal" id="book-modal">
    <div class="book-sheet">
      <div class="book-header">
        <div>
          <div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.2rem;">
            <span class="tag tag-terracotta" id="bk-location-tag">STOP 01 · SECURITY GATE</span>
            <span class="tag tag-meadow" id="bk-status-tag">🟢 ACTIVE MISSION</span>
          </div>
          <h2 id="bk-title" style="margin:0;font-family:var(--serif);font-size:1.5rem;line-height:1.35;">What an LLM Actually Is</h2>
        </div>
        <div style="display:flex;gap:0.5rem;align-items:center;">
          <a id="bk-standalone-link" class="thin-btn" href="#" target="_blank">↗ Reader View</a>
          <button class="thin-btn" onclick="closeBookModal()">✕ Back to 3D World (Esc)</button>
        </div>
      </div>

      <div class="book-tabs">
        <button class="book-tab active" data-tab="story" onclick="switchBookTab('story')">📖 1. Illustrated Story & Playground</button>
        <button class="book-tab" data-tab="lab" onclick="switchBookTab('lab')">🧪 2. Runnable Python Lab</button>
        <button class="book-tab" data-tab="gate" onclick="switchBookTab('gate')">🚧 3. Boss Gate Check (3 Questions)</button>
        <button class="book-tab" data-tab="share" onclick="switchBookTab('share')">🏆 4. Share Studio (X & IG)</button>
      </div>

      <div class="book-progress-track"><div class="book-progress-bar" id="bk-progress-bar"></div></div>
      <div class="book-body" id="bk-body-scroll" onscroll="updateBookReadingProgress()">
        <div class="book-pane active" id="bk-pane-story"></div>
        <div class="book-pane" id="bk-pane-lab"></div>
        <div class="book-pane" id="bk-pane-gate"></div>
        <div class="book-pane" id="bk-pane-share"></div>
      </div>
    </div>
  </div>

  <!-- SLIDE-OVER FAST-TRAVEL SYLLABUS DRAWER -->
  <div class="map-drawer-backdrop" id="map-drawer-backdrop" onclick="if(event.target===this)toggleTeleportDrawer(false)">
    <aside class="map-drawer">
      <div style="display:flex;justify-content:space-between;align-items:center;">
        <div>
          <div style="font-family:var(--mono);font-size:0.76rem;font-weight:700;color:var(--terracotta);">SELF-EXPANDING CAMPUS MAP</div>
          <h3 style="margin:0.1rem 0 0;font-family:var(--serif);font-size:1.25rem;line-height:1.35;">Fast-Travel Directory</h3>
        </div>
        <button class="thin-btn" onclick="toggleTeleportDrawer(false)">✕ Close</button>
      </div>
      <p style="margin:0;font-size:0.84rem;color:var(--ink-soft);">
        This university constructs new rooms and labs automatically as frontier AI papers drop. Click any unlocked stop to walk Ashwin there!
      </p>
      <div id="teleport-list" style="display:flex;flex-direction:column;gap:0.55rem;"></div>
    </aside>
  </div>

  <script>
    const CURRICULUM = {curriculum_json};
    const SEEDED_LESSONS = {lessons_json};

    const STORAGE_KEY = "bits_uni_cleared_v5";
    const INTRO_SEEN_KEY = "bits_uni_intro_seen_v5";
    let clearedIds = new Set(JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]"));

    function saveProgress() {{
      localStorage.setItem(STORAGE_KEY, JSON.stringify([...clearedIds]));
      refreshHudAndPins();
    }}

    function isGateOpen() {{
      return clearedIds.has("l0-what-is-an-llm");
    }}

    // =========================================================================
    // 3D KARPATHY PERIODIC CALLS & WALK-UP-TO-GATE STORY FLOW
    // =========================================================================
    // Periodic calls from Andrej Karpathy at key moments in the journey!
    const KARPATHY_CALL_SCRIPTS = {{
      "arrival": {{
        status: "📲 INCOMING 3D CALL",
        preview: "“Yo Ashwin! I dropped you the secret pin to our self-expanding AI campus. Walk up the South Road and head inside!”",
        btnLabel: "🚶 Walk Up Road to Campus Gate →",
        onAccept: "walkUpToGateAndGetStopped"
      }},
      "after_l0-what-is-an-llm": {{
        status: "📲 KARPATHY CHECK-IN · GATE CLEARED!",
        preview: "“Haha, I knew Officer Rajan would ambush you at the boom barrier! Now you know the secret: an LLM is just a 1-word relay runner rolling a Temperature-weighted die. Head west to Maya's Parking Lot — she'll show you why AI can't count the r's in strawberry!”",
        btnLabel: "🅿️ Walk to Maya's Parking Lot →",
        onAccept: "walkNext"
      }},
      "after_l0-tokens": {{
        status: "📲 KARPATHY CHECK-IN · BARCODES MASTERED",
        preview: "“3.3x more tokens for Hindi than English — wild, right? Every frontier lab is fighting tokenizer efficiency right now. Next stop: grab a cup of chai with Chef Kabir on the Terrace and see how raw barcode IDs turn into 4D Meaning GPS!”",
        btnLabel: "☕ Walk to Kabir's Chai Terrace →",
        onAccept: "walkNext"
      }},
      "after_l0-embeddings": {{
        status: "📲 KARPATHY CHECK-IN · VECTORS UNLOCKED",
        preview: "“king - man + woman = queen! Once words become coordinates in meaning space, you can search all of human knowledge by flashlight angle. Walk over to Prof. Meera at the Central Quad Fountain — she's running the Amnesia Chef lunch tray experiment!”",
        btnLabel: "⛲ Walk to Meera at Quad Fountain →",
        onAccept: "walkNext"
      }},
      "after_l0-context-window": {{
        status: "📲 KARPATHY CHECK-IN · QUAD CLEARED!",
        preview: "“You survived the 24-word Lunch Tray and the Lost-in-the-Middle U-curve! The cranes on the East Lawn just finished all 6 Academic Halls (49 modules). Step inside Hall 0 whenever you're ready!”",
        btnLabel: "🏛️ Enter Academic Hall 0 →",
        onAccept: "walkNext"
      }},
      "manual": {{
        status: "📡 LIVE 3D HOLO-CALL · ANDREJ KARPATHY",
        preview: "“Hey Ashwin! Remember: every time a new paper or model architecture drops, our campus cranes construct a new room automatically. Never memorize jargon — test the toy mechanism in pure Python first!”",
        btnLabel: "🚶 Continue Active Mission →",
        onAccept: "walkNext"
      }}
    }};

    let currentKarpathyCallKey = "arrival";

    function triggerKarpathyCall(callKey) {{
      const script = KARPATHY_CALL_SCRIPTS[callKey] || KARPATHY_CALL_SCRIPTS["manual"];
      currentKarpathyCallKey = callKey;
      document.getElementById("karpathy-call-status").innerText = script.status;
      document.getElementById("karpathy-call-preview").innerText = script.preview;
      document.getElementById("karpathy-call-action-btn").innerText = script.btnLabel;
      document.getElementById("karpathy-call-toast").classList.add("open");
      state.holoRinging = true;
    }}

    function dismissKarpathyToast() {{
      document.getElementById("karpathy-call-toast").classList.remove("open");
      state.holoRinging = false;
    }}

    function acceptKarpathyCall() {{
      const script = KARPATHY_CALL_SCRIPTS[currentKarpathyCallKey] || KARPATHY_CALL_SCRIPTS["manual"];
      dismissKarpathyToast();
      if (script.onAccept === "walkUpToGateAndGetStopped") {{
        startWalkToGateAmbush();
      }} else {{
        walkToCurrentQuest();
      }}
    }}

    // Natural narrative sequence: Ashwin walks up the South Road trying to enter the Quad,
    // and Officer Rajan physically blows his whistle, drops/flashes the boom gate, and stops him!
    function startWalkToGateAmbush() {{
      localStorage.setItem(INTRO_SEEN_KEY, "1");
      state.scene = "campus";
      state.activeStopId = "l0-what-is-an-llm";
      state.guardWhistleTimer = 95;
      state.player.targetX = 610;
      state.player.targetY = 618;
      state.player.pendingCallback = () => {{
        state.guardWhistleTimer = 110;
        openNpcDialogue("l0-what-is-an-llm", 0);
      }};
      refreshHudAndPins();
    }}

    const OUTDOOR_LANDMARKS = [
      {{
        id: "l0-what-is-an-llm",
        num: "STOP 01",
        name: "Entrance Security Gate",
        shortLabel: "1. Security Gate",
        icon: "🚧",
        npcName: "Officer Rajan",
        npcRole: "CHIEF OF CAMPUS SECURITY · SOUTH GATE",
        npcStyle: "guard",
        x: 610, y: 610, interactRadius: 95,
        dialogue: [
          {{
            text: "“🚨 PEEEEEP! WHOA THERE, ASHWIN! Did Karpathy call you and tell you that you could just stroll right through my South Gate?! Not on my watch! Last week I turned away three AI VPs who thought ChatGPT has a tiny philosopher inside. Tell me: what is an LLM actually doing when it replies?”",
            choices: [
              {{ label: "🤔 Karpathy didn't warn me! Break it down for me like I'm 12.", next: 1 }},
              {{ label: "😎 It's playing a one-word relay game with a weighted die — show me your trick!", next: 1 }},
              {{ label: "⚡ I'm ready — give me the 3-Question Boom Gate Test right now!", action: "openGateQuiz" }}
            ]
          }},
          {{
            text: "“Ha! Respect for honesty! An LLM has NO master plan and NO backspace key. It scores every word in the dictionary, rolls a weighted die (controlled by Temperature & Top-P), glues that ONE winning word onto your prompt, and repeats until <|eos|>! Test my Guard Booth Simulator or pass the 3-question check to lift this barrier!”",
            choices: [
              {{ label: "📖 Open Chapter 1 & Play the Temperature + Top-P Simulator", action: "openStory" }},
              {{ label: "🚧 Take the 3-Question Boom Gate Test to Lift the Barrier", action: "openGateQuiz" }}
            ]
          }}
        ],
        clearedDialogue: {{
          text: "“🫡 Welcome back through the South Gate, Ashwin! You already passed my Security Boom Check — the barrier stays wide open for you. Want to revise Chapter 1 (Temperature, Top-P & Post-Training), re-run the Python lab, or head straight to your next campus mission?”",
          choices: [
            {{ label: "📖 Revise Chapter 1 & Temperature/Top-P Playground", action: "openStory" }},
            {{ label: "🧪 Re-open Chapter 1 Runnable Python Lab", action: "openLab" }},
            {{ label: "🔁 Practice the 3-Question Security Check Again", action: "openGateQuiz" }},
            {{ label: "🚶 Walk to Next Campus Mission", action: "nextMission" }}
          ]
        }}
      }},
      {{
        id: "l0-tokens",
        num: "STOP 02",
        name: "Campus Parking Lot",
        shortLabel: "2. Parking Lot",
        icon: "🅿️",
        npcName: "Maya",
        npcRole: "PARKING & BARCODE ENGINEER · WEST LOT",
        npcStyle: "engineer",
        x: 225, y: 445, interactRadius: 95,
        dialogue: [
          {{
            text: "“Hey Ashwin! You got Officer Rajan to lift the boom gate! Look at these 3 parked cars in my lot: [str #496], [aw #675], and [berry #15717]. Ever wondered why a billion-dollar AI embarrassed itself counting the letter 'r' in 'strawberry'?”",
            choices: [
              {{ label: "🍓 Wait — why CAN'T it count the three r's in strawberry?", next: 1 }},
              {{ label: "🇮🇳 And why does Hindi cost 3.3x more tokens than English?", next: 1 }},
              {{ label: "⚡ Take me straight to the Parking Lot Barcode Test!", action: "openGateQuiz" }}
            ]
          }},
          {{
            text: "“Because an AI never reads letters! My BPE Token Chopper runs regex pre-tokenization and glues common chunks into integer barcodes before the AI even wakes up. Two of the 'r's are sealed inside barcode #15717 ('berry')! Come try the live Barcode Chopper inside Chapter 2.”",
            choices: [
              {{ label: "📖 Open Chapter 2 & Chop Custom Text into Barcodes", action: "openStory" }},
              {{ label: "🚧 Take the 3-Question Parking Lot Gate Test", action: "openGateQuiz" }}
            ]
          }}
        ],
        clearedDialogue: {{
          text: "“Hey Ashwin! Your Parking Lot Barcode pass is already stamped ✓. Swing by anytime you want to test custom words in my live BPE Chopper, review regex pre-tokenization & the 3.3x Hindi tax, or walk over to your next stop!”",
          choices: [
            {{ label: "📖 Revise Chapter 2 & Live Barcode Chopper", action: "openStory" }},
            {{ label: "🧪 Re-open BPE Python Lab (42 → 14 tokens)", action: "openLab" }},
            {{ label: "🔁 Practice the 3-Question Barcode Check Again", action: "openGateQuiz" }},
            {{ label: "🚶 Walk to Next Campus Mission", action: "nextMission" }}
          ]
        }}
      }},
      {{
        id: "l0-embeddings",
        num: "STOP 03",
        name: "Chai & Embeddings Terrace",
        shortLabel: "3. Chai Terrace",
        icon: "☕",
        npcName: "Chef Kabir",
        npcRole: "CHAI TERRACE HOST · MEANING MAPPER",
        npcStyle: "chef",
        x: 355, y: 295, interactRadius: 95,
        dialogue: [
          {{
            text: "“Pull up a chair under the umbrella, Ashwin! In Maya's dictionary, barcode #40,000 ('coffee') sits right next to #40,001 ('coffin'). Why doesn't the AI accidentally serve you a coffin when you order filter coffee?”",
            choices: [
              {{ label: "☕ Because you trade the barcode for GPS coordinates in the Cafeteria?", next: 1 }},
              {{ label: "👑 Show me how `king - man + woman = queen` actually works in math!", next: 1 }},
              {{ label: "⚡ Jump straight to the Cafeteria Gate Test!", action: "openGateQuiz" }}
            ]
          }},
          {{
            text: "“Spot on! The moment a barcode enters the model, we trade it for an Embedding — a list of GPS coordinates on a giant Meaning Map. Here on my patio, masala_chai and filter_coffee sit just 9.7° apart (+0.9858 similarity), while Kubernetes sits 88.2° away (+0.0322)! Come explore the Vector Angle Compass.”",
            choices: [
              {{ label: "📖 Open Chapter 3 & Explore the Vector Angle Compass", action: "openStory" }},
              {{ label: "🚧 Take the 3-Question Cafeteria Gate Test", action: "openGateQuiz" }}
            ]
          }}
        ],
        clearedDialogue: {{
          text: "“Fresh cutting chai on the house, Ashwin! You already cleared the Cafeteria Meaning Map ✓. Want to spin the 2D Vector Angle Compass, revisit the Antonym Trap (+0.8234) & Hybrid Search, or head to your next mission?”",
          choices: [
            {{ label: "📖 Revise Chapter 3 & Vector Angle Compass", action: "openStory" }},
            {{ label: "🧪 Re-open 4D Embeddings Python Lab", action: "openLab" }},
            {{ label: "🔁 Practice the 3-Question Cafeteria Check Again", action: "openGateQuiz" }},
            {{ label: "🚶 Walk to Next Campus Mission", action: "nextMission" }}
          ]
        }}
      }},
      {{
        id: "l0-context-window",
        num: "STOP 04",
        name: "Central Quad Fountain",
        shortLabel: "4. Quad Fountain",
        icon: "⛲",
        npcName: "Prof. Meera",
        npcRole: "QUAD FOUNTAIN MENTOR · MEMORY ARCHITECT",
        npcStyle: "prof",
        x: 610, y: 358, interactRadius: 95,
        dialogue: [
          {{
            text: "“Listen to the fountain, Ashwin. People think when they chat with an AI for an hour, the AI is 'getting to know them.' False! The AI is an Amnesia Chef whose brain resets to zero after every single reply. All it ever sees is what fits on a fixed-size lunch tray right now!”",
            choices: [
              {{ label: "🍱 What happens when the lunch tray fills up on Turn 4?", next: 1 }},
              {{ label: "📉 Why do facts buried in the middle of a huge prompt get ignored?", next: 1 }},
              {{ label: "⚡ Take me straight to the Quad Fountain Gate Test!", action: "openGateQuiz" }}
            ]
          }},
          {{
            text: "“When the tray hits its 24-word limit, the oldest words at the left edge literally slide off into the trash — taking your Turn 1 locker code 7492 with them! Worse, even when everything fits, attention follows a U-curve: 93% recall at the edges vs 38.7% in the middle, while KV Prefix Caching saves 81% on repeated turns!”",
            choices: [
              {{ label: "📖 Open Chapter 4 & Test the Lunch Tray + KV Cache Simulator", action: "openStory" }},
              {{ label: "🚧 Take the 3-Question Quad Gate Test", action: "openGateQuiz" }}
            ]
          }}
        ],
        clearedDialogue: {{
          text: "“Great to see you back by the Quad Fountain, Ashwin! You've mastered Context Windows & KV Prefix Caching ✓. Want to revise Chapter 4, inspect the O(N²) lab output, or walk into the Academic Halls?”",
          choices: [
            {{ label: "📖 Revise Chapter 4 & Lunch Tray + KV Cache Simulator", action: "openStory" }},
            {{ label: "🧪 Re-open Context Window & KV Cache Python Lab", action: "openLab" }},
            {{ label: "🔁 Practice the 3-Question Quad Check Again", action: "openGateQuiz" }},
            {{ label: "🚶 Walk to Next Campus Mission", action: "nextMission" }}
          ]
        }}
      }}
    ];

    const ACADEMIC_HALLS = [
      {{ level: 0, code: "HALL 0", name: "Foundations", sub: "Intuition, Eval & First Call", x: 870, y: 590, w: 120, d: 64, h: 48, roof: "#a9492f", wallL: "#faf8f4", wallR: "#e9e3d8" }},
      {{ level: 1, code: "HALL 1", name: "RAG & Search", sub: "Vectors, Chunking & Search", x: 1120, y: 590, w: 120, d: 64, h: 48, roof: "#4a6477", wallL: "#faf8f4", wallR: "#e9e3d8" }},
      {{ level: 2, code: "HALL 2", name: "Attention", sub: "Transformers & KV Cache", x: 870, y: 432, w: 120, d: 64, h: 48, roof: "#496b59", wallL: "#faf8f4", wallR: "#e9e3d8" }},
      {{ level: 3, code: "HALL 3", name: "Agents Wing", sub: "Tool Loops, MCP & Memory", x: 1120, y: 432, w: 120, d: 64, h: 48, roof: "#655670", wallL: "#faf8f4", wallR: "#e9e3d8" }},
      {{ level: 4, code: "HALL 4", name: "Fine-Tuning", sub: "LoRA, DPO & GRPO", x: 870, y: 274, w: 120, d: 64, h: 48, roof: "#8b6842", wallL: "#faf8f4", wallR: "#e9e3d8" }},
      {{ level: 5, code: "HALL 5", name: "Frontier Lab", sub: "MoE, Speculative & Prod", x: 1120, y: 274, w: 120, d: 64, h: 48, roof: "#7d4850", wallL: "#faf8f4", wallR: "#e9e3d8" }}
    ];

    const HALL_ROOMS = [
      {{ idx: 0, x: 95,  y: 110, w: 240, h: 185 }},
      {{ idx: 1, x: 375, y: 110, w: 240, h: 185 }},
      {{ idx: 2, x: 655, y: 110, w: 240, h: 185 }},
      {{ idx: 3, x: 935, y: 110, w: 240, h: 185 }},
      {{ idx: 4, x: 95,  y: 465, w: 240, h: 185 }},
      {{ idx: 5, x: 375, y: 465, w: 240, h: 185 }},
      {{ idx: 6, x: 655, y: 465, w: 240, h: 185 }},
      {{ idx: 7, x: 935, y: 465, w: 240, h: 185 }}
    ];

    const state = {{
      scene: "campus",
      hallLevel: 0,
      activeStopId: "l0-what-is-an-llm",
      activePortraitStyle: "guard",
      nearbyLandmark: null,
      nearbyHall: null,
      nearbyRoomIdx: -1,
      hoveredHallLevel: -1,
      holoRinging: false,
      guardWhistleTimer: 0,
      player: {{
        x: 610,
        y: 722, // Spawns down the approach road walking up toward the gate!
        targetX: 610,
        targetY: 668,
        speed: 4.6,
        frame: 0,
        pendingCallback: null
      }},
      hallPlayer: {{
        x: 215,
        y: 380,
        targetX: null,
        targetY: null,
        frame: 0,
        pendingCallback: null
      }},
      keys: {{}},
      quizAnswers: {{}},
      tick: 0,
      typewriterTimer: null
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

    // =========================================================================
    // 3D CARICATURE RENDERER (Karpathy & Campus Characters in 3D Canvas!)
    // =========================================================================
    function draw3DCaricaturePortrait(pCtx, w, h, style, tick) {{
      pCtx.clearRect(0, 0, w, h);
      const cx = w / 2;
      const cy = h / 2 + 10;
      const bob = Math.sin(tick * 0.12) * 2.5;
      const tilt = Math.sin(tick * 0.07) * 0.04;
      const talkOpen = Math.abs(Math.sin(tick * 0.22)) * 4.5;

      pCtx.save();
      pCtx.translate(cx, cy + bob);
      pCtx.rotate(tilt);

      if (style === "karpathy") {{
        // Hologram scanline aura & 3D depth rings
        const bgGrad = pCtx.createRadialGradient(0, -10, 6, 0, 0, w * 0.48);
        bgGrad.addColorStop(0, "#bae6fd");
        bgGrad.addColorStop(1, "#e0f2fe");
        pCtx.fillStyle = bgGrad;
        pCtx.fillRect(-w, -h, w * 2, h * 2);

        // Hoodie & Laptop with neural network sticker
        pCtx.fillStyle = "#1e293b";
        pCtx.strokeStyle = "#111c16";
        pCtx.lineWidth = 2.4;
        pCtx.beginPath();
        pCtx.roundRect(-28, 12, 56, 36, 12);
        pCtx.fill();
        pCtx.stroke();

        // Hoodie drawstrings
        pCtx.strokeStyle = "#38bdf8";
        pCtx.lineWidth = 2;
        pCtx.beginPath();
        pCtx.moveTo(-7, 15); pCtx.lineTo(-9, 30);
        pCtx.moveTo(7, 15); pCtx.lineTo(9, 30);
        pCtx.stroke();

        // 3D Neck & Sculpted Head
        pCtx.fillStyle = "#fdba74";
        pCtx.fillRect(-7, 4, 14, 12);
        pCtx.fillStyle = "#fed7aa";
        pCtx.strokeStyle = "#111c16";
        pCtx.lineWidth = 2.4;
        pCtx.beginPath();
        pCtx.roundRect(-21, -30, 42, 38, 15);
        pCtx.fill();
        pCtx.stroke();

        // 3D Cheek shading
        pCtx.fillStyle = "rgba(234, 88, 12, 0.16)";
        pCtx.beginPath();
        pCtx.arc(-12, -7, 5, 0, Math.PI * 2);
        pCtx.arc(12, -7, 5, 0, Math.PI * 2);
        pCtx.fill();

        // Signature tousled wavy brown hair (3D layered tufts)
        pCtx.fillStyle = "#451a03";
        pCtx.beginPath();
        pCtx.arc(0, -28, 22, Math.PI * 0.92, Math.PI * 2.08);
        pCtx.fill();
        pCtx.stroke();
        // Hair curls on top
        pCtx.beginPath();
        pCtx.arc(-11, -36, 8, 0, Math.PI * 2);
        pCtx.arc(2, -38, 9, 0, Math.PI * 2);
        pCtx.arc(13, -34, 7, 0, Math.PI * 2);
        pCtx.fill();

        // Signature rectangular dark-rimmed glasses with glowing lens reflection
        pCtx.fillStyle = "rgba(56, 189, 248, 0.22)";
        pCtx.strokeStyle = "#111c16";
        pCtx.lineWidth = 2.4;
        pCtx.beginPath();
        pCtx.roundRect(-17, -20, 14, 10, 3);
        pCtx.roundRect(3, -20, 14, 10, 3);
        pCtx.fill();
        pCtx.stroke();
        // Glasses bridge
        pCtx.beginPath();
        pCtx.moveTo(-3, -15);
        pCtx.lineTo(3, -15);
        pCtx.stroke();

        // Expressive eyes behind glasses
        pCtx.fillStyle = "#111c16";
        pCtx.beginPath();
        pCtx.arc(-10, -15, 2.2, 0, Math.PI * 2);
        pCtx.arc(10, -15, 2.2, 0, Math.PI * 2);
        pCtx.fill();

        // Headset mic boom
        pCtx.strokeStyle = "#0284c7";
        pCtx.lineWidth = 2.2;
        pCtx.beginPath();
        pCtx.moveTo(-21, -12);
        pCtx.quadraticCurveTo(-24, -1, -8, -1);
        pCtx.stroke();
        pCtx.fillStyle = "#0284c7";
        pCtx.beginPath();
        pCtx.arc(-7, -1, 2.8, 0, Math.PI * 2);
        pCtx.fill();

        // Animated talking smile
        pCtx.fillStyle = "#7c2d12";
        pCtx.beginPath();
        pCtx.ellipse(0, -3, 6.5, 1.8 + talkOpen * 0.6, 0, 0, Math.PI * 2);
        pCtx.fill();
      }} else {{
        // 3D Caricature for Officer Rajan, Maya, Chef Kabir, or Prof. Meera
        const colors = {{
          guard: {{ bg: "#fef3c7", coat: "#1e3a8a", hat: "#1e3a8a", badge: "#facc15" }},
          engineer: {{ bg: "#e0f2fe", coat: "#0284c7", hat: "#eab308", badge: "#38bdf8" }},
          chef: {{ bg: "#ffedd5", coat: "#ea580c", hat: "#ffffff", badge: "#fed7aa" }},
          prof: {{ bg: "#f3e8ff", coat: "#6b21a8", hat: "#4c1d95", badge: "#e9d5ff" }}
        }}[style] || {{ bg: "#fef3c7", coat: "#9a2c13", hat: "#7c2d12", badge: "#facc15" }};

        pCtx.fillStyle = colors.bg;
        pCtx.fillRect(-w, -h, w * 2, h * 2);

        // Coat / shoulders
        pCtx.fillStyle = colors.coat;
        pCtx.strokeStyle = "#111c16";
        pCtx.lineWidth = 3;
        pCtx.beginPath();
        pCtx.roundRect(-38, 16, 76, 48, 16);
        pCtx.fill();
        pCtx.stroke();

        // Head
        pCtx.fillStyle = "#fed7aa";
        pCtx.beginPath();
        pCtx.roundRect(-26, -34, 52, 48, 20);
        pCtx.fill();
        pCtx.stroke();

        // Hat / Cap / Hair
        pCtx.fillStyle = colors.hat;
        pCtx.beginPath();
        pCtx.roundRect(-29, -46, 58, 18, 8);
        pCtx.fill();
        pCtx.stroke();

        if (style === "guard") {{
          // Gold Security Cap Emblem & Whistle
          pCtx.fillStyle = "#facc15";
          pCtx.beginPath();
          pCtx.arc(0, -37, 5, 0, Math.PI * 2);
          pCtx.fill();
          // Mustache
          pCtx.fillStyle = "#111c16";
          pCtx.fillRect(-12, -4, 24, 4.5);
        }}

        // Eyes
        pCtx.fillStyle = "#111c16";
        pCtx.beginPath();
        pCtx.arc(-11, -16, 3.2, 0, Math.PI * 2);
        pCtx.arc(11, -16, 3.2, 0, Math.PI * 2);
        pCtx.fill();

        // Talking mouth
        pCtx.fillStyle = "#7c2d12";
        pCtx.beginPath();
        pCtx.ellipse(0, 3, 7, 2 + talkOpen * 0.7, 0, 0, Math.PI * 2);
        pCtx.fill();
      }}
      pCtx.restore();
    }}

    // =========================================================================
    // TYPEWRITER RPG DIALOGUE ENGINE
    // =========================================================================
    function playTypewriterText(elementId, fullText) {{
      if (state.typewriterTimer) clearInterval(state.typewriterTimer);
      const el = document.getElementById(elementId);
      el.innerText = "";
      let idx = 0;
      state.typewriterTimer = setInterval(() => {{
        idx += 3;
        el.innerText = fullText.slice(0, idx);
        if (idx >= fullText.length) {{
          el.innerText = fullText;
          clearInterval(state.typewriterTimer);
          state.typewriterTimer = null;
        }}
      }}, 16);
    }}

    function openNpcDialogue(stopId, nodeIdx = 0) {{
      const stop = OUTDOOR_LANDMARKS.find(s => s.id === stopId);
      if (!stop) return;
      state.activeStopId = stopId;
      state.activePortraitStyle = stop.npcStyle || "guard";
      const isCleared = clearedIds.has(stopId) && stop.clearedDialogue;
      const node = isCleared ? stop.clearedDialogue : (stop.dialogue[nodeIdx] || stop.dialogue[0]);
      const modeKey = isCleared ? -1 : nodeIdx;

      document.getElementById("rpg-speaker-name").innerText = stop.npcName;
      const roleEl = document.getElementById("rpg-speaker-role");
      roleEl.innerText = isCleared ? `✓ CLEARED · REVISION MODE · ${{stop.npcRole}}` : stop.npcRole;
      roleEl.style.color = isCleared ? "var(--meadow)" : "";
      playTypewriterText("rpg-speech-text", node.text);

      const choicesEl = document.getElementById("rpg-choices");
      choicesEl.innerHTML = node.choices.map((c, i) => `
        <button class="rpg-choice-btn ${{i === 0 ? 'choice-primary' : ''}}" onclick="handleNpcChoice('${{stopId}}', ${{modeKey}}, ${{i}})">
          <span>${{c.label}}</span>
          <span>→</span>
        </button>
      `).join("") + `
        <button class="rpg-choice-btn" onclick="closeRpgDialogue()">
          <span>🚶 Keep walking around campus</span>
          <span>Esc</span>
        </button>
      `;
      document.getElementById("rpg-dialogue-backdrop").classList.add("open");
    }}

    function handleNpcChoice(stopId, nodeIdx, choiceIdx) {{
      const stop = OUTDOOR_LANDMARKS.find(s => s.id === stopId);
      const node = (nodeIdx === -1 && stop.clearedDialogue) ? stop.clearedDialogue : stop.dialogue[nodeIdx];
      const choice = node && node.choices[choiceIdx];
      if (!choice) return;
      if (typeof choice.next === "number") {{
        openNpcDialogue(stopId, choice.next);
      }} else if (choice.action === "openStory") {{
        closeRpgDialogue();
        openLessonBook(stopId, "story");
      }} else if (choice.action === "openLab") {{
        closeRpgDialogue();
        openLessonBook(stopId, "lab");
      }} else if (choice.action === "openGateQuiz") {{
        closeRpgDialogue();
        openLessonBook(stopId, "gate");
      }} else if (choice.action === "nextMission") {{
        closeRpgDialogue();
        walkToCurrentQuest();
      }}
    }}

    function closeRpgDialogue() {{
      if (state.typewriterTimer) clearInterval(state.typewriterTimer);
      document.getElementById("rpg-dialogue-backdrop").classList.remove("open");
    }}

    // =========================================================================
    // NAVIGATION, QUEST TRACKER & CRISP HTML PINS
    // =========================================================================
    function walkToOutdoorStop(stopId, talkOnArrival = true) {{
      const stop = OUTDOOR_LANDMARKS.find(s => s.id === stopId);
      if (!stop) return;
      if (stopId !== "l0-what-is-an-llm" && !isGateOpen()) {{
        // Boom barrier is closed! Officer Rajan intercepts Ashwin at the South Gate!
        startWalkToGateAmbush();
        return;
      }}
      state.scene = "campus";
      state.activeStopId = stopId;
      state.player.targetX = stop.x;
      state.player.targetY = stop.y + 24;
      state.player.pendingCallback = talkOnArrival ? () => openNpcDialogue(stopId, 0) : null;
      refreshHudAndPins();
    }}

    function walkToCurrentQuest() {{
      if (!isGateOpen()) {{
        startWalkToGateAmbush();
        return;
      }}
      for (const s of OUTDOOR_LANDMARKS) {{
        if (!clearedIds.has(s.id)) {{
          walkToOutdoorStop(s.id, true);
          return;
        }}
      }}
      switchScene("hall", 0);
    }}

    function switchScene(sceneName, hallLvl) {{
      state.scene = sceneName;
      if (typeof hallLvl === "number") {{
        state.hallLevel = hallLvl;
        state.hallPlayer.x = 215;
        state.hallPlayer.y = 380;
        state.hallPlayer.targetX = null;
        state.hallPlayer.targetY = null;
      }}
      document.getElementById("btn-exit-hall").style.display = sceneName === "hall" ? "inline-flex" : "none";
      refreshHudAndPins();
    }}

    function toggleTeleportDrawer(open) {{
      document.getElementById("map-drawer-backdrop").classList.toggle("open", open);
    }}

    function refreshHudAndPins() {{
      const gateEl = document.getElementById("hud-gate-state");
      if (isGateOpen()) {{
        gateEl.innerText = "OPEN";
        gateEl.style.color = "var(--meadow)";
      }} else {{
        gateEl.innerText = "LOCKED";
        gateEl.style.color = "var(--terracotta)";
      }}
      document.getElementById("hud-cleared-count").innerText = `${{clearedIds.size}} / ${{CURRICULUM.modules.length}}`;

      // Update Compact Floating Mission Strip
      let nextQuestStop = OUTDOOR_LANDMARKS.find(s => !clearedIds.has(s.id));
      if (!nextQuestStop) {{
        document.getElementById("quest-kicker").innerText = "🏛️ QUAD CLEARED · ENTER HALLS";
        document.getElementById("quest-headline").innerText = "Explore the 6 Self-Expanding Academic Halls";
      }} else {{
        document.getElementById("quest-kicker").innerText = `🎯 ACTIVE · ${{nextQuestStop.num}}`;
        document.getElementById("quest-headline").innerText = `${{nextQuestStop.icon}} Talk to ${{nextQuestStop.npcName}} at ${{nextQuestStop.name}}`;
      }}

      // Populate Fast-Travel Drawer
      const tpEl = document.getElementById("teleport-list");
      let tpHtml = "";
      for (const s of OUTDOOR_LANDMARKS) {{
        const mod = CURRICULUM.modules.find(m => m.id === s.id);
        const cleared = clearedIds.has(s.id);
        const unlocked = isModuleUnlocked(s.id);
        tpHtml += `
          <div class="teleport-row" onclick="toggleTeleportDrawer(false);walkToOutdoorStop('${{s.id}}', true)">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.2rem;">
              <span style="font-family:var(--mono);font-size:0.76rem;font-weight:700;color:var(--terracotta);">${{s.icon}} ${{s.num}} · ${{s.name}}</span>
              <span class="tag ${{cleared ? 'tag-meadow' : (unlocked ? 'tag-amber' : '')}}">${{cleared ? '✓ CLEARED' : (unlocked ? '● READY' : '🔒 GATE')}}</span>
            </div>
            <div style="font-family:var(--serif);font-weight:800;font-size:0.95rem;">${{mod ? mod.title : s.name}}</div>
          </div>
        `;
      }}
      for (const h of ACADEMIC_HALLS) {{
        const mods = getModulesForLevel(h.level);
        const done = mods.filter(m => clearedIds.has(m.id)).length;
        tpHtml += `
          <div class="teleport-row" onclick="toggleTeleportDrawer(false);if(!isGateOpen())startWalkToGateAmbush();else switchScene('hall',${{h.level}})">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.2rem;">
              <span style="font-family:var(--mono);font-size:0.76rem;font-weight:700;color:var(--sky);">🏛️ ${{h.code}}</span>
              <span class="tag tag-sky">${{done}}/${{mods.length}} Rooms</span>
            </div>
            <div style="font-family:var(--serif);font-weight:800;font-size:0.95rem;">${{h.name}}</div>
            <div style="font-size:0.78rem;color:var(--muted);">${{h.sub}}</div>
          </div>
        `;
      }}
      tpEl.innerHTML = tpHtml;
      renderHtmlWorldPins();
    }}

    // =========================================================================
    // CRISP HTML OVERLAY PINS (Projected onto 1280x760 World Coordinates)
    // =========================================================================
    const canvas = document.getElementById("campus-canvas");
    const ctx = canvas.getContext("2d");
    const karpathyAvatarCanvas = document.getElementById("karpathy-avatar-canvas");
    const karpathyAvatarCtx = karpathyAvatarCanvas.getContext("2d");
    const rpgPortraitCanvas = document.getElementById("rpg-portrait-canvas");
    const rpgPortraitCtx = rpgPortraitCanvas.getContext("2d");

    function renderHtmlWorldPins() {{
      const layer = document.getElementById("pins-layer");
      let html = "";

      if (state.scene === "campus") {{
        for (const s of OUTDOOR_LANDMARKS) {{
          const cleared = clearedIds.has(s.id);
          const unlocked = isModuleUnlocked(s.id);
          const active = state.activeStopId === s.id;
          const leftPct = ((s.x / 1280) * 100).toFixed(2);
          const topPct = (((s.y - 54) / 760) * 100).toFixed(2);
          const cls = cleared ? "pin-cleared" : (active ? "pin-active" : (!unlocked ? "pin-locked" : ""));
          const badgeTxt = cleared ? "✓" : (unlocked ? s.num : "🔒");
          html += `
            <div class="world-pin ${{cls}}" data-stop-id="${{s.id}}" style="left:${{leftPct}}%;top:${{topPct}}%;" onclick="walkToOutdoorStop('${{s.id}}', true)">
              <span class="pin-badge">${{badgeTxt}}</span>
              <span class="pin-label">${{s.icon}} ${{s.shortLabel}}</span>
            </div>
          `;
        }}
        for (const h of ACADEMIC_HALLS) {{
          const mods = getModulesForLevel(h.level);
          const done = mods.filter(m => clearedIds.has(m.id)).length;
          const leftPct = ((h.x / 1280) * 100).toFixed(2);
          const topPct = (((h.y - h.h - h.d / 2 - 10) / 760) * 100).toFixed(2);
          html += `
            <div class="world-pin pin-hall" data-hall-level="${{h.level}}" style="left:${{leftPct}}%;top:${{topPct}}%;" onclick="if(!isGateOpen())startWalkToGateAmbush();else switchScene('hall',${{h.level}})">
              <span class="pin-badge">${{h.code}} · ${{done}}/${{mods.length}}</span>
              <span class="pin-label">${{h.name}}</span>
            </div>
          `;
        }}
      }} else {{
        const mods = getModulesForLevel(state.hallLevel);
        for (let i = 0; i < Math.min(HALL_ROOMS.length, mods.length); i++) {{
          const r = HALL_ROOMS[i];
          const m = mods[i];
          const cleared = clearedIds.has(m.id);
          const seeded = Boolean(SEEDED_LESSONS[m.id]);
          const leftPct = (((r.x + r.w / 2) / 1280) * 100).toFixed(2);
          const topPct = (((r.y + 42) / 760) * 100).toFixed(2);
          html += `
            <div class="world-pin ${{cleared ? 'pin-cleared' : (seeded ? 'pin-active' : '')}}" style="left:${{leftPct}}%;top:${{topPct}}%;" onclick="walkToHallClassroom(${{i}})">
              <span class="pin-badge">ROOM ${{state.hallLevel + 1}}0${{i + 1}}</span>
              <span class="pin-label">${{m.title}}</span>
            </div>
          `;
        }}
      }}
      layer.innerHTML = html;
    }}

    function walkToHallClassroom(idx) {{
      const mods = getModulesForLevel(state.hallLevel);
      const m = mods[idx];
      if (!m) return;
      const r = HALL_ROOMS[idx];
      state.hallPlayer.targetX = r.x + r.w / 2;
      state.hallPlayer.targetY = r.y + r.h / 2 + 20;
      state.hallPlayer.pendingCallback = () => openLessonBook(m.id, "story");
    }}

    // =========================================================================
    // HIGH-DPI 3D ISOMETRIC ARCHITECTURAL RENDERER
    // =========================================================================
    function syncCanvasRetina() {{
      const dpr = window.devicePixelRatio || 1;
      const targetW = 1280 * dpr;
      const targetH = 760 * dpr;
      if (canvas.width !== targetW || canvas.height !== targetH) {{
        canvas.width = targetW;
        canvas.height = targetH;
      }}
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }}

    function drawIsoBuilding3D(cx, cy, w, d, h, roofColor, leftWall, rightWall, hasWindows = true, isHovered = false) {{
      const hw = w / 2;
      const hd = d / 2;
      const lift = isHovered ? 5 : 0;
      const by = cy - lift;

      // Ground contact shadow (softens slightly when hovered)
      ctx.fillStyle = isHovered ? "rgba(17, 28, 22, 0.16)" : "rgba(17, 28, 22, 0.22)";
      ctx.beginPath();
      ctx.moveTo(cx, cy + hd + 13);
      ctx.lineTo(cx + hw + 18, cy + 10);
      ctx.lineTo(cx, cy - hd + 10);
      ctx.lineTo(cx - hw + 6, cy + 10);
      ctx.closePath();
      ctx.fill();

      // Stepped limestone foundation plinth (architectural base)
      const ph = hasWindows ? 6 : 3;
      ctx.fillStyle = "#d9d2c5";
      ctx.beginPath();
      ctx.moveTo(cx - hw - 3, by + 2);
      ctx.lineTo(cx, by + hd + 4);
      ctx.lineTo(cx + hw + 3, by + 2);
      ctx.lineTo(cx + hw + 3, by + 2 - ph);
      ctx.lineTo(cx, by + hd + 4 - ph);
      ctx.lineTo(cx - hw - 3, by + 2 - ph);
      ctx.closePath();
      ctx.fill();
      ctx.strokeStyle = "#48524c";
      ctx.lineWidth = 1.1;
      ctx.stroke();

      // Left sun-lit facade
      ctx.fillStyle = leftWall;
      ctx.beginPath();
      ctx.moveTo(cx - hw, by);
      ctx.lineTo(cx, by + hd);
      ctx.lineTo(cx, by + hd - h);
      ctx.lineTo(cx - hw, by - h);
      ctx.closePath();
      ctx.fill();
      ctx.strokeStyle = "#2e3b34";
      ctx.lineWidth = 1.4;
      ctx.stroke();

      // Right shaded facade
      ctx.fillStyle = rightWall;
      ctx.beginPath();
      ctx.moveTo(cx, by + hd);
      ctx.lineTo(cx + hw, by);
      ctx.lineTo(cx + hw, by - h);
      ctx.lineTo(cx, by + hd - h);
      ctx.closePath();
      ctx.fill();
      ctx.stroke();

      // Subtle architectural roof-under-eave shadow band
      ctx.fillStyle = "rgba(17, 28, 22, 0.08)";
      ctx.beginPath();
      ctx.moveTo(cx - hw, by - h);
      ctx.lineTo(cx, by + hd - h);
      ctx.lineTo(cx, by + hd - h + 6);
      ctx.lineTo(cx - hw, by - h + 6);
      ctx.closePath();
      ctx.fill();
      ctx.beginPath();
      ctx.moveTo(cx, by + hd - h);
      ctx.lineTo(cx + hw, by - h);
      ctx.lineTo(cx + hw, by - h + 6);
      ctx.lineTo(cx, by + hd - h + 6);
      ctx.closePath();
      ctx.fill();

      if (hasWindows && h >= 44) {{
        const rows = h >= 62 ? 2 : 1;
        for (let r = 0; r < rows; r++) {{
          const yOff = -h + 14 + r * 20;
          for (let c = 1; c <= 3; c++) {{
            const t = c / 4;
            const lx = (cx - hw) * (1 - t) + cx * t;
            const ly = by * (1 - t) + (by + hd) * t + yOff;
            const warmLeft = (c + r) % 3 === 0;
            ctx.fillStyle = warmLeft ? "#e8c47a" : "#567d92";
            ctx.fillRect(lx - 4, ly, 7.5, 11);
            // Glazed diagonal sheen
            ctx.fillStyle = "rgba(255,255,255,0.32)";
            ctx.fillRect(lx - 3, ly + 1, 2.2, 8);
            ctx.strokeStyle = "#2e3b34";
            ctx.lineWidth = 1;
            ctx.strokeRect(lx - 4, ly, 7.5, 11);

            const rx = cx * (1 - t) + (cx + hw) * t;
            const ry = (by + hd) * (1 - t) + by * t + yOff;
            const warmRight = (c + r) % 2 === 1;
            ctx.fillStyle = warmRight ? "#d8b16a" : "#436678";
            ctx.fillRect(rx - 4, ry, 7.5, 11);
            ctx.fillStyle = "rgba(255,255,255,0.22)";
            ctx.fillRect(rx - 3, ry + 1, 2, 8);
            ctx.strokeRect(rx - 4, ry, 7.5, 11);
          }}
        }}
        // Arched wooden entry portal
        ctx.fillStyle = "#6c3f2b";
        ctx.fillRect(cx - 12, by + hd - 17, 9, 14);
        ctx.fillStyle = "#e8c47a";
        ctx.fillRect(cx - 10, by + hd - 15, 5, 4);
        ctx.strokeStyle = "#2e3b34";
        ctx.strokeRect(cx - 12, by + hd - 17, 9, 14);
      }}

      const oh = 4.5;
      ctx.fillStyle = roofColor;
      ctx.beginPath();
      ctx.moveTo(cx, by - hd - h - oh);
      ctx.lineTo(cx + hw + oh, by - h);
      ctx.lineTo(cx, by + hd - h + oh);
      ctx.lineTo(cx - hw - oh, by - h);
      ctx.closePath();
      ctx.fill();
      ctx.strokeStyle = isHovered ? "#111c16" : "#2e3b34";
      ctx.lineWidth = isHovered ? 2.1 : 1.4;
      ctx.stroke();

      // Sunlit roof bevel + glass skylight lantern on Academic Halls
      ctx.fillStyle = "rgba(255,255,255,0.26)";
      ctx.beginPath();
      ctx.moveTo(cx, by - hd * 0.45 - h);
      ctx.lineTo(cx + hw * 0.45, by - h);
      ctx.lineTo(cx, by + hd * 0.45 - h);
      ctx.lineTo(cx - hw * 0.45, by - h);
      ctx.closePath();
      ctx.fill();

      if (hasWindows && w >= 90) {{
        // Glass atrium skylight crown
        ctx.fillStyle = "rgba(224, 242, 254, 0.72)";
        ctx.strokeStyle = "#2e3b34";
        ctx.lineWidth = 1.1;
        ctx.beginPath();
        ctx.moveTo(cx, by - hd * 0.32 - h - 5);
        ctx.lineTo(cx + hw * 0.28, by - h - 3);
        ctx.lineTo(cx, by + hd * 0.32 - h - 1);
        ctx.lineTo(cx - hw * 0.28, by - h - 3);
        ctx.closePath();
        ctx.fill();
        ctx.stroke();
      }}
    }}

    function drawTree3D(x, y, scale = 1.0) {{
      const sway = Math.sin(state.tick * 0.03 + x) * 2;
      ctx.fillStyle = "rgba(20, 29, 24, 0.14)";
      ctx.beginPath();
      ctx.ellipse(x + 6, y + 5, 16 * scale, 8 * scale, 0, 0, Math.PI * 2);
      ctx.fill();

      ctx.fillStyle = "#6e5645";
      ctx.fillRect(x - 3 * scale, y - 15 * scale, 6 * scale, 17 * scale);

      ctx.fillStyle = "#4c6e55";
      ctx.beginPath();
      ctx.arc(x + sway, y - 21 * scale, 16 * scale, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = "#608469";
      ctx.beginPath();
      ctx.arc(x - 4 * scale + sway, y - 26 * scale, 12 * scale, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = "#83a68a";
      ctx.beginPath();
      ctx.arc(x - 5 * scale + sway, y - 30 * scale, 6 * scale, 0, Math.PI * 2);
      ctx.fill();
    }}

    function drawCar3D(x, y, bodyColor, cabinColor) {{
      drawIsoBuilding3D(x, y, 48, 26, 12, bodyColor, bodyColor, "#1e293b", false);
      drawIsoBuilding3D(x, y - 10, 28, 18, 9, cabinColor, "#e0f2fe", "#bae6fd", false);
    }}

    function drawUmbrellaTable3D(x, y, canopyColor) {{
      ctx.fillStyle = "rgba(17,28,22,0.2)";
      ctx.beginPath();
      ctx.ellipse(x, y + 7, 20, 10, 0, 0, Math.PI * 2);
      ctx.fill();

      ctx.fillStyle = "#fef3c7";
      ctx.strokeStyle = "#111c16";
      ctx.lineWidth = 1.6;
      ctx.beginPath();
      ctx.ellipse(x, y, 17, 9, 0, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();

      ctx.strokeStyle = "#26382e";
      ctx.lineWidth = 2.2;
      ctx.beginPath();
      ctx.moveTo(x, y);
      ctx.lineTo(x, y - 22);
      ctx.stroke();

      ctx.fillStyle = canopyColor;
      ctx.beginPath();
      ctx.ellipse(x, y - 22, 23, 11, 0, 0, Math.PI * 2);
      ctx.fill();
      ctx.strokeStyle = "#111c16";
      ctx.lineWidth = 1.6;
      ctx.stroke();
    }}

    function drawCharacter3D(x, y, jacketColor, isPlayer = false, hasExclamation = false, isClearedBadge = false) {{
      const bounce = isPlayer
        ? Math.abs(Math.sin(state.player.frame)) * 3.5
        : Math.sin(state.tick * 0.05 + x) * 1.5;

      ctx.fillStyle = isPlayer ? "rgba(154, 44, 19, 0.35)" : "rgba(17, 28, 22, 0.28)";
      ctx.beginPath();
      ctx.ellipse(x, y + 13, isPlayer ? 16 : 14, isPlayer ? 8 : 6.5, 0, 0, Math.PI * 2);
      ctx.fill();

      if (isPlayer) {{
        ctx.strokeStyle = "#ffffff";
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.ellipse(x, y + 13, 18, 9, 0, 0, Math.PI * 2);
        ctx.stroke();
      }}

      ctx.fillStyle = "#1e293b";
      ctx.fillRect(x - 6, y + 1 - bounce, 5, 11);
      ctx.fillRect(x + 1, y + 1 - bounce, 5, 11);

      ctx.fillStyle = jacketColor;
      ctx.strokeStyle = "#111c16";
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.roundRect(x - 11, y - 15 - bounce, 22, 18, 6);
      ctx.fill();
      ctx.stroke();

      ctx.fillStyle = "#fed7aa";
      ctx.beginPath();
      ctx.arc(x, y - 23 - bounce, 9.5, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();

      ctx.fillStyle = isPlayer ? "#9a2c13" : "#111c16";
      ctx.beginPath();
      ctx.arc(x, y - 26 - bounce, 9.5, Math.PI, Math.PI * 2);
      ctx.fill();

      ctx.fillStyle = "#111c16";
      ctx.fillRect(x - 4, y - 24 - bounce, 2.5, 3);
      ctx.fillRect(x + 2, y - 24 - bounce, 2.5, 3);

      // If Ashwin's communicator is ringing, project a miniature 3D Karpathy hologram beam above his hand!
      if (isPlayer && state.holoRinging) {{
        const pulse = Math.sin(state.tick * 0.15) * 3;
        ctx.save();
        ctx.strokeStyle = "rgba(14, 165, 233, 0.75)";
        ctx.fillStyle = "rgba(56, 189, 248, 0.22)";
        ctx.lineWidth = 1.8;
        ctx.beginPath();
        ctx.moveTo(x + 10, y - 10 - bounce);
        ctx.lineTo(x + 28, y - 42 - bounce + pulse);
        ctx.lineTo(x + 48, y - 42 - bounce + pulse);
        ctx.closePath();
        ctx.fill();
        ctx.stroke();

        // Floating 3D Karpathy holo-head right in the 3D world!
        ctx.fillStyle = "#38bdf8";
        ctx.strokeStyle = "#111c16";
        ctx.beginPath();
        ctx.arc(x + 38, y - 50 - bounce + pulse, 10, 0, Math.PI * 2);
        ctx.fill();
        ctx.stroke();
        // Glasses on mini 3D hologram
        ctx.fillStyle = "#111c16";
        ctx.fillRect(x + 32, y - 53 - bounce + pulse, 5, 3.5);
        ctx.fillRect(x + 39, y - 53 - bounce + pulse, 5, 3.5);
        ctx.restore();
      }}

      if (hasExclamation) {{
        const floatY = Math.sin(state.tick * 0.08 + x) * 3;
        ctx.fillStyle = "#e0a952";
        ctx.strokeStyle = "#2e3b34";
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(x, y - 44 - bounce + floatY, 10, 0, Math.PI * 2);
        ctx.fill();
        ctx.stroke();

        ctx.fillStyle = "#111c16";
        ctx.fillRect(x - 1.5, y - 49 - bounce + floatY, 3, 6);
        ctx.fillRect(x - 1.5, y - 41 - bounce + floatY, 3, 2.5);
      }} else if (isClearedBadge) {{
        const floatY = Math.sin(state.tick * 0.06 + x) * 2;
        ctx.fillStyle = "#2c6b4f";
        ctx.strokeStyle = "#ffffff";
        ctx.lineWidth = 1.8;
        ctx.beginPath();
        ctx.arc(x, y - 44 - bounce + floatY, 9.5, 0, Math.PI * 2);
        ctx.fill();
        ctx.stroke();
        ctx.strokeStyle = "#ffffff";
        ctx.lineWidth = 2.1;
        ctx.beginPath();
        ctx.moveTo(x - 4, y - 44 - bounce + floatY);
        ctx.lineTo(x - 1, y - 41 - bounce + floatY);
        ctx.lineTo(x + 4.5, y - 47.5 - bounce + floatY);
        ctx.stroke();
      }}
    }}

    function drawCampusWorld() {{
      syncCanvasRetina();

      // Serene Morning Mist Sky (Top HUD Safe Zone: 0..145px)
      const skyGrad = ctx.createLinearGradient(0, 0, 0, 155);
      skyGrad.addColorStop(0, "#d7e5ec");
      skyGrad.addColorStop(1, "#eff4f6");
      ctx.fillStyle = skyGrad;
      ctx.fillRect(0, 0, 1280, 155);

      // Gentle Drifting Morning Clouds
      ctx.fillStyle = "rgba(255, 255, 255, 0.55)";
      const c1 = ((state.tick * 0.14) % 1420) - 120;
      const c2 = (((state.tick * 0.09) + 640) % 1420) - 120;
      ctx.beginPath();
      ctx.ellipse(c1, 74, 58, 15, 0, 0, Math.PI * 2);
      ctx.ellipse(c1 + 32, 68, 36, 12, 0, 0, Math.PI * 2);
      ctx.ellipse(c2, 92, 48, 13, 0, 0, Math.PI * 2);
      ctx.ellipse(c2 - 26, 88, 30, 10, 0, 0, Math.PI * 2);
      ctx.fill();

      // Soft Distant Botanical Hills (Atmospheric Depth)
      ctx.fillStyle = "#c2d2c4";
      ctx.beginPath();
      ctx.moveTo(0, 152);
      ctx.quadraticCurveTo(260, 96, 590, 134);
      ctx.quadraticCurveTo(950, 88, 1280, 136);
      ctx.lineTo(1280, 760);
      ctx.lineTo(0, 760);
      ctx.closePath();
      ctx.fill();

      // Desaturated Architectural Sage-Meadow Lawn (Restrained, calm ground)
      const lawnGrad = ctx.createLinearGradient(0, 142, 0, 760);
      lawnGrad.addColorStop(0, "#cddbc7");
      lawnGrad.addColorStop(0.55, "#c0d1b9");
      lawnGrad.addColorStop(1, "#b2c5ab");
      ctx.fillStyle = lawnGrad;
      ctx.fillRect(0, 142, 1280, 618);

      ctx.strokeStyle = "rgba(255, 255, 255, 0.16)";
      ctx.lineWidth = 1;
      for (let i = -800; i < 1800; i += 96) {{
        ctx.beginPath();
        ctx.moveTo(i, 142);
        ctx.lineTo(i + 620, 760);
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(i + 620, 142);
        ctx.lineTo(i, 760);
        ctx.stroke();
      }}

      // South Entrance Approach Road (Refined Slate Asphalt)
      ctx.fillStyle = "#3e464d";
      ctx.fillRect(560, 560, 100, 200);
      ctx.strokeStyle = "#f4f1ea";
      ctx.lineWidth = 2;
      ctx.setLineDash([12, 12]);
      ctx.beginPath();
      ctx.moveTo(610, 575);
      ctx.lineTo(610, 755);
      ctx.stroke();
      ctx.setLineDash([]);

      // Warm Limestone Walkways (Aligned to shifted Academic Hall Rows: y=260, 418, 576)
      ctx.fillStyle = "#f4f1ea";
      ctx.strokeStyle = "#d5cfc2";
      ctx.lineWidth = 2;
      ctx.beginPath(); ctx.roundRect(582, 248, 56, 322, 14); ctx.fill(); ctx.stroke();
      ctx.beginPath(); ctx.roundRect(225, 428, 385, 38, 12); ctx.fill(); ctx.stroke();
      ctx.beginPath(); ctx.roundRect(355, 278, 255, 38, 12); ctx.fill(); ctx.stroke();
      ctx.beginPath(); ctx.roundRect(610, 566, 530, 36, 12); ctx.fill(); ctx.stroke();
      ctx.beginPath(); ctx.roundRect(610, 408, 530, 36, 12); ctx.fill(); ctx.stroke();
      ctx.beginPath(); ctx.roundRect(610, 250, 530, 36, 12); ctx.fill(); ctx.stroke();

      // Campus Perimeter Clay-Brick Wall
      ctx.fillStyle = "#914531";
      ctx.fillRect(40, 646, 505, 14);
      ctx.fillRect(675, 646, 565, 14);
      ctx.fillStyle = "#e6dcd0";
      ctx.fillRect(40, 642, 505, 4);
      ctx.fillRect(675, 642, 565, 4);

      // LANDMARK 2: WEST CAMPUS PARKING LOT (Compact, cleanly above bottom-left call card!)
      ctx.save();
      ctx.fillStyle = "#3e464d";
      ctx.strokeStyle = "#cfd6d2";
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.roundRect(75, 344, 255, 148, 16);
      ctx.fill();
      ctx.stroke();

      ctx.strokeStyle = "#d4a656";
      ctx.lineWidth = 1.8;
      for (let bx = 120; bx <= 280; bx += 54) {{
        ctx.beginPath();
        ctx.moveTo(bx, 356);
        ctx.lineTo(bx, 416);
        ctx.stroke();
      }}
      // Painted BPE Barcode Stall Stencils
      ctx.fillStyle = "rgba(244, 241, 234, 0.65)";
      ctx.font = "700 9.5px 'IBM Plex Mono', monospace";
      ctx.textAlign = "center";
      ctx.fillText("#496", 147, 368);
      ctx.fillText("#675", 201, 368);
      ctx.fillText("#15717", 255, 368);

      drawCar3D(147, 394, "#b3543e", "#ead2ca");
      drawCar3D(201, 394, "#4a6b82", "#d3e0e8");
      drawCar3D(255, 394, "#4d735e", "#d2e2d8");

      drawIsoBuilding3D(130, 468, 58, 34, 34, "#4a6477", "#faf8f4", "#e6e0d5", false);
      drawCharacter3D(225, 456, "#4a6477", false, !clearedIds.has("l0-tokens"), clearedIds.has("l0-tokens"));
      ctx.restore();

      // LANDMARK 3: CHAI & EMBEDDINGS TERRACE
      ctx.save();
      ctx.fillStyle = "#efe6d8";
      ctx.strokeStyle = "#c4b6a1";
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.roundRect(225, 198, 248, 138, 16);
      ctx.fill();
      ctx.stroke();

      drawIsoBuilding3D(298, 248, 98, 56, 44, "#a9492f", "#faf8f4", "#e9e3d8", true);
      // Aromatic rising Chai steam wisps above the cafe roof
      for (let sw = 0; sw < 3; sw++) {{
        const phase = ((state.tick * 0.03 + sw * 0.33) % 1);
        const sx = 290 + sw * 9 + Math.sin(state.tick * 0.08 + sw) * 3;
        const sy = 178 - phase * 22;
        ctx.strokeStyle = `rgba(255, 250, 240, ${{0.65 * (1 - phase)}})`;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(sx, sy, 3.5 + phase * 3, 0, Math.PI * 1.4);
        ctx.stroke();
      }}
      drawUmbrellaTable3D(396, 232, "#b3543e");
      drawUmbrellaTable3D(436, 268, "#c48f45");
      drawUmbrellaTable3D(388, 294, "#4d735e");
      drawCharacter3D(355, 310, "#a9492f", false, !clearedIds.has("l0-embeddings"), clearedIds.has("l0-embeddings"));
      ctx.restore();

      // LANDMARK 4: CENTRAL QUAD FOUNTAIN
      ctx.save();
      ctx.fillStyle = "#ebe8e1";
      ctx.strokeStyle = "#b8b3a8";
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.ellipse(610, 355, 88, 50, 0, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();

      ctx.fillStyle = "#52829a";
      ctx.strokeStyle = "#2e3b34";
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.ellipse(610, 353, 50, 28, 0, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();

      const ripple = (state.tick % 45) / 45;
      ctx.strokeStyle = `rgba(255, 255, 255, ${{0.85 * (1 - ripple)}})`;
      ctx.lineWidth = 1.8;
      ctx.beginPath();
      ctx.ellipse(610, 353, 14 + ripple * 32, 7 + ripple * 16, 0, 0, Math.PI * 2);
      ctx.stroke();

      drawIsoBuilding3D(610, 353, 22, 15, 24, "#83a9bc", "#faf8f4", "#dce3e6", false);
      // Animated Twin Parabolic Fountain Water Arcs
      ctx.strokeStyle = "rgba(224, 242, 254, 0.85)";
      ctx.lineWidth = 1.8;
      const jet = Math.sin(state.tick * 0.14) * 2.5;
      ctx.beginPath();
      ctx.moveTo(610, 326);
      ctx.quadraticCurveTo(590, 308 + jet, 578, 349);
      ctx.moveTo(610, 326);
      ctx.quadraticCurveTo(630, 308 - jet, 642, 349);
      ctx.stroke();
      drawCharacter3D(662, 372, "#655670", false, !clearedIds.has("l0-context-window"), clearedIds.has("l0-context-window"));
      ctx.restore();

      // 6 ACADEMIC HALLS (Cleanly below top HUD safe zone, with subtle hover elevation!)
      for (const h of ACADEMIC_HALLS) {{
        drawIsoBuilding3D(h.x, h.y, h.w, h.d, h.h, h.roof, h.wallL, h.wallR, true, state.hoveredHallLevel === h.level);
      }}

      // Self-Expanding Campus Construction Crane behind Hall 5 (Swaying hook!)
      ctx.save();
      const hookSway = Math.sin(state.tick * 0.04) * 5;
      ctx.strokeStyle = "#b3833e";
      ctx.lineWidth = 2.6;
      ctx.beginPath();
      ctx.moveTo(1224, 265);
      ctx.lineTo(1224, 178);
      ctx.lineTo(1166, 178);
      ctx.stroke();
      ctx.strokeStyle = "#6c5230";
      ctx.lineWidth = 1.4;
      ctx.beginPath();
      ctx.moveTo(1176, 178);
      ctx.lineTo(1176 + hookSway, 206);
      ctx.stroke();
      ctx.fillStyle = "#c89242";
      ctx.fillRect(1168 + hookSway, 206, 16, 6);
      ctx.restore();

      // LANDMARK 1: SOUTH ENTRANCE SECURITY GATE & GUARD BOOTH
      ctx.save();
      drawIsoBuilding3D(520, 610, 62, 40, 44, "#a9492f", "#faf8f4", "#e9e3d8", false);
      ctx.fillStyle = "#7a9eb0";
      ctx.fillRect(528, 582, 16, 14);
      ctx.strokeStyle = "#111c16";
      ctx.lineWidth = 1.5;
      ctx.strokeRect(528, 582, 16, 14);

      ctx.fillStyle = isGateOpen() ? "#2c6b4f" : "#b83b2a";
      ctx.fillRect(552, 602, 14, 26);
      ctx.strokeRect(552, 602, 14, 26);
      // Gate Status LED Lamp
      ctx.fillStyle = isGateOpen() ? "#4ade80" : "#f87171";
      ctx.beginPath();
      ctx.arc(559, 597, 4.2, 0, Math.PI * 2);
      ctx.fill();
      ctx.strokeStyle = "#111c16";
      ctx.lineWidth = 1.2;
      ctx.stroke();

      // Red-and-White Boom Arm (Flashes/vibrates when Officer Rajan blows whistle!)
      ctx.save();
      ctx.translate(559, 608);
      if (isGateOpen()) {{
        ctx.rotate(-1.25);
      }} else if (state.guardWhistleTimer > 0) {{
        ctx.rotate(Math.sin(state.tick * 0.45) * 0.06);
      }}
      for (let seg = 0; seg < 6; seg++) {{
        ctx.fillStyle = seg % 2 === 0 ? "#ef4444" : "#ffffff";
        ctx.fillRect(seg * 18, -4.5, 18, 9);
        ctx.strokeStyle = "#111c16";
        ctx.lineWidth = 1.5;
        ctx.strokeRect(seg * 18, -4.5, 18, 9);
      }}
      ctx.restore();

      // Officer Rajan Security Guard NPC
      const rajanX = state.guardWhistleTimer > 0 ? 596 : 580;
      drawCharacter3D(rajanX, 598, "#1e3a8a", false, !clearedIds.has("l0-what-is-an-llm"), clearedIds.has("l0-what-is-an-llm"));

      // Animated Whistle Alert Rings when Rajan stops Ashwin at the gate!
      if (state.guardWhistleTimer > 0) {{
        state.guardWhistleTimer -= 1;
        const rPulse = (state.tick % 20) * 2.2;
        ctx.strokeStyle = "rgba(220, 38, 38, 0.75)";
        ctx.lineWidth = 2.5;
        ctx.beginPath();
        ctx.arc(rajanX, 568, 12 + rPulse, 0, Math.PI * 2);
        ctx.stroke();
      }}
      ctx.restore();

      // 3D Trees lining the South Approach Road & Campus
      const trees = [
        [105, 225], [168, 272], [440, 575],
        [525, 705], [695, 705], [742, 585], [748, 425],
        [748, 268], [520, 198], [1232, 595], [1232, 435], [1232, 295]
      ];
      for (const [tx, ty] of trees) {{
        drawTree3D(tx, ty, 1.0);
      }}

      // Player Avatar (Ashwin)
      drawCharacter3D(state.player.x, state.player.y, "#9a2c13", true, false);
    }}

    function drawHallInteriorWorld() {{
      syncCanvasRetina();
      ctx.fillStyle = "#f5ebe0";
      ctx.fillRect(0, 0, 1280, 760);

      ctx.strokeStyle = "#e6ccb2";
      ctx.lineWidth = 1;
      for (let gx = 0; gx < 1280; gx += 48) {{
        ctx.beginPath(); ctx.moveTo(gx, 0); ctx.lineTo(gx, 760); ctx.stroke();
      }}
      for (let gy = 0; gy < 760; gy += 48) {{
        ctx.beginPath(); ctx.moveTo(0, gy); ctx.lineTo(1280, gy); ctx.stroke();
      }}

      ctx.fillStyle = "#ddb892";
      ctx.strokeStyle = "#9c6644";
      ctx.lineWidth = 3;
      ctx.fillRect(60, 315, 1160, 130);
      ctx.strokeRect(60, 315, 1160, 130);

      const mods = getModulesForLevel(state.hallLevel);
      for (let i = 0; i < Math.min(HALL_ROOMS.length, mods.length); i++) {{
        const r = HALL_ROOMS[i];
        const m = mods[i];
        const cleared = clearedIds.has(m.id);
        const seeded = Boolean(SEEDED_LESSONS[m.id]);

        ctx.fillStyle = cleared ? "#f0fdf4" : (seeded ? "#fffbeb" : "#ffffff");
        ctx.strokeStyle = cleared ? "#14532d" : (seeded ? "#9a2c13" : "#8fa99b");
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.roundRect(r.x, r.y, r.w, r.h, 16);
        ctx.fill();
        ctx.stroke();

        drawIsoBuilding3D(r.x + r.w / 2, r.y + 135, 76, 40, 22, "#d97706", "#fef3c7", "#fde68a", false);
      }}

      drawCharacter3D(state.hallPlayer.x, state.hallPlayer.y, "#9a2c13", true, false);
    }}

    // =========================================================================
    // MOVEMENT, PROXIMITY DETECTION & FLOATING [E] INTERACTION BUTTON
    // =========================================================================
    window.addEventListener("keydown", e => {{
      if (document.getElementById("book-modal").classList.contains("open")) {{
        if (e.key === "Escape") closeBookModal();
        return;
      }}
      if (document.getElementById("rpg-dialogue-backdrop").classList.contains("open")) {{
        if (e.key === "Escape") closeRpgDialogue();
        return;
      }}
      state.keys[e.key.toLowerCase()] = true;
      if (["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", " "].includes(e.key)) {{
        e.preventDefault();
      }}
      if (e.key.toLowerCase() === "e" || e.key === "Enter") {{
        triggerNearbyInteraction();
      }}
    }});

    window.addEventListener("keyup", e => {{
      state.keys[e.key.toLowerCase()] = false;
    }});

    canvas.addEventListener("mousemove", e => {{
      const rect = canvas.getBoundingClientRect();
      const cx = (e.clientX - rect.left) * (1280 / rect.width);
      const cy = (e.clientY - rect.top) * (760 / rect.height);
      state.hoveredHallLevel = -1;
      let overInteractive = false;
      if (state.scene === "campus") {{
        for (const s of OUTDOOR_LANDMARKS) {{
          if (Math.hypot(cx - s.x, cy - s.y) < 75) {{ overInteractive = true; break; }}
        }}
        for (const h of ACADEMIC_HALLS) {{
          if (cx >= h.x - h.w / 2 - 15 && cx <= h.x + h.w / 2 + 15 &&
              cy >= h.y - h.h - h.d / 2 - 20 && cy <= h.y + h.d / 2 + 15) {{
            state.hoveredHallLevel = h.level;
            overInteractive = true;
            break;
          }}
        }}
      }}
      canvas.style.cursor = overInteractive ? "pointer" : "default";
    }});

    canvas.addEventListener("click", e => {{
      const rect = canvas.getBoundingClientRect();
      const cx = (e.clientX - rect.left) * (1280 / rect.width);
      const cy = (e.clientY - rect.top) * (760 / rect.height);

      if (state.scene === "campus") {{
        for (const s of OUTDOOR_LANDMARKS) {{
          if (Math.hypot(cx - s.x, cy - s.y) < 75) {{
            walkToOutdoorStop(s.id, true);
            return;
          }}
        }}
        for (const h of ACADEMIC_HALLS) {{
          if (cx >= h.x - h.w / 2 - 15 && cx <= h.x + h.w / 2 + 15 &&
              cy >= h.y - h.h - h.d / 2 - 20 && cy <= h.y + h.d / 2 + 15) {{
            if (!isGateOpen()) {{
              startWalkToGateAmbush();
              return;
            }}
            switchScene("hall", h.level);
            return;
          }}
        }}
        if (!isGateOpen() && cy < 608) {{
          // Trying to click past the South Gate triggers Officer Rajan's ambush!
          startWalkToGateAmbush();
          return;
        }}
        state.player.targetX = cx;
        state.player.targetY = cy;
        state.player.pendingCallback = null;
      }} else {{
        const mods = getModulesForLevel(state.hallLevel);
        for (let i = 0; i < Math.min(HALL_ROOMS.length, mods.length); i++) {{
          const r = HALL_ROOMS[i];
          if (cx >= r.x && cx <= r.x + r.w && cy >= r.y && cy <= r.y + r.h) {{
            walkToHallClassroom(i);
            return;
          }}
        }}
        state.hallPlayer.targetX = cx;
        state.hallPlayer.targetY = cy;
      }}
    }});

    function triggerNearbyInteraction() {{
      if (state.scene === "campus") {{
        if (state.nearbyLandmark) {{
          openNpcDialogue(state.nearbyLandmark.id, 0);
          return;
        }}
        if (state.nearbyHall) {{
          if (!isGateOpen()) {{
            startWalkToGateAmbush();
          }} else {{
            switchScene("hall", state.nearbyHall.level);
          }}
          return;
        }}
        openNpcDialogue(state.activeStopId || "l0-what-is-an-llm", 0);
      }} else {{
        const mods = getModulesForLevel(state.hallLevel);
        if (state.nearbyRoomIdx >= 0 && mods[state.nearbyRoomIdx]) {{
          openLessonBook(mods[state.nearbyRoomIdx].id, "story");
        }}
      }}
    }}

    function updatePhysicsAndProximity() {{
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
        p.pendingCallback = null;
        const len = Math.hypot(dx, dy);
        let nx = p.x + (dx / len) * state.player.speed;
        let ny = p.y + (dy / len) * state.player.speed;
        if (state.scene === "campus" && !isGateOpen() && ny < 614) {{
          ny = 614;
          if (state.guardWhistleTimer <= 0 && !document.getElementById("rpg-dialogue-backdrop").classList.contains("open")) {{
            state.guardWhistleTimer = 95;
            openNpcDialogue("l0-what-is-an-llm", 0);
          }}
        }}
        p.x = Math.max(50, Math.min(1230, nx));
        p.y = Math.max(110, Math.min(735, ny));
        state.player.frame += 0.22;
      }} else if (p.targetX !== null && p.targetY !== null) {{
        const tx = p.targetX - p.x;
        const ty = p.targetY - p.y;
        const dist = Math.hypot(tx, ty);
        if (dist <= state.player.speed * 1.35) {{
          p.x = p.targetX;
          p.y = p.targetY;
          p.targetX = null;
          p.targetY = null;
          if (p.pendingCallback) {{
            const fn = p.pendingCallback;
            p.pendingCallback = null;
            fn();
          }}
        }} else {{
          p.x += (tx / dist) * state.player.speed * 1.15;
          p.y += (ty / dist) * state.player.speed * 1.15;
          state.player.frame += 0.24;
        }}
      }}

      // Animate 3D Karpathy Caricature & RPG Dialogue Portrait Canvases!
      if (document.getElementById("karpathy-call-toast").classList.contains("open")) {{
        draw3DCaricaturePortrait(karpathyAvatarCtx, 104, 104, "karpathy", state.tick);
      }}
      if (document.getElementById("rpg-dialogue-backdrop").classList.contains("open")) {{
        draw3DCaricaturePortrait(rpgPortraitCtx, 192, 192, state.activePortraitStyle, state.tick);
      }}

      const proxBtn = document.getElementById("proximity-btn");
      state.nearbyLandmark = null;
      state.nearbyHall = null;
      state.nearbyRoomIdx = -1;

      if (state.scene === "campus") {{
        for (const s of OUTDOOR_LANDMARKS) {{
          if (Math.hypot(state.player.x - s.x, state.player.y - s.y) <= s.interactRadius) {{
            state.nearbyLandmark = s;
            break;
          }}
        }}
        if (!state.nearbyLandmark) {{
          for (const h of ACADEMIC_HALLS) {{
            if (Math.hypot(state.player.x - h.x, state.player.y - h.y) <= 105) {{
              state.nearbyHall = h;
              break;
            }}
          }}
        }}

        document.querySelectorAll(".world-pin.pin-hidden-by-prox").forEach(el => el.classList.remove("pin-hidden-by-prox"));
        if (state.nearbyLandmark) {{
          const s = state.nearbyLandmark;
          const hiddenPin = document.querySelector(`.world-pin[data-stop-id="${{s.id}}"]`);
          if (hiddenPin) hiddenPin.classList.add("pin-hidden-by-prox");
          proxBtn.style.display = "inline-flex";
          proxBtn.style.left = ((state.player.x / 1280) * 100).toFixed(2) + "%";
          proxBtn.style.top = (((state.player.y - 46) / 760) * 100).toFixed(2) + "%";
          proxBtn.innerText = clearedIds.has(s.id)
            ? `✓ Revise with ${{s.npcName}} · Press E`
            : `👋 Talk to ${{s.npcName}} · Press E`;
        }} else if (state.nearbyHall) {{
          const h = state.nearbyHall;
          const hiddenHallPin = document.querySelector(`.world-pin[data-hall-level="${{h.level}}"]`);
          if (hiddenHallPin) hiddenHallPin.classList.add("pin-hidden-by-prox");
          proxBtn.style.display = "inline-flex";
          proxBtn.style.left = ((state.player.x / 1280) * 100).toFixed(2) + "%";
          proxBtn.style.top = (((state.player.y - 46) / 760) * 100).toFixed(2) + "%";
          proxBtn.innerText = `🏛️ Enter ${{h.name}} · Press E`;
        }} else {{
          proxBtn.style.display = "none";
        }}
      }} else {{
        const mods = getModulesForLevel(state.hallLevel);
        for (let i = 0; i < Math.min(HALL_ROOMS.length, mods.length); i++) {{
          const r = HALL_ROOMS[i];
          if (state.hallPlayer.x >= r.x - 20 && state.hallPlayer.x <= r.x + r.w + 20 &&
              state.hallPlayer.y >= r.y - 20 && state.hallPlayer.y <= r.y + r.h + 20) {{
            state.nearbyRoomIdx = i;
            break;
          }}
        }}
        if (state.nearbyRoomIdx >= 0 && mods[state.nearbyRoomIdx]) {{
          proxBtn.style.display = "inline-flex";
          proxBtn.style.left = ((state.hallPlayer.x / 1280) * 100).toFixed(2) + "%";
          proxBtn.style.top = (((state.hallPlayer.y - 44) / 760) * 100).toFixed(2) + "%";
          proxBtn.innerText = `📖 Open ${{mods[state.nearbyRoomIdx].title}} [Press E]`;
        }} else {{
          proxBtn.style.display = "none";
        }}
      }}
    }}

    function loop() {{
      updatePhysicsAndProximity();
      if (state.scene === "campus") drawCampusWorld();
      else drawHallInteriorWorld();
      requestAnimationFrame(loop);
    }}

    // =========================================================================
    // STORY-FIRST ILLUSTRATED CHAPTER BOOK & INTERACTIVE SIMULATORS
    // =========================================================================
    function openLessonBook(lessonId, initialTab = "story") {{
      state.activeStopId = lessonId;
      state.quizAnswers = {{}};
      refreshHudAndPins();

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
      switchBookTab(initialTab);
    }}

    function closeBookModal() {{
      document.getElementById("book-modal").classList.remove("open");
    }}

    function updateBookReadingProgress() {{
      const scroller = document.getElementById("bk-body-scroll");
      const bar = document.getElementById("bk-progress-bar");
      if (!scroller || !bar) return;
      const maxScroll = scroller.scrollHeight - scroller.clientHeight;
      const pct = maxScroll > 0 ? Math.min(100, Math.max(0, (scroller.scrollTop / maxScroll) * 100)) : 0;
      bar.style.width = pct.toFixed(1) + "%";
    }}

    function scrollBookTo(elId) {{
      const target = document.getElementById(elId);
      if (target) target.scrollIntoView({{ behavior: "smooth", block: "start" }});
    }}

    function switchBookTab(tabName) {{
      document.querySelectorAll(".book-tab").forEach(b => {{
        b.classList.toggle("active", b.getAttribute("data-tab") === tabName);
      }});
      document.querySelectorAll(".book-pane").forEach(p => p.classList.remove("active"));
      document.getElementById("bk-pane-" + tabName).classList.add("active");
      const scroller = document.getElementById("bk-body-scroll");
      if (scroller) scroller.scrollTop = 0;
      updateBookReadingProgress();
    }}

    function formatSimpleMarkdown(text) {{
      if (!text) return "";
      const inlineFmt = (s) => s
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/`([^`]+)`/g, "<code>$1</code>")
        .replace(/\\*\\*([^*]+)\\*\\*/g, "<strong>$1</strong>")
        .replace(/\\*([^*]+)\\*/g, "<em>$1</em>");

      const blocks = text.trim().split(/\\n\\n+/);
      return blocks.map(block => {{
        const lines = block.split("\\n").map(l => l.trim()).filter(Boolean);
        if (!lines.length) return "";
        if (lines.every(l => l.startsWith("- "))) {{
          return `<ul>${{lines.map(l => `<li>${{inlineFmt(l.slice(2))}}</li>`).join("")}}</ul>`;
        }}
        if (lines.every(l => /^\\d+\\.\\s/.test(l))) {{
          return `<ol>${{lines.map(l => `<li>${{inlineFmt(l.replace(/^\\d+\\.\\s*/, ""))}}</li>`).join("")}}</ol>`;
        }}
        if (lines.length === 1 && lines[0].startsWith("### ")) {{
          return `<h4 style="margin:0.9rem 0 0.35rem;font-family:var(--serif);font-size:1.12rem;color:var(--ink);">${{inlineFmt(lines[0].slice(4))}}</h4>`;
        }}
        return `<p>${{inlineFmt(lines.join(" "))}}</p>`;
      }}).join("");
    }}

    function buildInteractivePlayground(lessonId) {{
      if (lessonId === "l0-what-is-an-llm") {{
        return `
          <div class="playground-band" id="bk-playground">
            <div class="chapter-kicker">🎲 OFFICER RAJAN'S GUARD BOOTH SIMULATOR · TEMPERATURE + TOP-P NUCLEUS</div>
            <h3 style="margin:0.2rem 0 0.45rem;font-family:var(--serif);font-size:1.35rem;line-height:1.35;">Dial Temperature & Top-P to Watch Tail Pruning Live</h3>
            <p style="margin:0 0 0.85rem;font-size:0.94rem;color:var(--ink-soft);">
              Scoreboard after <code>"the server"</code>. Raise Temperature to <strong>1.8</strong> to see <code>"danced"</code> try to sneak onto the die — then slide <strong>Top-P</strong> to <strong>0.90</strong> to chop off the crazy tail! Keep rolling until <code>&lt;|eos|&gt;</code> ends the turn.
            </p>
            <div style="display:flex;gap:1rem;align-items:center;flex-wrap:wrap;margin-bottom:0.85rem;">
              <label style="font-family:var(--mono);font-size:0.82rem;font-weight:700;display:flex;align-items:center;gap:0.45rem;">
                Temp: <strong id="sim-l0-temp-val" style="color:var(--terracotta);min-width:28px;">1.0</strong>
                <input id="sim-l0-temp" type="range" min="0" max="2.0" step="0.1" value="1.0" oninput="updateL0Sim()" style="width:135px;accent-color:var(--terracotta);" />
              </label>
              <label style="font-family:var(--mono);font-size:0.82rem;font-weight:700;display:flex;align-items:center;gap:0.45rem;">
                Top-P: <strong id="sim-l0-topp-val" style="color:var(--meadow);min-width:34px;">0.90</strong>
                <input id="sim-l0-topp" type="range" min="0.20" max="1.00" step="0.05" value="0.90" oninput="updateL0Sim()" style="width:135px;accent-color:var(--meadow);" />
              </label>
              <button class="btn btn-primary" onclick="rollL0NextWord()">🎲 Roll & Glue Word →</button>
              <button class="btn" onclick="resetL0Sim()">↺ Reset</button>
            </div>
            <div id="sim-l0-bars" style="margin-bottom:0.8rem;"></div>
            <div style="background:#ffffff;padding:0.75rem 1rem;border-radius:10px;border:1.5px solid var(--line-strong);font-family:var(--mono);font-size:0.86rem;display:flex;justify-content:space-between;flex-wrap:wrap;gap:0.5rem;">
              <span>Relay Prompt: <strong id="sim-l0-sentence" style="color:var(--terracotta);">the server</strong></span>
              <span id="sim-l0-status" style="color:var(--meadow);font-weight:700;">Active · Rolling next token</span>
            </div>
          </div>
        `;
      }}
      if (lessonId === "l0-tokens") {{
        return `
          <div class="playground-band" id="bk-playground">
            <div class="chapter-kicker">🅿️ MAYA'S PARKING LOT CHOPPER · REGEX PRE-TOKENIZER & BPE BARCODES</div>
            <h3 style="margin:0.2rem 0 0.45rem;font-family:var(--serif);font-size:1.35rem;line-height:1.35;">Type Any Phrase or Pick a Preset to Inspect Its Barcodes</h3>
            <p style="margin:0 0 0.8rem;font-size:0.94rem;color:var(--ink-soft);">
              Try <code>"strawberry"</code> vs spaced <code>"s t r a w b e r r y"</code>, see how regex splits punctuation before BPE, or type Hindi / emojis to watch the fertility multiplier jump.
            </p>
            <div style="display:flex;gap:0.5rem;flex-wrap:wrap;margin-bottom:0.7rem;">
              <input id="sim-tok-input" class="sim-input" type="text" value="strawberry" oninput="inspectCustomTokenText(this.value)" placeholder="Type any word, Hindi text, code, or emoji..." />
              <button class="btn btn-primary" onclick="inspectTokenPreset('strawberry')">🍓 strawberry</button>
              <button class="btn" onclick="inspectTokenPreset('s t r a w b e r r y')">✨ Spaced Fix</button>
              <button class="btn" onclick="inspectTokenPreset('The server responded in 12ms.')">🇬🇧 English</button>
              <button class="btn" onclick="inspectTokenPreset('नमस्ते दुनिया')">🇮🇳 Hindi (3.3x)</button>
              <button class="btn" onclick="inspectTokenPreset('🚀🔥🤖')">🚀 Emojis (7.2x)</button>
            </div>
            <div id="sim-tok-chips" style="display:flex;gap:0.45rem;flex-wrap:wrap;margin-bottom:0.75rem;"></div>
            <div id="sim-tok-note" style="background:#ffffff;padding:0.75rem 1rem;border-radius:10px;border:1.5px solid var(--line-strong);font-family:var(--mono);font-size:0.84rem;"></div>
          </div>
        `;
      }}
      if (lessonId === "l0-embeddings") {{
        return `
          <div class="playground-band" id="bk-playground">
            <div class="chapter-kicker">☕ CHEF KABIR'S VECTOR ANGLE COMPASS · 4D CAFETERIA GPS</div>
            <h3 style="margin:0.2rem 0 0.45rem;font-family:var(--serif);font-size:1.35rem;line-height:1.35;">Measure Flashlight Angles Against Masala Chai (or Run Vector Math)</h3>
            <p style="margin:0 0 0.8rem;font-size:0.94rem;color:var(--ink-soft);">
              4D Cafeteria axes: <code>[drink, hot_temp, sweet_or_spiced, computer_tech]</code>. Watch the live angle compass + L2-normalized dot-product proof!
            </p>
            <div style="display:flex;gap:0.45rem;flex-wrap:wrap;margin-bottom:0.85rem;">
              <button class="btn btn-primary" onclick="inspectEmbeddingItem('filter_coffee')">☕ filter_coffee (9.7°)</button>
              <button class="btn" onclick="inspectEmbeddingItem('iced_chai')">🧊 iced_chai (Antonym Trap!)</button>
              <button class="btn" onclick="inspectEmbeddingItem('samosa')">🥟 samosa (34.8°)</button>
              <button class="btn" onclick="inspectEmbeddingItem('kubernetes')">☸️ kubernetes (88.2°)</button>
              <button class="btn btn-meadow" onclick="inspectEmbeddingItem('king_math')">👑 king - man + woman</button>
            </div>
            <canvas id="sim-emb-canvas" width="580" height="196" style="width:100%;max-width:580px;height:auto;display:block;margin:0 auto 0.75rem;background:#ffffff;border:1.5px solid var(--line-strong);border-radius:12px;"></canvas>
            <div id="sim-emb-output" style="background:#ffffff;padding:0.8rem 1rem;border-radius:10px;border:1.5px solid var(--line-strong);font-family:var(--mono);font-size:0.83rem;white-space:pre-line;"></div>
          </div>
        `;
      }}
      if (lessonId === "l0-context-window") {{
        return `
          <div class="playground-band" id="bk-playground">
            <div class="chapter-kicker">⛲ PROF. MEERA'S LUNCH TRAY · SLIDING WINDOW, KV CACHE & U-CURVE</div>
            <h3 style="margin:0.2rem 0 0.45rem;font-family:var(--serif);font-size:1.35rem;line-height:1.35;">Watch Code 7492 Slide Off the 24-Word Tray & Compare KV Caching</h3>
            <p style="margin:0 0 0.8rem;font-size:0.94rem;color:var(--ink-soft);">
              Step through Turns 1 → 4 on the 24-word tray, inspect the <strong>81.0% KV Prefix Cache</strong> billing discount, or plot the 10-chunk U-curve!
            </p>
            <div style="display:flex;gap:0.45rem;flex-wrap:wrap;margin-bottom:0.85rem;">
              <button class="btn btn-primary" onclick="inspectTrayStep(1)">Turn 1 (8/24)</button>
              <button class="btn" onclick="inspectTrayStep(2)">Turn 2 (16/24)</button>
              <button class="btn" onclick="inspectTrayStep(3)">Turn 3 (24/24 FULL)</button>
              <button class="btn" onclick="inspectTrayStep(4)">Turn 4 (7492 Dropped!)</button>
              <button class="btn btn-meadow" onclick="inspectTrayStep(5)">⚡ KV Cache (-81%)</button>
              <button class="btn" onclick="inspectTrayStep(6)">📉 U-Curve Recall</button>
            </div>
            <div id="sim-ctx-output" style="background:#ffffff;padding:0.9rem 1rem;border-radius:10px;border:1.5px solid var(--line-strong);font-family:var(--mono);font-size:0.83rem;"></div>
          </div>
        `;
      }}
      return "";
    }}

    function renderSeededLessonBook(mod, lesson, stop, unlocked, cleared) {{
      const figsById = {{}};
      (lesson.figures || []).forEach(f => {{ figsById[f.id] = f; }});

      const tocChips = [
        `<button class="toc-chip" onclick="scrollBookTo('bk-playground')">⚡ Playground</button>`,
        ...(lesson.sections || []).map((sec, idx) =>
          `<button class="toc-chip" onclick="scrollBookTo('bk-sec-${{idx}}')">0${{idx + 1}} · ${{sec.badge || 'Part ' + (idx + 1)}}</button>`
        ),
        `<button class="toc-chip" onclick="scrollBookTo('bk-jargon')">📚 Jargon</button>`
      ].join("");

      const chaptersHtml = (lesson.sections || []).map((sec, idx) => {{
        let figHtml = "";
        if (sec.figure_id && figsById[sec.figure_id]) {{
          const f = figsById[sec.figure_id];
          figHtml = `
            <div class="inline-figure">
              <img src="lessons/${{lesson.id}}/${{f.id}}.svg" alt="${{f.title}}" style="width:100%;height:auto;display:block;border-radius:8px;" />
              <div style="display:flex;justify-content:space-between;align-items:center;margin-top:0.65rem;padding-top:0.5rem;border-top:1.5px dashed var(--line-strong);font-size:0.82rem;color:var(--ink-soft);flex-wrap:wrap;gap:0.5rem;">
                <span><strong>📐 ${{f.title}}:</strong> ${{f.caption}}</span>
                <a href="lessons/${{lesson.id}}/${{f.id}}.excalidraw" download style="font-family:var(--mono);color:var(--terracotta);font-weight:700;">⬇ .excalidraw</a>
              </div>
            </div>
          `;
        }}
        const expertHtml = sec.expert_note ? `
          <div class="callout-box callout-expert">
            <div class="callout-title">⚙️ Under the Hood · Production Depth</div>
            <div>${{formatSimpleMarkdown(sec.expert_note)}}</div>
          </div>
        ` : "";
        const trapHtml = sec.trap_note ? `
          <div class="callout-box callout-trap">
            <div class="callout-title">⚠️ Production Engineering Trap</div>
            <div>${{formatSimpleMarkdown(sec.trap_note)}}</div>
          </div>
        ` : "";
        const calloutsHtml = (expertHtml || trapHtml) ? `<div class="callout-grid">${{expertHtml}}${{trapHtml}}</div>` : "";
        return `
          <section class="story-section" id="bk-sec-${{idx}}">
            <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:0.5rem;">
              <span class="chapter-kicker">PART 0${{idx + 1}}</span>
              <span class="tag tag-amber">${{sec.badge || ''}}</span>
            </div>
            <h3 class="chapter-heading">${{sec.heading}}</h3>
            <div class="chapter-prose">${{formatSimpleMarkdown(sec.body_md)}}</div>
            ${{figHtml}}
            ${{calloutsHtml}}
          </section>
        `;
      }}).join("");

      const jargonRows = (lesson.jargon_decoder || []).map(j => `
        <tr>
          <td><strong style="color:var(--terracotta);font-family:var(--serif);font-size:1.05rem;">${{j.term}}</strong></td>
          <td>${{j.plain_words}}</td>
          <td style="color:var(--muted);">${{j.why_you_care}}</td>
        </tr>
      `).join("");

      document.getElementById("bk-pane-story").innerHTML = `
        <div style="border:1.5px solid var(--line-strong);padding:0.85rem 1.15rem;margin-bottom:1.2rem;background:var(--paper);border-radius:12px;">
          <div style="font-family:var(--serif);font-size:1.3rem;line-height:1.4;font-style:italic;color:var(--terracotta);margin-bottom:0.35rem;">
            “${{lesson.question}}”
          </div>
          <div style="font-size:1.02rem;color:var(--ink);">
            <strong>The Big Picture:</strong> ${{lesson.one_line}}
          </div>
        </div>

        <div class="chapter-toc">${{tocChips}}</div>

        ${{buildInteractivePlayground(lesson.id)}}

        ${{chaptersHtml}}

        <h3 class="chapter-heading" id="bk-jargon" style="margin-top:2.25rem;">Plain-English Jargon Decoder</h3>
        <table class="jargon-table">
          <thead><tr><th>Term</th><th>In Plain Words</th><th>Why You Care</th></tr></thead>
          <tbody>${{jargonRows}}</tbody>
        </table>

        <div style="text-align:center;margin-top:2rem;">
          <button class="btn btn-primary" style="font-size:0.96rem;padding:0.75rem 1.6rem;" onclick="switchBookTab('gate')">
            ${{cleared ? '🔁 Practice the 3-Question Checkpoint Check Again →' : '🚧 Ready? Take the 3-Question Checkpoint Gate Test →'}}
          </button>
        </div>
      `;

      const lab = lesson.lab;
      const accList = (lab.acceptance || []).map(a => `
        <li style="margin-bottom:0.5rem;">
          <strong>${{a.criterion}}</strong>
          <div style="font-family:var(--mono);font-size:0.78rem;color:var(--meadow);">✓ Verified proof: ${{a.evidence}}</div>
        </li>
      `).join("");

      document.getElementById("bk-pane-lab").innerHTML = `
        <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:0.75rem;margin-bottom:1rem;">
          <div>
            <div class="chapter-kicker">PURE PYTHON HANDS-ON LAB (ZERO API KEYS)</div>
            <h3 class="chapter-heading" style="margin:0.2rem 0;">${{lab.title}}</h3>
          </div>
          <a class="btn btn-primary" href="lessons/${{lesson.id}}/${{lab.code_file}}" download>⬇ Download ${{lab.code_file}}</a>
        </div>
        <p style="font-size:1rem;color:var(--ink-soft);">${{lab.goal}}</p>
        <ul style="padding-left:1.25rem;margin-bottom:1.5rem;">${{accList}}</ul>
        <h4 style="font-family:var(--mono);font-size:0.82rem;color:var(--meadow);margin-top:1.5rem;">REAL VERIFIED TERMINAL OUTPUT (EXIT CODE 0)</h4>
        <pre><code>${{lab.real_output}}</code></pre>
        <h4 style="font-family:var(--mono);font-size:0.82rem;color:var(--terracotta);margin-top:1.5rem;">COMPLETE SOURCE CODE (${{lab.code_file}})</h4>
        <pre><code>${{(lesson.code_text || "").replace(/</g, "&lt;")}}</code></pre>
      `;

      const questions = lesson.gate_challenge || [];
      const qHtml = questions.map((qObj, qIdx) => {{
        const opts = qObj.options.map((opt, oIdx) => `
          <button class="quiz-option" id="q-${{qIdx}}-opt-${{oIdx}}" onclick="selectQuizAnswer(${{qIdx}}, ${{oIdx}})">
            ${{opt}}
          </button>
        `).join("");
        return `
          <div class="story-section" style="padding:1.25rem 0;">
            <div style="font-weight:800;font-size:1.04rem;margin-bottom:0.85rem;">${{qObj.q}}</div>
            ${{opts}}
            <div id="q-${{qIdx}}-feedback" style="display:none;margin-top:0.55rem;font-size:0.9rem;font-weight:700;padding:0.65rem 0.9rem;border-radius:10px;"></div>
          </div>
        `;
      }}).join("");

      document.getElementById("bk-pane-gate").innerHTML = `
        <div class="playground-band" style="margin-top:0;">
          <div class="chapter-kicker">${{cleared ? '✓ CHECKPOINT CLEARED · PRACTICE MODE' : '🚧 CAMPUS CHECKPOINT BOSS CHECK'}}</div>
          <h3 style="margin:0.2rem 0 0.35rem;font-family:var(--serif);font-size:1.4rem;line-height:1.35;">
            ${{cleared ? 'Re-test Your Mastery Anytime (Progress Saved)' : 'Pass All 3 Questions to Unlock the Next Campus Stop'}}
          </h3>
          <p style="margin:0;font-size:0.95rem;color:var(--ink-soft);">
            Every answer comes straight from the story and the verified Python lab output.
          </p>
        </div>
        ${{qHtml}}
        <div id="gate-success-banner"></div>
      `;

      const sh = lesson.shareable;
      const tweetsHtml = (sh.x_thread || []).map(t => `
        <div style="padding:1rem 0;border-bottom:1.5px solid var(--line);display:flex;justify-content:space-between;gap:1rem;align-items:flex-start;">
          <div style="white-space:pre-line;font-size:0.95rem;">${{t}}</div>
          <button class="btn" onclick="navigator.clipboard.writeText(this.previousElementSibling.innerText);this.innerText='Copied!'">Copy</button>
        </div>
      `).join("");

      const igHtml = (sh.instagram_carousel || []).map(s => `
        <div class="ig-slide">
          <div style="font-family:var(--mono);font-size:0.78rem;font-weight:700;color:var(--terracotta);">SLIDE 0${{s.slide}} · ${{sh.notebook_shelf}}</div>
          <div>
            <h4 style="font-family:var(--serif);font-size:1.18rem;line-height:1.35;margin:0.35rem 0;color:var(--ink);">${{s.headline}}</h4>
            <p style="font-size:0.86rem;color:var(--ink-soft);margin:0;white-space:pre-line;">${{s.body}}</p>
          </div>
          <div style="font-family:var(--mono);font-size:0.76rem;color:var(--muted);border-top:1.5px solid var(--line-strong);padding-top:0.4rem;display:flex;justify-content:space-between;">
            <span>@ashwinYardi</span><span>Bits University</span>
          </div>
        </div>
      `).join("");

      document.getElementById("bk-pane-share").innerHTML = `
        <div class="playground-band" style="margin-top:0;">
          <div class="chapter-kicker">🏆 SHAREABLE FIELD NOTE · ${{sh.notebook_shelf}}</div>
          <h3 style="font-family:var(--serif);font-size:1.5rem;line-height:1.35;margin:0.25rem 0;">${{lesson.title}}</h3>
          <p style="font-family:var(--serif);font-style:italic;font-size:1.18rem;line-height:1.4;color:var(--terracotta);margin:0.5rem 0 0.85rem;">
            “${{sh.the_turn}}”
          </p>
          <div style="font-size:0.92rem;color:var(--ink-soft);margin-bottom:0.95rem;">
            <strong>60-Second Reel / Short Hook:</strong> ${{sh.reel_hook}}
          </div>
          <div style="display:flex;gap:0.65rem;flex-wrap:wrap;">
            <button class="btn btn-primary" onclick="copyFullXThread()">📋 Copy Complete X Thread (${{sh.x_thread.length}} posts)</button>
            <button class="btn" onclick="copyTurnQuote()">📋 Copy 'The Turn' Quote</button>
          </div>
        </div>
        <h3 class="chapter-heading">Ready-to-Post X Thread</h3>
        ${{tweetsHtml}}
        <h3 class="chapter-heading" style="margin-top:2rem;">4:5 Instagram Carousel Deck</h3>
        <div class="ig-deck">${{igHtml}}</div>
      `;

      if (lesson.id === "l0-what-is-an-llm") {{ resetL0Sim(); }}
      if (lesson.id === "l0-tokens") inspectTokenPreset("strawberry");
      if (lesson.id === "l0-embeddings") inspectEmbeddingItem("filter_coffee");
      if (lesson.id === "l0-context-window") inspectTrayStep(1);
    }}

    function renderSyllabusPreviewBook(mod, unlocked, cleared) {{
      if (!mod) return;
      document.getElementById("bk-pane-story").innerHTML = `
        <section class="story-section">
          <div class="chapter-kicker">SELF-EXPANDING UNIVERSITY BLUEPRINT · HALL ${{mod.level}}</div>
          <h3 class="chapter-heading">${{mod.title}}</h3>
          <p style="font-family:var(--serif);font-style:italic;font-size:1.2rem;line-height:1.4;color:var(--terracotta);">“${{mod.question}}”</p>
          <p><strong>What you can build after clearing this lab:</strong> ${{mod.can}}</p>
          <p><strong>Hands-on Python Lab Specification:</strong> ${{mod.exercise}}</p>
          <p style="font-family:var(--mono);font-size:0.84rem;color:var(--muted);">Jargon decoded in this room: ${{(mod.jargon || []).join(", ")}}</p>
        </section>
      `;
      document.getElementById("bk-pane-lab").innerHTML = `<p>Lab specification: ${{mod.exercise}}</p>`;
      document.getElementById("bk-pane-gate").innerHTML = `<p>Clear the 4 outdoor Rung 0 campus checkpoints first so the University cranes unlock this hall classroom!</p>`;
      document.getElementById("bk-pane-share").innerHTML = `<p>Share cards mint as soon as this classroom's lab is completed.</p>`;
    }}

    // =========================================================================
    // 4 LIVE INTERACTIVE MECHANISM PLAYGROUNDS (V6 UPGRADED)
    // =========================================================================
    const L0_LOGITS = {{
      "the server": {{"crashed": 3.2, "responded": 2.9, "timed": 2.4, "melted": 0.4, "danced": -1.5}},
      "server crashed": {{"because": 3.6, "after": 2.5, "at": 1.8, "<|eos|>": 1.1}},
      "server responded": {{"in": 3.4, "with": 2.8, "<|eos|>": 1.6, "slowly": 1.1}},
      "server timed": {{"out": 4.5, "<|eos|>": 1.2, "twice": 0.8}},
      "timed out": {{"<|eos|>": 3.9, "after": 2.6, "again": 1.7}},
      "responded in": {{"12ms": 3.8, "time": 2.4, "seconds": 1.9}},
      "in 12ms": {{"<|eos|>": 4.2, "with": 2.1, "today": 1.3}},
      "crashed because": {{"memory": 3.5, "disk": 2.9, "traffic": 2.6}}
    }};
    let simL0Words = ["the", "server"];
    let simL0Ended = false;

    function computeL0Probs(logits, temp, topP) {{
      const entries = Object.entries(logits);
      let rawProbs = {{}};
      if (temp <= 0.01) {{
        let best = entries[0][0], bestV = entries[0][1];
        entries.forEach(([k, v]) => {{ if (v > bestV) {{ best = k; bestV = v; }} }});
        entries.forEach(([k]) => rawProbs[k] = (k === best ? 1.0 : 0.0));
      }} else {{
        const scaled = entries.map(([k, v]) => [k, v / temp]);
        const maxL = Math.max(...scaled.map(x => x[1]));
        const exps = scaled.map(([k, v]) => [k, Math.exp(v - maxL)]);
        const sum = exps.reduce((a, b) => a + b[1], 0);
        exps.forEach(([k, e]) => rawProbs[k] = e / sum);
      }}
      const sorted = Object.entries(rawProbs).sort((a, b) => b[1] - a[1]);
      let cum = 0;
      const kept = {{}};
      const pruned = new Set();
      for (const [tok, p] of sorted) {{
        if (Object.keys(kept).length === 0 || cum < topP) {{
          kept[tok] = p;
          cum += p;
        }} else {{
          pruned.add(tok);
        }}
      }}
      const kSum = Object.values(kept).reduce((a, b) => a + b, 0) || 1;
      const finalProbs = {{}};
      sorted.forEach(([tok]) => {{
        finalProbs[tok] = pruned.has(tok) ? 0 : (kept[tok] / kSum);
      }});
      return {{ sorted, rawProbs, finalProbs, pruned }};
    }}

    function updateL0Sim() {{
      const slider = document.getElementById("sim-l0-temp");
      const toppSlider = document.getElementById("sim-l0-topp");
      if (!slider || !toppSlider) return;
      const temp = parseFloat(slider.value);
      const topP = parseFloat(toppSlider.value);
      document.getElementById("sim-l0-temp-val").innerText = temp.toFixed(1);
      document.getElementById("sim-l0-topp-val").innerText = topP.toFixed(2);
      const key = simL0Words.slice(-2).join(" ");
      const logits = L0_LOGITS[key] || {{"<|eos|>": 3.4, "and": 2.1, "recovered": 2.4, "cleanly": 1.6}};
      const {{ sorted, finalProbs, pruned }} = computeL0Probs(logits, temp, topP);
      const barsEl = document.getElementById("sim-l0-bars");
      barsEl.innerHTML = sorted.map(([tok]) => {{
        const isPruned = pruned.has(tok);
        const pct = (finalProbs[tok] * 100).toFixed(1);
        const barColor = isPruned ? "#cbd5e1" : (tok === "<|eos|>" ? "#2c6b4f" : "var(--terracotta)");
        return `<div style="display:grid;grid-template-columns:108px 78px 1fr 94px;gap:0.55rem;align-items:center;font-family:var(--mono);font-size:0.82rem;margin-bottom:0.35rem;opacity:${{isPruned ? 0.55 : 1}};">
          <strong>${{tok.replace(/</g, "&lt;").replace(/>/g, "&gt;")}}</strong>
          <span style="color:var(--muted);">z=${{logits[tok].toFixed(1)}}</span>
          <div style="background:#ffffff;height:14px;border-radius:6px;overflow:hidden;border:1.5px solid var(--line-strong);">
            <div style="background:${{barColor}};height:100%;width:${{pct}}%;transition:width 140ms ease-out;"></div>
          </div>
          <span style="text-align:right;font-weight:700;color:${{isPruned ? '#64748b' : 'var(--ink)'}};">${{isPruned ? 'PRUNED' : pct + '%'}}</span>
        </div>`;
      }}).join("");
      document.getElementById("sim-l0-sentence").innerText = simL0Words.join(" ");
      const stEl = document.getElementById("sim-l0-status");
      if (stEl) {{
        stEl.innerText = simL0Ended ? "⏹ Stopped on <|eos|> (Click Reset)" : `Nucleus kept: ${{sorted.length - pruned.size}}/${{sorted.length}} tokens`;
        stEl.style.color = simL0Ended ? "var(--terracotta)" : "var(--meadow)";
      }}
    }}

    function rollL0NextWord() {{
      if (simL0Ended) {{ resetL0Sim(); return; }}
      const temp = parseFloat(document.getElementById("sim-l0-temp").value);
      const topP = parseFloat(document.getElementById("sim-l0-topp").value);
      const key = simL0Words.slice(-2).join(" ");
      const logits = L0_LOGITS[key] || {{"<|eos|>": 3.4, "and": 2.1, "recovered": 2.4, "cleanly": 1.6}};
      const {{ finalProbs }} = computeL0Probs(logits, temp, topP);
      let r = Math.random(), acc = 0, pick = Object.keys(finalProbs)[0];
      for (const [t, p] of Object.entries(finalProbs)) {{
        acc += p;
        if (r <= acc && p > 0) {{ pick = t; break; }}
      }}
      simL0Words.push(pick);
      if (pick === "<|eos|>" || simL0Words.length >= 10) simL0Ended = true;
      updateL0Sim();
    }}

    function resetL0Sim() {{
      simL0Words = ["the", "server"];
      simL0Ended = false;
      updateL0Sim();
    }}

    const TOKEN_PRESETS = {{
      "strawberry": {{
        pieces: [["str", 496], ["aw", 675], ["berry", 15717]],
        note: "10 chars → 3 barcodes (0.30 tok/char). Barcode #15717 ('berry') seals TWO 'r' letters inside one integer!"
      }},
      "s t r a w b e r r y": {{
        pieces: [["s", 82], [" t", 259], [" r", 436], [" a", 264], [" w", 289], [" b", 293], [" e", 384], [" r", 436], [" r", 436], [" y", 379]],
        note: "Spaced Fix: Every letter gets its own barcode! Barcode #436 (' r') appears 3 distinct times, so the model counts 3 'r's cleanly."
      }},
      "The server responded in 12ms.": {{
        pieces: [["The", 791], [" server", 3585], [" responded", 31574], [" in", 304], [" ", 220], ["12", 717], ["ms", 1294], [".", 13]],
        note: "29 chars → 8 barcodes (0.28 tok/char · 1.0x baseline). Notice how regex pre-tokenization isolates '12' and '.' BEFORE BPE!"
      }},
      "नमस्ते दुनिया": {{
        pieces: [["न", 28001], ["म", 44102], ["स", 31902], ["्", 11904], ["त", 29501], ["े", 19822], [" द", 85120], ["ु", 22911], ["न", 28001], ["ि", 18312], ["य", 34112], ["ा", 15209]],
        note: "13 chars → 12 barcodes (0.92 tok/char · 3.3x cost & latency tax vs English in cl100k!)."
      }},
      "🚀🔥🤖": {{
        pieces: [["🚀", 9468], ["<0xF0>", 242], ["🔥", 9469], ["<0x9F>", 161], ["🤖", 99812], ["<0x96>", 152]],
        note: "3 emojis → 6 byte-fallback barcodes (2.00 tok/char · 7.2x fertility multiplier!)."
      }}
    }};

    function renderTokenChips(pieces, noteText) {{
      const chipsEl = document.getElementById("sim-tok-chips");
      if (!chipsEl) return;
      const colors = ["#a9492f", "#355f73", "#2c6b4f", "#655670", "#8b6842"];
      chipsEl.innerHTML = pieces.map(([txt, id], i) => {{
        const c = colors[i % colors.length];
        const safe = String(txt).replace(/</g, "&lt;").replace(/>/g, "&gt;");
        return `<div style="background:#ffffff;border:1.5px solid ${{c}};border-bottom:3px solid ${{c}};border-radius:10px;padding:0.32rem 0.68rem;font-family:var(--mono);font-size:0.82rem;">
          <strong>"${{safe}}"</strong> <span style="color:var(--muted);font-size:0.76rem;">#${{id}}</span>
        </div>`;
      }}).join("");
      document.getElementById("sim-tok-note").innerText = noteText;
    }}

    function inspectTokenPreset(key) {{
      const inp = document.getElementById("sim-tok-input");
      if (inp) inp.value = key;
      const preset = TOKEN_PRESETS[key];
      if (preset) renderTokenChips(preset.pieces, preset.note);
    }}

    function inspectCustomTokenText(raw) {{
      if (!raw) {{
        renderTokenChips([], "Type any phrase above to inspect regex pre-tokenization + BPE barcode chopping.");
        return;
      }}
      if (TOKEN_PRESETS[raw]) {{
        renderTokenChips(TOKEN_PRESETS[raw].pieces, TOKEN_PRESETS[raw].note);
        return;
      }}
      const pieces = [];
      const regex = / ?[A-Za-z]+| ?[0-9]{{1,3}}| ?[^\\sA-Za-z0-9]+|\\s+/g;
      const chunks = raw.match(regex) || [raw];
      for (const ch of chunks) {{
        if (/^ ?[A-Za-z]+$/.test(ch) && ch.length > 7) {{
          const mid = Math.ceil(ch.length * 0.55);
          [ch.slice(0, mid), ch.slice(mid)].forEach(sub => {{
            let h = 256;
            for (let i = 0; i < sub.length; i++) h = (h * 33 + sub.charCodeAt(i)) % 98000;
            pieces.push([sub, 256 + h]);
          }});
        }} else if (/[^\\x00-\\x7F]/.test(ch)) {{
          for (const cp of Array.from(ch)) {{
            const bytes = new TextEncoder().encode(cp);
            if (bytes.length >= 4) {{
              pieces.push([cp, 9000 + (cp.codePointAt(0) % 900)]);
              pieces.push([`<0x${{bytes[1].toString(16).toUpperCase()}}>`, bytes[1]]);
            }} else {{
              pieces.push([cp, 15000 + (cp.charCodeAt(0) % 70000)]);
            }}
          }}
        }} else {{
          let h = 256;
          for (let i = 0; i < ch.length; i++) h = (h * 31 + ch.charCodeAt(i)) % 95000;
          pieces.push([ch, 256 + h]);
        }}
      }}
      const ratio = (pieces.length / Math.max(1, Array.from(raw).length));
      const mult = (ratio / 0.28).toFixed(1);
      renderTokenChips(
        pieces,
        `Custom Input: ${{Array.from(raw).length}} chars → ${{pieces.length}} barcodes (${{ratio.toFixed(2)}} tok/char · ~${{mult}}x vs English baseline). Notice punctuation & 3-digit numbers are split by regex before BPE!`
      );
    }}

    function drawEmbeddingCompass(targetLabel, deg, cosVal, accentColor) {{
      const cv = document.getElementById("sim-emb-canvas");
      if (!cv) return;
      const c = cv.getContext("2d");
      const W = cv.width, H = cv.height;
      c.clearRect(0, 0, W, H);
      c.fillStyle = "#fbfaf7";
      c.fillRect(0, 0, W, H);

      const ox = 86, oy = 162, R = 128;
      // Subtle polar grid arcs
      c.strokeStyle = "#e4dfd5";
      c.lineWidth = 1;
      [0.45, 0.75, 1.0].forEach(f => {{
        c.beginPath();
        c.arc(ox, oy, R * f, -Math.PI * 0.52, 0.04);
        c.stroke();
      }});
      // 0° and 90° axes
      c.strokeStyle = "#cbd5e1";
      c.beginPath();
      c.moveTo(ox, oy); c.lineTo(ox + R + 18, oy);
      c.moveTo(ox, oy); c.lineTo(ox, oy - R - 14);
      c.stroke();

      // Angle arc sector
      const rad = (deg * Math.PI) / 180;
      c.fillStyle = "rgba(169, 73, 47, 0.12)";
      c.beginPath();
      c.moveTo(ox, oy);
      c.arc(ox, oy, 54, -rad, 0);
      c.closePath();
      c.fill();
      c.strokeStyle = accentColor;
      c.lineWidth = 1.8;
      c.beginPath();
      c.arc(ox, oy, 54, -rad, 0);
      c.stroke();

      // Base vector (0°): masala_chai (or target queen)
      const baseLabel = targetLabel === "queen" ? "king - man + woman" : "masala_chai (ref)";
      c.strokeStyle = "#2c6b4f";
      c.lineWidth = 3;
      c.beginPath();
      c.moveTo(ox, oy); c.lineTo(ox + R, oy);
      c.stroke();
      c.fillStyle = "#2c6b4f";
      c.beginPath(); c.arc(ox + R, oy, 5, 0, Math.PI * 2); c.fill();
      c.font = "700 12px 'IBM Plex Mono', monospace";
      c.fillText(baseLabel, ox + R + 10, oy + 4);

      // Compared vector at exact angle
      const tx = ox + Math.cos(rad) * R;
      const ty = oy - Math.sin(rad) * R;
      c.strokeStyle = accentColor;
      c.lineWidth = 3;
      c.beginPath();
      c.moveTo(ox, oy); c.lineTo(tx, ty);
      c.stroke();
      c.fillStyle = accentColor;
      c.beginPath(); c.arc(tx, ty, 5.5, 0, Math.PI * 2); c.fill();
      c.fillText(`${{targetLabel}} (${{deg.toFixed(1)}}°)`, tx + 10, ty + 4);

      // Score readout box on the right
      c.fillStyle = "#ffffff";
      c.strokeStyle = "#d9d2c5";
      c.lineWidth = 1.5;
      c.beginPath();
      c.roundRect(356, 22, 204, 108, 10);
      c.fill();
      c.stroke();
      c.fillStyle = "#64748b";
      c.font = "700 11px 'IBM Plex Mono', monospace";
      c.fillText("COSINE SIMILARITY", 372, 46);
      c.fillStyle = accentColor;
      c.font = "800 28px 'Bricolage Grotesque', sans-serif";
      c.fillText(`+${{cosVal.toFixed(4)}}`, 372, 82);
      c.fillStyle = "#334155";
      c.font = "600 11.5px 'IBM Plex Mono', monospace";
      c.fillText(`Angle θ = ${{deg.toFixed(1)}}°`, 372, 104);
      c.fillText(`L2 dot(û,v̂) = ${{cosVal.toFixed(4)}}`, 372, 120);
    }}

    function inspectEmbeddingItem(key) {{
      const el = document.getElementById("sim-emb-output");
      if (!el) return;
      const items = {{
        "filter_coffee": {{
          label: "filter_coffee", deg: 9.7, cos: 0.9858, color: "#2c6b4f",
          text: "masala_chai [0.95, 0.90, 0.85, 0.02] vs filter_coffee [0.95, 0.92, 0.55, 0.02]\\n→ Cosine = +0.9858 (9.7° apart) · L2-normalized dot product = +0.985850!\\n→ Sitting at the exact same Cafeteria Hot-Drinks table."
        }},
        "iced_chai": {{
          label: "iced_chai", deg: 34.6, cos: 0.8234, color: "#a9492f",
          text: "masala_chai [0.95, 0.90, 0.85, 0.02] vs iced_chai [0.95, 0.05, 0.85, 0.02]\\n→ Cosine = +0.8234 (34.6°) — THE ANTONYM TRAP!\\n→ Hot & Cold are opposites, yet they still score 0.8234 because they share the drink & spice axes!"
        }},
        "samosa": {{
          label: "samosa", deg: 34.8, cos: 0.8216, color: "#8b6842",
          text: "masala_chai [0.95, 0.90, 0.85, 0.02] vs samosa [0.15, 0.80, 0.85, 0.02]\\n→ Cosine = +0.8216 (34.8°) · Same warm Indian snack table, lower on the drink axis."
        }},
        "kubernetes": {{
          label: "kubernetes", deg: 88.2, cos: 0.0322, color: "#355f73",
          text: "masala_chai [0.95, 0.90, 0.85, 0.02] vs kubernetes [0.01, 0.01, 0.01, 0.99]\\n→ Cosine = +0.0322 (88.2° — nearly perpendicular!). Completely unrelated cloud-infra table."
        }},
        "king_math": {{
          label: "queen", deg: 0.0, cos: 1.0000, color: "#655670",
          text: "Vector Walk: king [0.95, 0.95, 0.05, 0.05] - man [0.05, 0.95, 0.05, 0.05] + woman [0.05, 0.05, 0.95, 0.05]\\n→ Target = [0.95, 0.05, 0.95, 0.05] == queen! Cosine = +1.0000 (0.0° exact direction match!)"
        }}
      }};
      const item = items[key] || items.filter_coffee;
      drawEmbeddingCompass(item.label, item.deg, item.cos, item.color);
      el.innerText = item.text;
    }}

    function inspectTrayStep(step) {{
      const el = document.getElementById("sim-ctx-output");
      if (!el) return;
      const t1 = ["User:", "Remember", "secret", "locker", "code", "7492", "for", "tomorrow."];
      const t2 = ["AI:", "Got", "it,", "I", "saved", "your", "locker", "code."];
      const t3 = ["User:", "Also", "pack", "two", "masala", "dosa", "boxes", "please."];
      const t4 = ["AI:", "Packed", "two", "masala", "dosa", "boxes", "for", "lunch", "today!", "Enjoy!"];

      const renderTray = (kept, dropped, title, statusHtml) => {{
        const dropHtml = dropped.length ? `
          <div style="margin-top:0.55rem;font-size:0.78rem;color:#991b1b;font-weight:700;">🗑 DROPPED OFF LEFT EDGE (${{dropped.length}} words):</div>
          <div class="tray-slot-grid">${{dropped.map(w => `<span class="tray-word dropped">${{w}}</span>`).join("")}}</div>
        ` : "";
        const keepHtml = `
          <div style="margin-top:0.55rem;font-size:0.78rem;color:var(--meadow);font-weight:700;">🍱 ACTIVE ON 24-WORD LUNCH TRAY (${{kept.length}} / 24):</div>
          <div class="tray-slot-grid">${{kept.map(w => `<span class="tray-word ${{w === '7492' ? 'secret' : ''}}">${{w}}</span>`).join("")}}</div>
        `;
        el.innerHTML = `<div style="font-weight:800;margin-bottom:0.35rem;">${{title}}</div>${{statusHtml}}${{dropHtml}}${{keepHtml}}`;
      }};

      if (step === 1) {{
        renderTray(t1, [], "TURN 1 · 8 / 24 words used", `<div style="color:var(--meadow);font-weight:700;">Locker code 7492 on tray? YES ✅</div>`);
      }} else if (step === 2) {{
        renderTray([...t1, ...t2], [], "TURN 2 · 16 / 24 words used (entire Turn 1 re-sent!)", `<div style="color:var(--meadow);font-weight:700;">Locker code 7492 on tray? YES ✅</div>`);
      }} else if (step === 3) {{
        renderTray([...t1, ...t2, ...t3], [], "TURN 3 · 24 / 24 words (TRAY 100% FULL!)", `<div style="color:#b45309;font-weight:700;">Locker code 7492 on tray? YES ⚠️ (Sitting right on the left cliff!)</div>`);
      }} else if (step === 4) {{
        const all = [...t1, ...t2, ...t3, ...t4];
        renderTray(all.slice(-24), all.slice(0, all.length - 24), "TURN 4 · 34 total words → 10 oldest words evicted!", `<div style="color:#991b1b;font-weight:700;">Locker code 7492 on tray? NO ❌ (Model literally never receives it!)</div>`);
      }} else if (step === 5) {{
        el.innerHTML = `
          <div style="font-weight:800;margin-bottom:0.55rem;">⚡ 10-TURN CHAT BILLING · UNCACHED vs KV PREFIX CACHING (1,000-tok system prompt)</div>
          <div style="margin-bottom:0.55rem;">
            <div style="display:flex;justify-content:space-between;font-size:0.8rem;margin-bottom:0.2rem;"><span>Without KV Prefix Cache (re-billed every turn)</span><strong>19,000 tokens (100%)</strong></div>
            <div style="background:#f1f5f9;height:16px;border-radius:6px;overflow:hidden;border:1px solid var(--line-strong);"><div style="width:100%;height:100%;background:#a9492f;"></div></div>
          </div>
          <div style="margin-bottom:0.65rem;">
            <div style="display:flex;justify-content:space-between;font-size:0.8rem;margin-bottom:0.2rem;"><span>With KV Prefix Caching (90% off cached prefix)</span><strong style="color:var(--meadow);">3,610 eff. tokens (-81.0%!)</strong></div>
            <div style="background:#f1f5f9;height:16px;border-radius:6px;overflow:hidden;border:1px solid var(--line-strong);"><div style="width:19%;height:100%;background:#2c6b4f;"></div></div>
          </div>
          <div style="font-size:0.8rem;color:var(--ink-soft);">⚠️ Cache-Invalidation Trap: Putting <code>Current time: 14:32:09</code> on Line 1 breaks the prefix hash on EVERY turn and destroys the 81% discount!</div>
        `;
      }} else if (step === 6) {{
        const pts = [[1,93.0],[2,66.2],[3,51.0],[4,42.7],[5,38.7],[6,38.7],[7,42.7],[8,51.0],[9,66.2],[10,93.0]];
        el.innerHTML = `
          <div style="font-weight:800;margin-bottom:0.35rem;">📉 LOST-IN-THE-MIDDLE U-CURVE (Analytical Model of Liu et al., 2023)</div>
          <div style="display:grid;grid-template-columns:repeat(10, 1fr);gap:0.3rem;align-items:end;height:108px;padding:0.5rem 0.25rem 0.25rem;border-bottom:1.5px solid var(--line-strong);">
            ${{pts.map(([ch, pct]) => `
              <div style="display:flex;flex-direction:column;align-items:center;justify-content:flex-end;height:100%;">
                <span style="font-size:0.7rem;font-weight:700;color:${{pct < 45 ? '#a9492f' : '#2c6b4f'}};">${{pct.toFixed(0)}}%</span>
                <div style="width:100%;height:${{Math.round(pct * 0.78)}}px;background:${{pct < 45 ? '#a9492f' : (pct > 80 ? '#2c6b4f' : '#8b6842')}};border-radius:5px 5px 0 0;"></div>
              </div>
            `).join("")}}
          </div>
          <div style="display:grid;grid-template-columns:repeat(10, 1fr);gap:0.3rem;text-align:center;font-size:0.72rem;color:var(--muted);margin-top:0.25rem;">
            ${{pts.map(([ch]) => `<span>C${{ch}}</span>`).join("")}}
          </div>
          <div style="font-size:0.8rem;color:var(--ink-soft);margin-top:0.5rem;">Put critical instructions at <strong>Chunk 1 (System Prompt)</strong> and the current goal at <strong>Chunk 10 (Bottom)</strong> — never buried in C5/C6!</div>
        `;
      }}
    }}

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
          <div class="playground-band" style="background:var(--meadow-soft);border-color:var(--meadow);margin-top:1rem;">
            <div class="chapter-kicker" style="color:var(--meadow);">🎉 CHECKPOINT PASSED!</div>
            <h3 style="margin:0.2rem 0 0.4rem;font-family:var(--serif);font-size:1.45rem;line-height:1.35;color:#14532d;">
              ${{isFirstGate ? "🚧 Officer Rajan Salutes & Lifts the Campus Boom Barrier!" : "★ You Cleared " + lesson.title + "!"}}
            </h3>
            <p style="margin:0 0 0.9rem;font-size:0.95rem;color:#14532d;">
              ${{isFirstGate
                ? "The South Entrance Boom Gate is wide open — and your pocket communicator is ringing with a follow-up call from Andrej Karpathy!"
                : "Your badge is minted — and Andrej Karpathy is calling in on your pocket communicator with the next tip!"}}
            </p>
            <div style="display:flex;gap:0.65rem;flex-wrap:wrap;">
              <button class="btn btn-meadow" onclick="closeBookModal();triggerKarpathyCall('after_${{lesson.id}}');walkToCurrentQuest()">📞 Return to Campus & Take Karpathy's Call →</button>
              <button class="btn" onclick="switchBookTab('share')">🏆 Grab Shareable X Thread & IG Carousel</button>
            </div>
          </div>
        `;
      }}
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

    refreshHudAndPins();
    requestAnimationFrame(loop);

    // As Ashwin walks up the South Approach Road on load, his pocket communicator rings with a 3D call from Karpathy!
    if (!isGateOpen()) {{
      setTimeout(() => triggerKarpathyCall("arrival"), 450);
    }}
  </script>
</body>
</html>
"""


def _render_lesson_page(curriculum: dict, lesson: dict, live_ids: set[str], code_text: str) -> str:
    """Render standalone editorial Field Guide page at lessons/<id>/index.html."""
    lid = lesson["id"]
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
                f'<div style="background:#fff;border:2.5px solid var(--ink);box-shadow:0 3px 0 var(--line-strong), 0 8px 20px rgba(17,28,22,0.08);padding:1.15rem;border-radius:14px;margin:1.35rem 0 0.4rem;">'
                f'<img src="{_esc(fid)}.svg" alt="{_esc(fobj["title"])}" style="width:100%;height:auto;display:block;" />'
                f'<div style="display:flex;justify-content:space-between;align-items:center;margin-top:0.65rem;padding-top:0.5rem;border-top:1.5px dashed var(--line-strong);font-size:0.82rem;color:var(--ink-soft);">'
                f'<span><strong>📐 {_esc(fobj["title"])}:</strong> {_esc(fobj["caption"])}</span>'
                f'<a href="{_esc(fid)}.excalidraw" download style="font-family:var(--mono);">⬇ .excalidraw</a>'
                f'</div></div>'
            )
        expert_block = ""
        if sec.get("expert_note"):
            expert_block = (
                f'<div style="background:#f2f6f9;border:1.5px solid #b4ccd9;border-radius:12px;padding:0.9rem 1.1rem;margin-top:1rem;font-size:0.94rem;color:#1c2e38;">'
                f'<div style="font-family:var(--mono);font-size:0.76rem;font-weight:700;color:#264d60;text-transform:uppercase;margin-bottom:0.3rem;">⚙️ Under the Hood · Production Depth</div>'
                f'{_md_to_html(sec["expert_note"])}</div>'
            )
        trap_block = ""
        if sec.get("trap_note"):
            trap_block = (
                f'<div style="background:#fdf4ee;border:1.5px solid #e2baa7;border-radius:12px;padding:0.9rem 1.1rem;margin-top:0.75rem;font-size:0.94rem;color:#3a1d15;">'
                f'<div style="font-family:var(--mono);font-size:0.76rem;font-weight:700;color:#8c331c;text-transform:uppercase;margin-bottom:0.3rem;">⚠️ Production Engineering Trap</div>'
                f'{_md_to_html(sec["trap_note"])}</div>'
            )
        sections_html.append(
            f'<section style="padding:1.75rem 0;border-bottom:2px dashed var(--line);">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.4rem;">'
            f'<span style="font-family:var(--mono);font-size:0.78rem;font-weight:800;color:var(--terracotta);">PART 0{idx}</span>'
            f'<span class="tag tag-amber">{_esc(sec.get("badge", ""))}</span>'
            f'</div>'
            f'<h2 style="margin:0.1rem 0 0.85rem;font-family:var(--serif);font-size:1.55rem;line-height:1.35;">{_esc(sec["heading"])}</h2>'
            f'<div style="font-size:1.06rem;color:var(--ink-soft);line-height:1.78;">{_md_to_html(sec["body_md"])}</div>'
            f'{fig_block}'
            f'{expert_block}'
            f'{trap_block}'
            f'</section>'
        )

    jargon_rows = "".join(
        f'<tr><td style="padding:0.8rem;border-bottom:1.5px solid var(--line);"><strong>{_esc(r["term"])}</strong></td>'
        f'<td style="padding:0.8rem;border-bottom:1.5px solid var(--line);">{_esc(r["plain_words"])}</td>'
        f'<td style="padding:0.8rem;border-bottom:1.5px solid var(--line);color:var(--muted);">{_esc(r["why_you_care"])}</td></tr>'
        for r in lesson.get("jargon_decoder", [])
    )

    tweets_html = "".join(
        f'<div style="padding:1rem 0;border-bottom:1.5px solid var(--line);display:flex;justify-content:space-between;gap:1rem;">'
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
      <a class="crest-badge" href="../../index.html">← 3D CAMPUS RPG</a>
      <div>
        <div class="brand-title">{_esc(lesson["title"])}</div>
        <div class="brand-sub">BitsByBlocks AI University · Rung {lesson["level"]}: {_esc(lesson["level_name"])}</div>
      </div>
    </div>
    <div style="display:flex;gap:0.6rem;">
      <a class="btn" href="lesson.json" target="_blank">lesson.json</a>
      <a class="btn btn-primary" href="../../index.html">🎮 Enter 3D Campus & Talk to Characters</a>
    </div>
  </header>

  <main style="max-width:780px;margin:0 auto;padding:2.5rem 1.5rem 5rem;">
    <div style="display:flex;gap:0.5rem;flex-wrap:wrap;margin-bottom:0.75rem;">
      <span class="tag tag-terracotta">{_esc(sh["notebook_shelf"])}</span>
      <span class="tag tag-sky">Hall {lesson["level"]}: {_esc(lesson["level_name"])}</span>
      <span class="tag tag-meadow">✓ Python Lab Verified</span>
    </div>
    <h1 style="font-family:var(--serif);font-size:2.4rem;line-height:1.35;margin:0.2rem 0 0.5rem;">{_esc(lesson["title"])}</h1>
    <div style="font-family:var(--serif);font-style:italic;font-size:1.25rem;line-height:1.45;color:var(--terracotta);margin-bottom:1.25rem;">“{_esc(lesson["question"])}”</div>
    <div style="background:var(--paper-warm);border:2.5px solid var(--ink);box-shadow:0 3px 0 var(--ink), 0 8px 20px rgba(17,28,22,0.10);padding:1rem 1.35rem;border-radius:14px;margin-bottom:2rem;">
      <strong>In One Line:</strong> {_esc(lesson["one_line"])}
    </div>

    {"".join(sections_html)}

    <h2 style="font-family:var(--serif);line-height:1.35;margin-top:2.5rem;">Plain-English Jargon Decoder</h2>
    <table style="width:100%;border-collapse:collapse;background:var(--paper-card);border:2px solid var(--line-strong);border-radius:12px;overflow:hidden;font-size:0.94rem;">
      <thead><tr style="background:var(--paper-warm);text-align:left;"><th style="padding:0.8rem;">Term</th><th style="padding:0.8rem;">In Plain Words</th><th style="padding:0.8rem;">Why You Care</th></tr></thead>
      <tbody>{jargon_rows}</tbody>
    </table>

    <h2 style="font-family:var(--serif);line-height:1.35;margin-top:2.5rem;">Hands-On Python Lab: {_esc(lab["title"])}</h2>
    <p>{_esc(lab["goal"])}</p>
    <pre style="background:#111c16;color:#f2f7f4;padding:1.1rem;border-radius:12px;border:2px solid var(--ink);overflow-x:auto;"><code>{_esc(lab["real_output"])}</code></pre>
    <pre style="background:#111c16;color:#f2f7f4;padding:1.1rem;border-radius:12px;border:2px solid var(--ink);overflow-x:auto;margin-top:1rem;"><code>{_esc(code_text)}</code></pre>

    <h2 style="font-family:var(--serif);line-height:1.35;margin-top:2.5rem;">Share Studio · The Turn & X Thread</h2>
    <div style="background:var(--paper-warm);border:2.5px solid var(--ink);box-shadow:0 3px 0 var(--ink), 0 8px 20px rgba(17,28,22,0.10);border-radius:14px;padding:1.25rem;margin-bottom:1.25rem;">
      <div style="font-family:var(--mono);font-size:0.78rem;font-weight:800;color:var(--terracotta);">THE NOTEBOOK TURN</div>
      <div style="font-family:var(--serif);font-size:1.3rem;line-height:1.45;margin:0.35rem 0;">“{_esc(sh["the_turn"])}”</div>
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
    print(f"Built Bits University 3D RPG Adventure in {DIST} and {docs} with {len(lessons)} seeded lessons across {len(curriculum['modules'])} total modules.")


if __name__ == "__main__":
    build_site()
