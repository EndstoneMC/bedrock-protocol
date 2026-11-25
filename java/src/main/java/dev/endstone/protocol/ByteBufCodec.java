package dev.endstone.protocol;

import dev.endstone.protocol.datastore.DynamicValue;
import dev.endstone.protocol.nbt.CompoundTag;
import dev.endstone.protocol.nbt.CompoundTagData;
import dev.endstone.protocol.nbt.Tag;
import dev.endstone.protocol.nbt.TagType;
import dev.endstone.protocol.nbt.TagTypes;
import io.netty.buffer.ByteBuf;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.BitSet;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.jetbrains.annotations.NotNull;

/** The encodings ByteBuf lacks, with every read checked before it touches the buffer. */
public final class ByteBufCodec {

    /** Orders strings by the unsigned bytes writeString writes. */
    public static final @NotNull Comparator<String> STR_ORDER =
            (a, b) -> Arrays.compareUnsigned(utf8(a), utf8(b));

    private static final int MAX_INITIAL_CAPACITY = 65_536;
    private static final int ESCAPE_BASE = 0xDC00;

    private ByteBufCodec() {}

    /** Throws DecodeException.truncated unless n bytes are readable. */
    public static void need(@NotNull ByteBuf buf, int n) {
        if (buf.readableBytes() < n) {
            throw DecodeException.truncated(buf.readerIndex());
        }
    }

    public static boolean readBoolean(@NotNull ByteBuf buf) {
        need(buf, 1);
        return buf.readByte() != 0;
    }

    public static byte readByte(@NotNull ByteBuf buf) {
        need(buf, 1);
        return buf.readByte();
    }

    public static int readUnsignedByte(@NotNull ByteBuf buf) {
        need(buf, 1);
        return buf.readUnsignedByte();
    }

    public static short readShortLE(@NotNull ByteBuf buf) {
        need(buf, 2);
        return buf.readShortLE();
    }

    public static int readUnsignedShortLE(@NotNull ByteBuf buf) {
        need(buf, 2);
        return buf.readUnsignedShortLE();
    }

    public static int readIntLE(@NotNull ByteBuf buf) {
        need(buf, 4);
        return buf.readIntLE();
    }

    public static long readLongLE(@NotNull ByteBuf buf) {
        need(buf, 8);
        return buf.readLongLE();
    }

    public static float readFloatLE(@NotNull ByteBuf buf) {
        need(buf, 4);
        return buf.readFloatLE();
    }

    public static double readDoubleLE(@NotNull ByteBuf buf) {
        need(buf, 8);
        return buf.readDoubleLE();
    }

    public static int readInt(@NotNull ByteBuf buf) {
        need(buf, 4);
        return buf.readInt();
    }

    /** Reads an unsigned varint of at most 5 bytes, as raw bits. */
    public static int readUnsignedVarInt(@NotNull ByteBuf buf) {
        int value = 0;
        for (int n = 0; n < 5; n++) {
            int b = readUnsignedByte(buf);
            if (n == 4 && (b & 0x7F) > 0x0F) {
                throw DecodeException.outOfRange(buf.readerIndex());
            }
            value |= (b & 0x7F) << (n * 7);
            if ((b & 0x80) == 0) {
                return value;
            }
        }
        throw DecodeException.outOfRange(buf.readerIndex());
    }

    /** Reads an unsigned varint of at most 10 bytes, as raw bits. */
    public static long readUnsignedVarLong(@NotNull ByteBuf buf) {
        long value = 0;
        for (int n = 0; n < 10; n++) {
            int b = readUnsignedByte(buf);
            if (n == 9 && (b & 0x7F) > 0x01) {
                throw DecodeException.outOfRange(buf.readerIndex());
            }
            value |= (long) (b & 0x7F) << (n * 7);
            if ((b & 0x80) == 0) {
                return value;
            }
        }
        throw DecodeException.outOfRange(buf.readerIndex());
    }

    public static int readVarInt(@NotNull ByteBuf buf) {
        int bits = readUnsignedVarInt(buf);
        return (bits >>> 1) ^ -(bits & 1);
    }

    public static long readVarLong(@NotNull ByteBuf buf) {
        long bits = readUnsignedVarLong(buf);
        return (bits >>> 1) ^ -(bits & 1);
    }

    public static void writeUnsignedVarInt(@NotNull ByteBuf buf, int value) {
        while ((value & ~0x7F) != 0) {
            buf.writeByte((value & 0x7F) | 0x80);
            value >>>= 7;
        }
        buf.writeByte(value);
    }

