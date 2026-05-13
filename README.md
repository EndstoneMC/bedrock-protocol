# bedrock-protocol

A protoc-style packet codegen for Minecraft Bedrock-flavoured wire packets,
where the *schema language* is Python (read statically, à la conanfile) and
templates are Jinja2. CMake integration mirrors `protobuf_generate`.

Consume it as a library — `add_subdirectory()` this project, link
`bedrock::protocol`, and the packets defined under `protocol/` are
auto-generated at configure time and bundled into the library.

## Layout

| Path                              | What it is                                          |
| --------------------------------- | --------------------------------------------------- |
| `bpc/`                            | The codegen (Bedrock-Protocol Compiler) — see `bpc/README.md` |
| `cmake/BedrockProtocol.cmake`     | `bedrock_protocol_generate()` CMake function        |
| `include/bedrock/`                | C++ runtime (`protocol.hpp`, `stream.hpp`)          |
| `protocol/`                       | Packet definitions in the Python DSL                |

## DSL

A packet file is plain Python — read by the parser as syntax, never executed,
so forward references to C++ types just work:

```python
from typing import ClassVar

class DisconnectPacket:
    id: ClassVar[int] = 5
    reason: DisconnectFailReason
    messages: DisconnectPacketMessages | None
```

Interpretation:

* Class with `id: ClassVar[int] = N` ⇒ a packet. `ClassVar` marks `id` as
  packet metadata, not a wire field.
* `field: <primitive>` (e.g. `uvarint32`, `string`, `u32`) ⇒ primitive field.
* `field: SomeName` (bare named type) ⇒ enum-typed field, discriminator
  `uvarint32` by default.
* `field: A | B | None` ⇒ tagged-union / switch field. Each case is a struct
  payload (or `None` for the empty case, `std::monostate`).

## Build

```sh
pip install -r bpc/requirements.txt
cmake -S . -B build
cmake --build build
```

The build produces `libbedrock_protocol.a` with all packets in `protocol/`
auto-generated and compiled in.

## Consuming from another project

```cmake
add_subdirectory(third_party/bedrock-protocol)

add_executable(my_app main.cpp)
target_link_libraries(my_app PRIVATE bedrock::protocol)
```

Then in your code:

```cpp
#include "DisconnectPacket.h"
#include <bedrock/protocol.hpp>

namespace bp = bedrock::protocol;

auto pkt = DisconnectPacket{};
auto out = bp::BinaryStream{};
pkt.Write(out);
```

### Adding your own packets in a downstream target

If you want to compile additional packets defined outside this repo into
your own target, also include the CMake module:

```cmake
list(APPEND CMAKE_MODULE_PATH
     ${CMAKE_CURRENT_SOURCE_DIR}/third_party/bedrock-protocol/cmake)
include(BedrockProtocol)
add_subdirectory(third_party/bedrock-protocol)

add_executable(my_app main.cpp)
target_link_libraries(my_app PRIVATE bedrock::protocol)

bedrock_protocol_generate(
    TARGET  my_app
    PACKETS my_packets/custom_packet.py)
```
