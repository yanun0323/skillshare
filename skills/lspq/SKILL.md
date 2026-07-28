---
name: lspq
description: Semantic code navigation through LSP. Use when the user wants a file's symbol structure, type information at a position, a symbol's definition, or reference-based change-impact tracing in Go, Rust, Python, TypeScript/JavaScript, C, or C++.
---

# lspq

LSP navigation starts from a **semantic anchor**: one workspace, source file, language, and—when required—zero-based position. Use textual search to find candidate anchors; use `lspq` to prove symbol identity.

## 1. Establish the semantic anchor

Resolve:

- `workspace`: the project root the language server should load.
- `file`: the source file containing the symbol or occurrence.
- `language`: one of `go`, `rust`, `python`, `typescript`, `c`, or `cpp`.
- `line` and `character`: the zero-based LSP position for `definition`, `references`, or `hover`. `character` counts UTF-16 code units.

For a named declaration, run `symbols` first and use its matching symbol range as the position. For an occurrence, locate it in the source and convert its line and character to zero-based coordinates.

This step is complete when the anchor identifies one exact source occurrence. If multiple same-name candidates remain, inspect their surrounding source until one is selected.

## 2. Run the narrowest semantic query

Inspect file structure:

```sh
lspq symbols --language "$language" --workspace "$workspace" --file "$file"
```

Query a position:

```sh
lspq hover      --language "$language" --workspace "$workspace" --file "$file" --line "$line" --character "$character"
lspq definition --language "$language" --workspace "$workspace" --file "$file" --line "$line" --character "$character"
lspq references --language "$language" --workspace "$workspace" --file "$file" --line "$line" --character "$character"
```

Choose one command per question:

| Question | Command |
| --- | --- |
| What declarations does this file contain? | `symbols` |
| What is the type, signature, or documentation here? | `hover` |
| Where is this occurrence defined? | `definition` |
| Which occurrences resolve to this symbol? | `references` |

This step is complete when the command exits successfully and stdout is valid JSON for the requested command.

## 3. Follow semantic evidence

- For `symbols`, traverse nested `children` and match by name, kind, and enclosing symbol.
- For `definition`, open every returned URI/range needed to identify the owning declaration.
- For `references`, account for every returned URI/range when assessing change impact; classify generated, test, and production occurrences when that distinction affects the answer.
- For `hover`, use `contents.kind`, `contents.value`, and the returned range as the server's answer for the anchored occurrence.

LSP ranges are zero-based. Convert `range.start.line` to one-based lines when presenting clickable file locations to the user.

This step is complete when every claim in the answer is backed by a returned semantic location or hover payload, and change-impact answers account for every returned reference.

## Recovery branch

When `lspq` is missing, exits non-zero, returns an error envelope, or unexpectedly returns no result, read [TROUBLESHOOTING.md](TROUBLESHOOTING.md) and recover there before answering.
