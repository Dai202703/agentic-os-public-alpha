# Role Tutorials

These mini tutorials show the same AOS pattern across different jobs: create a category, save memory, compile provider instructions, and keep private details local.

## Writer

Use AOS to keep voice, outline decisions, and unresolved edits consistent across drafting sessions.

```bash
mkdir -p /tmp/aos-writer
aos link-project --project-root /tmp/aos-writer --id book-draft --name "Book Draft" --provider chatgpt --provider codex
aos memory add session --project-id book-draft --title "Voice rule" --summary "Write practical, example-led chapters with concise transitions."
aos compile chatgpt --project-root /tmp/aos-writer
```

Before a new writing session, run `aos memory search "Voice rule" --project-id book-draft` and re-run `aos compile` if you added new memory.

## Researcher

Use AOS to separate source quality notes, hypotheses, and synthesis decisions.

```bash
mkdir -p /tmp/aos-research
aos link-project --project-root /tmp/aos-research --id source-map --name "Source Map" --provider claude --provider chatgpt
aos memory add session --project-id source-map --title "Source hierarchy" --summary "Separate primary sources, analyst commentary, and unverified claims."
aos compile claude --project-root /tmp/aos-research
```

Keep citations and private notes in your local workspace. Do not paste restricted documents into public issues.

## Student

Use AOS as a study continuity file for classes, exam prep, or thesis notes.

```bash
mkdir -p /tmp/aos-study
aos link-project --project-root /tmp/aos-study --id exam-prep --name "Exam Prep" --provider gemini --provider chatgpt
aos memory add session --project-id exam-prep --title "Weak topics" --summary "Prioritize spaced repetition for cell signaling and genetics problems."
aos compile gemini --project-root /tmp/aos-study
```

When the study plan changes, add a session memory and compile again before asking an AI tutor to continue.

## Lawyer

Use AOS to structure matter notes without publishing client-sensitive material.

```bash
mkdir -p /tmp/aos-matter
aos link-project --project-root /tmp/aos-matter --id matter-notes --name "Matter Notes" --provider claude --provider chatgpt
aos memory add session --project-id matter-notes --title "Review scope" --summary "Track issue list, cited authority, and drafting boundaries without public client facts."
aos compile chatgpt --project-root /tmp/aos-matter
```

Use neutral category IDs. Keep client names and privileged facts in private local files, not public docs or screenshots.

## Developer

Use AOS to make AI coding sessions start with the same rules, test commands, and release constraints.

```bash
mkdir -p /tmp/aos-dev
aos link-project --project-root /tmp/aos-dev --id product-mvp --name "Product MVP" --provider codex --provider claude --provider gemini --provider chatgpt
aos memory add session --project-id product-mvp --title "Release rule" --summary "Run targeted tests first, then full unittest before release."
aos compile codex --project-root /tmp/aos-dev
```

After meaningful decisions, record memory so the next provider output carries the current project rules.
