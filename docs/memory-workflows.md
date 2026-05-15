# Memory Workflows

Use memory when a fact, decision, constraint, or next action should survive across AI sessions. Private details stay local in your AOS home and should not be copied into public issues, screenshots, or shared release docs.

## Session Memory

Use session memory after meaningful work:

```bash
aos memory template session --project-id demo
aos memory add session --project-id demo \
  --title "Session title" \
  --summary "What changed, why it matters, and what should persist." \
  --tag "handoff" \
  --decision "Key decision made during the session." \
  --artifact "path/or/link-to-important-output" \
  --next-action "Concrete next step."
```

Good session memory includes:

- What changed
- Why it matters
- Decisions made during the session
- Important artifacts or files
- Concrete next actions

After recording memory, re-run `aos compile` for the provider you use when you want that memory reflected in provider instructions.

## Decision Memory

Use decision memory for choices that should be easy to recover later:

```bash
aos memory template decision --project-id demo
aos memory add decision --project-id demo \
  --title "Decision title" \
  --rationale "Context, options considered, and why this path was chosen."
```

Good decision memory includes the context, options considered, selected path, and reason the rejected options were not chosen.

## Recovery

List recent memory:

```bash
aos memory list --project-id demo
```

Search for a prior decision or session:

```bash
aos memory search "provider instructions" --project-id demo
```
