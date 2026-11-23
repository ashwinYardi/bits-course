"""Tiny, pure-Python next-token prediction lab for Module l0-what-is-an-llm.

Shows what an LLM actually does at every step:
1. Takes the current token sequence (context).
2. Produces raw scores (logits) over its vocabulary.
3. Scales logits by temperature and runs softmax to get a probability distribution.
4. Samples one next token, appends it to the prompt, and repeats.

Zero external dependencies (Python 3 stdlib only) so any developer can run it immediately.
"""

from __future__ import annotations

import math
import random

# A tiny toy vocabulary and pre-trained logit table conditioned on the last two words.
# In a real 70B LLM, these logits come from 80 transformer layers multiplying billions of weights.
# Here we inspect the exact output stage of that pipeline: logits -> softmax -> sample -> append.
LOGIT_TABLE: dict[tuple[str, str], dict[str, float]] = {
    ("the", "server"): {"crashed": 3.2, "responded": 2.9, "timed": 2.4, "melted": 0.4, "danced": -1.5},
    ("server", "crashed"): {"because": 3.6, "after": 2.5, "at": 1.8, "quietly": 0.9},
    ("server", "responded"): {"in": 3.4, "with": 2.8, "after": 1.7, "slowly": 1.1},
    ("server", "timed"): {"out": 4.5, "at": 1.1, "twice": 0.8},
    ("crashed", "because"): {"memory": 3.3, "traffic": 2.9, "disk": 2.1, "aliens": -2.0},
    ("crashed", "after"): {"ten": 3.0, "heavy": 2.7, "midnight": 2.0},
    ("responded", "in"): {"twelve": 3.1, "two": 2.8, "forty": 2.2},
    ("responded", "with"): {"valid": 3.2, "stale": 2.6, "empty": 2.1},
    ("timed", "out"): {"after": 3.5, "during": 2.7, "under": 2.2},
    ("because", "memory"): {"ran": 3.8, "leaked": 3.1, "spiked": 2.4},
    ("because", "traffic"): {"doubled": 3.5, "spiked": 3.2, "surged": 2.5},
    ("after", "ten"): {"seconds": 3.9, "requests": 2.8, "retries": 2.3},
    ("in", "twelve"): {"milliseconds": 4.2, "seconds": 2.1},
    ("with", "valid"): {"json": 3.9, "headers": 2.6, "bytes": 2.0},
    ("out", "after"): {"thirty": 3.4, "five": 3.0, "three": 2.4},
}

DEFAULT_LOGITS: dict[str, float] = {"and": 2.2, "then": 2.0, "stopped": 2.6, "recovered": 2.3}


def softmax(logits: dict[str, float], temperature: float) -> dict[str, float]:
    """Turn raw logit scores into probabilities that sum to 1.0."""
    if temperature <= 0:
        # Greedy decoding: 100% probability on the single highest logit
        best_token = max(logits.items(), key=lambda kv: kv[1])[0]
        return {k: (1.0 if k == best_token else 0.0) for k in logits}

    scaled = {k: v / temperature for k, v in logits.items()}
    max_logit = max(scaled.values())
    exps = {k: math.exp(v - max_logit) for k, v in scaled.items()}
    total = sum(exps.values())
    return {k: v / total for k, v in exps.items()}


def sample_token(probs: dict[str, float], rng: random.Random) -> str:
    """Pick one token according to its probability mass."""
    r = rng.random()
    cumulative = 0.0
    for token, p in probs.items():
        cumulative += p
        if r <= cumulative:
            return token
    return list(probs.keys())[-1]


def generate(prompt: list[str], steps: int, temperature: float, rng: random.Random) -> list[str]:
    """Autoregressive loop: predict one token, append to context, repeat."""
    tokens = list(prompt)
    for _ in range(steps):
        context_key = (tokens[-2], tokens[-1])
        logits = LOGIT_TABLE.get(context_key, DEFAULT_LOGITS)
        probs = softmax(logits, temperature=temperature)
        next_tok = sample_token(probs, rng)
        tokens.append(next_tok)
    return tokens


def main() -> None:
    prompt = ["the", "server"]
    first_logits = LOGIT_TABLE[("the", "server")]

    print("=== STEP 1: Raw logits vs probabilities after (" + " ".join(prompt) + ") ===")
    for temp in (0.2, 1.0, 1.8):
        probs = softmax(first_logits, temperature=temp)
        top_str = ", ".join(f"{tok}: {p*100:5.1f}%" for tok, p in sorted(probs.items(), key=lambda x: -x[1]))
        print(f"Temp {temp:3.1f} -> {top_str}")

    print("\n=== STEP 2: 5 runs at temperature = 0.0 (Greedy decoding) ===")
    greedy_runs = set()
    for i in range(5):
        rng = random.Random(100 + i)
        out = " ".join(generate(prompt, steps=5, temperature=0.0, rng=rng))
        greedy_runs.add(out)
        print(f"  Run {i+1}: {out}")
    print(f"Unique outputs at temp 0.0: {len(greedy_runs)} / 5")

    print("\n=== STEP 3: 5 runs at temperature = 1.0 (Sampling from the distribution) ===")
    sampled_runs = set()
    for i in range(5):
        rng = random.Random(42 + i * 7)
        out = " ".join(generate(prompt, steps=5, temperature=1.0, rng=rng))
        sampled_runs.add(out)
        print(f"  Run {i+1}: {out}")
    print(f"Unique outputs at temp 1.0: {len(sampled_runs)} / 5")


if __name__ == "__main__":
    main()
