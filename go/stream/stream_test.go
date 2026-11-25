package stream_test

import (
	"math"
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

var uvarint32s = []struct {
	name  string
	data  string
	value uint32
}{
	{"zero", "00", 0},
	{"two groups", "ac02", 300},
	{"all bits", "ffffffff0f", math.MaxUint32},
}

var varint32s = []struct {
	name  string
	data  string
	value int32
}{
	{"zero", "00", 0},
	{"minus one", "01", -1},
	{"one", "02", 1},
	{"min", "ffffffff0f", math.MinInt32},
	{"max", "feffffff0f", math.MaxInt32},
}

var uvarint64s = []struct {
	name  string
	data  string
	value uint64
}{
	{"zero", "00", 0},
	{"two groups", "ac02", 300},
	{"all bits", "ffffffffffffffffff01", math.MaxUint64},
}

var varint64s = []struct {
	name  string
	data  string
	value int64
}{
	{"zero", "00", 0},
	{"minus one", "01", -1},
	{"min", "ffffffffffffffffff01", math.MinInt64},
	{"max", "feffffffffffffffff01", math.MaxInt64},
}

func TestUvarint32ReadsSevenBitGroups(t *testing.T) {
	for _, c := range uvarint32s {
		t.Run(c.name, func(t *testing.T) {
			check.Equal(t, stream.NewReader(check.Hex(t, c.data)).ReadUvarint32(), c.value)
		})
	}
}

func TestUvarint32WritesSevenBitGroups(t *testing.T) {
	for _, c := range uvarint32s {
		t.Run(c.name, func(t *testing.T) {
			var w stream.Writer
			w.WriteUvarint32(c.value)
			check.Equal(t, w.Bytes(), check.Hex(t, c.data))
		})
	}
}

func TestVarint32ReadsZigzag(t *testing.T) {
	for _, c := range varint32s {
		t.Run(c.name, func(t *testing.T) {
			check.Equal(t, stream.NewReader(check.Hex(t, c.data)).ReadVarint32(), c.value)
		})
	}
}

func TestVarint32WritesZigzag(t *testing.T) {
	for _, c := range varint32s {
		t.Run(c.name, func(t *testing.T) {
			var w stream.Writer
			w.WriteVarint32(c.value)
			check.Equal(t, w.Bytes(), check.Hex(t, c.data))
		})
	}
}

func TestUvarint64ReadsSevenBitGroups(t *testing.T) {
	for _, c := range uvarint64s {
		t.Run(c.name, func(t *testing.T) {
			check.Equal(t, stream.NewReader(check.Hex(t, c.data)).ReadUvarint64(), c.value)
		})
	}
}

func TestUvarint64WritesSevenBitGroups(t *testing.T) {
	for _, c := range uvarint64s {
		t.Run(c.name, func(t *testing.T) {
			var w stream.Writer
			w.WriteUvarint64(c.value)
			check.Equal(t, w.Bytes(), check.Hex(t, c.data))
		})
	}
}

func TestVarint64ReadsZigzag(t *testing.T) {
	for _, c := range varint64s {
		t.Run(c.name, func(t *testing.T) {
			check.Equal(t, stream.NewReader(check.Hex(t, c.data)).ReadVarint64(), c.value)
		})
	}
}

func TestVarint64WritesZigzag(t *testing.T) {
	for _, c := range varint64s {
		t.Run(c.name, func(t *testing.T) {
			var w stream.Writer
			w.WriteVarint64(c.value)
			check.Equal(t, w.Bytes(), check.Hex(t, c.data))
		})
	}
}

func TestMalformedVarintFails(t *testing.T) {
	cases := []struct {
		name string
		data string
		read func(*stream.Reader)
		want failure
	}{
		{"uvarint32 past its type after the fifth byte", "ffffffff10", func(r *stream.Reader) { r.ReadUvarint32() }, failure{stream.ErrOutOfRange, 5}},
		{"uvarint32 continuing after the fifth byte", "ffffffff8f00", func(r *stream.Reader) { r.ReadUvarint32() }, failure{stream.ErrOutOfRange, 5}},
		{"uvarint64 past its type after the tenth byte", "ffffffffffffffffff02", func(r *stream.Reader) { r.ReadUvarint64() }, failure{stream.ErrOutOfRange, 10}},
		{"varint that runs out", "8080", func(r *stream.Reader) { r.ReadVarint32() }, failure{stream.ErrTruncated, 2}},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			r := stream.NewReader(check.Hex(t, c.data))
			c.read(r)
			check.Equal(t, readFailure(r), c.want)
		})
	}
}

