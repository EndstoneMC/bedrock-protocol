package dev.endstone.protocol;

import dev.endstone.protocol.DecodeException.Reason;
import io.netty.buffer.ByteBuf;
import java.util.Arrays;
import java.util.BitSet;
import java.util.Comparator;
import java.util.UUID;

/** The wire formats ByteBuf lacks, with every read checked before it touches the buffer. */
public final class Wire {

    /** Orders strings by the unsigned bytes writeStr writes. */
    public static final Comparator<String> STR_ORDER =
            (a, b) -> Arrays.compareUnsigned(utf8(a), utf8(b));

    private static final int MAX_INITIAL_CAPACITY = 65_536;
    private static final int ESCAPE_BASE = 0xDC00;

    private Wire() {}

    /** Throws TRUNCATED unless n bytes are readable. */
    public static void need(ByteBuf buf, int n) {
        if (buf.readableBytes() < n) {
            throw new DecodeException(Reason.TRUNCATED, buf.readerIndex());
        }
    }

    public static boolean readBool(ByteBuf buf) {
        need(buf, 1);
        return buf.readByte() != 0;
    }

    public static byte readInt8(ByteBuf buf) {
        need(buf, 1);
        return buf.readByte();
    }

    public static int readUint8(ByteBuf buf) {
        need(buf, 1);
        return buf.readUnsignedByte();
    }

    public static short readInt16(ByteBuf buf) {
        need(buf, 2);
        return buf.readShortLE();
    }

    public static int readUint16(ByteBuf buf) {
        need(buf, 2);
        return buf.readUnsignedShortLE();
    }

    public static int readInt32(ByteBuf buf) {
        need(buf, 4);
        return buf.readIntLE();
    }

    public static long readInt64(ByteBuf buf) {
        need(buf, 8);
        return buf.readLongLE();
    }

    public static float readFloat(ByteBuf buf) {
        need(buf, 4);
        return buf.readFloatLE();
    }

    public static double readDouble(ByteBuf buf) {
        need(buf, 8);
        return buf.readDoubleLE();
    }

    public static int readInt32Be(ByteBuf buf) {
        need(buf, 4);
        return buf.readInt();
    }

    /** Reads an unsigned varint of at most 5 bytes, as raw bits. */
    public static int readUvarint32(ByteBuf buf) {
        int value = 0;
        for (int n = 0; n < 5; n++) {
            int b = readUint8(buf);
            if (n == 4 && (b & 0x7F) > 0x0F) {
                throw new DecodeException(Reason.OUT_OF_RANGE, buf.readerIndex());
            }
            value |= (b & 0x7F) << (n * 7);
            if ((b & 0x80) == 0) {
                return value;
            }
        }
        throw new DecodeException(Reason.OUT_OF_RANGE, buf.readerIndex());
    }

    /** Reads an unsigned varint of at most 10 bytes, as raw bits. */
    public static long readUvarint64(ByteBuf buf) {
        long value = 0;
        for (int n = 0; n < 10; n++) {
            int b = readUint8(buf);
            if (n == 9 && (b & 0x7F) > 0x01) {
                throw new DecodeException(Reason.OUT_OF_RANGE, buf.readerIndex());
            }
            value |= (long) (b & 0x7F) << (n * 7);
            if ((b & 0x80) == 0) {
                return value;
            }
        }
        throw new DecodeException(Reason.OUT_OF_RANGE, buf.readerIndex());
    }

    public static int readVarint32(ByteBuf buf) {
        int bits = readUvarint32(buf);
        return (bits >>> 1) ^ -(bits & 1);
    }

    public static long readVarint64(ByteBuf buf) {
        long bits = readUvarint64(buf);
        return (bits >>> 1) ^ -(bits & 1);
    }

    public static void writeUvarint32(ByteBuf buf, int value) {
        while ((value & ~0x7F) != 0) {
            buf.writeByte((value & 0x7F) | 0x80);
            value >>>= 7;
        }
        buf.writeByte(value);
    }

    public static void writeUvarint64(ByteBuf buf, long value) {
        while ((value & ~0x7FL) != 0) {
            buf.writeByte((int) (value & 0x7F) | 0x80);
            value >>>= 7;
        }
        buf.writeByte((int) value);
    }

    public static void writeVarint32(ByteBuf buf, int value) {
        writeUvarint32(buf, (value << 1) ^ (value >> 31));
    }

    public static void writeVarint64(ByteBuf buf, long value) {
        writeUvarint64(buf, (value << 1) ^ (value >> 63));
    }

    /** Reads a uvarint32 count as an unsigned value. */
    public static long readUvarint32Count(ByteBuf buf) {
        return Integer.toUnsignedLong(readUvarint32(buf));
    }

    /** Reads a uint32 count as an unsigned value. */
    public static long readUint32Count(ByteBuf buf) {
        return Integer.toUnsignedLong(readInt32(buf));
    }

