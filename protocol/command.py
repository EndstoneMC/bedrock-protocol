from protocol import packet

package = "bedrock.protocol"


@packet(id=140, since=2168)
class SettingsCommandPacket:
    command_string: str
    suppress_output: bool
