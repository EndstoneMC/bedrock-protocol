package protocol

import (
	"errors"
	"testing"

	"github.com/EndstoneMC/bedrock-protocol/go/internal/check"
	"github.com/EndstoneMC/bedrock-protocol/go/stream"
)

func TestDecodeErrorMessageLocatesTheFailure(t *testing.T) {
	err := &DecodeError{Reason: stream.ErrTruncated, Type: "TextPacket", Path: []any{"messages", 2, "text"}, Offset: 5, Length: 9}
	check.Equal(t, err.Error(), "TextPacket.messages[2].text: truncated at byte 5 of 9")
}

func TestDecodeErrorIsItsReason(t *testing.T) {
	check.Equal(t, errors.Is(&DecodeError{Reason: stream.ErrTrailingBytes}, stream.ErrTrailingBytes), true)
}

func TestEncodeErrorMessageLocatesTheFailure(t *testing.T) {
	err := &EncodeError{Reason: stream.ErrOutOfRange, Type: "TextPacket", Path: []any{"messages", 2}}
	check.Equal(t, err.Error(), "TextPacket.messages[2]: out of range")
}

func TestEncodeErrorIsItsReason(t *testing.T) {
	check.Equal(t, errors.Is(&EncodeError{Reason: stream.ErrUnknownValue}, stream.ErrUnknownValue), true)
}

func TestEncodingNilIsNotATypeAtTheProtocol(t *testing.T) {
	_, err := V2259.Encode(nil)
	check.Equal(t, err.Error(), "<nil>: is not a type at protocol 2259")
}

func TestDecodingIntoNilIsNotATypeAtTheProtocol(t *testing.T) {
	err := V2259.Decode(nil, nil)
	check.Equal(t, err.Error(), "<nil>: is not a type at protocol 2259")
}

func TestEncodingAPacketAtAProtocolItLacksNamesItsType(t *testing.T) {
	_, err := V2259.Encode(new(TextPacket_v686))
	check.Equal(t, err.Error(), "protocol.TextPacket_v686: is not a type at protocol 2259")
}

func TestDecodingIntoAPacketAtAProtocolItLacksNamesItsType(t *testing.T) {
	err := V2259.Decode(nil, new(TextPacket_v686))
	check.Equal(t, err.Error(), "protocol.TextPacket_v686: is not a type at protocol 2259")
}

func TestDecodingIntoANilPacketNamesItsType(t *testing.T) {
	err := V2259.Decode(nil, (*TextPacket)(nil))
	check.Equal(t, err.Error(), "protocol.TextPacket: is nil")
}
