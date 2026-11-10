---
paths:
  - "protocol/**"
---

# Gating

## Redeclare or gate
- Redeclare the whole class at the change point for a reshape: a cerealisation, or any change to a field's type, including a union gaining a case, a field turning optional, and a rename.
- `field(since=)` and `field(until=)` gate only a field's presence.
- Ask whether any field's type moved; if one did, redeclare, even when the packet was already cerealised.
- Express a reorder, a rename or a retyped field only by redeclaration.
- Never use `field(type=X, until=N)`, which removes the field at N; never declare one field twice over disjoint gates.
- Tile redeclarations over one range: the same id, each `until=` meeting the next `since=`, and only the last open.
- Model both sides of a cerealisation, gated at the boundary: the switch arms before it, a flat redeclaration after it.
- Never assume the pre-cereal form used the same construct as the cerealised one.
- Read a delete plus an add at the same position with the same type as a rename; redeclare, and check whether its meaning changed.
- A union gaining or losing a case is a wire change, and an insertion renumbers every case after it.
- When BDS drops an always-true marker, gate that one `Literal[True]` field `until=<version>` and move nothing else.
- Gate a whole type with `@type(since=, until=)`; outside that range the type does not exist.

## What the evidence separates
- Gate only the fields and types that the evidence separates.
- Check that two eras really encode differently before splitting anything.
- Before calling a field wrong because the target era lacks it, check whether it is right at the other era; if it is, that is two models, not a fix.
- Gate a type that BDS version-stamped, never one that only became reachable.
- Gate a retro-fix at the older era it corrects.

## Packets and ids
- Gate a packet from the version that introduced it; an ungated `@packet` claims protocol 0.
- Gate a packet's body and its `MinecraftPacketIds` member at the same version, in the same commit.
- An id that moved is a break for the packet that took it, never a rename.
- An id that changed owner is two classes tiling one id.
- A delta lands as a packet redeclaration, a gate on a closure type, or an inline field gate; check all three before calling a packet unhandled.
- Never audit coverage by grepping `@packet` lines.
- "Modelled" is not "supported at this version"; the gate is the claim.

## Lowering a gate
- Never lower a gate past what the evidence covers; below a cerealisation, lowering it becomes real modelling.
- Treat gates on the schema's bootstrap floor as unverified; sweep them by diffing each packet's dump between the target and the floor branch.
- Confirm each sweep candidate with a closure diff, because a packet's own JSON does not clear its closure.
- For a packet cerealised at or below the target whose dump JSON is identical at both eras, lower the gate and stop.
- Before gating an enum member, find every test and consumer that names it.
