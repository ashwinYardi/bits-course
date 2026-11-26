"""Pure-Python Embeddings, Cosine Similarity, Vector Arithmetic & L2-Norm Lab (l0-embeddings).

Demonstrates:
1. 4D Semantic Vectors: [warm_drink, sweet_or_spicy_food, computer_tech, morning_or_royalty]
   — actually cleanly split into two experiments:
   (A) Cafeteria Semantic Search + The Antonym Trap ('masala_chai' vs 'iced_chai').
   (B) Famous Vector Arithmetic ('king - man + woman -> queen').
2. Mathematical proof that for L2-normalized vectors, dot_product(u, v) == cosine_similarity(u, v).

Zero external dependencies (Python 3 stdlib only).
"""

from __future__ import annotations

import math

# Experiment A: Campus Cafeteria 4D Embeddings
# Dimensions: [drink, hot_temperature, sweet_or_spiced, computer_tech]
CAFETERIA_VECTORS: dict[str, list[float]] = {
    "masala_chai":   [0.95, 0.90, 0.72, 0.02],
    "filter_coffee": [0.94, 0.88, 0.45, 0.05],
    "iced_chai":     [0.92, 0.05, 0.70, 0.02],  # Opposite temperature, same drink/spice topic!
    "samosa":        [0.10, 0.80, 0.78, 0.02],
    "mango_lassi":   [0.85, 0.05, 0.92, 0.01],
    "kubernetes":    [0.01, 0.02, 0.00, 0.98],
    "postgres_db":   [0.02, 0.02, 0.01, 0.95],
}

# Experiment B: Royalty & Gender Subspace [royalty, human_adult, feminine_axis, tech]
ANALOGY_VECTORS: dict[str, list[float]] = {
    "king":   [0.95, 0.90, 0.05, 0.02],
    "man":    [0.05, 0.90, 0.05, 0.02],
    "woman":  [0.05, 0.90, 0.95, 0.02],
    "queen":  [0.95, 0.90, 0.95, 0.02],
    "prince": [0.75, 0.45, 0.08, 0.02],
}


def dot_product(a: list[float], b: list[float]) -> float:
    """Multiply matching coordinates and add them up."""
    return sum(x * y for x, y in zip(a, b))


def magnitude(v: list[float]) -> float:
    """Euclidean length (L2 norm) of the vector from the origin."""
    return math.sqrt(sum(x * x for x in v))


def normalize(v: list[float]) -> list[float]:
    """Scale vector to unit length (magnitude = 1.0)."""
    mag = magnitude(v)
    return [x / mag for x in v] if mag > 0 else list(v)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine of the angle between two vectors: +1.0 = identical direction, 0.0 = 90 deg."""
    mag = magnitude(a) * magnitude(b)
    return dot_product(a, b) / mag if mag > 0 else 0.0


def main() -> None:
    print("=== STEP 1: Cafeteria Nearest Neighbors to 'masala_chai' ===")
    print("Axes: [drink, hot_temp, sweet_or_spiced, computer_tech]")
    chai = CAFETERIA_VECTORS["masala_chai"]
    ranked = sorted(
        ((cosine_similarity(chai, vec), name) for name, vec in CAFETERIA_VECTORS.items() if name != "masala_chai"),
        reverse=True,
    )
    for sim, name in ranked:
        angle_deg = math.degrees(math.acos(max(-1.0, min(1.0, sim))))
        print(f"  cosine(masala_chai, {name:14}) = {sim:.4f}  (angle = {angle_deg:4.1f} deg)")

    print("\n=== STEP 2: The Antonym Trap (Hot Chai vs Iced Chai) ===")
    hot_vs_cold = cosine_similarity(CAFETERIA_VECTORS["masala_chai"], CAFETERIA_VECTORS["iced_chai"])
    print(f"  cosine(masala_chai, iced_chai) = {hot_vs_cold:.4f}")
    print("  Why so high? Opposites share 2 of 4 topic axes (drink + spice), so vector search alone")
    print("  cannot reliably distinguish 'hot' from 'cold' or 'love' from 'hate' without a reranker!")

    print("\n=== STEP 3: Vector Arithmetic (king - man + woman) ===")
    target = [
        k - m + w
        for k, m, w in zip(ANALOGY_VECTORS["king"], ANALOGY_VECTORS["man"], ANALOGY_VECTORS["woman"])
    ]
    print(f"  king - man + woman = {[round(x, 2) for x in target]}")
    for name in ("queen", "prince", "woman"):
        sim = cosine_similarity(target, ANALOGY_VECTORS[name])
        print(f"  similarity to {name:7} = {sim:.4f}")

    print("\n=== STEP 4: Production Optimization — L2 Normalization Proof ===")
    u = normalize(CAFETERIA_VECTORS["masala_chai"])
    v = normalize(CAFETERIA_VECTORS["filter_coffee"])
    cos_raw = cosine_similarity(CAFETERIA_VECTORS["masala_chai"], CAFETERIA_VECTORS["filter_coffee"])
    dot_norm = dot_product(u, v)
    print(f"  cosine(raw chai, raw coffee)       = {cos_raw:.6f}")
    print(f"  dot_product(norm chai, norm coffee)= {dot_norm:.6f}")
    print("  Because OpenAI/Cohere/BGE embeddings are L2-normalized, vector DBs just run fast dot products!")


if __name__ == "__main__":
    main()
