---
name: spell
description: Execution phase for talking head video generation
workflows:
  - talking-head-create
  - talking-head-copy
---

# Spell — Execution Phase

Execute the spell phases for the selected workflow.
Requires cast to have been completed first (planning data available).

## Rules
- Execute phases sequentially
- Each phase builds on previous phase outputs
- Error recovery: retry failed chunks, preserve completed work
- All python commands use `.venv/bin/python`
- Progress updates at each step
