// Package check holds the assertions the module's tests share.
package check

import (
	"encoding/hex"
	"reflect"
	"testing"
)

func Equal[T any](t testing.TB, got, want T) {
	t.Helper()
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("got %#v, want %#v", got, want)
	}
}

func Hex(t testing.TB, literal string) []byte {
	t.Helper()
	decoded, err := hex.DecodeString(literal)
	if err != nil {
		t.Fatalf("%s: %v", literal, err)
	}
	return decoded
}
