// Package uuid holds the mce::UUID the protocol encodes as two little-endian 64-bit halves.
package uuid

import (
	"encoding/binary"
	"encoding/hex"

	"github.com/EndstoneMC/bedrock-protocol/go/stream"
)

// UUID holds the 16 bytes in RFC 4122 order, most significant first.
type UUID [16]byte

// String spells the UUID as lower-case 8-4-4-4-12 hex.
func (u UUID) String() string {
	text := make([]byte, 36)
	hex.Encode(text[0:8], u[0:4])
	text[8] = '-'
	hex.Encode(text[9:13], u[4:6])
	text[13] = '-'
	hex.Encode(text[14:18], u[6:8])
	text[18] = '-'
	hex.Encode(text[19:23], u[8:10])
	text[23] = '-'
	hex.Encode(text[24:], u[10:])
	return string(text)
}

// ReadUUID reads the most significant half, then the least, each little-endian.
func ReadUUID(r *stream.Reader) UUID {
	var u UUID
	binary.BigEndian.PutUint64(u[:8], r.ReadUint64())
	binary.BigEndian.PutUint64(u[8:], r.ReadUint64())
	return u
}

// WriteUUID writes the most significant half, then the least, each little-endian.
func WriteUUID(w *stream.Writer, u UUID) {
	w.WriteUint64(binary.BigEndian.Uint64(u[:8]))
	w.WriteUint64(binary.BigEndian.Uint64(u[8:]))
}
