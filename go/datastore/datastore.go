// Package datastore holds the DynamicValue a data store carries: a uint32 tag, then its payload.
package datastore

import (
	"maps"
	"math"
	"slices"

	"github.com/EndstoneMC/bedrock-protocol/go/stream"
)

const maxNestingDepth = 512

// DynamicValue is one of the value types this package declares; a nil one is Null.
type DynamicValue interface {
	isDynamicValue()
}

type (
	Null    struct{}
	Bool    bool
	Integer int64
	Number  float64
	String  string
	Array   []DynamicValue
	Object  map[string]DynamicValue
)

const (
	tagNull uint32 = iota
	tagBool
	tagInteger
	tagNumber
	tagString
	tagArray
	tagObject
)

func (Null) isDynamicValue()    {}
func (Bool) isDynamicValue()    {}
func (Integer) isDynamicValue() {}
func (Number) isDynamicValue()  {}
func (String) isDynamicValue()  {}
func (Array) isDynamicValue()   {}
func (Object) isDynamicValue()  {}

func ReadDynamicValue(r *stream.Reader) DynamicValue {
	return read(r, 0)
}

func WriteDynamicValue(w *stream.Writer, value DynamicValue) {
	switch value := value.(type) {
	case nil, Null:
		w.WriteUint32(tagNull)
	case Bool:
		w.WriteUint32(tagBool)
		w.WriteBool(bool(value))
	case Integer:
		w.WriteUint32(tagInteger)
		w.WriteInt64(int64(value))
	case Number:
		w.WriteUint32(tagNumber)
		w.WriteDouble(float64(value))
	case String:
		w.WriteUint32(tagString)
		w.WriteString(string(value))
	case Array:
		w.WriteUint32(tagArray)
		writeCount(w, len(value))
		for _, element := range value {
			WriteDynamicValue(w, element)
		}
	case Object:
		w.WriteUint32(tagObject)
		writeCount(w, len(value))
		for _, key := range slices.Sorted(maps.Keys(value)) {
			w.WriteString(key)
			WriteDynamicValue(w, value[key])
		}
	}
}

func writeCount(w *stream.Writer, count int) {
	if uint64(count) > math.MaxUint32 {
		w.Fail(stream.ErrOutOfRange)
		return
	}
	w.WriteUvarint32(uint32(count))
}

func read(r *stream.Reader, depth int) DynamicValue {
	if depth > maxNestingDepth {
		r.Fail(stream.ErrOutOfRange)
		return nil
	}
	switch r.ReadUint32() {
	case tagNull:
		return Null{}
	case tagBool:
		return Bool(r.ReadBool())
	case tagInteger:
		return Integer(r.ReadInt64())
	case tagNumber:
		return Number(r.ReadDouble())
	case tagString:
		return String(r.ReadString())
	case tagArray:
		count := r.ReadUvarint32()
		var out Array
		for range count {
			element := read(r, depth+1)
			if r.Failed() {
				return nil
			}
			out = append(out, element)
		}
		return out
	case tagObject:
		count := r.ReadUvarint32()
		var out Object
		for range count {
			key := r.ReadString()
			child := read(r, depth+1)
			if r.Failed() {
				return nil
			}
			if _, seen := out[key]; !seen {
				if out == nil {
					out = make(Object)
				}
				out[key] = child
			}
		}
		return out
	}
	r.Fail(stream.ErrUnknownValue)
	return nil
}
