---
name: hf-context
description: Background on the HuggingFace ecosystem so HFSonar's curator and writer make informed calls
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
*derivative news*, not *primary news*. Posting the upstream is almost always
better unless the quantization itself is novel (first MLX port, first AWQ
fitting in 24GB, etc.).

## Daily Papers

`huggingface.co/papers` is curated daily; high-upvote papers usually have
genuinely interesting findings. The HF papers page links to the arXiv abstract
*and* shows community comments, so prefer that URL when posting.

## Watchlist orgs (current)

`meta-llama`, `mistralai`, `Qwen`, `deepseek-ai`, `google`, `microsoft`,
`stabilityai`, `black-forest-labs`, `nvidia`, `anthropic`. Releases from these
are noteworthy by default; the bar for "is this interesting?" is lower because
the audience cares about the source.

## Things that look exciting but usually aren't

- Empty repos (downloads == 0, no model files yet).
- README-only repos.
- "Test" / "demo" / "scratch" / "tmp" in the model ID.
- Re-uploads of public datasets (e.g. someone copying The Pile).
- Aggressive `merge` / `slerp` / `dare_ties` chimera models with vague claims.
