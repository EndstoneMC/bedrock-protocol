// Package stream reads and writes the Bedrock protocol's primitive encodings.
package stream

import (
	"errors"
	"math"
	"math/bits"
)

var (
	ErrTruncated     = errors.New("truncated")
	ErrOutOfRange    = errors.New("out of range")
	ErrUnknownValue  = errors.New("unknown value")
	ErrTrailingBytes = errors.New("trailing bytes")
)

const maxInitialCapacity = 65_536

// InitialCapacity caps what a decoded collection reserves up front.
func InitialCapacity(count int) int {
	return min(count, maxInitialCapacity)
}

// FoldASCII lowercases A-Z only.
func FoldASCII(s string) string {
	folded := []byte(s)
	for i, c := range folded {
		if 'A' <= c && c <= 'Z' {
			folded[i] = c + 'a' - 'A'
		}
	}
	return string(folded)
}

type failure struct {
	reason   error
	reversed []any
}

func (f *failure) Failed() bool {
	return f.reason != nil
}

// Fail records the reason unless an earlier one is recorded; a failed stream moves no further.
func (f *failure) Fail(reason error) {
	if f.reason == nil {
		f.reason = reason
	}
}

// PrependField puts a field name in front of the failure's path.
func (f *failure) PrependField(name string) {
	if f.reason != nil {
		f.reversed = append(f.reversed, name)
	}
}

// PrependIndex puts a list index in front of the failure's path.
func (f *failure) PrependIndex(index int) {
	if f.reason != nil {
		f.reversed = append(f.reversed, index)
	}
}

func (f *failure) path() []any {
	path := make([]any, len(f.reversed))
	for i, segment := range f.reversed {
		path[len(path)-1-i] = segment
	}
	return path
}

// Reader decodes from a byte slice; once failed, every read returns the zero value and moves nothing.
type Reader struct {
	failure
	data []byte
	pos  int
}

func NewReader(data []byte) *Reader {
	return &Reader{data: data}
}

// Failure gives the first failure's reason, its path outermost first and its offset, or a nil reason.
func (r *Reader) Failure() (reason error, path []any, offset int) {
	return r.reason, r.path(), r.pos
}

func (r *Reader) Remaining() int {
	return len(r.data) - r.pos
}

func (r *Reader) take(n int) []byte {
	if r.reason != nil {
		return nil
	}
	if n > len(r.data)-r.pos {
		r.Fail(ErrTruncated)
		return nil
	}
	taken := r.data[r.pos : r.pos+n]
	r.pos += n
	return taken
}

func (r *Reader) ReadBool() bool {
	return r.ReadUint8() != 0
}

func (r *Reader) ReadInt8() int8 {
	return int8(r.ReadUint8())
}

func (r *Reader) ReadUint8() uint8 {
	taken := r.take(1)
	if taken == nil {
		return 0
	}
	return taken[0]
}

func (r *Reader) ReadInt16() int16 {
	return int16(r.ReadUint16())
}

func (r *Reader) ReadUint16() uint16 {
	taken := r.take(2)
	if taken == nil {
		return 0
	}
	return uint16(taken[0]) | uint16(taken[1])<<8
}

func (r *Reader) ReadInt32() int32 {
	return int32(r.ReadUint32())
}

func (r *Reader) ReadUint32() uint32 {
	taken := r.take(4)
	if taken == nil {
		return 0
	}
	return uint32(taken[0]) | uint32(taken[1])<<8 | uint32(taken[2])<<16 | uint32(taken[3])<<24
}

func (r *Reader) ReadInt64() int64 {
	return int64(r.ReadUint64())
}

func (r *Reader) ReadUint64() uint64 {
	taken := r.take(8)
	if taken == nil {
		return 0
	}
	var value uint64
	for i := 7; i >= 0; i-- {
		value = value<<8 | uint64(taken[i])
	}
	return value
}

func (r *Reader) ReadInt32BE() int32 {
	taken := r.take(4)
	if taken == nil {
		return 0
	}
	return int32(uint32(taken[0])<<24 | uint32(taken[1])<<16 | uint32(taken[2])<<8 | uint32(taken[3]))
}

func (r *Reader) ReadFloat() float32 {
	return math.Float32frombits(r.ReadUint32())
}

func (r *Reader) ReadDouble() float64 {
	return math.Float64frombits(r.ReadUint64())
}

// ReadUvarint32 reads an unsigned varint of at most 5 bytes.
func (r *Reader) ReadUvarint32() uint32 {
	var value uint32
	for n := range 5 {
		b := r.ReadUint8()
		if r.reason != nil {
			return 0
		}
		if n == 4 && b&0x7F > 0x0F {
			r.Fail(ErrOutOfRange)
			return 0
		}
		value |= uint32(b&0x7F) << (7 * n)
		if b&0x80 == 0 {
			return value
		}
	}
	r.Fail(ErrOutOfRange)
	return 0
}

// ReadUvarint64 reads an unsigned varint of at most 10 bytes.
func (r *Reader) ReadUvarint64() uint64 {
	var value uint64
	for n := range 10 {
		b := r.ReadUint8()
		if r.reason != nil {
			return 0
		}
		if n == 9 && b&0x7F > 0x01 {
			r.Fail(ErrOutOfRange)
			return 0
		}
		value |= uint64(b&0x7F) << (7 * n)
		if b&0x80 == 0 {
			return value
		}
	}
	r.Fail(ErrOutOfRange)
	return 0
}

