"""Pure-Python Embeddings & Cosine Similarity Lab for Module l0-embeddings.

Shows how a machine knows that 'chai' and 'coffee' are close neighbors while
'chai' and 'kubernetes' live on opposite sides of the map — using nothing
but lists of numbers (vectors) and the angle between them (cosine similarity).
"""

from __future__ import annotations

import math

# 4-dimensional toy embedding vectors:
# [warm_drink, sweet_food, computer_tech, morning_energy]
EMBEDDINGS: dict[str, list[float]] = {
    "masala_chai": [0.95, 0.40, 0.02, 0.88],
    "filter_coffee": [0.92, 0.25, 0.05, 0.94],
    "mango_lassi": [0.15, 0.92, 0.01, 0.35],
    "croissant": [0.20, 0.85, 0.03, 0.60],
    "kubernetes": [0.01, 0.00, 0.98, 0.12],
    "postgres_db": [0.02, 0.01, 0.95, 0.10],
}


def dot_product(a: list[float], b: list[float]) -> float:
    """Multiply matching coordinates and add them up."""
    return sum(x * y for x, y in zip(a, b))


def magnitude(v: list[float]) -> float:
    """Length of the arrow from the origin (Pythagorean theorem)."""
    return math.sqrt(sum(x * x for x in v))


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine of the angle between two vectors: 1.0 = identical direction, 0.0 = unrelated."""
    mag = magnitude(a) * magnitude(b)
    return dot_product(a, b) / mag if mag > 0 else 0.0


def main() -> None:
    print("=== STEP 1: Coordinates (Vectors) in 4D Meaning Space ===")
    print("Dimensions: [warm_drink, sweet_food, computer_tech, morning_energy]")
    for word, vec in EMBEDDINGS.items():
        print(f"  {word:15} -> {vec}")

    print("\n=== STEP 2: Nearest Neighbors to 'masala_chai' ===")
    target = "masala_chai"
    scores = []
    for word, vec in EMBEDDINGS.items():
        if word == target:
            continue
        sim = cosine_similarity(EMBEDDINGS[target], vec)
        scores.append((sim, word))
    scores.sort(reverse=True)
    for sim, word in scores:
        print(f"  cosine(masala_chai, {word:14}) = {sim:.4f}")

    print("\n=== STEP 3: All-Pairs Closest & Farthest Meaning Pairs ===")
    words = list(EMBEDDINGS.keys())
    pairs = []
    for i in range(len(words)):
        for j in range(i + 1, len(words)):
            w1, w2 = words[i], words[j]
            pairs.append((cosine_similarity(EMBEDDINGS[w1], EMBEDDINGS[w2]), w1, w2))
    pairs.sort(reverse=True)
    best = pairs[0]
    worst = pairs[-1]
    print(f"  Closest pair:  {best[1]} <-> {best[2]} (similarity = {best[0]:.4f})")
    print(f"  Farthest pair: {worst[1]} <-> {worst[2]} (similarity = {worst[0]:.4f})")


if __name__ == "__main__":
    main()
