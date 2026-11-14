package dev.endstone.protocol.datastore;

import dev.endstone.protocol.ByteBufCodec;
import java.util.Collections;
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

    static @NotNull DynamicValue getDefaultInstance() {
        return new NullValue();
    }

    default @NotNull DynamicValue copy() {
        return this;
    }
}
