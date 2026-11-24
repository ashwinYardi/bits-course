"""Pure-Python Byte Pair Encoding (BPE) & Tokenizer Fertility Lab for Module l0-tokens.

Demonstrates:
1. Why character/UTF-8 byte length != token count.
2. How BPE merges the most frequent adjacent byte pairs iteratively to build a vocabulary.
3. Why 'strawberry' splits into pieces that hide individual 'r' letters from the model.
4. Why Hindi, emojis, and numbers have higher token fertility (cost multiplier) than English prose.
"""

from __future__ import annotations

from collections import Counter


def get_pair_counts(token_seq: list[int]) -> Counter[tuple[int, int]]:
    """Count frequency of every adjacent pair of token IDs."""
    return Counter(zip(token_seq, token_seq[1:]))


def merge_pair(token_seq: list[int], pair: tuple[int, int], new_id: int) -> list[int]:
    """Replace all non-overlapping occurrences of `pair` with `new_id`."""
    out: list[int] = []
    i = 0
    while i < len(token_seq):
        if i + 1 < len(token_seq) and token_seq[i] == pair[0] and token_seq[i + 1] == pair[1]:
            out.append(new_id)
            i += 2
        else:
            out.append(token_seq[i])
            i += 1
    return out


def train_tiny_bpe(corpus: str, num_merges: int = 8) -> tuple[list[int], dict[int, bytes]]:
    """Train a minimal byte-level BPE tokenizer from raw UTF-8 bytes."""
    ids = list(corpus.encode("utf-8"))
    vocab: dict[int, bytes] = {i: bytes([i]) for i in range(256)}
    next_id = 256

    for _ in range(num_merges):
        counts = get_pair_counts(ids)
        if not counts:
            break
        best_pair, freq = counts.most_common(1)[0]
        if freq < 2:
            break
        ids = merge_pair(ids, best_pair, next_id)
        vocab[next_id] = vocab[best_pair[0]] + vocab[best_pair[1]]
        next_id += 1
    return ids, vocab


# Simulated cl100k_base (GPT-4 style) subword splits for 6 real-world test strings
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
    sample_corpus = "strawberry berry straw berry strawberry"
    raw_bytes = list(sample_corpus.encode("utf-8"))
    merged_ids, vocab = train_tiny_bpe(sample_corpus, num_merges=8)

    print("=== STEP 1: Byte Pair Encoding (BPE) Compression on 'strawberry' corpus ===")
    print(f"Raw UTF-8 byte length: {len(raw_bytes)} tokens")
    print(f"After 8 BPE merges:    {len(merged_ids)} tokens ({len(merged_ids)/len(raw_bytes)*100:.1f}% of original)")
    pieces = [vocab[i].decode("utf-8", errors="replace") for i in merged_ids]
    print("Merged pieces:", " | ".join(repr(p) for p in pieces))

    print("\n=== STEP 2: Why the model miscounts 'r' in 'strawberry' ===")
    straw_tokens = CL100K_SPLITS["strawberry"]
    print("Model input for 'strawberry':", [f"{txt} (id={tid})" for txt, tid in straw_tokens])
    print("Notice: The model never sees individual characters ['s','t','r','a','w','b','e','r','r','y'].")
    print("It sees 3 integer IDs: [496, 675, 15717]. Token 15717 ('berry') hides two 'r's inside a single atomic integer!")

    print("\n=== STEP 3: Token Fertility & Cost Multiplier Across English, Hindi, and Emoji ===")
    for text, toks in CL100K_SPLITS.items():
        chars = len(text)
        ntoks = len(toks)
        ratio = ntoks / max(chars, 1)
        print(f"  {text!r:32} -> {chars:2d} chars | {ntoks:2d} tokens | {ratio:.2f} tokens/char")


if __name__ == "__main__":
    main()
