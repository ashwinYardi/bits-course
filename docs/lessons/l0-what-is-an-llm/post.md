# What an LLM actually is
*What is the model really doing when it answers you?*
> **In one line:** An LLM does not look up answers or plan sentences ahead of time; it scores every possible next word in its dictionary, rolls a weighted die to pick one, glues that word onto your prompt, and starts over from scratch.

## Explain it like I'm 12: The world's fastest relay game

Imagine you are playing a game with a friend who has read every book in the school library. You write two words on a slip of paper: `the server`.

Your friend is only allowed to write **one single word** on the slip and hand it back. They look at `the server`, quickly score every word in the English dictionary, write `crashed` at the end, and slide the paper back across the desk.

Now the slip says `the server crashed`. Here is the secret: your friend immediately gets amnesia about *why* they picked `crashed`. For the next word, they pick up the slip (`the server crashed`) as if they are seeing it for the very first time, score the whole dictionary again, and write `because`.

That relay loop is a **large language model** in plain words: a computer program trained on massive text that scores every possible next piece of text, picks one, glues it onto your message, and repeats. It never writes a whole paragraph at once. It plays the one-word relay game fifty times a second.

![Every single word the AI picks gets glued back onto your prompt for the next pass.](fig-01.svg)
*Every single word the AI picks gets glued back onto your prompt for the next pass.*

## Why the AI doesn't remember you from yesterday (Training vs Inference)

If you tell a chatbot your dog's name today and open a new window tomorrow, it has no clue who your dog is. Why?

Because the life of an AI is split into two completely separate phases:

1. **training** in plain words: the months-long factory phase where the model reads trillions of words and nudges billions of internal number dials (**parameters**) whenever it guesses the next word wrong.
2. **weights** in plain words: the final numbers locked into those dials when training finishes. A 7-billion-parameter model is literally just a giant file on a hard drive holding 7 billion frozen decimals.
3. **inference** in plain words: running your message through that frozen file to predict the next word. During inference, every single dial is glued shut. Your chat never edits the brain; it just passes through it.

![Training adjusts the dials once at massive cost. Your chat happens on a frozen copy.](fig-03.svg)
*Training adjusts the dials once at massive cost. Your chat happens on a frozen copy.*

## How the scoreboard and the weighted die work (Logits, Softmax & Temperature)

Wait — if the dials are frozen, why doesn't the AI give the exact same answer every time you ask the same question?

Because the frozen brain does not output a single word. It outputs a scoreboard across its entire dictionary, and then rolls a weighted die. Let's trace the exact numbers from our Python lab when the prompt is `the server`:

1. **The raw scoreboard (Logits).** The model outputs one raw score for every possible next word. Engineers call these **logits** in plain words: the raw, un-rounded scores the model gives each candidate word. In our lab, `crashed` gets `3.2`, `responded` gets `2.9`, `timed` gets `2.4`, `melted` gets `0.4`, and `danced` gets `-1.5`.
2. **The boldness dial (Temperature).** Before turning those raw scores into percentages, we divide every score by **temperature** in plain words: a dial that controls whether the #1 word hogs the spotlight or shares a chance with runner-up words.
3. **Turning scores into percentages (Softmax).** You cannot roll a die with a negative number like `-1.5`. So the computer runs **softmax** in plain words: a math formula (`2.718` raised to each score, divided by the total) that turns any list of raw scores into clean percentages that add up to `100%`.
4. **Watch the table above (`Figure 2`).** At Temperature `0.2`, `crashed` grabs `80.6%` of the pie. At Temperature `1.0`, `crashed` drops to `44.2%`, `responded` gets `32.8%`, and `timed` gets `19.9%`. Same frozen brain, completely different odds on the die.

![Real numbers from our 40-line Python lab: low temperature locks onto the #1 word, high temperature lets underdogs win.](fig-02.svg)
*Real numbers from our 40-line Python lab: low temperature locks onto the #1 word, high temperature lets underdogs win.*

## The Snowball Trap: How a 12-year-old intuition fixes a senior engineer's bug

Once you picture the one-word-at-a-time conveyor belt, you can immediately spot the #1 mistake developers make in production.

Suppose a developer writes a prompt: `'Answer YES or NO on line 1, then explain your reasoning on line 2.'`

Why is that a trap? Imagine the true answer is `NO`, so the scoreboard gives `NO` a `75%` chance and `YES` a `25%` chance. At Temperature `1.0`, the weighted die rolls a `25%` underdog and picks `YES`.

Now `YES` is glued onto the slip of paper! On the very next tick of the conveyor belt, the model reads `Answer: YES. Explanation:` and asks itself: *what words usually follow a YES answer?* It is now trapped into inventing an excuse for `YES`, even though its own weights knew `NO` was better.

**The pro fix:** Never ask a forward-only machine to state its verdict first. Always ask it to write the step-by-step reasoning *first* and put the `YES/NO` verdict on the very last token, so the reasoning sits on the slip of paper before the verdict die is rolled.

## Jargon Decoder

| Term | In plain words | Why you care |
|---|---|---|
| **large language model (LLM)** | A neural network trained on massive text that scores every possible next word. | Reminds you it is a pattern-completion relay engine, not an oracle or database. |
| **next-token prediction** | Guessing the single next piece of text given all the pieces before it. | Explains why word order in your prompt changes quality: the model cannot plan backwards. |
| **parameters** | The adjustable number dials inside the neural network. | More parameters (8B vs 70B) store subtler patterns, at higher memory and latency cost. |
| **weights** | The exact frozen numbers saved inside the parameters after training. | Weights are read-only during your chat; the model learns zero permanent facts from your prompt. |
| **training** | Showing the model trillions of words and nudging weights to shrink prediction mistakes. | Where the model's baseline knowledge and cutoff date come from. |
| **inference** | Running your prompt through the frozen weights to generate words. | What you actually pay for per million tokens when your app is live. |
| **logits** | The raw scoreboard numbers the model gives every word before turning them into percentages. | Every decoding control (temperature, top-p, JSON schemas) works by editing logits before rolling. |
| **softmax** | The formula that converts raw positive or negative logits into percentages summing to 100%. | Shows why runner-up words still have a chance to be picked when temperature > 0. |
| **temperature** | A divisor on logits before softmax that sharpens (0.2) or flattens (1.8) the odds. | Your main dial between repeatable greedy answers (0.0) and creative variety (1.0). |

## Hands-On Lab: Build the 40-line next-token predictor & diff 5 runs across temperatures

See with your own eyes how raw logits turn into probabilities under temperature 0.2, 1.0, and 1.8, and why temperature 0.0 produces 1 unique output across 5 runs while temperature 1.0 produces 5 distinct trajectories.
