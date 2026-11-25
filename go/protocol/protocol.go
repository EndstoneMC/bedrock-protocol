// Package protocol holds the generated packets and the codecs that pin them to one protocol.
package protocol

import (
	"fmt"
	"reflect"
	"strings"

	"github.com/EndstoneMC/bedrock-protocol/go/stream"
)

// Packet is a generated packet, implemented by its pointer type.
type Packet interface {
	PacketId() int
	encodeAt(w *stream.Writer, version int) bool
	decodeAt(r *stream.Reader, version int) bool
}

// Pinned encodes and decodes packets at one protocol.
type Pinned struct {
	version int
}

func (p Pinned) Version() int {
	return p.version
}

func (p Pinned) Encode(packet Packet) ([]byte, error) {
	var w stream.Writer
	if packet == nil || !packet.encodeAt(&w, p.version) {
		return nil, p.notAType(packet)
	}
	if reason, path := w.Failure(); reason != nil {
		return nil, &EncodeError{Reason: reason, Type: reflect.TypeOf(packet).Elem().Name(), Path: path}
	}
	return w.Bytes(), nil
}

// Decode decodes data into the packet in place, rejecting bytes left after it.
func (p Pinned) Decode(data []byte, packet Packet) error {
	if packet == nil {
		return p.notAType(packet)
	}
	if reflect.ValueOf(packet).IsNil() {
		return fmt.Errorf("%s: is nil", reflect.TypeOf(packet).Elem())
	}
	r := stream.NewReader(data)
	if !packet.decodeAt(r, p.version) {
		return p.notAType(packet)
	}
	if r.Remaining() > 0 {
		r.Fail(stream.ErrTrailingBytes)
	}
	if reason, path, offset := r.Failure(); reason != nil {
		return &DecodeError{Reason: reason, Type: reflect.TypeOf(packet).Elem().Name(), Path: path, Offset: offset, Length: len(data)}
	}
	return nil
}

func (p Pinned) notAType(packet Packet) error {
	return fmt.Errorf("%s: is not a type at protocol %d", strings.TrimPrefix(fmt.Sprintf("%T", packet), "*"), p.version)
}

// DecodeError reports bytes that do not decode as a packet, the path naming fields outermost first.
type DecodeError struct {
	Reason error
	Type   string
	Path   []any
	Offset int
	Length int
}

func (e *DecodeError) Error() string {
	return fmt.Sprintf("%s: %v at byte %d of %d", formatPath(e.Type, e.Path), e.Reason, e.Offset, e.Length)
}

func (e *DecodeError) Unwrap() error {
	return e.Reason
}

// EncodeError reports a packet value its encoding cannot hold, the path naming fields outermost first.
type EncodeError struct {
	Reason error
	Type   string
	Path   []any
}

func (e *EncodeError) Error() string {
	return fmt.Sprintf("%s: %v", formatPath(e.Type, e.Path), e.Reason)
}

func (e *EncodeError) Unwrap() error {
	return e.Reason
}

func formatPath(typeName string, path []any) string {
	var text strings.Builder
	text.WriteString(typeName)
	for _, segment := range path {
		if index, isIndex := segment.(int); isIndex {
			fmt.Fprintf(&text, "[%d]", index)
		} else {
			fmt.Fprintf(&text, ".%v", segment)
		}
	}
	return text.String()
}
