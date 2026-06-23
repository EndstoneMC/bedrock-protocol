"""DDUI (Data Driven UI) types -- compiler built-ins.

`DynamicValue` (Bedrock::DDUI's cereal::DynamicValue) is the recursive,
self-describing value the data-store packets carry. It is hand-written in
include/bedrock/ddui.hpp -- a tagged union whose Array and Object arms recurse
into the value itself, which the DSL cannot spell. The class below carries
`@builtin`, so the compiler references it by name and routes it through
`Serializer<DynamicValue>` without emitting a definition of its own.
"""

from protocol import builtin

package = "bedrock.protocol"


@builtin
class DynamicValue:
    """A recursive DDUI data-store value: null, boolean, integer, number,
    string, array, or object (a string-keyed map of values)."""
