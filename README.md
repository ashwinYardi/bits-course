# BitsByBlocks · AI Engineering Notebook (`bits-course`)

Ashwin Yardi's living basics-to-pro AI engineering course and learning-in-public notebook.

Every module is authored as a structured [`lesson.json`](lesson.schema.json) inside `lessons/<module-id>/` along with a runnable pure-Python lab (`lab_main.py`), compiled into a static site (`dist/`) with hand-drawn Excalidraw figures (`.excalidraw` + `.svg`), an interactive mechanism sandbox, and a **Share Studio** (ready-to-post X thread, 4:5 Instagram carousel deck, and *The Turn*).

## Architecture

- **`curriculum.json`** — The 49 spine modules across 6 rungs (Rung 0 *Ground floor* through Rung 5 *Builder*), triangulated against Stanford CS336, Karpathy Zero to Hero, Raschka *Build an LLM from Scratch*, Hugging Face LLM Course, Chip Huyen *AI Engineering*, and Maxime Labonne.
- **`lesson.schema.json`** — The JSON schema for each module's `lesson.json` (Story Spine, Excalidraw figure specs, progressive sections, jargon decoder, runnable lab + verified output, and Share Studio assets).
- **`lessons/<id>/lesson.json` & `lab_main.py`** — The source of truth for each lesson and its hands-on executable lab.
- **`scripts/excalidraw.py`** — Deterministic Excalidraw `.excalidraw` scene builder, linter, and zero-dependency hand-drawn `.svg` renderer (`flow`, `stack`, `grid`, `tree` layouts).
- **`scripts/build.py`** — Compiles `curriculum.json` and all `lessons/*/lesson.json` into `dist/` (HTML pages, `post.md`, `.excalidraw`, `.svg`, and runnable lab downloads).
- **`.github/workflows/deploy.yml`** — Verifies every lesson's `lab_main.py` executes cleanly, builds `dist/`, and deploys to GitHub Pages on every push to `main`.

## Local Build

```bash
python3 lessons/l0-what-is-an-llm/lab_main.py   # Run Lesson 01 lab
python3 scripts/build.py                        # Build static site into dist/
```
