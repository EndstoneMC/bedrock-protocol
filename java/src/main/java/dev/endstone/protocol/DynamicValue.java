package dev.endstone.protocol;

import dev.endstone.protocol.DecodeException.Reason;
import io.netty.buffer.ByteBuf;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.TreeMap;

/** A data store value: null, bool, int64, double, string, array or object. */
public sealed interface DynamicValue {
    int NULL = 0;
    int BOOL = 1;
    int INTEGER = 2;
    int NUMBER = 3;
    int STRING = 4;
    int ARRAY = 5;
    int OBJECT = 6;

    record NullValue() implements DynamicValue {}

    record BoolValue(boolean value) implements DynamicValue {}

    record IntegerValue(long value) implements DynamicValue {}

    record NumberValue(double value) implements DynamicValue {}

    record StringValue(String value) implements DynamicValue {
        public StringValue {
            Objects.requireNonNull(value, "StringValue.value");
        }
    }

    record ArrayValue(List<DynamicValue> values) implements DynamicValue {
        public ArrayValue {
            values = List.copyOf(values);
        }
    }

    /** An object; its entries are kept, and written, in the unsigned byte order of their keys. */
    record ObjectValue(Map<String, DynamicValue> entries) implements DynamicValue {
        public ObjectValue {
            TreeMap<String, DynamicValue> sorted = new TreeMap<>(Wire.STR_ORDER);
            for (Map.Entry<String, DynamicValue> entry : entries.entrySet()) {
                sorted.put(
                        Objects.requireNonNull(entry.getKey(), "ObjectValue.entries key"),
                        Objects.requireNonNull(entry.getValue(), "ObjectValue.entries value"));
            }
            entries = Collections.unmodifiableMap(sorted);
        }
    }

    default void encode(ByteBuf buf) {
        switch (this) {
            case NullValue v -> buf.writeIntLE(NULL);
            case BoolValue v -> {
                buf.writeIntLE(BOOL);
                buf.writeBoolean(v.value());
            }
            case IntegerValue v -> {
                buf.writeIntLE(INTEGER);
                buf.writeLongLE(v.value());
            }
            case NumberValue v -> {
                buf.writeIntLE(NUMBER);
                buf.writeDoubleLE(v.value());
            }
            case StringValue v -> {
                buf.writeIntLE(STRING);
                Wire.writeStr(buf, v.value());
            }
            case ArrayValue v -> {
                buf.writeIntLE(ARRAY);
                Wire.writeUvarint32(buf, v.values().size());
                for (DynamicValue element : v.values()) {
                    element.encode(buf);
                }
            }
            case ObjectValue v -> {
                buf.writeIntLE(OBJECT);
                Wire.writeUvarint32(buf, v.entries().size());
                for (Map.Entry<String, DynamicValue> entry : v.entries().entrySet()) {
                    Wire.writeStr(buf, entry.getKey());
                    entry.getValue().encode(buf);
                }
            }
        }
    }

    static DynamicValue read(ByteBuf buf, DecodeBudget budget) {
        budget.enter(buf.readerIndex());
        try {
            long tag = Integer.toUnsignedLong(Wire.readInt32(buf));
            if (tag == NULL) {
                return new NullValue();
            } else if (tag == BOOL) {
                return new BoolValue(Wire.readBool(buf));
            } else if (tag == INTEGER) {
                return new IntegerValue(Wire.readInt64(buf));
            } else if (tag == NUMBER) {
                return new NumberValue(Wire.readDouble(buf));
            } else if (tag == STRING) {
                return new StringValue(Wire.readStr(buf, budget));
            } else if (tag == ARRAY) {
                int count = Wire.charge(buf, budget, Wire.readUvarint32Count(buf), 0);
                List<DynamicValue> values = new ArrayList<>(Wire.initialCapacity(count));
                for (int i = 0; i < count; i++) {
                    values.add(read(buf, budget));
                }
                return new ArrayValue(values);
            } else if (tag == OBJECT) {
                int count = Wire.charge(buf, budget, Wire.readUvarint32Count(buf), 0);
                Map<String, DynamicValue> entries = new HashMap<>();
                for (int i = 0; i < count; i++) {
                    String key = Wire.readStr(buf, budget);
                    entries.putIfAbsent(key, read(buf, budget));
                }
                return new ObjectValue(entries);
            }
            throw new DecodeException(Reason.UNKNOWN_VALUE, buf.readerIndex());
        } finally {
            budget.leave();
        }
    }
}
