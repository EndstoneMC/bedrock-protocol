---
paths:
  - "protocol/**"
---

# Gating

## Redeclare or gate

- Redeclare the whole class at the change point for a reshape: a cerealisation, a reorder, a rename, even in a packet already cerealised.
- `field(since=)` and `field(until=)` gate only a field's presence, and so does the same pair on a `with field(...)` block.
- Never switch a field's type with `field(type=X, until=N)`, which removes the field at N.
- Tile redeclarations over one range: the same id, each `until=` meeting the next `since=`, and only the last open.
- Model both sides of a cerealisation, gated at the boundary: the switch arms before it, a flat redeclaration after it.
- Never assume the pre-cereal form used the same construct as the cerealised one: a cerealised optional or variant can be a plain `bool` and a value before it.
- Read a delete plus an add at the same position with the same type as a rename, and check whether its meaning changed.
- Inserting a union case renumbers every case after it.
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
- For a packet BDS writes through cereal at or below the target whose dump closure is identical at both eras, lower the gate and stop.
- Before gating an enum member, find every test and consumer that names it.
