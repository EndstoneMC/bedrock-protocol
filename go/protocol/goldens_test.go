package protocol

import (
	"bytes"
	"cmp"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"maps"
	"math"
	"os"
	"path/filepath"
	"reflect"
	"regexp"
	"slices"
	"strconv"
	"strings"
	"testing"
	"unicode/utf8"

	"github.com/EndstoneMC/bedrock-protocol/go/datastore"
	"github.com/EndstoneMC/bedrock-protocol/go/internal/check"
	"github.com/EndstoneMC/bedrock-protocol/go/nbt"
	"github.com/EndstoneMC/bedrock-protocol/go/stream"
	"github.com/EndstoneMC/bedrock-protocol/go/uuid"
)

type caseEntry struct {
	key     string
	value   any
	literal bool
}

type caseObject []caseEntry

type caseFloat struct {
	value float64
	bits  int
}

type caseUnbound struct{}

type caser interface {
	caseAt(version int) any
}

type golden struct {
	name   string
	pinned Pinned
	packet func() Packet
	value  any
	bytes  []byte
}

var (
	colour    = regexp.MustCompile(`^#[0-9a-f]{8}$`)
	unquoted  = regexp.MustCompile(`^[a-zA-Z0-9._+-]+$`)
	nonFinite = map[string]float64{"NaN": math.NaN(), "Infinity": math.Inf(1), "-Infinity": math.Inf(-1)}
)

func caseClass(name string, value any) any {
	if object, isObject := value.(caseObject); isObject {
		return append(caseObject{{key: "__class__", value: name}}, object...)
	}
	return value
}

func caseString(text string) any {
	if utf8.ValidString(text) {
		return text
	}
	return caseBytes([]byte(text))
}

func caseBytes(raw []byte) any {
	var text strings.Builder
	for _, each := range raw {
		fmt.Fprintf(&text, `\x%02x`, each)
	}
	return text.String()
}

func caseFloat32(value float32) any {
	return caseFloat{float64(value), 32}
}

func caseFloat64(value float64) any {
	return caseFloat{value, 64}
}

func caseNumber[T any](number T, placed bool) any {
	if !placed {
		return caseUnbound{}
	}
	return number
}

func caseName(name string, placed bool) any {
	if !placed {
		return caseUnbound{}
	}
	return name
}

func caseList[T any](values []T, each func(T) any) any {
	listed := []any{}
	for _, value := range values {
		listed = append(listed, each(value))
	}
	return listed
}

func caseMap[K cmp.Ordered, V any](entries map[K]V, key func(K) any, value func(V) any) any {
	keys := slices.Sorted(maps.Keys(entries))
	if _, named := any(*new(K)).(string); named {
		object := caseObject{}
		for _, each := range keys {
			object = append(object, caseEntry{key: any(each).(string), value: value(entries[each])})
		}
		return object
	}
	pairs := []any{}
	for _, each := range keys {
		pairs = append(pairs, caseObject{{key: "key", value: key(each)}, {key: "value", value: value(entries[each])}})
	}
	return pairs
}

func caseBitset(value Bitset) any {
	if value.Len() == 0 {
		return "0b0"
	}
	bits := []byte("0b")
	for bit := value.Len() - 1; bit >= 0; bit-- {
		bits = append(bits, '0'+numberOf[byte](value.Test(bit)))
	}
	return string(bits)
}

func caseUUID(value uuid.UUID) any {
	return value.String()
}

func caseCompoundTag(value nbt.CompoundTag) any {
	return snbt(value)
}

func caseCompoundTagData(value nbt.CompoundTagData) any {
	return snbt(nbt.CompoundTag(value))
}

func caseDynamicValue(value datastore.DynamicValue) any {
	switch value := value.(type) {
	case datastore.Bool:
		return bool(value)
	case datastore.Integer:
		return int64(value)
	case datastore.Number:
		return caseFloat64(float64(value))
	case datastore.String:
		return string(value)
	case datastore.Array:
		return caseList(value, caseDynamicValue)
	case datastore.Object:
		return caseMap(value, func(key string) any { return key }, caseDynamicValue)
	}
	return nil
}