    public static void writeUnsignedVarLong(@NotNull ByteBuf buf, long value) {
        while ((value & ~0x7FL) != 0) {
            buf.writeByte((int) (value & 0x7F) | 0x80);
            value >>>= 7;
        }
        buf.writeByte((int) value);
    }

    public static void writeVarInt(@NotNull ByteBuf buf, int value) {
        writeUnsignedVarInt(buf, (value << 1) ^ (value >> 31));
    }

    public static void writeVarLong(@NotNull ByteBuf buf, long value) {
        writeUnsignedVarLong(buf, (value << 1) ^ (value >> 63));
    }

    /** Reads a uvarint32 count as an unsigned value. */
    public static long readUvarint32Count(@NotNull ByteBuf buf) {
        return Integer.toUnsignedLong(readUnsignedVarInt(buf));
    }

    /** Reads a uint32 count as an unsigned value. */
    public static long readUint32Count(@NotNull ByteBuf buf) {
        return Integer.toUnsignedLong(readIntLE(buf));
    }

    /** Reads a uint16 count. */
    public static long readUint16Count(@NotNull ByteBuf buf) {
        return readUnsignedShortLE(buf);
    }

    /** Reads a varint32 count as a signed value. */
    public static long readVarint32Count(@NotNull ByteBuf buf) {
        return readVarInt(buf);
    }

    /** Throws DecodeException.outOfRange for a negative count factor. */
    public static long countValue(@NotNull ByteBuf buf, long value) {
        if (value < 0) {
            throw DecodeException.outOfRange(buf.readerIndex());
        }
        return value;
    }

    /**
     * Multiplies two count factors as unsigned 64-bit values; overflow is
     * DecodeException.outOfRange.
     */
    public static long countProduct(@NotNull ByteBuf buf, long a, long b) {
        countValue(buf, a);
        countValue(buf, b);
        if (Math.unsignedMultiplyHigh(a, b) != 0) {
            throw DecodeException.outOfRange(buf.readerIndex());
        }
        return a * b;
    }

    /**
     * Narrows a count to an int; a negative one or one past Integer.MAX_VALUE is
     * DecodeException.outOfRange.
     */
    public static int toCount(@NotNull ByteBuf buf, long count) {
        if (countValue(buf, count) > Integer.MAX_VALUE) {
            throw DecodeException.outOfRange(buf.readerIndex());
        }
        return (int) count;
    }

    /** Caps what a decoded collection reserves up front. */
    public static int initialCapacity(int count) {
        return Math.min(count, MAX_INITIAL_CAPACITY);
    }

    /**
     * Throws DecodeException.truncated at the first element that does not fit, with its index in
     * the path.
     */
    public static void needElements(@NotNull ByteBuf buf, int count, int width) {
        if ((long) count * width > buf.readableBytes()) {
            int fits = buf.readableBytes() / width;
            throw DecodeException.truncated(buf.readerIndex() + fits * width).prepend(fits);
        }
    }

    /** Reads a length-prefixed byte array. */
    public static byte @NotNull [] readByteArray(@NotNull ByteBuf buf) {
        int length = readUnsignedVarInt(buf);
        if (Integer.compareUnsigned(length, buf.readableBytes()) > 0) {
            throw DecodeException.truncated(buf.readerIndex());
        }
        byte[] bytes = new byte[length];
        buf.readBytes(bytes);
        return bytes;
    }

    public static void writeByteArray(@NotNull ByteBuf buf, byte @NotNull [] bytes) {
        writeUnsignedVarInt(buf, bytes.length);
        buf.writeBytes(bytes);
    }

    /**
     * Reads a length-prefixed string; bytes that are not well-formed UTF-8 become U+DC80..U+DCFF.
     */
    public static @NotNull String readString(@NotNull ByteBuf buf) {
        byte[] bytes = readByteArray(buf);
        StringBuilder out = new StringBuilder(bytes.length);
        int i = 0;
        while (i < bytes.length) {
            int lead = bytes[i] & 0xFF;
            if (lead < 0x80) {
                out.append((char) lead);
                i++;
                continue;
            }
            int size = 0;
            int low = 0x80;
            int high = 0xBF;
            if (lead >= 0xC2 && lead <= 0xDF) {
                size = 2;
            } else if (lead >= 0xE0 && lead <= 0xEF) {
                size = 3;
                if (lead == 0xE0) {
                    low = 0xA0;
                } else if (lead == 0xED) {
                    high = 0x9F;
                }
            } else if (lead >= 0xF0 && lead <= 0xF4) {
                size = 4;
                if (lead == 0xF0) {
                    low = 0x90;
                } else if (lead == 0xF4) {
                    high = 0x8F;
                }
            }
            boolean valid = size > 0 && i + size <= bytes.length;
            for (int k = 1; valid && k < size; k++) {
                int next = bytes[i + k] & 0xFF;
                valid = next >= (k == 1 ? low : 0x80) && next <= (k == 1 ? high : 0xBF);
            }
            if (!valid) {
                out.append((char) (ESCAPE_BASE + lead));
                i++;
            } else {
                int codePoint = lead & (0xFF >> (size + 1));
                for (int k = 1; k < size; k++) {
                    codePoint = codePoint << 6 | bytes[i + k] & 0x3F;
                }
                out.appendCodePoint(codePoint);
                i += size;
            }
        }
        return out.toString();
    }

