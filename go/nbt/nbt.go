// Package nbt holds the network NBT tags: little-endian, with varint ints, longs and lengths.
package nbt

import (
	"maps"
	"math"
	"slices"

	"github.com/EndstoneMC/bedrock-protocol/go/stream"
)

type Type uint8

const (
	TypeEnd Type = iota
	TypeByte
	TypeShort
	TypeInt
	TypeInt64
	TypeFloat
	TypeDouble
	TypeByteArray
	TypeString
	TypeList
	TypeCompound
	TypeIntArray
)

const maxNestingDepth = 512

// Tag is one of the tag types this package declares.
type Tag interface {
	Type() Type
	isTag()
}

type (
	ByteTag      uint8
	ShortTag     int16
	IntTag       int32
	Int64Tag     int64
	FloatTag     float32
	DoubleTag    float64
	ByteArrayTag []uint8
	StringTag    string
	// ListTag holds elements of one type; an End ElementType takes the first element's.
	ListTag struct {
		ElementType Type
		Elements    []Tag
	}
	CompoundTag map[string]Tag
	IntArrayTag []int32
	// CompoundTagData is a compound's entries and its End, with no root type or name.
	CompoundTagData map[string]Tag
)

func (ByteTag) Type() Type      { return TypeByte }
func (ShortTag) Type() Type     { return TypeShort }
func (IntTag) Type() Type       { return TypeInt }
func (Int64Tag) Type() Type     { return TypeInt64 }
func (FloatTag) Type() Type     { return TypeFloat }
func (DoubleTag) Type() Type    { return TypeDouble }
func (ByteArrayTag) Type() Type { return TypeByteArray }
func (StringTag) Type() Type    { return TypeString }
func (ListTag) Type() Type      { return TypeList }
func (CompoundTag) Type() Type  { return TypeCompound }
func (IntArrayTag) Type() Type  { return TypeIntArray }

func (ByteTag) isTag()      {}
func (ShortTag) isTag()     {}
func (IntTag) isTag()       {}
func (Int64Tag) isTag()     {}
func (FloatTag) isTag()     {}
func (DoubleTag) isTag()    {}
func (ByteArrayTag) isTag() {}
func (StringTag) isTag()    {}
func (ListTag) isTag()      {}
func (CompoundTag) isTag()  {}
func (IntArrayTag) isTag()  {}

// ReadCompoundTag reads a root compound, dropping its name.
func ReadCompoundTag(r *stream.Reader) CompoundTag {
	rootType := Type(r.ReadUint8())
	if rootType == TypeEnd || rootType > TypeIntArray {
		r.Fail(stream.ErrUnknownValue)
		return nil
	}
	r.ReadString()
	compound, isCompound := readPayload(r, rootType, 0).(CompoundTag)
	if !isCompound {
		r.Fail(stream.ErrUnknownValue)
	}
	return compound
}

// WriteCompoundTag writes a root compound with an empty name.
func WriteCompoundTag(w *stream.Writer, compound CompoundTag) {
	w.WriteUint8(uint8(TypeCompound))
	w.WriteString("")
	writeCompound(w, compound)
}

func ReadCompoundTagData(r *stream.Reader) CompoundTagData {
	return CompoundTagData(readCompound(r, 0))
}

func WriteCompoundTagData(w *stream.Writer, data CompoundTagData) {
	writeCompound(w, data)
}

