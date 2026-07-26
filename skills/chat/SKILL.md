---
name: chat
description: Answer questions from local and web evidence while keeping the workspace unchanged.
disable-model-invocation: true
---

# Read-Only Chat

## 1. Establish the Boundary

Operate entirely through known read-only actions. Keep files, dependencies, processes, external systems, and Git history unchanged.

If the request includes a mutation, treat that part as a request for analysis or a proposed plan. State that `action-chat` is read-only and that implementation requires leaving this mode. The boundary is established when every requested action is classified as inspection or mutation and only inspection remains executable.

## 2. Gather Evidence

Inspect local files, repository state, and read-only command output. Search the web when the user requests it or when a material fact is current or uncertain; cite the supporting sources.

Use only commands whose behavior is known to be read-only. Write operators and mutating utilities—including `>`, `>>`, `tee`, `touch`, `mkdir`, `cp`, `mv`, `rm`, in-place editors, patch tools, installers, formatters, generators, and history-changing Git commands—are outside this mode.

Evidence gathering is complete when each material claim is supported by local evidence, a cited source, or an explicit uncertainty.

## 3. Answer

Explain, compare, summarize, review, diagnose, or propose a plan from the gathered evidence. Cite local paths and line numbers where useful. Finish with the workspace unchanged and clearly identify any requested mutation that remains unperformed.
