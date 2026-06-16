# PlayerVideoCapturePacket (id 324, since 786)

Used by a test command to start/stop video capture.

## Wire shape

BDS models the payload as `std::variant<StartVideoCapture, StopVideoCapture>`.
The byte on the wire is the variant index (0 = start, 1 = stop), followed by
the active case's body. We follow BDS ordering. CloudburstMC uses the inverse
mapping (STOP = 0, START = 1).

DSL:

```python
class StartVideoCapture:
    frame_rate: uint32
    file_prefix: str


class StopVideoCapture:
    pass


@packet(id=324, since=786)
class PlayerVideoCapturePacket:
    """Used by a test command to start/stop video capture."""

    params: StartVideoCapture | StopVideoCapture = field(tag=uint8)
```

- The two cases are standalone structs combined into a `tag=`-discriminated
  union, mirroring the idiom in `protocol/book.py` and `protocol/attributes.py`.
- `StartVideoCapture` carries `frame_rate` (uint32) and `file_prefix` (str);
  `StopVideoCapture` is empty. The variant index gates the whole payload, so
  the start-only fields need no per-field `when=`.

## Open question: variant-tag wire width

Sources disagree on the discriminator width, so the tag is drafted as `uint8`:

| Source                     | Tag width   |
| -------------------------- | ----------- |
| gophertunnel               | 1-byte      |
| CloudburstMC               | 1-byte      |
| protocol-docs JSON         | `uvarint32` |
| bedrock-protocol-docs HTML | `uint32`    |

BDS has a `std::variant` whose cereal serialization is not visible from the
header. `uint8` matches both other reference libraries (gophertunnel,
CloudburstMC). Revisit if BDS disassembly clarifies the width.
