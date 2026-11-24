"""Pure-Python Context Window & 'Lost in the Middle' Lab for Module l0-context-window.

Shows:
1. Why an LLM has zero memory between API calls unless you re-send the whole chat history.
2. What happens when your conversation exceeds the context window budget (FIFO truncation).
3. The 'Lost in the Middle' U-shaped attention curve discovered by Liu et al. (2023).
"""

from __future__ import annotations


def build_chat_payload(history: list[str], max_tokens: int) -> tuple[list[str], list[str]]:
    """Simulate a sliding context window that drops oldest tokens when full."""
    kept: list[str] = []
    dropped: list[str] = []
    used = 0
    # Keep newest messages from the end backward until budget is full
    for msg in reversed(history):
        cost = len(msg.split())
        if used + cost <= max_tokens:
            kept.append(msg)
            used += cost
        else:
            dropped.append(msg)
    kept.reverse()
    dropped.reverse()
    return kept, dropped


def attention_recall_probability(position_index: int, total_chunks: int) -> float:
    """U-shaped recall curve (primacy + recency bias in long context windows)."""
    # Normalized position from 0.0 (very start) to 1.0 (very end)
    x = position_index / max(total_chunks - 1, 1)
    # Parabola centered at 0.5 (the middle trough)
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
    kept, dropped = build_chat_payload(conversation, max_tokens=24)
    print(f"Dropped at the door ({len(dropped)} turns): {dropped}")
    print(f"Inside context window ({len(kept)} turns): {kept}")
    has_secret = any("7492" in m for m in kept)
    print(f"Can the model see '7492'? -> {has_secret} (Turn 1 fell off the tray!)")

    print("\n=== STEP 2: 'Lost in the Middle' Recall Across a 10-Chunk Document ===")
    for idx in (0, 2, 5, 7, 9):
        prob = attention_recall_probability(idx, total_chunks=10)
        zone = "START (Primacy)" if idx == 0 else ("END (Recency)" if idx == 9 else ("DEAD MIDDLE" if idx == 5 else "INNER"))
        print(f"  Chunk {idx+1:2d}/10 [{zone:15}] -> Recall accuracy: {prob*100:5.1f}%")


if __name__ == "__main__":
    main()
