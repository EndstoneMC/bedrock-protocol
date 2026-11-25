package protocol

import (
	"math/bits"
	"slices"

	"github.com/EndstoneMC/bedrock-protocol/go/stream"
)

// Bitset holds a set of bit indices; a copy never sees the original's later changes.
type Bitset struct {
	words []uint64
}

func (b Bitset) Test(bit int) bool {
	return bit >= 0 && bit/64 < len(b.words) && b.words[bit/64]&(1<<(bit%64)) != 0
}

// Set adds the bit, ignoring a negative one.
func (b *Bitset) Set(bit int) {
	if bit < 0 {
		return
	}
	words := slices.Clone(b.words)
	if missing := bit/64 + 1 - len(words); missing > 0 {
		words = append(words, make([]uint64, missing)...)
	}
	words[bit/64] |= 1 << (bit % 64)
	b.words = words
}

func (b *Bitset) Clear(bit int) {
	if !b.Test(bit) {
		return
	}
	words := slices.Clone(b.words)
	words[bit/64] &^= 1 << (bit % 64)
	kept := len(words)
	for kept > 0 && words[kept-1] == 0 {
		kept--
	}
	if kept == 0 {
		words = nil
	}
	b.words = words[:kept]
}

// Len gives one past the highest set bit, or 0 when none is set.
func (b Bitset) Len() int {
	if len(b.words) == 0 {
		return 0
	}
	return (len(b.words)-1)*64 + bits.Len64(b.words[len(b.words)-1])
}

func readBitset(r *stream.Reader, width int) Bitset {
	var out Bitset
	for group := 0; ; group++ {
		groupBits := r.ReadUint8()
		if r.Failed() {
			return Bitset{}
		}
		for k := range 7 {
			if groupBits&(1<<k) != 0 {
				if group*7+k >= width {
					r.Fail(stream.ErrOutOfRange)
					return Bitset{}
				}
				out.Set(group*7 + k)
			}
		}
		if groupBits&0x80 == 0 {
			return out
		}
		if (group+1)*7 >= width {
			r.Fail(stream.ErrOutOfRange)
			return Bitset{}
		}
	}
}

func writeBitset(w *stream.Writer, value Bitset, width int) {
	if value.Len() > width {
		w.Fail(stream.ErrOutOfRange)
		return
	}
	groups := max(1, (value.Len()+6)/7)
	for group := range groups {
		var groupBits uint8
		for k := range 7 {
			if value.Test(group*7 + k) {
				groupBits |= 1 << k
			}
		}
		if group+1 < groups {
			groupBits |= 0x80
		}
		w.WriteUint8(groupBits)
	}
}
