package protocol

import (
	"encoding/hex"
	"strings"
	"testing"

	"github.com/EndstoneMC/bedrock-protocol/go/internal/check"
)

func TestPre898AvailableCommandsEncodesEnumIndicesByEnumValueCount(t *testing.T) {
	cases := []struct {
		name       string
		valueCount int
		index      uint32
		count      string
		encoded    string
	}{
		{"one value uses uint8", 1, 0, "01", "00"},
		{"256 values use uint8", 256, 255, "8002", "ff"},
		{"257 values use uint16", 257, 256, "8102", "0001"},
		{"65536 values use uint16", 65536, 65535, "808004", "ffff"},
		{"65537 values use uint32", 65537, 65536, "818004", "00000100"},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			enums := []*AvailableCommandsPacket_EnumData{{Name: "e", Values: []uint32{c.index}}}
			encoded, err := V859.Encode(&AvailableCommandsPacket{EnumValues: make([]string, c.valueCount), Enums: enums})
			check.Equal(t, err, nil)
			check.Equal(t, hex.EncodeToString(encoded), c.count+strings.Repeat("00", c.valueCount+2)+"01016501"+c.encoded+"00000000")
			decoded := new(AvailableCommandsPacket)
			check.Equal(t, V859.Decode(encoded, decoded), nil)
			check.Equal(t, decoded.GetEnums(), enums)
		})
	}
}

func TestPre898AvailableCommandsRejectsAnEnumIndexOutsideTheChosenWidth(t *testing.T) {
	cases := []struct {
		name       string
		valueCount int
		index      uint32
	}{
		{"uint8", 256, 256},
		{"uint16", 65536, 65536},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			enums := []*AvailableCommandsPacket_EnumData{{Name: "e", Values: []uint32{c.index}}}
			_, err := V859.Encode(&AvailableCommandsPacket{EnumValues: make([]string, c.valueCount), Enums: enums})
			check.Equal(t, err.Error(), "AvailableCommandsPacket.enums[0].values[0]: out of range")
		})
	}
}
