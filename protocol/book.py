from protocol import packet, varint32

package = "bedrock.protocol"


class BookEditActionReplacePage:
    page_index: varint32
    page_text: str
    photo_name: str


class BookEditActionAddPage:
    page_index: varint32
    page_text: str
    photo_name: str


class BookEditActionDeletePage:
    page_index: varint32


class BookEditActionSwapPages:
    page_index: varint32
    swap_with_index: varint32


class BookEditActionFinalize:
    title: str
    author: str
    xuid: str


@packet(id=97, since=924)
class BookEditPacket:
    """Sends the updated state of the Book and Quill item from client to server
    during use."""

    book_slot: varint32
    operation: (
        BookEditActionReplacePage
        | BookEditActionAddPage
        | BookEditActionDeletePage
        | BookEditActionSwapPages
        | BookEditActionFinalize
    )