    /**
     * Writes a string; throws IllegalArgumentException for an unpaired surrogate outside
     * U+DC80..U+DCFF.
     */
    public static void writeString(@NotNull ByteBuf buf, @NotNull String value) {
        writeByteArray(buf, utf8(value));
    }

    public static @NotNull UUID readUuid(@NotNull ByteBuf buf) {
        return new UUID(readLongLE(buf), readLongLE(buf));
    }

    public static void writeUuid(@NotNull ByteBuf buf, @NotNull UUID value) {
        buf.writeLongLE(value.getMostSignificantBits());
        buf.writeLongLE(value.getLeastSignificantBits());
    }

    /** Reads base-128 groups into a bitset of the given width. */
    public static @NotNull BitSet readBitSet(@NotNull ByteBuf buf, int width) {
        BitSet out = new BitSet();
        for (int group = 0; ; group++) {
            int b = readUnsignedByte(buf);
            for (int k = 0; k < 7; k++) {
                if ((b & (1 << k)) != 0) {
                    int bit = group * 7 + k;
                    if (bit >= width) {
                        throw DecodeException.outOfRange(buf.readerIndex());
                    }
                    out.set(bit);
                }
            }
            if ((b & 0x80) == 0) {
                return out;
            }
            if ((group + 1) * 7 >= width) {
                throw DecodeException.outOfRange(buf.readerIndex());
            }
        }
    }

    /** Writes base-128 groups up to the highest set bit, at least one. */
    public static void writeBitSet(
            @NotNull ByteBuf buf, @NotNull BitSet value, int width, @NotNull String field) {
        if (value.length() > width) {
            throw new IllegalStateException(
                    field + ": bit " + (value.length() - 1) + " is past the width " + width);
        }
        int groups = Math.max(1, (value.length() + 6) / 7);
        for (int group = 0; group < groups; group++) {
            int b = 0;
            for (int k = 0; k < 7; k++) {
                if (value.get(group * 7 + k)) {
                    b |= 1 << k;
                }
            }
            buf.writeByte(group + 1 < groups ? b | 0x80 : b);
        }
    }

    /** Lowercases A-Z only. */
    public static @NotNull String foldAscii(@NotNull String value) {
        char[] chars = value.toCharArray();
        for (int i = 0; i < chars.length; i++) {
            if (chars[i] >= 'A' && chars[i] <= 'Z') {
                chars[i] += 'a' - 'A';
            }
        }
        return new String(chars);
    }

    /** Reads a root compound and drops its name. */
    public static @NotNull CompoundTag readCompoundTag(@NotNull ByteBuf buf) {
        int id = readUnsignedByte(buf);
        TagType<?> type = TagTypes.getType(id);
        if (type == null || id == Tag.TAG_END) {
            throw DecodeException.unknownValue(buf.readerIndex());
        }
        readString(buf);
        if (!(type.decode(buf) instanceof CompoundTag tag)) {
            throw DecodeException.unknownValue(buf.readerIndex());
        }
        return tag;
    }

    /** Writes a root compound: type id, empty name, payload. */
    public static void writeCompoundTag(@NotNull ByteBuf buf, @NotNull CompoundTag tag) {
        buf.writeByte(Tag.TAG_COMPOUND);
        writeString(buf, "");
        tag.encode(buf);
    }

    public static @NotNull CompoundTagData readCompoundTagData(@NotNull ByteBuf buf) {
        return new CompoundTagData(CompoundTag.TYPE.decode(buf));
    }

    public static void writeCompoundTagData(@NotNull ByteBuf buf, @NotNull CompoundTagData value) {
        value.tag().encode(buf);
    }

