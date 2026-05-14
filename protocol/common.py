from typing import Annotated

package = "bedrock.protocol"

type varint32 = Annotated[int, "std::int32_t"]
type varint64 = Annotated[int, "std::int64_t"]
type uvarint32 = Annotated[int, "std::uint32_t"]
type uvarint64 = Annotated[int, "std::uint64_t"]
type int8 = Annotated[int, "std::int8_t"]
type int16 = Annotated[int, "std::int16_t"]
type int32 = Annotated[int, "std::int32_t"]
type int64 = Annotated[int, "std::int64_t"]
type uint8 = Annotated[int, "std::uint8_t"]
type uint16 = Annotated[int, "std::uint16_t"]
type uint32 = Annotated[int, "std::uint32_t"]
type uint64 = Annotated[int, "std::uint64_t"]
type double = Annotated[float, "double"]


class Vec3:
    x: float
    y: float
    z: float
