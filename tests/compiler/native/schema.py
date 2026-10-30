from protocol import field, packet, uint8

package = "bedrock.protocol"


class Child:
    value: uint8


type Children = list[Child]
type ChildMap = dict[str, Child]


@packet(id=1)
class Aliases:
    children: Children
    by_name: ChildMap


@packet(id=2)
class Counted:
    enabled: bool
    selected: bool
    count: uint8
    with field(when=lambda p: p.enabled and p.selected):
        values: list[uint8] | None = field(count=lambda p: p.count)


@packet(id=3)
class NarrowMap:
    values: dict[str, uint8] = field(prefix=uint8)


@packet(id=4)
class WideMap:
    values: dict[str, uint8]
