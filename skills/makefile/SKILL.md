---
name: makefile
description: Entrypoint standardization. Use when creating or updating build, test, run, environment, or Docker wrappers in a Makefile or equivalent package scripts.
disable-model-invocation: false
---

# Entrypoint Standardization

## 1. Discover the Real Commands

Inspect the repository's existing documentation, automation, manifests, and CI before choosing entrypoints. Account for every requested lifecycle operation by tracing it to an existing command or confirming that the repository has none.

## 2. Choose the Entrypoint

Prefer `make build`, `make test`, and `make run` when the repository has or needs a Makefile.

- In a `package.json` repository, equivalent `build`, `test`, and `run` scripts are sufficient. A Makefile may delegate to them when Make is the repository's standard entrypoint.
- In a `Package.swift` repository, wrap `swift build`, `swift test`, and `swift run` unless an equivalent standard entrypoint already exists.

The choice is complete when each requested operation has one clear, repository-native entrypoint.

## 3. Add Thin Wrappers

Wrap established commands without changing dependencies, toolchains, or architecture. Add only targets supported by a real workflow; typical names are `run`, `dev`, `build`, `test`, `lint`, `fmt`, and `clean`.

For a Makefile:

- Give every explicit target a `## ` help comment.
- Declare `.PHONY: $(wildcard *)`.
- Preserve command arguments with `ARGS := $(word 2,$(MAKECMDGOALS))` and a catch-all target when the wrapped command accepts them.

When the request includes environment or Docker wrappers, apply the relevant reference below. The edit is complete when every new entrypoint is thin, discoverable through help, and maps to the command found in step 1.

## 4. Verify the Surface

Parse the Makefile or package manifest, inspect the generated help, and exercise the safest relevant entrypoints. Use dry runs for stateful commands. Verification is complete when every added or changed entrypoint resolves to the intended underlying command and failures are reported with the exact check that could not run.

## Environment Reference

- `Makefile.env` holds git-ignored build or deployment environment values.
- Add committed `Makefile.local.env` only when a local template is needed; load it after `Makefile.env` so it can override shared values.
- A target that needs `Makefile.local.env` sources it explicitly with `set -a; . ./Makefile.local.env; set +a; ...`.
- Keep credentials out of committed files.

## Docker Reference

Wrap existing Docker assets with only the targets the request needs: `docker-build`, `docker-run`, `compose-up`, `compose-down`, and `compose-logs`. Use `docker compose` unless the repository already standardizes on `docker-compose`.

When ports, environment values, services, or build behavior change, update the corresponding infrastructure configuration already present in the repository.

## Base Makefile

Use this only when the repository needs a new Makefile; remove any line the actual workflows do not use.

```make
-include Makefile.env
export

.PHONY: $(wildcard *)

## help: show help
help:
	@echo ""
	@echo "Usage:"
	@echo ""
	@sed -n 's/^## //p' Makefile | column -t -s ':' | sed -e 's/^/\t/'
	@echo ""

ARGS := $(word 2,$(MAKECMDGOALS))
%:
	@:
```
