import pytest

import bedrock_protocol
from bedrock_protocol import v2168

VIDEO_CAPTURE = v2168.PlayerVideoCapturePacket


@pytest.mark.parametrize(
    ("encoded", "last"),
    [
        pytest.param("003c00000004636c697001", VIDEO_CAPTURE.StopVideoCapture(), id="start_then_stop"),
        pytest.param(
            "01001e000000026162",
            VIDEO_CAPTURE.StartVideoCapture(frame_rate=30, file_prefix="ab"),
            id="stop_then_start",
        ),
    ],
)
def test_copies_that_differ_decode_to_the_last_copy(encoded, last):
    assert v2168.decode(VIDEO_CAPTURE, bytes.fromhex(encoded)).params == last


def test_a_bad_later_copy_fails_the_decode():
    with pytest.raises(
        bedrock_protocol.DecodeError, match=r"^PlayerVideoCapturePacket\.params: unknown value at byte 11 of 11$"
    ):
        v2168.decode(VIDEO_CAPTURE, bytes.fromhex("003c00000004636c697002"))
