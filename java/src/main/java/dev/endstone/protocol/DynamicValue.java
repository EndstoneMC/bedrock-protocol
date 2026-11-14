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
            TreeMap<String, DynamicValue> sorted = new TreeMap<>(ByteBufUtils.STR_ORDER);
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
                ByteBufUtils.writeString(buf, v.value());
            }
            case ArrayValue v -> {
                buf.writeIntLE(5);
                ByteBufUtils.writeUnsignedVarInt(buf, v.values().size());
                for (DynamicValue element : v.values()) {
                    element.encode(buf);
                }
            }
            case ObjectValue v -> {
                buf.writeIntLE(6);
                ByteBufUtils.writeUnsignedVarInt(buf, v.entries().size());
                for (Map.Entry<String, DynamicValue> entry : v.entries().entrySet()) {
                    ByteBufUtils.writeString(buf, entry.getKey());
                    entry.getValue().encode(buf);
                }
            }
        }
    }

    static DynamicValue read(ByteBuf buf, DecodeBudget budget) {
        budget.enter(buf.readerIndex());
        try {
            return switch (ByteBufUtils.readIntLE(buf)) {
                case 0 -> new NullValue();
                case 1 -> new BoolValue(ByteBufUtils.readBoolean(buf));
                case 2 -> new IntegerValue(ByteBufUtils.readLongLE(buf));
                case 3 -> new NumberValue(ByteBufUtils.readDoubleLE(buf));
                case 4 -> new StringValue(ByteBufUtils.readString(buf, budget));
                case 5 -> {
                    int count =
                            ByteBufUtils.charge(
                                    buf, budget, ByteBufUtils.readUvarint32Count(buf), 0);
                    List<DynamicValue> values =
                            new ArrayList<>(ByteBufUtils.initialCapacity(count));
                    for (int i = 0; i < count; i++) {
                        values.add(read(buf, budget));
                    }
                    yield new ArrayValue(values);
                }
                case 6 -> {
                    int count =
                            ByteBufUtils.charge(
                                    buf, budget, ByteBufUtils.readUvarint32Count(buf), 0);
                    Map<String, DynamicValue> entries = new HashMap<>();
                    for (int i = 0; i < count; i++) {
                        String key = ByteBufUtils.readString(buf, budget);
                        entries.putIfAbsent(key, read(buf, budget));
                    }
                    yield new ObjectValue(entries);
                }
                default -> throw new DecodeException(Reason.UNKNOWN_VALUE, buf.readerIndex());
            };
        } finally {
            budget.leave();
        }
    }
}
