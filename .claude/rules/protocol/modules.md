---
paths:
  - "protocol/**"
---

# Modules

## Placement

- Group the schema by topic, the way Paper's API splits its packages: one module per topic, named in one lowercase word, with the BDS folders it draws from listed in `folders.md`.
- Open every module with a one-sentence docstring in the style of a Paper package doc: `"""Packets and types relating to <subject>."""`, or a `Types ...` sentence for a module without packets.
- Say only what a module holds: no lists, exclusions, history or implementation notes.
- Keep BDS internals out of the DSL files: no folder, header, namespace, member or function name in a docstring or comment; name a subject by its schema name.
- Settle placement by grepping the docstrings (`head -qn 1 protocol/*.py`) and `folders.md`, never by re-deriving the taxonomy.
- Declare `package = "bedrock.protocol"` after a module's imports, `java_package = "dev.endstone.protocol"` on the line below it and `go_package = "github.com/EndstoneMC/bedrock-protocol/go/protocol"` below that, and add the module's header to `include/bedrock/protocol.hpp` in the same commit.
- Change a module's docstring and its `folders.md` row in the same commit that widens its subject or adds a folder it draws from.
- Place a declaration in its topic's module, taking the BDS header's folder as the first guide, since BDS mostly groups by topic too:
  - a reusable type goes to its topic's module;
  - an encoding-only type under `network/packet/types/<path>/` goes to the module of `<path>`'s topic;
  - a payload declared in the packet's own header nests in the `@packet`;
  - where the folder and the topic disagree, the topic wins.
- Where the folder cannot decide (it appears at two depths, or holds over 100 headers or under 3), place a packet in the module whose docstring names its subject, never by the types it references.
- Keep a packet family, such as every move, motion and movement-prediction packet with its data types, in one module, and let no two module docstrings claim the same subject.
- Never create a module because of size; a lookup table lives with its subject.
- Give a topic Paper's API designs on its own, such as boss bars, skins or abilities, its own module, even when BDS files it under a larger folder; never fold one into actor.py or player.py.

## Order

- Order a module live-first: classes live at the last of `versions` on top, then the dead ones, newest `until=` first, with no banner between them.
- Keep a redeclaration chain together in ascending order; it moves to the tail only when its last declaration carries `until=`.
- Treat declaration order as meaningless beyond that layout.