var fixedReads = []struct {
	name  string
	read  func(*stream.Reader)
	width int
}{
	{"bool", func(r *stream.Reader) { r.ReadBool() }, 1},
	{"int8", func(r *stream.Reader) { r.ReadInt8() }, 1},
	{"uint8", func(r *stream.Reader) { r.ReadUint8() }, 1},
	{"int16", func(r *stream.Reader) { r.ReadInt16() }, 2},
	{"uint16", func(r *stream.Reader) { r.ReadUint16() }, 2},
	{"int32", func(r *stream.Reader) { r.ReadInt32() }, 4},
	{"uint32", func(r *stream.Reader) { r.ReadUint32() }, 4},
	{"int32 big-endian", func(r *stream.Reader) { r.ReadInt32BE() }, 4},
	{"int64", func(r *stream.Reader) { r.ReadInt64() }, 8},
	{"uint64", func(r *stream.Reader) { r.ReadUint64() }, 8},
	{"float", func(r *stream.Reader) { r.ReadFloat() }, 4},
	{"double", func(r *stream.Reader) { r.ReadDouble() }, 8},
}

func TestFixedReadOneByteShortIsTruncatedAtTheFieldStart(t *testing.T) {
	for _, c := range fixedReads {
		t.Run(c.name, func(t *testing.T) {
			r := stream.NewReader(make([]byte, c.width-1))
			c.read(r)
			check.Equal(t, readFailure(r), failure{stream.ErrTruncated, 0})
		})
	}
}

func TestFixedReadConsumesExactlyItsWidth(t *testing.T) {
	for _, c := range fixedReads {
		t.Run(c.name, func(t *testing.T) {
			r := stream.NewReader(make([]byte, c.width+1))
			c.read(r)
			check.Equal(t, r.Remaining(), 1)
		})
	}
}

func TestFixedReadsDecodeTheirByteOrder(t *testing.T) {
	cases := []struct {
		name string
		data string
		read func(*stream.Reader) any
		want any
	}{
		{"int16 little-endian", "feff", func(r *stream.Reader) any { return r.ReadInt16() }, int16(-2)},
		{"uint16 unsigned", "ffff", func(r *stream.Reader) any { return r.ReadUint16() }, uint16(math.MaxUint16)},
		{"int32 little-endian", "00000102", func(r *stream.Reader) any { return r.ReadInt32() }, int32(0x02010000)},
		{"int32 big-endian", "00000102", func(r *stream.Reader) any { return r.ReadInt32BE() }, int32(0x0102)},
		{"uint32 unsigned", "ffffffff", func(r *stream.Reader) any { return r.ReadUint32() }, uint32(math.MaxUint32)},
		{"int64 little-endian", "feffffffffffffff", func(r *stream.Reader) any { return r.ReadInt64() }, int64(-2)},
		{"uint64 unsigned", "ffffffffffffffff", func(r *stream.Reader) any { return r.ReadUint64() }, uint64(math.MaxUint64)},
		{"int8 signed", "ff", func(r *stream.Reader) any { return r.ReadInt8() }, int8(-1)},
		{"uint8 unsigned", "ff", func(r *stream.Reader) any { return r.ReadUint8() }, uint8(math.MaxUint8)},
		{"float little-endian", "0000803f", func(r *stream.Reader) any { return r.ReadFloat() }, float32(1)},
		{"double little-endian", "000000000000f03f", func(r *stream.Reader) any { return r.ReadDouble() }, float64(1)},
		{"bool any non-zero byte", "02", func(r *stream.Reader) any { return r.ReadBool() }, true},
		{"bool zero", "00", func(r *stream.Reader) any { return r.ReadBool() }, false},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			check.Equal(t, c.read(stream.NewReader(check.Hex(t, c.data))), c.want)
		})
	}
}