    public static @NotNull DynamicValue readDynamicValue(@NotNull ByteBuf buf) {
        return switch (readIntLE(buf)) {
            case 0 -> new DynamicValue.NullValue();
            case 1 -> new DynamicValue.BoolValue(readBoolean(buf));
            case 2 -> new DynamicValue.IntegerValue(readLongLE(buf));
            case 3 -> new DynamicValue.NumberValue(readDoubleLE(buf));
            case 4 -> new DynamicValue.StringValue(readString(buf));
            case 5 -> {
                int count = toCount(buf, readUvarint32Count(buf));
                List<DynamicValue> values = new ArrayList<>(initialCapacity(count));
                for (int i = 0; i < count; i++) {
                    values.add(readDynamicValue(buf));
                }
                yield new DynamicValue.ArrayValue(values);
            }
            case 6 -> {
                int count = toCount(buf, readUvarint32Count(buf));
                Map<String, DynamicValue> entries = new HashMap<>();
                for (int i = 0; i < count; i++) {
                    String key = readString(buf);
                    entries.putIfAbsent(key, readDynamicValue(buf));
                }
                yield new DynamicValue.ObjectValue(entries);
            }
            default -> throw DecodeException.unknownValue(buf.readerIndex());
        };
    }

    public static void writeDynamicValue(@NotNull ByteBuf buf, @NotNull DynamicValue value) {
        switch (value) {
            case DynamicValue.NullValue v -> buf.writeIntLE(0);
            case DynamicValue.BoolValue v -> {
                buf.writeIntLE(1);
                buf.writeBoolean(v.value());
            }
            case DynamicValue.IntegerValue v -> {
                buf.writeIntLE(2);
                buf.writeLongLE(v.value());
            }
            case DynamicValue.NumberValue v -> {
                buf.writeIntLE(3);
                buf.writeDoubleLE(v.value());
            }
            case DynamicValue.StringValue v -> {
                buf.writeIntLE(4);
                writeString(buf, v.value());
            }
            case DynamicValue.ArrayValue v -> {
                buf.writeIntLE(5);
                writeUnsignedVarInt(buf, v.values().size());
                for (DynamicValue element : v.values()) {
                    writeDynamicValue(buf, element);
                }
            }
            case DynamicValue.ObjectValue v -> {
                buf.writeIntLE(6);
                writeUnsignedVarInt(buf, v.entries().size());
                for (Map.Entry<String, DynamicValue> entry : v.entries().entrySet()) {
                    writeString(buf, entry.getKey());
                    writeDynamicValue(buf, entry.getValue());
                }
            }
        }
    }

    /** Runs a reader over the whole value; on failure the buffer is left where it was. */
    public static <T> T decode(
            @NotNull ByteBuf buf, @NotNull String type, @NotNull Decoder<T> decoder) {
        int start = buf.readerIndex();
        int length = buf.readableBytes();
        try {
            T value = decoder.decode(buf);
            if (buf.isReadable()) {
                throw DecodeException.trailingBytes(buf.readerIndex());
            }
            return value;
        } catch (DecodeException e) {
            e.stamp(type, e.getOffset() - start, length);
            buf.readerIndex(start);
            throw e;
        }
    }

    private static byte[] utf8(String value) {
        int n = value.length();
        byte[] out = new byte[n * 3];
        int size = 0;
        for (int i = 0; i < n; i++) {
            char c = value.charAt(i);
            if (c < 0x80) {
                out[size++] = (byte) c;
            } else if (c < 0x800) {
                out[size++] = (byte) (0xC0 | c >> 6);
                out[size++] = (byte) (0x80 | c & 0x3F);
            } else if (Character.isHighSurrogate(c)
                    && i + 1 < n
                    && Character.isLowSurrogate(value.charAt(i + 1))) {
                int cp = Character.toCodePoint(c, value.charAt(++i));
                out[size++] = (byte) (0xF0 | cp >> 18);
                out[size++] = (byte) (0x80 | cp >> 12 & 0x3F);
                out[size++] = (byte) (0x80 | cp >> 6 & 0x3F);
                out[size++] = (byte) (0x80 | cp & 0x3F);
            } else if (c >= 0xDC80 && c <= 0xDCFF) {
                out[size++] = (byte) (c - ESCAPE_BASE);
            } else if (Character.isSurrogate(c)) {
                throw new IllegalArgumentException(
                        "string has an unpaired surrogate at index " + i);
            } else {
                out[size++] = (byte) (0xE0 | c >> 12);
                out[size++] = (byte) (0x80 | c >> 6 & 0x3F);
                out[size++] = (byte) (0x80 | c & 0x3F);
            }
        }
        return Arrays.copyOf(out, size);
    }
}
