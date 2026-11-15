^bedrock_protocol(?:\._core)?\.versions$:
    versions: tuple[int, ...]

^bedrock_protocol(?:\._core)?\.releases$:
    releases: tuple[ProtocolVersion, ...]

^bedrock_protocol\.v\d+\.packets$:
    \import types
    packets: types.MappingProxyType[int, type]

^bedrock_protocol\.v\d+\.encodings$:
    \import types
    encodings: types.MappingProxyType[type, int]

^bedrock_protocol\.v\d+\.modes$:
    \import types
    \import bedrock_protocol
    modes: types.MappingProxyType[type, types.MappingProxyType[bedrock_protocol.SerializationMode, int]]

^bedrock_protocol\.DecodeError\.__suffix__$:
    reason: str
    path: tuple[str | int, ...]
    offset: int

^bedrock_protocol\.EncodeError\.__suffix__$:
    reason: str
    path: tuple[str | int, ...]
