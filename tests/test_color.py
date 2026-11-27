import pytest

import bedrock_protocol as bp
from bedrock_protocol import _core, v649, v729


@pytest.mark.parametrize(
    ("data", "color"),
    [
        pytest.param(
            bytes.fromhex("10706572736f6e615f736b656c65746f6e0100000009233130323033303430"),
            bp.Color(r=32 / 255, g=48 / 255, b=64 / 255, a=16 / 255),
            id="argb-hex",
        ),
        pytest.param(
            bytes.fromhex("10706572736f6e615f736b656c65746f6e0100000009783130323033303430"),
            bp.Color(r=32 / 255, g=48 / 255, b=64 / 255, a=16 / 255),
            id="any-first-character",
        ),
        pytest.param(
            bytes.fromhex("10706572736f6e615f736b656c65746f6e0100000000"),
            bp.Color(),
            id="empty",
        ),
        pytest.param(
            bytes.fromhex("10706572736f6e615f736b656c65746f6e0100000003237a7a"),
            bp.Color(),
            id="no-hex-digit",
        ),
        pytest.param(
            bytes.fromhex("10706572736f6e615f736b656c65746f6e010000000a23316666666666666666"),
            bp.Color(r=1, g=1, b=1, a=1),
            id="beyond-32-bits-saturates",
        ),
        pytest.param(
            bytes.fromhex("10706572736f6e615f736b656c65746f6e01000000112366666666666666663030303030303031"),
            bp.Color(b=1 / 255),
            id="from-ffffffff00000000-keeps-the-low-32-bits",
        ),
    ],
)
def test_a_color_text_reads_as_mce_color_from_hex_string_reads_it(data, color):
    assert _core.decode(v729.VERSION, v649.TintMapColor, data).colors == [color]


def test_a_color_text_is_written_without_padding():
    value = v649.TintMapColor(
        piece_type=bp.PieceType.SKELETON, colors=[bp.Color(r=2 / 255, g=3 / 255, b=4 / 255, a=1 / 255)]
    )
    assert _core.encode(v729.VERSION, value) == bytes.fromhex(
        "10706572736f6e615f736b656c65746f6e01000000082331303230333034"
    )


@pytest.mark.parametrize("channel", [pytest.param(1.5, id="above-one"), pytest.param(-0.5, id="below-zero")])
def test_encode_rejects_a_color_channel_outside_zero_to_one(channel):
    value = v649.TintMapColor(piece_type=bp.PieceType.SKELETON, colors=[bp.Color(g=channel)])
    with pytest.raises(bp.EncodeError, match=r"^TintMapColor\.colors\[0\]: out of range$"):
        _core.encode(v729.VERSION, value)
