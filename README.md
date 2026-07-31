# skillshare

[English](README.md) | [繁體中文](README_TW.md)

This repository is a personal collection of AI CLI configuration. It provides reusable `skills`, `agents`, and RTK command-output integration, then uses [`skillshare`](https://github.com/runkids/skillshare) to synchronize one source of truth to Claude Code, Codex CLI, and Pi.

This is not a standalone application. The repository mainly contains Markdown, YAML, TOML, Python, and JavaScript configuration files. `config.yaml` defines the synchronization rules, while `skills/`, `extras/`, and `extensions/` contain the managed content.

## Contents

- `skills/`: Skills available to AI agents. Each skill defines its behavior in `SKILL.md` and may include references and scripts.
- `agents/`: Agent configurations that can be synchronized to different AI CLIs. Shared templates are converted to each target's format.
- `rtk`: A PreToolUse hook that routes eligible Bash commands through `rtk`. If `rtk` is not installed, the original command is left unchanged.

## Quick start

The current configuration expects this repository at `~/.config/skillshare`. After confirming that `skillshare` is installed and available on `PATH`:

```bash
cd ~/.config/skillshare

# Inspect source, targets, and synchronization status
skillshare status

# Preview changes for skills, agents, and extras
skillshare sync --dry-run

# Run the security scan, then apply changes to all targets
skillshare audit --no-tui --yes
skillshare sync --all

# Verify the resulting state and remaining differences
skillshare status
skillshare diff --stat
```

Useful partial-sync commands:

```bash
skillshare sync          # Sync skills only
skillshare sync agents   # Sync agents only
skillshare sync --all    # Sync skills, agents, and extras
```

If the repository is stored elsewhere, update the `~/.config/skillshare/...` paths in `sources.skills` and each `extras[].source` entry in `config.yaml`, or create an equivalent project-mode configuration.

## Using skills

After synchronization, each AI CLI loads skills from its configured target directory. The invocation syntax depends on the tool, for example:

```text
Claude Code: /<skill-name>
Codex CLI:   $<skill-name>
```

The skill name is the directory name under `skills/<name>/`. The corresponding `SKILL.md` contains the skill's behavior and usage rules. Agents are loaded from each AI CLI's agents directory.

The `disable-model-invocation` field in `SKILL.md` controls whether a skill must be explicitly invoked by the user:

- `true`: The skill can only be invoked explicitly by the user.
- `false` or omitted: The model may choose the skill based on its description.

Read the relevant `SKILL.md` for details, and avoid editing synchronized files in the target directories directly.

## Repository layout

```text
.
├── config.yaml                         # skillshare source, target, and extras configuration
├── skills/
│   ├── <name>/SKILL.md                  # Main skill file
│   ├── <name>/agents/openai.yaml        # Optional agent metadata
│   ├── <name>/references/               # On-demand skill references
│   ├── <name>/scripts/                  # Skill helper scripts
│   └── .metadata.json                   # Source, version, and hash metadata
├── extras/
│   ├── all/agents/                      # Shared agents
│   ├── all/hooks/                       # Shared hooks
│   ├── claude/                          # Claude Code instructions and agents
│   └── codex/                           # Codex CLI instructions and agents
└── extensions/
    ├── agents_convert_tool/             # Markdown/YAML conversion core
    ├── claude-agents/                   # Converts to Claude agent Markdown
    └── codex-agents/                    # Converts to Codex agent TOML
```

## Synchronization targets and exclusions

`config.yaml` currently uses `merge` mode to combine the source with these targets:

| Target | Skills path | Notes |
| --- | --- | --- |
| Claude Code | `~/.claude/skills` | Synced according to the exclusions in the configuration. |
| Codex CLI | `~/.codex-cli/skills` | Syncs skills from the source. |
| Pi | `~/.pi/agent/skills` | Syncs skills from the source. |

`extras` manages the following additional content:

- Claude instructions, `CLAUDE.md`, settings, and status line: `extras/claude/instructions` → `~/.claude`.
- Codex instructions, `AGENTS.md`, and `config.toml`: `extras/codex/instructions` → `~/.codex-cli`.
- Shared agents: `extras/all/agents` are converted for each target tool and written to its agents directory.
- RTK hook: `extras/all/hooks` is synchronized to both Claude and Codex hook directories.

To change which targets receive which skills, edit the `targets` or exclusion rules in `config.yaml`, then run `skillshare sync --dry-run` to inspect the result.

## Adding or modifying content

### Add a skill

Use the CLI to create a template:

```bash
skillshare new my-skill --global
```

Then edit `skills/my-skill/SKILL.md` and add `references/`, `scripts/`, or `agents/openai.yaml` when needed. Recommended follow-up checks:

```bash
skillshare audit ./skills/my-skill --no-tui
skillshare sync --dry-run
skillshare sync --all
```

Install an external skill with `skillshare install <source>`. To update tracked external sources, run `skillshare check` first, then use `skillshare update` as needed.

### Add or modify an agent

Place shared agents in `extras/all/agents/` and target-specific agents in `extras/<target>/agents/`. Shared templates can use target-specific frontmatter; the `claude-agents` and `codex-agents` extensions convert it to the target tool's format.

```markdown
---
name: example
description: Handle a bounded example task.
claude:
  model: sonnet
codex:
  model: gpt-5.3-codex-spark
---

Mission: Describe the agent's bounded outcome and validation target.
```

Edit the source files instead of editing synchronized output under `~/.claude` or `~/.codex-cli` directly.

## Validation

This repository does not currently have a unified package build. After making changes, use the following commands to check formatting and synchronization state:

```bash
git diff --check
skillshare status
```

Some image-processing scripts require Python 3, `Pillow`, or `numpy`; these dependencies are only needed when running the relevant scripts.

Before synchronizing, inspect file-level differences with:

```bash
skillshare diff --stat
skillshare diff --patch
```

Because the targets use `merge` mode, inspect local changes in target directories first. `skillshare sync --force` may overwrite local target content.