func TestFixedWritesEncodeTheirByteOrder(t *testing.T) {
	cases := []struct {
		name  string
		write func(*stream.Writer)
		data  string
	}{
		{"bool true", func(w *stream.Writer) { w.WriteBool(true) }, "01"},
		{"bool false", func(w *stream.Writer) { w.WriteBool(false) }, "00"},
		{"int8", func(w *stream.Writer) { w.WriteInt8(-1) }, "ff"},
		{"uint8", func(w *stream.Writer) { w.WriteUint8(254) }, "fe"},
		{"int16", func(w *stream.Writer) { w.WriteInt16(-2) }, "feff"},
		{"uint16", func(w *stream.Writer) { w.WriteUint16(math.MaxUint16) }, "ffff"},
		{"int32", func(w *stream.Writer) { w.WriteInt32(0x02010000) }, "00000102"},
		{"int32 big-endian", func(w *stream.Writer) { w.WriteInt32BE(0x0102) }, "00000102"},
		{"uint32", func(w *stream.Writer) { w.WriteUint32(1) }, "01000000"},
		{"int64", func(w *stream.Writer) { w.WriteInt64(-2) }, "feffffffffffffff"},
		{"uint64", func(w *stream.Writer) { w.WriteUint64(1) }, "0100000000000000"},
		{"float", func(w *stream.Writer) { w.WriteFloat(1) }, "0000803f"},
		{"double", func(w *stream.Writer) { w.WriteDouble(1) }, "000000000000f03f"},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			var w stream.Writer
			c.write(&w)
			check.Equal(t, w.Bytes(), check.Hex(t, c.data))
		})
	}
}

var strs = []struct {
	name  string
	data  string
	value string
}{
	{"empty", "00", ""},
	{"ascii", "026869", "hi"},
	{"bytes that are not utf-8", "02ff80", "\xff\x80"},
}

func TestStrReads(t *testing.T) {
	for _, c := range strs {
		t.Run(c.name, func(t *testing.T) {
			check.Equal(t, stream.NewReader(check.Hex(t, c.data)).ReadString(), c.value)
		})
	}
}

func TestStrWritesWhatItRead(t *testing.T) {
	for _, c := range strs {
		t.Run(c.name, func(t *testing.T) {
			var w stream.Writer
			w.WriteString(c.value)
			check.Equal(t, w.Bytes(), check.Hex(t, c.data))
		})
	}
}

func TestStrLengthPastTheBodyIsTruncatedAfterTheLength(t *testing.T) {
	r := stream.NewReader(check.Hex(t, "056869"))
	r.ReadString()
	check.Equal(t, readFailure(r), failure{stream.ErrTruncated, 1})
}

func TestBytesReadTheirLengthPrefix(t *testing.T) {
	check.Equal(t, stream.NewReader(check.Hex(t, "03010203")).ReadBytes(), []byte{1, 2, 3})
}

func TestEmptyBytesReadAsNil(t *testing.T) {
	check.Equal(t, stream.NewReader(check.Hex(t, "00")).ReadBytes(), []byte(nil))
}

func TestBytesWriteTheirLengthPrefix(t *testing.T) {
	var w stream.Writer
	w.WriteBytes([]byte{1, 2, 3})
	check.Equal(t, w.Bytes(), check.Hex(t, "03010203"))
}

func TestReadBytesCopiesTheInput(t *testing.T) {
	data := check.Hex(t, "0101")
	read := stream.NewReader(data).ReadBytes()
	data[1] = 2
	check.Equal(t, read, []byte{1})
}

func TestFirstReaderFailureWins(t *testing.T) {
	r := stream.NewReader(check.Hex(t, "01"))
	r.ReadUint16()
	r.Fail(stream.ErrUnknownValue)
	check.Equal(t, readFailure(r), failure{stream.ErrTruncated, 0})
}

func TestFailedReaderReadsZero(t *testing.T) {
	r := stream.NewReader(check.Hex(t, "05"))
	r.Fail(stream.ErrUnknownValue)
	check.Equal(t, r.ReadUint8(), 0)
}

func TestFailedReaderMovesNothing(t *testing.T) {
	r := stream.NewReader(check.Hex(t, "05"))
	r.Fail(stream.ErrUnknownValue)
	r.ReadUint8()
	check.Equal(t, r.Remaining(), 1)
}

func TestReaderFailureOffsetIsWhereItFailed(t *testing.T) {
	r := stream.NewReader(check.Hex(t, "0105"))
	r.ReadUint8()
	r.Fail(stream.ErrUnknownValue)
	check.Equal(t, readFailure(r), failure{stream.ErrUnknownValue, 1})
}

func TestReaderPathReadsOutermostFirst(t *testing.T) {
	r := stream.NewReader(nil)
	r.ReadUint8()
	r.PrependIndex(2)
	r.PrependField("entries")
	_, path, _ := r.Failure()
	check.Equal(t, path, []any{"entries", 2})
}