func (r *Reader) ReadVarint32() int32 {
	zigzag := r.ReadUvarint32()
	return int32(zigzag>>1) ^ -int32(zigzag&1)
}

func (r *Reader) ReadVarint64() int64 {
	zigzag := r.ReadUvarint64()
	return int64(zigzag>>1) ^ -int64(zigzag&1)
}

func (r *Reader) prefixed() []byte {
	length := r.ReadUvarint32()
	if r.reason != nil {
		return nil
	}
	if uint64(length) > uint64(r.Remaining()) {
		r.Fail(ErrTruncated)
		return nil
	}
	return r.take(int(length))
}

// ReadString reads a uvarint32-length-prefixed string of any bytes.
func (r *Reader) ReadString() string {
	return string(r.prefixed())
}

// ReadBytes reads a uvarint32-length-prefixed copy of the bytes, nil when empty.
func (r *Reader) ReadBytes() []byte {
	prefixed := r.prefixed()
	if len(prefixed) == 0 {
		return nil
	}
	return append([]byte(nil), prefixed...)
}

// Count narrows a count, failing a negative one or one past math.MaxInt32 as out of range.
func (r *Reader) Count(value int64) int {
	if value < 0 || value > math.MaxInt32 {
		r.Fail(ErrOutOfRange)
		return 0
	}
	return int(value)
}

// CountProduct multiplies two count factors, failing a negative one or an unsigned 64-bit overflow as out of range.
func (r *Reader) CountProduct(a, b int64) int64 {
	if a < 0 || b < 0 {
		r.Fail(ErrOutOfRange)
		return 0
	}
	high, low := bits.Mul64(uint64(a), uint64(b))
	if high != 0 {
		r.Fail(ErrOutOfRange)
		return 0
	}
	return int64(low)
}

func (r *Reader) ReadUvarint32Count() int {
	return r.Count(int64(r.ReadUvarint32()))
}

func (r *Reader) ReadUint32Count() int {
	return r.Count(int64(r.ReadUint32()))
}

func (r *Reader) ReadUint16Count() int {
	return r.Count(int64(r.ReadUint16()))
}

func (r *Reader) ReadVarint32Count() int {
	return r.Count(int64(r.ReadVarint32()))
}

// Writer encodes into a growing byte slice; its zero value is ready, and once failed it writes nothing more.
type Writer struct {
	failure
	buf []byte
}

func (w *Writer) Bytes() []byte {
	return w.buf
}

// Failure gives the first failure's reason and its path outermost first, or a nil reason.
func (w *Writer) Failure() (reason error, path []any) {
	return w.reason, w.path()
}

func (w *Writer) put(b ...byte) {
	if w.reason == nil {
		w.buf = append(w.buf, b...)
	}
}

func (w *Writer) WriteBool(v bool) {
	if v {
		w.put(1)
	} else {
		w.put(0)
	}
}

func (w *Writer) WriteInt8(v int8) {
	w.put(byte(v))
}

func (w *Writer) WriteUint8(v uint8) {
	w.put(v)
}

func (w *Writer) WriteInt16(v int16) {
	w.WriteUint16(uint16(v))
}

func (w *Writer) WriteUint16(v uint16) {
	w.put(byte(v), byte(v>>8))
}

func (w *Writer) WriteInt32(v int32) {
	w.WriteUint32(uint32(v))
}

func (w *Writer) WriteUint32(v uint32) {
	w.put(byte(v), byte(v>>8), byte(v>>16), byte(v>>24))
}

func (w *Writer) WriteInt64(v int64) {
	w.WriteUint64(uint64(v))
}

func (w *Writer) WriteUint64(v uint64) {
	w.put(byte(v), byte(v>>8), byte(v>>16), byte(v>>24), byte(v>>32), byte(v>>40), byte(v>>48), byte(v>>56))
}

func (w *Writer) WriteInt32BE(v int32) {
	w.put(byte(v>>24), byte(v>>16), byte(v>>8), byte(v))
}

func (w *Writer) WriteFloat(v float32) {
	w.WriteUint32(math.Float32bits(v))
}

func (w *Writer) WriteDouble(v float64) {
	w.WriteUint64(math.Float64bits(v))
}

func (w *Writer) WriteUvarint32(v uint32) {
	w.WriteUvarint64(uint64(v))
}

func (w *Writer) WriteUvarint64(v uint64) {
	for v >= 0x80 {
		w.put(byte(v) | 0x80)
		v >>= 7
	}
	w.put(byte(v))
}

func (w *Writer) WriteVarint32(v int32) {
	w.WriteUvarint32(uint32(v<<1) ^ uint32(v>>31))
}

func (w *Writer) WriteVarint64(v int64) {
	w.WriteUvarint64(uint64(v<<1) ^ uint64(v>>63))
}

func (w *Writer) prefix(length int) {
	if uint64(length) > math.MaxUint32 {
		w.Fail(ErrOutOfRange)
		return
	}
	w.WriteUvarint32(uint32(length))
}

// WriteString writes a uvarint32 length prefix and the string's bytes.
func (w *Writer) WriteString(v string) {
	w.prefix(len(v))
	if w.reason == nil {
		w.buf = append(w.buf, v...)
	}
}

// WriteBytes writes a uvarint32 length prefix and the bytes.
func (w *Writer) WriteBytes(v []byte) {
	w.prefix(len(v))
	w.put(v...)
}
