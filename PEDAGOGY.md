# BitsByBlocks Pedagogy & Lesson Design Playbook

This document is the permanent teaching standard for every lesson, interactive playground, Python lab, and checkpoint in **BitsByBlocks AI University**. Every module generated or revised must pass all **7 pillars** below.

---

## 1. Concreteness Fading (Concrete → Schematic → Formal)
Human working memory holds only 3–5 new chunks at once. Never open a lesson with equations or abstract definitions.
1. **Concrete Anchor (Enactive):** Start with a vivid physical scene or everyday mental model (e.g., a security gate weighted die, parking-lot barcodes, cafeteria tables, a 24-word lunch tray).
2. **Schematic Model (Iconic):** Pair the concrete story with a clean architectural diagram and an interactive sandbox where one knob changes one visible outcome.
3. **Formal Mechanism (Symbolic):** Only after the intuition clicks, reveal the real math, tensor shapes, algorithms, and production systems jargon (`softmax`, `BPE regex pre-tokenization`, `L2 cosine`, `KV prefix caching`).

## 2. Dual Coding & Visual Memory Hooks (Memes + Diagrams)
Pair verbal explanation with distinct visual encodings—without split-attention clutter:
- **Editorial Hero Illustration:** One cohesive print-style visual metaphor per essay that encodes the core mechanism at a glance.
- **Architectural Diagrams:** Labels live directly inside the nodes; one clear left-to-right or top-to-bottom reading flow; zero decorative clutter.
- **Sharp Memes & Mnemonics:** Every lesson includes 1–2 memorable, programmer-culture meme cards (e.g., *"Expectation vs. Reality"*, *"Two Buttons"*, *"Antonym Trap"*) and a crisp one-line **Memory Hook** you can still recall six months later. Humor lowers cognitive friction and anchors retrieval cues—never cringe, always technically exact.

## 3. Core Code Walkthroughs (Worked Examples Before Open Practice)
Dumping raw Python code is passive reading. Following Cognitive Load Theory:
1. **Explain the Code at the Core:** Every lab includes a structured **Core Code Walkthrough** that breaks the runnable script into 3–4 logical blocks, explaining *why* each line exists, what breaks if you remove it, and how it maps to real frontier inference engines.
2. **Real Verified Output:** Every lab runs with pure Python 3 stdlib (zero API keys) and prints exact numbers that match the prose, diagrams, and quiz—zero invented or mismatched numbers.

## 4. Optional Deep-Dive Assignments + Copyable Agent Prompts
True expertise happens when the learner builds beyond the walkthrough. Every lesson includes **2–3 Optional In-Depth Assignments** (ranging from *Builder* to *Systems Deep Dive*), each paired with:
- What you will prove by building it.
- A **one-click copyable Agent Prompt** Ashwin can hand straight to his coding agent to scaffold, benchmark, and verify the experiment interactively.

## 5. Elaborative Interrogation & Production Traps
After each mechanism clicks, immediately ask *"Why does this break in production?"*
- **Under the Hood (Production Depth):** Connect the toy lab directly to frontier systems (`cl100k` vs `o200k`, Matryoshka embeddings, Hybrid BM25+Vector search, KV prefix caching, GPU non-determinism).
- **Production Trap:** Name the exact failure mode that bites real engineers (JSON verdict-before-reasoning, trailing-space tokenization, antonym cosine trap, timestamp cache invalidation).

## 6. Active Retrieval & Spaced Revision (Never Punitive)
- **3-Question Checkpoint Gate:** Tests applied reasoning and real lab numbers—never rote trivia.
- **Post-Clear Revision Mode:** Once passed, revisiting a checkpoint respects mastery and switches into Revision Mode (re-read essay, inspect code walkthrough, grab optional agent assignments, or practice the quiz again).
- **Fun Is Non-Negotiable:** Surprise interrupts, narrative continuity, and tactile interactive widgets turn study into play.

## 7. Mandatory Cross-Reference & Technical Fact-Check Gate (Zero Hallucinated Numbers)
Every new or revised chapter MUST pass this 4-step verification gate **before** committing or publishing:
1. **Cross-Reference Against Gold-Standard Sources:** Check the chapter's scope, terminology, equations, and current 2025/2026 frontier conventions against at least two primary references (e.g., Stanford CS336, Chip Huyen *AI Engineering*, Karpathy *Zero to Hero* / *LLM101n*, Raschka *Build an LLM from Scratch*, Hugging Face courses/playbooks, Anthropic engineering posts, or the original arXiv paper). Never teach outdated practices without flagging how modern models evolved.
2. **Execute Real Libraries for Every Real-World Claim:** Never estimate or hand-invent real-world token IDs, benchmark scores, memory sizes, or math outputs. If a chapter cites `cl100k_base` / `o200k_base` token IDs, run `tiktoken` / `js-tiktoken` live; if it cites an equation or VRAM count, compute it live in Python.
3. **Label Toy vs. Production Clearly:** Whenever a lab uses a simplified toy model (e.g., hand-crafted 4D analogy vectors, an analytical U-curve reproducing a paper's shape, or a 400-token prompt cache demo below real API minimums), explicitly disclose the toy assumption and state the real production behavior in an `expert_note`.
4. **Cross-Surface Consistency Audit:** Run an automated check verifying that `lab_main.py` exits 0, `lesson.json["lab"]["real_output"]` matches live stdout verbatim, and every number across the essay prose, figures, memes, `code_walkthrough`, `shareable` threads, interactive JS playgrounds, NPC dialogues, and `GATE_CHALLENGES` quiz options agrees to the exact digit.
