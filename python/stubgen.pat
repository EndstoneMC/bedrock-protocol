^bedrock_protocol\.ProtocolVersion\.SUPPORTED_VERSIONS$:
    \import typing
    SUPPORTED_VERSIONS: typing.ClassVar[tuple[ProtocolVersion, ...]]

^bedrock_protocol\.ProtocolVersion\.(MINIMUM|MAXIMUM)_VERSION$:
    \import typing
    \1_VERSION: typing.ClassVar[ProtocolVersion]

^bedrock_protocol\.v\d+\.packets$:
    \import types
    packets: types.MappingProxyType[int, type]

^bedrock_protocol\._core\.encodings$:
    \import types
    encodings: types.MappingProxyType[int, types.MappingProxyType[type, int]]

^bedrock_protocol\._core\.modes$:
    \import types
    modes: types.MappingProxyType[int, types.MappingProxyType[type, types.MappingProxyType[SerializationMode, int]]]

^bedrock_protocol\.DecodeError\.__suffix__$:
    reason: str
    path: tuple[str | int, ...]
    offset: int

^bedrock_protocol\.EncodeError\.__suffix__$:
    reason: str
    path: tuple[str | int, ...]
