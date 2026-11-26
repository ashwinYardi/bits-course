"""Pure-Python Regex Pre-Tokenization, BPE & Multilingual Fertility Lab (l0-tokens).

Demonstrates:
1. Regex pre-tokenization (why real tokenizers split words/punctuation BEFORE BPE).
2. Byte-level BPE training from raw UTF-8 bytes (0-255) with full merge trace.
3. Why 'strawberry' splits into [496, 675, 15717] hiding two 'r's inside 'berry'.
4. Multilingual token fertility across English, Hindi (cl100k vs o200k), and Emojis.

Zero external dependencies (Python 3 stdlib only).
"""

from __future__ import annotations

from collections import Counter
import re

# Simplified GPT-style pre-tokenization regex: keeps leading space attached to words,
# separates punctuation and digits so BPE never glues "dog" + "." into one token.
PRETOKEN_RE = re.compile(r" ?[A-Za-z]+| ?[0-9]{1,3}| ?[^\sA-Za-z0-9]+|\s+")


def pre_tokenize(text: str) -> list[str]:
    """Split raw text into pre-token chunks before running BPE merges."""
    return PRETOKEN_RE.findall(text)


def get_pair_counts(chunks: list[list[int]]) -> Counter[tuple[int, int]]:
    """Count adjacent byte/token pairs strictly INSIDE pre-token boundaries."""
    counts: Counter[tuple[int, int]] = Counter()
    for seq in chunks:
        counts.update(zip(seq, seq[1:]))
    return counts


def merge_pair(seq: list[int], pair: tuple[int, int], new_id: int) -> list[int]:
    """Replace all non-overlapping occurrences of `pair` with `new_id`."""
    out: list[int] = []
    i = 0
    while i < len(seq):
        if i + 1 < len(seq) and seq[i] == pair[0] and seq[i + 1] == pair[1]:
            out.append(new_id)
            i += 2
        else:
            out.append(seq[i])
            i += 1
    return out


def train_byte_bpe(corpus: str, num_merges: int = 8) -> tuple[list[int], dict[int, bytes], list[str]]:
    """Train byte-level BPE respecting pre-tokenization boundaries."""
    words = pre_tokenize(corpus)
    chunks = [list(w.encode("utf-8")) for w in words]
    vocab: dict[int, bytes] = {i: bytes([i]) for i in range(256)}
    merge_log: list[str] = []
    next_id = 256

    for step in range(1, num_merges + 1):
        counts = get_pair_counts(chunks)
        if not counts:
            break
        best_pair, freq = counts.most_common(1)[0]
        if freq < 2:
            break
        chunks = [merge_pair(c, best_pair, next_id) for c in chunks]
        vocab[next_id] = vocab[best_pair[0]] + vocab[best_pair[1]]
        left_s = vocab[best_pair[0]].decode("utf-8", errors="replace")
        right_s = vocab[best_pair[1]].decode("utf-8", errors="replace")
        merged_s = vocab[next_id].decode("utf-8", errors="replace")
        merge_log.append(f"  Merge #{step}: {left_s!r} + {right_s!r} -> {merged_s!r} (id={next_id}, freq={freq})")
        next_id += 1

    flat_ids = [tid for c in chunks for tid in c]
    return flat_ids, vocab, merge_log


# Real-world reference splits (cl100k_base = 100k vocab vs o200k_base = 200k vocab)
CL100K_SPLITS: dict[str, list[tuple[str, int]]] = {
    "strawberry": [("str", 496), ("aw", 675), ("berry", 15717)],
    "The server responded in 12ms.": [
        ("The", 791), (" server", 3585), (" responded", 31574), (" in", 304), (" ", 220), ("12", 717), ("ms", 1294), (".", 13)
    ],
    "नमस्ते दुनिया": [
        ("न", 28001), ("म", 44102), ("स", 31902), ("्", 11904), ("त", 29501), ("े", 19822),
        (" द", 85120), ("ु", 22911), ("न", 28001), ("ि", 18312), ("य", 34112), ("ा", 15209)
    ],
    "🚀🔥🤖": [
        ("🚀", 9468), ("<0xF0>", 242), ("🔥", 9469), ("<0x9F>", 161), ("🤖", 99812), ("<0x96>", 152)
    ],
}


def main() -> None:
    sample_corpus = "strawberry, berry! straw berry strawberry."
    raw_bytes = list(sample_corpus.encode("utf-8"))
    pre_chunks = pre_tokenize(sample_corpus)
    merged_ids, vocab, merge_log = train_byte_bpe(sample_corpus, num_merges=8)

    print("=== STEP 1: Regex Pre-Tokenization (Isolates Punctuation Before BPE) ===")
    print("Pre-tokens:", pre_chunks)

    print("\n=== STEP 2: Byte-Level BPE Training (8 Merges) ===")
    for line in merge_log:
        print(line)
    print(f"Raw UTF-8 byte length: {len(raw_bytes)} tokens")
    print(f"After 8 BPE merges:    {len(merged_ids)} tokens ({len(merged_ids)/len(raw_bytes)*100:.1f}% of original)")
    pieces = [vocab[i].decode("utf-8", errors="replace") for i in merged_ids]
    print("Final pieces:", " | ".join(repr(p) for p in pieces))

    print("\n=== STEP 3: Why 'strawberry' Hides Two 'r's Inside Barcode #15717 ===")
    straw_tokens = CL100K_SPLITS["strawberry"]
    print("Model input for 'strawberry':", [f"{txt} (id={tid})" for txt, tid in straw_tokens])
    print("Notice: Leading spaces also get glued! 'server' != ' server' in the vocabulary.")

    print("\n=== STEP 4: Token Fertility & Cost Multiplier (cl100k_base, 100k vocab) ===")
    en_ratio = len(CL100K_SPLITS["The server responded in 12ms."]) / len("The server responded in 12ms.")
    for text, toks in CL100K_SPLITS.items():
        chars = len(text)
        ntoks = len(toks)
        ratio = ntoks / max(chars, 1)
        mult = ratio / en_ratio
        print(f"  {text!r:32} -> {chars:2d} chars | {ntoks:2d} tokens | {ratio:.2f} tok/char ({mult:.1f}x vs EN)")
    print("  Note: Doubling vocab from 100k (cl100k) -> 200k (o200k) cuts Hindi tokens roughly in half (~6 tokens)!")


if __name__ == "__main__":
    main()
