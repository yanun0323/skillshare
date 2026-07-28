# lspq troubleshooting

Read this reference only after the main semantic query cannot produce usable evidence.

## `lspq` is unavailable

Check the executable:

```sh
command -v lspq
```

Installing a user-level executable and language toolchains changes the environment. Obtain user approval before running:

```sh
curl -fsSL https://raw.githubusercontent.com/yanun0323/lspq/master/install.sh | sh
```

If the repository contains the lspq source, it can be exercised without installation:

```sh
go run ./cmd/lspq <command> ...
```

## Language server startup fails

Run the adapter health check with the same workspace and timeout:

```sh
lspq doctor --language "$language" --workspace "$workspace" --timeout 30s
```

The built-in executables are:

| Language | Executable and default arguments |
| --- | --- |
| `go` | `gopls` |
| `rust` | `rust-analyzer` |
| `python` | `pyright-langserver --stdio` |
| `typescript` | `typescript-language-server --stdio` |
| `c`, `cpp` | `clangd` |

Use an installed server outside PATH with `--server`; supply each replacement argument with a separate `--server-arg`:

```sh
lspq doctor --language python --workspace "$workspace" \
  --server /absolute/path/pyright-langserver --server-arg=--stdio
```

## Error envelopes

`lspq` writes machine-readable errors to stdout:

| Code | Recovery |
| --- | --- |
| `unsupported_language` | Select a language from the supported table. |
| `server_unavailable` | Run `doctor`; verify executable, workspace, and timeout. |
| `query_failed` | Verify the file belongs to the workspace and the anchor is inside the file. |
| `shutdown_failed` | Retry once after confirming no stale server process owns the workspace. |
| `usage` | Correct the command flags; `--file` is required for semantic queries. |

## An expected result is empty

Validate the anchor in this order:

1. Run `symbols` for a declaration or `hover` for an occurrence.
2. Confirm the returned range contains the intended source token.
3. Confirm `workspace` is the root that owns the file.
4. Retry with `--timeout 60s` to allow initial indexing.

An empty result after all four checks is valid semantic evidence: report that the language server found no result for the confirmed anchor.

## Language-specific workspace checks

- Go: the workspace should expose its `go.mod` or `go.work` to `gopls`.
- Rust: the workspace should contain the owning `Cargo.toml`.
- Python: use the project root containing `pyproject.toml`, `setup.py`, or requirements files.
- TypeScript/JavaScript: use the root containing `tsconfig.json`, `jsconfig.json`, or `package.json`.
- C/C++: provide `compile_commands.json` or `compile_flags.txt` so clangd sees the build flags.
