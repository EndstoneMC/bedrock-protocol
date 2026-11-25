package nbt

import (
	"strings"
	"testing"

	"github.com/EndstoneMC/bedrock-protocol/go/internal/check"
	"github.com/EndstoneMC/bedrock-protocol/go/stream"
)

type failure struct {
	reason error
	offset int
}

func readFailure(r *stream.Reader) failure {
	reason, _, offset := r.Failure()
	return failure{reason, offset}
}

var payloads = []struct {
	name string
	tag  Tag
	data string
}{
	{"byte", ByteTag(5), "05"},
	{"byte past int8", ByteTag(254), "fe"},
	{"short", ShortTag(-2), "feff"},
	{"int as a zigzag varint", IntTag(-1), "01"},
	{"int of two groups", IntTag(300), "d804"},
	{"int64 as a zigzag varint", Int64Tag(-2), "03"},
	{"float", FloatTag(1), "0000803f"},
	{"double", DoubleTag(1), "000000000000f03f"},
	{"string", StringTag("hi"), "026869"},
	{"byte array", ByteArrayTag{1, 2}, "040102"},
	{"byte array past int8", ByteArrayTag{254, 255}, "04feff"},
	{"int array", IntArrayTag{1, -1}, "040201"},
	{"list", ListTag{ElementType: TypeInt, Elements: []Tag{IntTag(1)}}, "030202"},
	{"empty list", ListTag{}, "0000"},
	{"compound", CompoundTag{"b": ByteTag(1), "a": IntTag(1)}, "030161020101620100"},
}

func TestPayloadWritesTheNetworkForm(t *testing.T) {
	for _, c := range payloads {
		t.Run(c.name, func(t *testing.T) {
			var w stream.Writer
			writePayload(&w, c.tag)
			check.Equal(t, w.Bytes(), check.Hex(t, c.data))
		})
	}
}

func TestPayloadReadsTheNetworkForm(t *testing.T) {
	for _, c := range payloads {
		t.Run(c.name, func(t *testing.T) {
			check.Equal(t, readPayload(stream.NewReader(check.Hex(t, c.data)), c.tag.Type(), 0), c.tag)
		})
	}
}

func TestRootWritesTheTypeAnEmptyNameAndThePayload(t *testing.T) {
	var w stream.Writer
	WriteCompoundTag(&w, CompoundTag{"a": IntTag(1)})
	check.Equal(t, w.Bytes(), check.Hex(t, "0a000301610200"))
}

func TestRootReadDropsTheName(t *testing.T) {
	check.Equal(t, ReadCompoundTag(stream.NewReader(check.Hex(t, "0a036162630301610200"))), CompoundTag{"a": IntTag(1)})
}

func TestEmptyRootReadsAsNil(t *testing.T) {
	check.Equal(t, ReadCompoundTag(stream.NewReader(check.Hex(t, "0a0000"))), CompoundTag(nil))
}

func TestCompoundTagDataWritesThePayloadWithoutARoot(t *testing.T) {
	var w stream.Writer
	WriteCompoundTagData(&w, CompoundTagData{"a": IntTag(1)})
	check.Equal(t, w.Bytes(), check.Hex(t, "0301610200"))
}

func TestCompoundTagDataReadsThePayloadWithoutARoot(t *testing.T) {
	check.Equal(t, ReadCompoundTagData(stream.NewReader(check.Hex(t, "0301610200"))), CompoundTagData{"a": IntTag(1)})
}

func TestCompoundKeysAreWrittenInByteOrder(t *testing.T) {
	var w stream.Writer
	writePayload(&w, CompoundTag{"\U00010000": ByteTag(0), "￿": ByteTag(0)})
	check.Equal(t, w.Bytes(), check.Hex(t, "0103efbfbf000104f09080800000"))
}

func TestDuplicateKeyKeepsTheFirstValue(t *testing.T) {
	check.Equal(t, ReadCompoundTag(stream.NewReader(check.Hex(t, "0a00010161010101610200"))), CompoundTag{"a": ByteTag(1)})
}

