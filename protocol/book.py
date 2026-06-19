from protocol import packet, type, uint8, varint32

package = "bedrock.protocol"


class BookEditAction:
    @type(until=924)
    class ReplacePage:
        page_index: uint8
        page_text: str
        photo_name: str

    @type(since=924)
    class ReplacePage:
        page_index: varint32
        page_text: str
        photo_name: str

    @type(until=924)
    class AddPage:
        page_index: uint8
        page_text: str
        photo_name: str

    @type(since=924)
    class AddPage:
        page_index: varint32
        page_text: str
        photo_name: str

    @type(until=924)
    class DeletePage:
        page_index: uint8

    @type(since=924)
    class DeletePage:
        page_index: varint32

    @type(until=924)
    class SwapPages:
        page_index: uint8
        swap_with_index: uint8

    @type(since=924)
    class SwapPages:
        page_index: varint32
        swap_with_index: varint32

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
class BookEditPacket:
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