func snbt(tag nbt.Tag) string {
	switch tag := tag.(type) {
	case nbt.ByteTag:
		return strconv.Itoa(int(int8(tag))) + "b"
	case nbt.ShortTag:
		return strconv.Itoa(int(tag)) + "s"
	case nbt.IntTag:
		return strconv.Itoa(int(tag))
	case nbt.Int64Tag:
		return strconv.FormatInt(int64(tag), 10) + "L"
	case nbt.FloatTag:
		return pythonFloat(shortestFloat32(float32(tag))) + "f"
	case nbt.DoubleTag:
		return pythonFloat(float64(tag)) + "d"
	case nbt.StringTag:
		return quoted(string(tag))
	case nbt.ByteArrayTag:
		elements := []string{}
		for _, each := range tag {
			elements = append(elements, strconv.Itoa(int(int8(each)))+"B")
		}
		return "[B;" + strings.Join(elements, ",") + "]"
	case nbt.IntArrayTag:
		elements := []string{}
		for _, each := range tag {
			elements = append(elements, strconv.Itoa(int(each)))
		}
		return "[I;" + strings.Join(elements, ",") + "]"
	case nbt.ListTag:
		elements := []string{}
		for _, each := range tag.Elements {
			elements = append(elements, snbt(each))
		}
		return "[" + strings.Join(elements, ",") + "]"
	case nbt.CompoundTag:
		entries := []string{}
		for _, key := range slices.Sorted(maps.Keys(tag)) {
			name := key
			if !unquoted.MatchString(key) {
				name = quoted(key)
			}
			entries = append(entries, name+":"+snbt(tag[key]))
		}
		return "{" + strings.Join(entries, ",") + "}"
	}
	return fmt.Sprintf("%T", tag)
}

