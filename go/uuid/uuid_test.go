package uuid_test

import (
	"testing"

	"github.com/EndstoneMC/bedrock-protocol/go/internal/check"
	"github.com/EndstoneMC/bedrock-protocol/go/stream"
	"github.com/EndstoneMC/bedrock-protocol/go/uuid"
)

var sequential = uuid.UUID{1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16}

func TestUUIDReadsTwoLittleEndianHalvesMostSignificantFirst(t *testing.T) {
	check.Equal(t, uuid.ReadUUID(stream.NewReader(check.Hex(t, "0807060504030201100f0e0d0c0b0a09"))), sequential)
}

func TestUUIDWritesTwoLittleEndianHalvesMostSignificantFirst(t *testing.T) {
	var w stream.Writer
	uuid.WriteUUID(&w, sequential)
	check.Equal(t, w.Bytes(), check.Hex(t, "0807060504030201100f0e0d0c0b0a09"))
}

func TestUUIDShortOfItsSecondHalfIsTruncatedAtTheSecondHalf(t *testing.T) {
	r := stream.NewReader(check.Hex(t, "0807060504030201100f0e0d0c0b0a"))
	uuid.ReadUUID(r)
	reason, _, offset := r.Failure()
	check.Equal(t, []any{reason, offset}, []any{stream.ErrTruncated, 8})
}

func TestUUIDStringIsLowerCaseHyphenatedHex(t *testing.T) {
	check.Equal(t, sequential.String(), "01020304-0506-0708-090a-0b0c0d0e0f10")
}
