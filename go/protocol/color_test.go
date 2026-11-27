package protocol

import (
	"math"
	"testing"

	"github.com/EndstoneMC/bedrock-protocol/go/internal/check"
)

type packedColor struct {
	value uint32
	held  bool
}

func TestColorPacksEachChannelIntoATruncatedByteTheFirstHighest(t *testing.T) {
	value, held := packColor(1, 0.5, 0.25, 0)
	check.Equal(t, packedColor{value, held}, packedColor{0xff7f3f00, true})
}

func TestColorChannelOutsideZeroToOneIsRejected(t *testing.T) {
	cases := []struct {
		name     string
		channels [4]float32
	}{
		{"first below zero", [4]float32{-0.01, 0, 0, 0}},
		{"second above one", [4]float32{0, 1.01, 0, 0}},
		{"third not a number", [4]float32{0, 0, float32(math.NaN()), 0}},
		{"fourth infinite", [4]float32{0, 0, 0, float32(math.Inf(1))}},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			value, held := packColor(c.channels[0], c.channels[1], c.channels[2], c.channels[3])
			check.Equal(t, packedColor{value, held}, packedColor{0, false})
		})
	}
}

func TestColorUnpacksEachByteOverTwoHundredFiftyFiveTheFirstHighest(t *testing.T) {
	a, r, g, b := unpackColor(0xff7f3f01)
	check.Equal(t, [4]float32{a, r, g, b}, [4]float32{1, 0.49803922, 0.24705882, 0.003921569})
}

func TestColorFormatsAsUnpaddedLowerCaseHexAfterAHash(t *testing.T) {
	check.Equal(t, formatColor(0x0abcdef0), "#abcdef0")
}

func TestColorTextReadsPastItsFirstByteAsStrtoullInBase16(t *testing.T) {
	cases := []struct {
		name string
		text string
		want uint32
	}{
		{"hex digits", "#ff00ff00", 0xff00ff00},
		{"upper-case digits", "#ABCDEF", 0xabcdef},
		{"any first byte", "zff", 0xff},
		{"leading C whitespace", "# \t\n\v\f\rff", 0xff},
		{"plus sign", "#+ff", 0xff},
		{"minus sign negating modulo 2^64", "#-ff", 0xffffff01},
		{"whitespace after the sign", "#- ff", 0},
		{"lower-case 0x", "#0xff", 0xff},
		{"upper-case 0X", "#0Xff", 0xff},
		{"whitespace and sign before 0x", "# +0xff", 0xff},
		{"0x before no hex digit", "#0xg", 0},
		{"0x alone", "#0x", 0},
		{"0x taken once", "#0x0xff", 0},
		{"digits up to the first other byte", "#ffz1", 0xff},
		{"no digits", "#z", 0},
		{"the first byte alone", "#", 0},
		{"overflow past 64 bits", "#10000000000000000", 0xffffffff},
		{"overflow not negated", "#-10000000000000000", 0xffffffff},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			check.Equal(t, parseColor(c.text), c.want)
		})
	}
}

func TestColorTextPastThirtyTwoBitsClampsBelowItsTopHalf(t *testing.T) {
	cases := []struct {
		name string
		text string
		want uint32
	}{
		{"the largest 32-bit value", "#ffffffff", 0xffffffff},
		{"one past 32 bits", "#100000000", 0xffffffff},
		{"the last below the top half", "#fffffffeffffffff", 0xffffffff},
		{"the first in the top half", "#ffffffff00000000", 0},
		{"within the top half", "#ffffffff12345678", 0x12345678},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			check.Equal(t, parseColor(c.text), c.want)
		})
	}
}

func TestEmptyColorTextIsZero(t *testing.T) {
	check.Equal(t, parseColor(""), 0)
}