func quoted(text string) string {
	quote := `"`
	if first := strings.IndexAny(text, `"'`); first >= 0 && text[first] == '"' {
		quote = "'"
	}
	text = strings.ReplaceAll(text, `\`, `\\`)
	return quote + strings.ReplaceAll(text, quote, `\`+quote) + quote
}

func shortestFloat32(value float32) float64 {
	for digits := 1; digits < 10; digits++ {
		parsed, _ := strconv.ParseFloat(strconv.FormatFloat(float64(value), 'g', digits, 32), 64)
		if float32(parsed) == value {
			return parsed
		}
	}
	return float64(value)
}

func pythonFloat(value float64) string {
	switch {
	case math.IsNaN(value):
		return "nan"
	case math.IsInf(value, 1):
		return "inf"
	case math.IsInf(value, -1):
		return "-inf"
	}
	scientific := strconv.FormatFloat(value, 'e', -1, 64)
	exponent, _ := strconv.Atoi(scientific[strings.IndexByte(scientific, 'e')+1:])
	if exponent < -4 || exponent >= 16 {
		return scientific
	}
	fixed := strconv.FormatFloat(value, 'f', -1, 64)
	if !strings.Contains(fixed, ".") {
		fixed += ".0"
	}
	return fixed
}

func mismatch(want, got any, path string) string {
	same := false
	switch got := got.(type) {
	case caseObject:
		object, isObject := want.(map[string]any)
		if text, isText := want.(string); isText && colour.MatchString(text) {
			pairs, _ := hex.DecodeString(text[1:])
			if len(pairs) != len(got) {
				break
			}
			object, isObject = map[string]any{}, true
			for index, entry := range got {
				number := strconv.Itoa(int(pairs[index]))
				if _, channel := entry.value.(caseFloat); channel {
					number = strconv.FormatFloat(float64(float32(pairs[(index+1)%len(pairs)])/255), 'g', -1, 32)
				}
				object[entry.key] = json.Number(number)
			}
		}
		if !isObject {
			break
		}
		found := 0
		for _, entry := range got {
			value, present := object[entry.key]
			if !present && entry.literal {
				continue
			}
			if !present {
				return fmt.Sprintf("%s.%s: missing from the case", path, entry.key)
			}
			found++
			if inner := mismatch(value, entry.value, path+"."+entry.key); inner != "" {
				return inner
			}
		}
		if found != len(object) {
			return fmt.Sprintf("%s: the case holds keys the packet lacks: %v", path, slices.Sorted(maps.Keys(object)))
		}
		return ""
	case []any:
		listed, isList := want.([]any)
		if !isList || len(listed) != len(got) {
			break
		}
		for index := range got {
			if inner := mismatch(listed[index], got[index], fmt.Sprintf("%s[%d]", path, index)); inner != "" {
				return inner
			}
		}
		return ""
	case caseFloat:
		expected, named := nonFinite[fmt.Sprint(want)]
		if number, isNumber := want.(json.Number); isNumber {
			parsed, err := strconv.ParseFloat(number.String(), 64)
			expected, named = parsed, err == nil
		}
		if got.bits == 32 {
			expected = float64(float32(expected))
		}
		same = named && (expected == got.value || (math.IsNaN(expected) && math.IsNaN(got.value)))
	case string, bool, nil:
		same = want == got
	case caseUnbound:
		return path + ": no number or name at this protocol"
	default:
		number, isNumber := want.(json.Number)
		value := reflect.ValueOf(got)
		spelled := fmt.Sprint(got)
		if value.CanInt() {
			spelled = strconv.FormatInt(value.Int(), 10)
		} else if value.CanUint() {
			spelled = strconv.FormatUint(value.Uint(), 10)
		}
		same = isNumber && number.String() == spelled
	}
	if same {
		return ""
	}
	return fmt.Sprintf("%s: case %v, decoded %#v", path, want, got)
}

func goldens(t *testing.T) []golden {
	t.Helper()
	paths, err := filepath.Glob(filepath.Join("..", "..", "tests", "goldens", "v*", "*.json"))
	check.Equal(t, err, nil)
	var found []golden
	for _, path := range paths {
		folder := filepath.Base(filepath.Dir(path))
		version, err := strconv.Atoi(strings.TrimPrefix(folder, "v"))
		check.Equal(t, err, nil)
		pinned := slices.IndexFunc(casePins, func(pin Pinned) bool { return pin.Version() == version })
		if pinned < 0 {
			t.Fatalf("%s: protocol %d is not modelled", path, version)
		}
		stem := strings.TrimSuffix(filepath.Base(path), ".json")
		prefix, _, _ := strings.Cut(stem, "_")
		id, err := strconv.Atoi(prefix)
		check.Equal(t, err, nil)
		var held []func() Packet
		for _, packet := range casePackets {
			if each := packet(); each.PacketId() == id && each.encodeAt(new(stream.Writer), version) {
				held = append(held, packet)
			}
		}
		if len(held) != 1 {
			t.Fatalf("%s: %d generated packets have id %d at protocol %d", path, len(held), id, version)
		}
		data, err := os.ReadFile(path)
		check.Equal(t, err, nil)
		decoder := json.NewDecoder(bytes.NewReader(data))
		decoder.UseNumber()
		var cases []struct {
			ID    string
			Value any
			Bytes string
		}
		check.Equal(t, decoder.Decode(&cases), nil)
		for _, each := range cases {
			encoded, err := hex.DecodeString(each.Bytes)
			check.Equal(t, err, nil)
			name := folder + "/" + stem + "/" + each.ID
			found = append(found, golden{name, casePins[pinned], held[0], each.Value, encoded})
		}
	}
	return found
}

func TestAGoldenDecodesToItsValue(t *testing.T) {
	for _, golden := range goldens(t) {
		t.Run(golden.name, func(t *testing.T) {
			packet := golden.packet()
			check.Equal(t, golden.pinned.Decode(golden.bytes, packet), nil)
			check.Equal(t, mismatch(golden.value, packet.(caser).caseAt(golden.pinned.Version()), ""), "")
		})
	}
}

func TestAGoldenEncodesToItsBytes(t *testing.T) {
	for _, golden := range goldens(t) {
		t.Run(golden.name, func(t *testing.T) {
			packet := golden.packet()
			check.Equal(t, golden.pinned.Decode(golden.bytes, packet), nil)
			encoded, err := golden.pinned.Encode(packet)
			check.Equal(t, err, nil)
			check.Equal(t, hex.EncodeToString(encoded), hex.EncodeToString(golden.bytes))
		})
	}
}
