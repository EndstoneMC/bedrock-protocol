---
paths:
  - "protocol/**"
---

# Names

## Names mirror BDS

- Match BDS class names and nesting exactly; never fold an enclosing namespace into a class name (`Bedrock::Profile::Whisker::Diagnostics::ScopeDataSummary` is `ScopeDataSummary`).
- Keep a BDS `Outer::Inner` nested; never flatten it to `OuterInner`.
- Map `FooPacketPayload` onto `@packet FooPacket` and move its nested types into the packet; no `...PacketPayload` class exists in the schema.
- Type actor ids as `ActorUniqueID` or `ActorRuntimeID` even where BDS declares a plain integer, keep the wire with `field(type=)` (`target_player_id: ActorUniqueID = field(type=int64)`), and pick which one from where BDS fills the member.
- Escape a field name that is a Python keyword with one trailing underscore (`pass_`); any other trailing underscore is part of the name.
- Enum members are the one exception to mirroring BDS (`enums.md`).

## Where a name comes from

- A name taken from EndstoneMC/bedrock-headers at the era's branch needs no TODO; cite that branch in the commit.
- On forward work, name anything the newest header branch declares as that branch does; it lists every enumerator, bound or not. Name anything newer by heuristic.
- Take a packet's name from its class header, not the id-enum symbol, which can be a stale alias; a deprecated suffix still names the same packet.
- Never take a name or a type from Sandertv/gophertunnel or CloudburstMC/Protocol.

## Keeping names

- Keep the existing declaration's names, field order and type vocabulary unless evidence names a change.
- Keep the DSL's name when the dump labels a field differently; dump labels are cereal display strings and they drift.
- Turn a genuinely new label into snake_case that follows the module's existing vocabulary rather than an awkward label's literal words (`"Bypass Listener Range Check"` becomes `bypass_listener_range_check`).
- Never rename an existing field as a side effect of a version bump; a real BDS rename needs its own evidence.

## References

- Take bytes, order and version from a community codec, and land them inside the type boundaries and names that the existing declaration and the era's header give.
- Never add or remove a type because a reference has or lacks one.
- Normalise every reference's packet names to BDS spelling (case, Entity to Actor, Armour to Armor) before comparing lists.
