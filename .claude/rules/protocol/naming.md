---
paths:
  - "protocol/**"
---

# Names

## Names mirror BDS

- Match BDS class names and nesting exactly; never fold an enclosing namespace into a class name (`Bedrock::Profile::Whisker::Diagnostics::ScopeDataSummary` is `ScopeDataSummary`).
- Keep a BDS `Outer::Inner` nested; never flatten it to `OuterInner`.
- Map `FooPacketPayload` onto `@packet FooPacket` and move its nested types into the packet; no `...PacketPayload` class exists in the schema.
- Type actor ids as `ActorUniqueID` or `ActorRuntimeID` even where BDS declares a plain integer, and pick which from where BDS fills the member.
- Keep the wire encoding with `field(type=)` (`target_player_id: ActorUniqueID = field(type=int64)`).
- Escape a field name that is a Python keyword with one trailing underscore (`pass_`); any other trailing underscore is part of the name.
- Enum members are the one exception to mirroring BDS (`enums.md`).

## Where a name comes from

- A name taken from EndstoneMC/bedrock-headers is authoritative and needs no TODO.
- Name a back-port from the era's header branch and cite that branch in the commit; name anything newer than the newest header branch by heuristic.
- On forward work, settle anything that already existed at the newest header branch on that branch; it lists every enumerator, bound or not.
- Take a packet's name from its class header, not the id-enum symbol, which can be a stale alias; a deprecated suffix still names the same packet.
- Never take a name or a type from Sandertv/gophertunnel or CloudburstMC/Protocol.

## Keeping names

- Keep the existing declaration's names, field order and type vocabulary unless evidence names a change.
- Keep the DSL's name when the dump labels a field differently; dump labels are cereal display strings and they drift.
- Turn a genuinely new label into snake_case that reads like its neighbours (`"Bypass Listener Range Check"` becomes `bypass_listener_range_check`).
- Follow the module's existing vocabulary rather than transcribing an awkward label literally.
- Never rename an existing field as a side effect of a version bump; a real BDS rename is a redeclaration on its own evidence.

## References

- Take bytes, order and version from a community codec, never its way of splitting a packet into types.
- Land a reference's finding inside the type boundaries and names that the existing declaration and the era's header give.
- Never add or remove a type because a reference has or lacks one.
- Normalise every reference's packet names to BDS spelling (case, Entity to Actor, Armour to Armor) before comparing lists.
