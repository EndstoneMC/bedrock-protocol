from protocol._dsl import packet
from protocol.common import varint32

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
    """Sent by the client each time it edits a book in its inventory.

    `operation` is a tagged union: a varint discriminator picks the action,
    then that action's payload follows.
    """

    book_slot: varint32
    operation: (
        BookEditActionReplacePage
        | BookEditActionAddPage
        | BookEditActionDeletePage
        | BookEditActionSwapPages
        | BookEditActionFinalize
    )
