---
name: go
description: Go backend guardrails. Use when changing or reviewing a Go backend, or when another skill needs its project constraints.
disable-model-invocation: false
---

# Go Backend Guardrails

Apply every relevant guardrail below. Repository evidence takes precedence over a listed default; when the repository clearly contradicts the project shape and the intended ownership is ambiguous, pause for user direction.

## Project Shape

Keep one monolithic backend binary at `cmd/server/main.go`. Keep `cmd/server` limited to bootstrap and wiring; place business logic in the owning application layer. Preserve the existing directory structure unless the request explicitly changes it.

| Directory | Ownership |
| --- | --- |
| `cmd/server` | Bootstrap and wiring |
| `config` | Schemas, defaults, and loaders |
| `internal/delivery` | Transport, validation, and mapping |
| `internal/usecase` | Business logic |
| `internal/repository` | Persistence |
| `internal/model` | Domain entities |
| `internal/model/enum` | Domain enums |
| `internal/adapter` | Ports and interfaces |
| `infrastructure` | Docker, Compose, Kubernetes, and deployment |
| `pkg` | Stateless shared utilities |

Dependencies point inward along these allowed edges:

- `model -> enum, pkg`
- `adapter -> model, enum, pkg`
- `delivery, usecase, repository -> adapter, model, enum, pkg`
- `config -> pkg`
- `pkg` remains independent of `internal`, `config`, and `cmd`

Treat a cross-layer edge outside this graph as an ownership conflict; resolve the owner before implementing it.

## Dependencies

Reuse the repository's established libraries. When a capability is absent, default to `viper` for configuration, `zerolog/log` for logging, `echo/v4` for HTTP, `gorilla/websocket` for WebSocket, `gorm` for ORM, and `sonic` for JSON. Add or replace a library only when the request requires it.

Keep `viper` inside `config` and bootstrap. Inject typed configuration into application layers.

## Runtime

- Keep handlers thin: parse and validate input, call a port, then map the response.
- Propagate request context. Bound external calls with cancellable timeouts.
- Return and handle application errors explicitly; reserve `panic` for unrecoverable bootstrap failures.
- Wrap an error with `%w` only when a caller needs to inspect its cause.
- Assign logging to one layer so the same error is not both logged and returned there.
- Return stable machine codes and safe messages to clients; retain internal details in server-side error context.
- Give every goroutine an owner, cancellation path, and shutdown path.
- Trace initialization explicitly from `cmd/server/main.go`; use constructors instead of `init()`.

## Contracts and Verification

Preserve existing API envelopes, status codes, and naming conventions. Keep the change local to the request and preserve exported API names unless the request changes the contract.

For every new or changed endpoint, add existing-pattern tests covering success, validation failure, and one meaningful edge case. If automated tests are unavailable or explicitly excluded, report concrete manual verification instead.

## Infrastructure and Decision Gates

When a change adds a port, environment variable, external service, or build/runtime requirement, update the corresponding infrastructure configuration already present in the repository.

Pause for user direction when authentication or authorization behavior, money or order invariants, irreversible migration behavior, goroutine lifecycle, or layer ownership cannot be established from repository evidence.
