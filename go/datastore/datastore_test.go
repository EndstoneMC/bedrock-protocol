package datastore_test

import (
	"slices"
	"strings"
	"testing"

	"github.com/EndstoneMC/bedrock-protocol/go/datastore"
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

var values = []struct {
	name  string
	value datastore.DynamicValue
	data  string
}{
	{"null", datastore.Null{}, "00000000"},
	{"bool", datastore.Bool(true), "0100000001"},
	{"integer", datastore.Integer(-2), "02000000feffffffffffffff"},
	{"number", datastore.Number(1), "03000000000000000000f03f"},
	{"string", datastore.String("hi"), "04000000026869"},
	{"array", datastore.Array{datastore.Null{}}, "050000000100000000"},
	{"array of two count groups", datastore.Array(slices.Repeat([]datastore.DynamicValue{datastore.Null{}}, 128)), "050000008001" + strings.Repeat("00000000", 128)},
	{"object", datastore.Object{"b": datastore.Null{}, "a": datastore.Bool(true)}, "060000000201610100000001016200000000"},
}

func TestWriteGivesTheTagThenThePayload(t *testing.T) {
	for _, c := range values {
		t.Run(c.name, func(t *testing.T) {
			var w stream.Writer
			datastore.WriteDynamicValue(&w, c.value)
			check.Equal(t, w.Bytes(), check.Hex(t, c.data))
		})
	}
}

func TestReadTakesTheTagThenThePayload(t *testing.T) {
	for _, c := range values {
		t.Run(c.name, func(t *testing.T) {
			check.Equal(t, datastore.ReadDynamicValue(stream.NewReader(check.Hex(t, c.data))), c.value)
		})
	}
}

func TestNilWritesNull(t *testing.T) {
	var w stream.Writer
	datastore.WriteDynamicValue(&w, nil)
	check.Equal(t, w.Bytes(), check.Hex(t, "00000000"))
}

func TestObjectKeysAreWrittenInByteOrder(t *testing.T) {
	var w stream.Writer
	datastore.WriteDynamicValue(&w, datastore.Object{"\U00010000": datastore.Null{}, "￿": datastore.Null{}})
	check.Equal(t, w.Bytes(), check.Hex(t, "060000000203efbfbf0000000004f090808000000000"))
}

func TestDuplicateKeyKeepsTheFirstValue(t *testing.T) {
	read := datastore.ReadDynamicValue(stream.NewReader(check.Hex(t, "060000000201610000000001610100000001")))
	check.Equal(t, read, datastore.DynamicValue(datastore.Object{"a": datastore.Null{}}))
}

func TestMalformedValueIsRejected(t *testing.T) {
	cases := []struct {
		name string
		data string
		want failure
	}{
		{"tag past the last type", "07000000", failure{stream.ErrUnknownValue, 4}},
		{"tag with every bit set", "ffffffff", failure{stream.ErrUnknownValue, 4}},
		{"missing payload", "01000000", failure{stream.ErrTruncated, 4}},
		{"array count past the body", "05000000ffffffff0f", failure{stream.ErrTruncated, 9}},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			r := stream.NewReader(check.Hex(t, c.data))
			datastore.ReadDynamicValue(r)
			check.Equal(t, readFailure(r), c.want)
		})
	}
}

func TestNestingAtTheDepthLimitReads(t *testing.T) {
	r := stream.NewReader(check.Hex(t, strings.Repeat("0500000001", 512)+"00000000"))
	datastore.ReadDynamicValue(r)
	check.Equal(t, r.Failed(), false)
}

func TestNestingPastTheDepthLimitIsOutOfRange(t *testing.T) {
	r := stream.NewReader(check.Hex(t, strings.Repeat("0500000001", 513)+"00000000"))
	datastore.ReadDynamicValue(r)
	check.Equal(t, readFailure(r), failure{stream.ErrOutOfRange, 2565})
}
