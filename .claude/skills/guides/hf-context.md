---
name: hf-context
description: Background on the HuggingFace ecosystem and where to find author contact info, so the curator / researcher / drafter make informed calls
---

# HuggingFace context for HFSonar

## What "trending" actually means

Trending on HuggingFace is dominated by:
1. Recently-released base models from major labs (Meta, Mistral, Qwen, DeepSeek, Google, Microsoft).
2. Community quantizations (GGUF, GPTQ, AWQ, MLX) of those base models — usually by
   `TheBloke`, `bartowski`, `mlx-community`, or similar handles.
3. Image / video gen checkpoints (Flux, Stable Diffusion variants, Wan, Hunyuan).
4. Embedding models — `BAAI/bge-*`, `mixedbread-ai/*`, `nomic-ai/*`.

A model with 1000 likes that's a quantization of a model with 10000 likes is
*derivative* — there's no individual researcher worth reaching out to about it.
The original release is where the people are.

## Daily Papers

`huggingface.co/papers` is curated daily. High-upvote papers usually have
identifiable corresponding authors in the abstract. The HF papers page links
to arXiv and shows community comments — both are good context for personalizing
outreach.

## Watchlist orgs (current)

`meta-llama`, `mistralai`, `Qwen`, `deepseek-ai`, `google`, `microsoft`,
`stabilityai`, `black-forest-labs`, `nvidia`, `anthropic`. Releases from these
are noteworthy by default — but be picky: a drop from "Meta" doesn't mean a
specific researcher to reach out to. Look in the model card for a named
contributor before drafting outreach.

## Author identification — where to look

For a **paper** (`source: daily_papers`):
- The HF papers page lists authors with affiliations.
- The arXiv abstract page is linked from HF papers; the PDF first page has
  the corresponding author's email almost always.
- The corresponding author is the one with the asterisk or "✉" — that's the
  primary outreach target.

For a **model** (`trending_models` / `new_models` / `watchlist`):
- The model card README often has an "Authors" or "Acknowledgments" section.
- The HF org page usually links to the team's website / Twitter.
- The author field is often an org, not a person — go to the HF org page and
  look for a "members" tab or social links.
- For independent uploaders (e.g. `someuser/somemodel`), `huggingface.co/<user>`
  often links Twitter and a personal website.

## Where contact info lives, ranked by reliability

| Source | What you find | Reliability |
| --- | --- | --- |
| arXiv PDF first page | Corresponding author email | Very high (but requires PDF fetch) |
| HF user/org profile page | Twitter, GitHub, website links | High |
| GitHub user profile | Public email (sometimes), Twitter | Medium |
| Personal website | Email, links to all socials | High when exists |
| Google Scholar profile | Affiliation, email (sometimes) | Medium |
| LinkedIn search | Name + affiliation match | Low — easy to mis-identify |

## Things that look exciting but usually aren't (for outreach purposes)

- Empty repos (downloads == 0, no model files yet) — no work to discuss.
- README-only repos.
- "Test" / "demo" / "scratch" / "tmp" in the model ID.
- Re-uploads of public datasets.
- Aggressive `merge` / `slerp` / `dare_ties` chimera models with vague claims —
  the "author" isn't really the originator.
- Releases attributed to a faceless team `support@<company>.com` with no
  named individual on the model card.