    /** Reads a uint16 count. */
    public static long readUint16Count(ByteBuf buf) {
        return readUint16(buf);
    }

    /** Reads a varint32 count; a negative one is OUT_OF_RANGE once charged. */
    public static long readVarint32Count(ByteBuf buf) {
        return readVarint32(buf);
    }

    /** Throws OUT_OF_RANGE for a negative count factor. */
    public static long countValue(ByteBuf buf, long value) {
        if (value < 0) {
            throw new DecodeException(Reason.OUT_OF_RANGE, buf.readerIndex());
        }
        return value;
    }

    /** Multiplies two count factors as unsigned 64-bit values; overflow is OUT_OF_RANGE. */
    public static long countProduct(ByteBuf buf, long a, long b) {
        countValue(buf, a);
        countValue(buf, b);
        if (Math.unsignedMultiplyHigh(a, b) != 0) {
            throw new DecodeException(Reason.OUT_OF_RANGE, buf.readerIndex());
        }
        return a * b;
    }

    /**
     * Charges count elements and, where width is above 0, count * width bytes; returns the count.
     */
    public static int charge(ByteBuf buf, DecodeBudget budget, long count, int width) {
        budget.chargeElements(count, buf.readerIndex());
        if (width > 0) {
            budget.chargeBytes(count * width, buf.readerIndex());
        }
        return (int) count;
    }

    /** Caps what a decoded collection reserves up front. */
    public static int initialCapacity(int count) {
        return Math.min(count, MAX_INITIAL_CAPACITY);
    }

    /** Throws TRUNCATED at the first element that does not fit, with its index in the path. */
    public static void needElements(ByteBuf buf, int count, int width) {
        if ((long) count * width > buf.readableBytes()) {
            int fits = buf.readableBytes() / width;
            throw new DecodeException(Reason.TRUNCATED, buf.readerIndex() + fits * width)
                    .prepend(fits);
        }
    }

    /** Reads a length-prefixed byte array. */
    public static byte[] readBytes(ByteBuf buf, DecodeBudget budget) {
        int length = readUvarint32(buf);
        if (Integer.compareUnsigned(length, buf.readableBytes()) > 0) {
            throw new DecodeException(Reason.TRUNCATED, buf.readerIndex());
        }
        budget.chargeBytes(length, buf.readerIndex());
        byte[] bytes = new byte[length];
        buf.readBytes(bytes);
        return bytes;
    }

    public static void writeBytes(ByteBuf buf, byte[] bytes) {
        writeUvarint32(buf, bytes.length);
        buf.writeBytes(bytes);
    }

    /**
     * Reads a length-prefixed string; bytes that are not well-formed UTF-8 become U+DC80..U+DCFF.
     */
    public static String readStr(ByteBuf buf, DecodeBudget budget) {
        byte[] bytes = readBytes(buf, budget);
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
    public static void writeStr(ByteBuf buf, String value) {
        writeBytes(buf, utf8(value));
    }

    public static UUID readUuid(ByteBuf buf) {
        return new UUID(readInt64(buf), readInt64(buf));
    }

    public static void writeUuid(ByteBuf buf, UUID value) {
        buf.writeLongLE(value.getMostSignificantBits());
        buf.writeLongLE(value.getLeastSignificantBits());
    }

    /** Reads base-128 groups into a bitset of the given width. */
    public static BitSet readBitset(ByteBuf buf, int width) {
        BitSet out = new BitSet();
        for (int group = 0; ; group++) {
            int b = readUint8(buf);
            for (int k = 0; k < 7; k++) {
                if ((b & (1 << k)) != 0) {
                    int bit = group * 7 + k;
                    if (bit >= width) {
                        throw new DecodeException(Reason.OUT_OF_RANGE, buf.readerIndex());
                    }
                    out.set(bit);
                }
            }
            if ((b & 0x80) == 0) {
                return out;
            }
            if ((group + 1) * 7 >= width) {
                throw new DecodeException(Reason.OUT_OF_RANGE, buf.readerIndex());
            }
        }
    }

    /** Writes base-128 groups up to the highest set bit, at least one. */
    public static void writeBitset(ByteBuf buf, BitSet value, int width, String field) {
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
    public static String foldAscii(String value) {
        char[] chars = value.toCharArray();
        for (int i = 0; i < chars.length; i++) {
            if (chars[i] >= 'A' && chars[i] <= 'Z') {
                chars[i] += 'a' - 'A';
            }
        }
        return new String(chars);
    }

    /** Runs a reader over the whole value; on failure the buffer is left where it was. */
    public static <T> T decode(ByteBuf buf, DecodeLimits limits, String type, Decoder<T> decoder) {
        int start = buf.readerIndex();
        int length = buf.readableBytes();
        try {
            T value = decoder.read(buf, new DecodeBudget(limits));
            if (buf.isReadable()) {
                throw new DecodeException(Reason.TRAILING_BYTES, buf.readerIndex());
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
