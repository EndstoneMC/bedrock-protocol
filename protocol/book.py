from protocol import field, packet, uint8, uvarint32, varint32

package = "bedrock.protocol"


class BookEditAction:
    class ReplacePage:
        page_index: varint32 = field(type=uint8, until=924)
        page_index: varint32 = field(since=924)
        page_text: str
        photo_name: str

    class AddPage:
        page_index: varint32 = field(type=uint8, until=924)
        page_index: varint32 = field(since=924)
        page_text: str
        photo_name: str

    class DeletePage:
        page_index: varint32 = field(type=uint8, until=924)
        page_index: varint32 = field(since=924)

    class SwapPages:
        page_index: varint32 = field(type=uint8, until=924)
        page_index: varint32 = field(since=924)
        swap_with_index: varint32 = field(type=uint8, until=924)
        swap_with_index: varint32 = field(since=924)

    class Finalize:
        title: str
        author: str
        xuid: str


@packet(id=97)
class BookEditPacket:
    """Sends the updated state of the Book and Quill item from client to server
    during use."""

    book_slot: varint32 = field(type=uint8, until=924)
    book_slot: varint32 = field(since=924)
    operation: (
        BookEditAction.ReplacePage
        | BookEditAction.AddPage
        | BookEditAction.DeletePage
        | BookEditAction.SwapPages
        | BookEditAction.Finalize
    ) = field(tag=uint8, until=924)
    operation: (
        BookEditAction.ReplacePage
        | BookEditAction.AddPage
        | BookEditAction.DeletePage
        | BookEditAction.SwapPages
        | BookEditAction.Finalize
    ) = field(tag=uvarint32, since=924)
