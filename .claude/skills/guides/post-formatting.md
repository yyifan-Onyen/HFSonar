---
name: post-formatting
description: Markdown shape for HFSonar's local-queue social posts
---

# Post format

Output is a Markdown file dropped into `runs/<ts>/posts/`. Frontmatter is added
by the Python runner — your job is the body, starting at line 1 of *your*
output.

## Structure

```
<one-line hook>

<2–4 paragraphs OR 4–7 bullets>

<single URL line, if not already in the hook>
```

## Specific rules

- Title-case proper nouns (HuggingFace, ChatGPT, but `transformers`, `bitsandbytes` lower-case).
- Model IDs in backticks: `Qwen/Qwen3-Next-80B`.
- Paper titles in *italics*.
- License names in plain text: Apache-2.0, MIT, CC-BY-4.0.
- If the signal is a paper, prefer the HuggingFace papers URL over arXiv (the
  HF page links to both and gathers community discussion).

## Anti-patterns to refuse

- Don't write "Check it out!" — useless filler.
- Don't write "More details below ↓" — the post IS the details.
- Don't promise context you don't have ("benchmarks coming soon") unless the
  source explicitly said so.
