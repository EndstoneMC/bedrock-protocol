from protocol import packet, uvarint32

package = "bedrock.protocol"


@packet(id=100, since=2168)
class ModalFormRequestPacket:
    form_id: uvarint32
    form_json: str


@packet(id=102, since=2168)
class ServerSettingsRequestPacket:
    pass


@packet(id=103, since=2168)
class ServerSettingsResponsePacket:
    """The server's answer to a settings request: the JSON describing a settings tab
    to draw for this server, and the form id the client echoes back when the player
    submits it."""

    form_id: uvarint32
    form_json: str
