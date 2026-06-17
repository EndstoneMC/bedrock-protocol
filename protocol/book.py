from protocol import field, packet, uint8, varint32

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


@packet(id=97, until=924)
class BookEditPacket:
    """Sends the updated state of the Book and Quill item from client to server
    during use."""

    book_slot: uint8
    operation: (
        BookEditAction.ReplacePage
        | BookEditAction.AddPage
        | BookEditAction.DeletePage
        | BookEditAction.SwapPages
        | BookEditAction.Finalize
    )


@packet(id=97, since=924)
class BookEditPacket:  # noqa: F811
    """Sends the updated state of the Book and Quill item from client to server
    during use."""

    book_slot: varint32
    operation: (
        BookEditAction.ReplacePage
        | BookEditAction.AddPage
        | BookEditAction.DeletePage
        | BookEditAction.SwapPages
        | BookEditAction.Finalize
    )
