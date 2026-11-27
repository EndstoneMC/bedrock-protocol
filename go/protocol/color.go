package protocol

import (
	"math"
	"strconv"
	"strings"
)

// packColor packs four channels in [0, 1] a byte each, the first in the highest, failing on one outside it.
func packColor(a, r, g, b float32) (uint32, bool) {
	var packed uint32
	for _, channel := range [...]float32{a, r, g, b} {
		if !(channel >= 0 && channel <= 1) {
			return 0, false
		}
		packed = packed<<8 | uint32(channel*255)
	}
	return packed, true
}

func unpackColor(packed uint32) (a, r, g, b float32) {
	return float32(packed>>24) / 255, float32(packed>>16&0xFF) / 255, float32(packed>>8&0xFF) / 255, float32(packed&0xFF) / 255
}

func formatColor(packed uint32) string {
	return "#" + strconv.FormatUint(uint64(packed), 16)
}

// parseColor reads text past its first byte as C's strtoull in base 16 does, saturating one in [2^32, 2^64 - 2^32).
func parseColor(text string) uint32 {
	if text == "" {
		return 0
	}
	rest := strings.TrimLeft(text[1:], " \t\n\v\f\r")
	negative := strings.HasPrefix(rest, "-")
	if negative || strings.HasPrefix(rest, "+") {
		rest = rest[1:]
	}
	if len(rest) > 1 && rest[0] == '0' && (rest[1] == 'x' || rest[1] == 'X') {
		rest = rest[2:]
	}
	end := 0
	for end < len(rest) && strings.IndexByte("0123456789abcdefABCDEF", rest[end]) >= 0 {
		end++
	}
	parsed, err := strconv.ParseUint(rest[:end], 16, 64)
	if negative && err == nil {
		parsed = -parsed
	}
	if parsed > math.MaxUint32 && parsed < 0xFFFFFFFF00000000 {
		return math.MaxUint32
	}
	return uint32(parsed)
}
