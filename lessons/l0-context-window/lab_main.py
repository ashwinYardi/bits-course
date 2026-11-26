"""Pure-Python Context Window, KV Prompt Caching & U-Curve Attention Lab (l0-context-window).

Demonstrates:
1. Sliding context window FIFO truncation (why Turn 1's locker code '7492' vanishes).
2. Multi-turn token billing: why uncached 10-turn chats re-pay for Turn 1 ten times —
   and how KV Prefix Caching cuts input costs by up to 80%+ when your prefix stays immutable.
3. Quadratic self-attention cost O(N^2) as context grows from 1k -> 10k -> 100k tokens.
4. Analytical U-curve model illustrating the primacy/recency shape from Liu et al. (2023).

Zero external dependencies (Python 3 stdlib only).
"""

from __future__ import annotations


def build_chat_payload(history: list[str], max_words: int) -> tuple[list[str], list[str], int]:
    """Simulate a sliding context window that drops oldest messages when budget overflows."""
    kept: list[str] = []
    dropped: list[str] = []
    used = 0
    for msg in reversed(history):
        cost = len(msg.split())
        if used + cost <= max_words:
            kept.append(msg)
            used += cost
        else:
            dropped.append(msg)
    kept.reverse()
    dropped.reverse()
    return kept, dropped, used


def simulate_multiturn_billing(turns: int = 10, system_tokens: int = 400, turn_tokens: int = 150) -> tuple[int, int, int]:
    """Compare total input tokens billed without vs with KV Prefix Caching (90% discount on cached prefix)."""
    uncached_input = 0
    cached_prefix_tokens = 0
    fresh_tokens = 0
    prefix_so_far = system_tokens
    for t in range(1, turns + 1):
        new_msg = turn_tokens
        if t == 1:
            # First turn computes the system prompt + Turn 1 fresh
            fresh_tokens += system_tokens + new_msg
        else:
            # Turns 2..N reuse the exact prefix KV cache from prior turns!
            cached_prefix_tokens += prefix_so_far
            fresh_tokens += new_msg
        uncached_input += prefix_so_far + new_msg
        prefix_so_far += new_msg + turn_tokens  # add user msg + assistant reply
    return uncached_input, cached_prefix_tokens, fresh_tokens


def liu_ucurve_model(position_index: int, total_chunks: int) -> float:
    """Analytical U-shaped curve reproducing the primacy/recency pattern from Liu et al. (2023).

    Note: This is a clean mathematical illustration of the published empirical finding (high accuracy
    at start/end, sharp trough in the middle), not a live LLM benchmark run.
    """
    x = position_index / max(total_chunks - 1, 1)
    recall = 0.38 + 2.2 * ((x - 0.5) ** 2)
    return min(0.96, round(recall, 3))


def main() -> None:
    conversation = [
        "Turn 1: My secret locker code is 7492.",
        "Turn 2: Let us discuss the cafeteria menu for Monday.",
        "Turn 3: The cafeteria serves masala dosa and filter coffee.",
        "Turn 4: On Tuesday the library hosts a robotics club demo.",
        "Turn 5: What was my secret locker code from Turn 1?",
    ]

    print("=== STEP 1: Sliding Context Window Budget (Max 24 words) ===")
    kept, dropped, used = build_chat_payload(conversation, max_words=24)
    print(f"Dropped at the door ({len(dropped)} turns): {dropped}")
    print(f"Inside context window ({len(kept)} turns, {used}/24 words): {kept}")
    has_secret = any("7492" in m for m in kept)
    print(f"Can the model see '7492'? -> {has_secret} (Turn 1 fell off the tray!)")

    print("\n=== STEP 2: 10-Turn Chat Billing — Uncached vs KV Prefix Caching ===")
    uncached, cached, fresh = simulate_multiturn_billing(turns=10, system_tokens=400, turn_tokens=150)
    # Effective billable units if cached tokens cost 0.1x (90% prompt-cache discount)
    effective_cached_bill = int(fresh + cached * 0.10)
    savings_pct = (1 - effective_cached_bill / uncached) * 100
    print(f"  Uncached total input tokens billed across 10 turns: {uncached:,}")
    print(f"  With Prefix KV Cache: {cached:,} cached (0.1x) + {fresh:,} fresh = {effective_cached_bill:,} eff. tokens ({savings_pct:.1f}% cheaper!)")

    print("\n=== STEP 3: Quadratic Self-Attention Pairs O(N^2) ===")
    for n in (1_000, 10_000, 100_000):
        pairs = n * (n + 1) // 2
        print(f"  Context N = {n:7,} tokens -> {pairs:13,} causal attention pairs")

    print("\n=== STEP 4: Illustrative U-Curve Model (Liu et al., 2023 'Lost in the Middle') ===")
    for idx in (0, 2, 5, 7, 9):
        prob = liu_ucurve_model(idx, total_chunks=10)
        zone = "START (Primacy)" if idx == 0 else ("END (Recency)" if idx == 9 else ("DEAD MIDDLE" if idx == 5 else "INNER"))
        print(f"  Chunk {idx+1:2d}/10 [{zone:15}] -> Modeled recall: {prob*100:5.1f}%")


if __name__ == "__main__":
    main()
