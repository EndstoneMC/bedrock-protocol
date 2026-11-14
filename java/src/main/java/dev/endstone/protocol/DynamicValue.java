package dev.endstone.protocol;

import io.netty.buffer.ByteBuf;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.TreeMap;
import org.jetbrains.annotations.NotNull;

/** A data store value: null, bool, int64, double, string, array or object. */
public sealed interface DynamicValue {
    record NullValue() implements DynamicValue {}

    record BoolValue(boolean value) implements DynamicValue {}

    record IntegerValue(long value) implements DynamicValue {}

    record NumberValue(double value) implements DynamicValue {}

    record StringValue(@NotNull String value) implements DynamicValue {
        public StringValue {
            Objects.requireNonNull(value, "StringValue.value");
        }
    }

    record ArrayValue(@NotNull List<DynamicValue> values) implements DynamicValue {
        public ArrayValue {
            values = List.copyOf(values);
        }
    }

    /** An object; its entries are kept, and written, in the unsigned byte order of their keys. */
    record ObjectValue(@NotNull Map<String, DynamicValue> entries) implements DynamicValue {
        public ObjectValue {
            TreeMap<String, DynamicValue> sorted = new TreeMap<>(ByteBufCodec.STR_ORDER);
            for (Map.Entry<String, DynamicValue> entry : entries.entrySet()) {
                sorted.put(
                        Objects.requireNonNull(entry.getKey(), "ObjectValue.entries key"),
                        Objects.requireNonNull(entry.getValue(), "ObjectValue.entries value"));
            }
            entries = Collections.unmodifiableMap(sorted);
        }
    }

    default void encode(@NotNull ByteBuf buf) {
        switch (this) {
            case NullValue v -> buf.writeIntLE(0);
            case BoolValue v -> {
                buf.writeIntLE(1);
                buf.writeBoolean(v.value());
            }
            case IntegerValue v -> {
                buf.writeIntLE(2);
                buf.writeLongLE(v.value());
            }
            case NumberValue v -> {
                buf.writeIntLE(3);
                buf.writeDoubleLE(v.value());
            }
            case StringValue v -> {
                buf.writeIntLE(4);
                ByteBufCodec.writeString(buf, v.value());
            }
            case ArrayValue v -> {
                buf.writeIntLE(5);
                ByteBufCodec.writeUnsignedVarInt(buf, v.values().size());
                for (DynamicValue element : v.values()) {
                    element.encode(buf);
                }
            }
            case ObjectValue v -> {
                buf.writeIntLE(6);
                ByteBufCodec.writeUnsignedVarInt(buf, v.entries().size());
                for (Map.Entry<String, DynamicValue> entry : v.entries().entrySet()) {
                    ByteBufCodec.writeString(buf, entry.getKey());
                    entry.getValue().encode(buf);
                }
            }
        }
    }

    static @NotNull DynamicValue decode(@NotNull ByteBuf buf) {
        return switch (ByteBufCodec.readIntLE(buf)) {
            case 0 -> new NullValue();
            case 1 -> new BoolValue(ByteBufCodec.readBoolean(buf));
            case 2 -> new IntegerValue(ByteBufCodec.readLongLE(buf));
            case 3 -> new NumberValue(ByteBufCodec.readDoubleLE(buf));
            case 4 -> new StringValue(ByteBufCodec.readString(buf));
            case 5 -> {
                int count = ByteBufCodec.toCount(buf, ByteBufCodec.readUvarint32Count(buf));
                List<DynamicValue> values = new ArrayList<>(ByteBufCodec.initialCapacity(count));
                for (int i = 0; i < count; i++) {
                    values.add(decode(buf));
                }
                yield new ArrayValue(values);
            }
            case 6 -> {
                int count = ByteBufCodec.toCount(buf, ByteBufCodec.readUvarint32Count(buf));
                Map<String, DynamicValue> entries = new HashMap<>();
                for (int i = 0; i < count; i++) {
                    String key = ByteBufCodec.readString(buf);
                    entries.putIfAbsent(key, decode(buf));
                }
                yield new ObjectValue(entries);
            }
            default -> throw DecodeException.unknownValue(buf.readerIndex());
        };
    }
}
