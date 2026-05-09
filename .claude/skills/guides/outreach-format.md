---
name: outreach-format
description: Required shape for HFSonar's outreach drafts so a Python post-processor can consume them
---

# Outreach draft format

Your output goes into `runs/<ts>/outreach/NN__source__id.md`. The Python
runner adds JSON frontmatter automatically — your output starts at line 1 of
the *body*, never includes its own `---` frontmatter block.

## Required body shape

```
**Channel:** <email | twitter_dm | github_comment>

**To:** <recipient name and best contact identifier>

**Subject:** <subject line — INCLUDE THIS LINE ONLY IF channel is email>

---

<message body — 3–5 sentences>

Best,
<your name>
```

## After the body

If multiple contact channels exist, append:

```

## Alternative channels

- twitter: @handle — context (e.g. "active there, posts about RL")
- github: username — context
- website: url — context
```

## Hard rules

- The `**Channel:**` line is mandatory and must be the FIRST non-blank line.
- Use `<…>` placeholders for facts you don't have (sender's name, sender's
  background). Never invent.
- Do NOT include the recipient's verified email address in the body itself.
  It already lives in the frontmatter that the runner adds. The body is the
  *content*, not the address.
- Use plain text. No HTML, no markdown styling inside the message body
  (bold/italic OK in the To/Subject lines, but not inside the message).
- One blank line between paragraphs.

## Specific rules per channel

### Email
- Subject must be specific to the work, not "Question" or "Hello".
- Sign-off: "Best," not "Sincerely," / "Cheers," / "Yours truly,".
- No emoji.

### Twitter / X DM
- Drop the Subject line entirely.
- Opener ≤ 280 chars so the user can copy just the opener as a public reply.
- Plain text. No "thread →" gimmicks.

### GitHub issue / discussion
- Frame as a question, not a critique.
- Reference the specific file / model / discussion if applicable.
- Include "no rush — just curious" so it doesn't look like a bug report.
