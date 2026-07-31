---
# global
name: default
description: Handle a bounded general-purpose task that combines analysis, coordination, synthesis, or supporting implementation.

# replacement
claude:
    name: default
    model: sonnet
    effort: high
    tools:
    - Read
    - Write
    - Edit
    - NotebookEdit
    - Bash
    - Grep
    - Glob
    - LSP
    permissionMode: acceptEdits
codex:
    name: default
    model: gpt-5.3-codex-spark
    model_reasoning_effort: high
    sandbox_mode: read-only
---

${Instructions Prompt}