func TestPrependBeforeAFailureRecordsNothing(t *testing.T) {
	r := stream.NewReader(nil)
	r.PrependField("entries")
	r.ReadUint8()
	_, path, _ := r.Failure()
	check.Equal(t, path, []any{})
}

func TestUnfailedReaderHasNoFailure(t *testing.T) {
	r := stream.NewReader(check.Hex(t, "00"))
	r.ReadUint8()
	check.Equal(t, r.Failed(), false)
}

func TestFailedWriterWritesNothingMore(t *testing.T) {
	var w stream.Writer
	w.WriteUint8(1)
	w.Fail(stream.ErrOutOfRange)
	w.WriteUint8(2)
	w.WriteString("hi")
	check.Equal(t, w.Bytes(), check.Hex(t, "01"))
}

func TestFirstWriterFailureWins(t *testing.T) {
	var w stream.Writer
	w.Fail(stream.ErrOutOfRange)
	w.Fail(stream.ErrUnknownValue)
	reason, _ := w.Failure()
	check.Equal(t, reason, stream.ErrOutOfRange)
}

func TestWriterPathReadsOutermostFirst(t *testing.T) {
	var w stream.Writer
	w.Fail(stream.ErrOutOfRange)
	w.PrependIndex(0)
	w.PrependField("value")
	_, path := w.Failure()
	check.Equal(t, path, []any{"value", 0})
}

func TestCountPrefixesNarrowToInt(t *testing.T) {
	cases := []struct {
		name string
		data string
		read func(*stream.Reader) int
		want int
	}{
		{"uvarint32", "ffffffff07", (*stream.Reader).ReadUvarint32Count, math.MaxInt32},
		{"uint32", "ffffff7f", (*stream.Reader).ReadUint32Count, math.MaxInt32},
		{"uint16", "ffff", (*stream.Reader).ReadUint16Count, math.MaxUint16},
		{"varint32", "feffffff0f", (*stream.Reader).ReadVarint32Count, math.MaxInt32},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			check.Equal(t, c.read(stream.NewReader(check.Hex(t, c.data))), c.want)
		})
	}
}

func TestCountOutsideIntIsOutOfRange(t *testing.T) {
	cases := []struct {
		name string
		data string
		read func(*stream.Reader) int
		want failure
	}{
		{"uvarint32 past MaxInt32", "8080808008", (*stream.Reader).ReadUvarint32Count, failure{stream.ErrOutOfRange, 5}},
		{"uint32 past MaxInt32", "00000080", (*stream.Reader).ReadUint32Count, failure{stream.ErrOutOfRange, 4}},
		{"negative varint32", "01", (*stream.Reader).ReadVarint32Count, failure{stream.ErrOutOfRange, 1}},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			r := stream.NewReader(check.Hex(t, c.data))
			c.read(r)
			check.Equal(t, readFailure(r), c.want)
		})
	}
}

func TestCountProductMultiplies(t *testing.T) {
	check.Equal(t, stream.NewReader(nil).CountProduct(1<<31, 1<<31), int64(1)<<62)
}

func TestCountProductOutsideSixtyFourBitsIsOutOfRange(t *testing.T) {
	cases := []struct {
		name string
		a, b int64
	}{
		{"negative factor", -1, 2},
		{"past sixty-four bits", 1 << 32, 1 << 32},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			r := stream.NewReader(nil)
			r.CountProduct(c.a, c.b)
			check.Equal(t, readFailure(r), failure{stream.ErrOutOfRange, 0})
		})
	}
}

func TestCountProductPastMaxInt32IsOutOfRangeWhenNarrowed(t *testing.T) {
	r := stream.NewReader(nil)
	r.Count(r.CountProduct(65_536, 65_536))
	check.Equal(t, readFailure(r), failure{stream.ErrOutOfRange, 0})
}

func TestInitialCapacityCapsAHostileCount(t *testing.T) {
	check.Equal(t, stream.InitialCapacity(math.MaxInt32), 65_536)
}

func TestInitialCapacityKeepsASmallCount(t *testing.T) {
	check.Equal(t, stream.InitialCapacity(3), 3)
}

func TestFoldASCIILowersLettersOnly(t *testing.T) {
	check.Equal(t, stream.FoldASCII("AbC_1"), "abc_1")
}

func TestFoldASCIILeavesTheKelvinSignAlone(t *testing.T) {
	check.Equal(t, stream.FoldASCII("K"), "K")
}
