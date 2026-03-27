---
name: cast
description: Planning phase for talking head video generation
workflows:
  - talking-head-create
  - talking-head-copy
---

# Cast — Planning Phase

Select a workflow and execute its cast phases sequentially.

## Available Workflows

1. **talking-head-create** — Original talking head from title/script
2. **talking-head-copy** — Recreate Instagram video with AI character

Load the workflow from `workflow.json` and execute each cast phase prompt in order.
Each phase prompt is in the `prompts/` directory.

## Rules
- Execute phases sequentially
- Each phase must complete before the next begins
- User approval required at the review phase before proceeding to spell
- All python commands use `.venv/bin/python`
