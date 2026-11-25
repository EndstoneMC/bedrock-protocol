package protocol

import (
	"testing"

	"github.com/EndstoneMC/bedrock-protocol/go/internal/check"
	"github.com/EndstoneMC/bedrock-protocol/go/stream"
)

type failure struct {
	reason error
	offset int
}

func bitsetOf(set ...int) Bitset {
	var out Bitset
	for _, bit := range set {
		out.Set(bit)
	}
	return out
}

func TestBitsetReadsSevenBitGroups(t *testing.T) {
	cases := []struct {
		name  string
		data  string
		width int
		want  Bitset
	}{
		{"empty", "00", 30, Bitset{}},
		{"bit zero", "01", 30, bitsetOf(0)},
		{"bit seven in the second group", "8001", 30, bitsetOf(7)},
		{"bits in two groups", "8101", 30, bitsetOf(0, 7)},
		{"last bit of the width", "808080808001", 36, bitsetOf(35)},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			check.Equal(t, readBitset(stream.NewReader(check.Hex(t, c.data)), c.width), c.want)
		})
	}
}

func TestMalformedBitsetIsRejected(t *testing.T) {
	cases := []struct {
		name  string
		data  string
		width int
		want  failure
	}{
		{"bit at the width", "08", 3, failure{stream.ErrOutOfRange, 1}},
		{"continuation into a group at the width", "8000", 7, failure{stream.ErrOutOfRange, 1}},
		{"groups that run out", "80", 30, failure{stream.ErrTruncated, 1}},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			r := stream.NewReader(check.Hex(t, c.data))
			readBitset(r, c.width)
			reason, _, offset := r.Failure()
			check.Equal(t, failure{reason, offset}, c.want)
		})
	}
}

func TestBitsetWritesGroupsUpToTheHighestBit(t *testing.T) {
	var w stream.Writer
	writeBitset(&w, bitsetOf(0, 7), 30)
	check.Equal(t, w.Bytes(), check.Hex(t, "8101"))
}

func TestEmptyBitsetWritesOneGroup(t *testing.T) {
	var w stream.Writer
	writeBitset(&w, Bitset{}, 30)
	check.Equal(t, w.Bytes(), check.Hex(t, "00"))
}

func TestBitsetPastItsWidthIsOutOfRangeOnEncode(t *testing.T) {
	var w stream.Writer
	writeBitset(&w, bitsetOf(5), 5)
	reason, _ := w.Failure()
	check.Equal(t, reason, stream.ErrOutOfRange)
}

func TestBitsetTestsASetBit(t *testing.T) {
	check.Equal(t, bitsetOf(70).Test(70), true)
}

func TestBitsetTestsAnUnsetBit(t *testing.T) {
	check.Equal(t, bitsetOf(70).Test(6), false)
}

func TestBitsetLenIsOnePastTheHighestBit(t *testing.T) {
	check.Equal(t, bitsetOf(3, 70).Len(), 71)
}

func TestClearingEveryBitGivesTheZeroBitset(t *testing.T) {
	set := bitsetOf(3, 70)
	set.Clear(70)
	set.Clear(3)
	check.Equal(t, set, Bitset{})
}

func TestBitsetCopyKeepsItsBitsWhenTheOriginalChanges(t *testing.T) {
	original := bitsetOf(3)
	copied := original
	original.Set(4)
	check.Equal(t, copied, bitsetOf(3))
}
