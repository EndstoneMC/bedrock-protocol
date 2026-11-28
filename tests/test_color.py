import pytest

import bedrock_protocol as bp
from bedrock_protocol import _core, v594, v729

SKELETON = bytes.fromhex("10706572736f6e615f736b656c65746f6e01000000")


@pytest.mark.parametrize(
    ("text", "color"),
    [
        pytest.param(b"#10203040", bp.Color(r=32 / 255, g=48 / 255, b=64 / 255, a=16 / 255), id="argb-hex"),
        pytest.param(b"x10203040", bp.Color(r=32 / 255, g=48 / 255, b=64 / 255, a=16 / 255), id="any-first-character"),
        pytest.param(b"", bp.Color(), id="empty"),
        pytest.param(b"#zz", bp.Color(), id="no-hex-digit"),
        pytest.param(b"# \t\n\v\f\rff", bp.Color(b=1), id="leading-c-whitespace"),
        pytest.param(b"#+ff", bp.Color(b=1), id="plus-sign"),
        pytest.param(b"#-ff", bp.Color(r=1, g=1, b=1 / 255, a=1), id="minus-sign-negates-modulo-2-to-the-64"),
        pytest.param(b"#- ff", bp.Color(), id="whitespace-after-the-sign"),
        pytest.param(b"#0xff", bp.Color(b=1), id="0x-prefix"),
        pytest.param(b"#0xg", bp.Color(), id="0x-without-a-hex-digit"),
        pytest.param(b"#100000000", bp.Color(r=1, g=1, b=1, a=1), id="beyond-32-bits-saturates"),
        pytest.param(b"#ffffffff00000001", bp.Color(b=1 / 255), id="from-ffffffff00000000-keeps-the-low-32-bits"),
        pytest.param(b"#-100000000", bp.Color(), id="negated-to-ffffffff00000000"),
        pytest.param(b"#10000000000000000", bp.Color(r=1, g=1, b=1, a=1), id="past-64-bits"),
        pytest.param(b"#-10000000000000000", bp.Color(r=1, g=1, b=1, a=1), id="past-64-bits-unnegated"),
    ],
)
def test_a_color_text_reads_as_mce_color_from_hex_string_reads_it(text, color):
    assert _core.decode(v729.VERSION, v594.TintMapColor, SKELETON + bytes([len(text)]) + text).colors == [color]


def test_a_color_text_is_written_without_padding():
    value = v594.TintMapColor(
        piece_type=bp.PieceType.SKELETON, colors=[bp.Color(r=2 / 255, g=3 / 255, b=4 / 255, a=1 / 255)]
    )
    assert _core.encode(v729.VERSION, value) == SKELETON + b"\x08#1020304"


@pytest.mark.parametrize(
    "channel",
    [
        pytest.param(1.5, id="above-one"),
        pytest.param(-0.5, id="below-zero"),
        pytest.param(float("nan"), id="not-a-number"),
        pytest.param(float("inf"), id="infinite"),
    ],
)
def test_encode_rejects_a_color_channel_outside_zero_to_one(channel):
    value = v594.TintMapColor(piece_type=bp.PieceType.SKELETON, colors=[bp.Color(g=channel)])
    with pytest.raises(bp.EncodeError, match=r"^TintMapColor\.colors\[0\]: out of range$"):
        _core.encode(v729.VERSION, value)
