package protocol

import (
	"math"

	"github.com/EndstoneMC/bedrock-protocol/go/stream"
)

func (x *AvailableCommandsPacket_EnumData) encode594(w *stream.Writer, argument int64) {
	if x == nil {
		x = new(AvailableCommandsPacket_EnumData)
	}
	w.WriteString(x.Name)
	w.WriteUvarint32(uint32(len(x.Values)))
	for i, index := range x.Values {
		switch {
		case argument > 0x10000:
			w.WriteUint32(index)
		case argument > 0x100 && index <= math.MaxUint16:
			w.WriteUint16(uint16(index))
		case argument <= 0x100 && index <= math.MaxUint8:
			w.WriteUint8(uint8(index))
		default:
			w.Fail(stream.ErrOutOfRange)
		}
		if w.Failed() {
			w.PrependIndex(i)
			w.PrependField("values")
			return
		}
	}
}

func (x *AvailableCommandsPacket_EnumData) decode594(r *stream.Reader, argument int64) {
	*x = AvailableCommandsPacket_EnumData{}
	x.Name = r.ReadString()
	if r.Failed() {
		r.PrependField("name")
		return
	}
	count := r.ReadUvarint32Count()
	values := make([]uint32, 0, stream.InitialCapacity(count))
	for i := 0; i < count; i++ {
		switch {
		case argument <= 0x100:
			values = append(values, uint32(r.ReadUint8()))
		case argument <= 0x10000:
			values = append(values, uint32(r.ReadUint16()))
		default:
			values = append(values, r.ReadUint32())
		}
		if r.Failed() {
			r.PrependIndex(i)
			break
		}
	}
	x.Values = values
	if r.Failed() {
		r.PrependField("values")
	}
}