func TestEmptyListKeepsItsElementType(t *testing.T) {
	var w stream.Writer
	writePayload(&w, ListTag{ElementType: TypeInt})
	check.Equal(t, w.Bytes(), check.Hex(t, "0300"))
}

func TestListWithoutAnElementTypeTakesItsFirstElements(t *testing.T) {
	var w stream.Writer
	writePayload(&w, ListTag{Elements: []Tag{IntTag(1)}})
	check.Equal(t, w.Bytes(), check.Hex(t, "030202"))
}

func TestMalformedRootIsRejected(t *testing.T) {
	cases := []struct {
		name string
		data string
		want failure
	}{
		{"unknown tag id in a compound", "0a000c", failure{stream.ErrUnknownValue, 3}},
		{"root that is not a compound", "010005", failure{stream.ErrUnknownValue, 3}},
		{"end root", "00", failure{stream.ErrUnknownValue, 1}},
		{"unknown root id before its name", "0c00", failure{stream.ErrUnknownValue, 1}},
		{"negative byte array length", "0a000701610100", failure{stream.ErrOutOfRange, 6}},
		{"byte array length past the body", "0a000701610a", failure{stream.ErrTruncated, 6}},
		{"byte array length past part of a body", "0a000701610a0102", failure{stream.ErrTruncated, 6}},
		{"negative int array length", "0a000b01610100", failure{stream.ErrOutOfRange, 6}},
		{"int array length past part of a body", "0a000b01610a0202", failure{stream.ErrTruncated, 6}},
		{"compound without its end", "0a00", failure{stream.ErrTruncated, 2}},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			r := stream.NewReader(check.Hex(t, c.data))
			ReadCompoundTag(r)
			check.Equal(t, readFailure(r), c.want)
		})
	}
}

func TestMalformedListHeaderIsRejected(t *testing.T) {
	cases := []struct {
		name string
		data string
		want failure
	}{
		{"unknown element type", "0c00", failure{stream.ErrUnknownValue, 2}},
		{"end elements", "0002", failure{stream.ErrUnknownValue, 2}},
		{"negative count", "0101", failure{stream.ErrOutOfRange, 2}},
		{"count past the body", "0104", failure{stream.ErrTruncated, 2}},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			r := stream.NewReader(check.Hex(t, c.data))
			readPayload(r, TypeList, 0)
			check.Equal(t, readFailure(r), c.want)
		})
	}
}

func TestNestingAtTheDepthLimitReads(t *testing.T) {
	r := stream.NewReader(check.Hex(t, "0a00"+strings.Repeat("0a00", 512)+strings.Repeat("00", 513)))
	ReadCompoundTag(r)
	check.Equal(t, r.Failed(), false)
}

func TestNestingPastTheDepthLimitIsOutOfRange(t *testing.T) {
	r := stream.NewReader(check.Hex(t, "0a00"+strings.Repeat("0a00", 513)+strings.Repeat("00", 514)))
	ReadCompoundTag(r)
	check.Equal(t, readFailure(r), failure{stream.ErrOutOfRange, 1028})
}

func TestUnencodableTagIsAnUnknownValue(t *testing.T) {
	cases := []struct {
		name string
		tag  Tag
	}{
		{"list element of another type", ListTag{ElementType: TypeInt, Elements: []Tag{ByteTag(1)}}},
		{"list of mixed elements", ListTag{Elements: []Tag{IntTag(1), ByteTag(1)}}},
		{"nil list element", ListTag{Elements: []Tag{nil}}},
		{"unknown list element type", ListTag{ElementType: 12}},
		{"nil compound entry", CompoundTag{"a": nil}},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			var w stream.Writer
			writePayload(&w, c.tag)
			reason, _ := w.Failure()
			check.Equal(t, reason, stream.ErrUnknownValue)
		})
	}
}
