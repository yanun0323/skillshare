---
name: no-skill
description: Disable optional skill loading for the current and subsequent work until the user explicitly changes mode.
disable-model-invocation: true
---

# No Skill Action

Disable automatic skill behavior.

## Rules

- Do not load, open, or apply other skills merely because they match the task.
- Do not inspect skill files, references, scripts, or assets unless the user explicitly requests that file/skill.
- Continue following system, developer, AGENTS, security, repo, and direct user instructions.
- Use normal tools and repo conventions.
- Stay active until the user invokes another skill, stops `no-skill`, or higher-priority instructions require a skill.
- Mention skipped skills only when it affects risk, verification, or expectations.