func readPayload(r *stream.Reader, tagType Type, depth int) Tag {
	if depth > maxNestingDepth {
		r.Fail(stream.ErrOutOfRange)
		return nil
	}
	switch tagType {
	case TypeByte:
		return ByteTag(r.ReadUint8())
	case TypeShort:
		return ShortTag(r.ReadInt16())
	case TypeInt:
		return IntTag(r.ReadVarint32())
	case TypeInt64:
		return Int64Tag(r.ReadVarint64())
	case TypeFloat:
		return FloatTag(r.ReadFloat())
	case TypeDouble:
		return DoubleTag(r.ReadDouble())
	case TypeString:
		return StringTag(r.ReadString())
	case TypeByteArray:
		count := readArrayCount(r)
		out := slices.Grow(ByteArrayTag(nil), count)
		for range count {
			out = append(out, r.ReadUint8())
		}
		return out
	case TypeIntArray:
		count := readArrayCount(r)
		out := slices.Grow(IntArrayTag(nil), count)
		for range count {
			out = append(out, r.ReadVarint32())
		}
		return out
	case TypeList:
		elementType := Type(r.ReadUint8())
		count := r.ReadVarint32()
		if elementType > TypeIntArray || count > 0 && elementType == TypeEnd {
			r.Fail(stream.ErrUnknownValue)
			return nil
		}
		if count < 0 {
			r.Fail(stream.ErrOutOfRange)
			return nil
		}
		out := ListTag{ElementType: elementType, Elements: slices.Grow([]Tag(nil), stream.InitialCapacity(int(count)))}
		for range count {
			element := readPayload(r, elementType, depth+1)
			if r.Failed() {
				return nil
			}
			out.Elements = append(out.Elements, element)
		}
		return out
	case TypeCompound:
		return readCompound(r, depth)
	}
	r.Fail(stream.ErrUnknownValue)
	return nil
}

func readArrayCount(r *stream.Reader) int {
	count := r.ReadVarint32()
	if count < 0 {
		r.Fail(stream.ErrOutOfRange)
		return 0
	}
	if int(count) > r.Remaining() {
		r.Fail(stream.ErrTruncated)
		return 0
	}
	return int(count)
}

func readCompound(r *stream.Reader, depth int) CompoundTag {
	var out CompoundTag
	for {
		entryType := Type(r.ReadUint8())
		if entryType == TypeEnd {
			return out
		}
		if entryType > TypeIntArray {
			r.Fail(stream.ErrUnknownValue)
			return nil
		}
		name := r.ReadString()
		entry := readPayload(r, entryType, depth+1)
		if r.Failed() {
			return nil
		}
		if _, seen := out[name]; !seen {
			if out == nil {
				out = make(CompoundTag)
			}
			out[name] = entry
		}
	}
}

func writePayload(w *stream.Writer, tag Tag) {
	switch tag := tag.(type) {
	case ByteTag:
		w.WriteUint8(uint8(tag))
	case ShortTag:
		w.WriteInt16(int16(tag))
	case IntTag:
		w.WriteVarint32(int32(tag))
	case Int64Tag:
		w.WriteVarint64(int64(tag))
	case FloatTag:
		w.WriteFloat(float32(tag))
	case DoubleTag:
		w.WriteDouble(float64(tag))
	case StringTag:
		w.WriteString(string(tag))
	case ByteArrayTag:
		writeCount(w, len(tag))
		for _, element := range tag {
			w.WriteUint8(element)
		}
	case IntArrayTag:
		writeCount(w, len(tag))
		for _, element := range tag {
			w.WriteVarint32(element)
		}
	case ListTag:
		elementType := tag.ElementType
		if elementType == TypeEnd && len(tag.Elements) > 0 && tag.Elements[0] != nil {
			elementType = tag.Elements[0].Type()
		}
		if elementType > TypeIntArray {
			w.Fail(stream.ErrUnknownValue)
			return
		}
		w.WriteUint8(uint8(elementType))
		writeCount(w, len(tag.Elements))
		for _, element := range tag.Elements {
			if element == nil || element.Type() != elementType {
				w.Fail(stream.ErrUnknownValue)
				return
			}
			writePayload(w, element)
		}
	case CompoundTag:
		writeCompound(w, tag)
	default:
		w.Fail(stream.ErrUnknownValue)
	}
}

func writeCount(w *stream.Writer, count int) {
	if count > math.MaxInt32 {
		w.Fail(stream.ErrOutOfRange)
		return
	}
	w.WriteVarint32(int32(count))
}

func writeCompound(w *stream.Writer, compound map[string]Tag) {
	for _, name := range slices.Sorted(maps.Keys(compound)) {
		entry := compound[name]
		if entry == nil {
			w.Fail(stream.ErrUnknownValue)
			return
		}
		w.WriteUint8(uint8(entry.Type()))
		w.WriteString(name)
		writePayload(w, entry)
	}
	w.WriteUint8(uint8(TypeEnd))
}
