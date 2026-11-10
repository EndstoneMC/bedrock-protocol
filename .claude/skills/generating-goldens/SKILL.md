---
name: generating-goldens
description: Generates golden wire bytes for a bedrock-protocol test by marshalling a packet or type with Sandertv/gophertunnel, at its current shape or at an older protocol's commit. Use whenever a test needs expected bytes, when adding, back-porting or renumbering a protocol version, or when a golden and the schema disagree.
---

# Generating goldens

Where a golden goes and how it is labelled is `.claude/rules/tests.md`; this is the procedure.

## Steps

1. In a Sandertv/gophertunnel clone (clone it if missing), pick the commit: HEAD for the latest protocol, otherwise the era's commit from `git log --reverse --format=%h -S'CurrentProtocol = <N>' -- minecraft/protocol/info.go | head -n 1`.
2. Run `git worktree add <dir> <commit>` rather than moving the clone.
3. In a scratch directory outside both repositories, write two files:
   - `go.mod` with `module golden`, `require github.com/sandertv/gophertunnel v0.0.0` and `replace github.com/sandertv/gophertunnel => <dir>`;
   - `main.go`, with the packet literal you need:
     ```go
     package main

     import (
     	"bytes"
     	"fmt"

     	"github.com/sandertv/gophertunnel/minecraft/protocol"
     	"github.com/sandertv/gophertunnel/minecraft/protocol/packet"
     )

     func main() {
     	pk := &packet.PlayStatus{Status: packet.PlayStatusPlayerSpawn}
     	buf := bytes.NewBuffer(nil)
     	pk.Marshal(protocol.NewWriter(buf, 0))
     	fmt.Printf("%x\n", buf.Bytes())
     }
     ```
4. Run `go mod tidy && go run .`, then paste the hex and the literal into the test the way `tests.md` says, naming the commit.
5. Run `git worktree remove <dir>`.

## When it goes wrong

- `Marshal` wants `protocol.IO` at one commit and `*protocol.Writer` at another -> pass `protocol.NewWriter(buf, 0)`, which satisfies both.
- `go` refuses the commit's `go` directive -> run with `GOTOOLCHAIN=auto`.
- The value is a type, not a packet -> call its `Marshal` on the same writer.
- gophertunnel lacks a field the schema has at that era -> it cannot marshal the shape; assert it structurally (`tests.md`).
- The bytes disagree with the schema -> follow the patch rule in `tests.md`.
- The header of a framed packet disagrees with BDS -> golden the body only (`.claude/rules/protocol/wire.md`).
