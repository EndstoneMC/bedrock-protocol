package dev.endstone.protocol.nbt;

import java.util.Optional;
import org.jetbrains.annotations.NotNull;

public sealed interface NumericTag extends PrimitiveTag
    permits ByteTag, ShortTag, IntTag, LongTag, FloatTag, DoubleTag {
  byte byteValue();

  short shortValue();

  int intValue();

  long longValue();

  float floatValue();

  double doubleValue();

  @NotNull
  Number numberValue();

  @Override
  default @NotNull Optional<Number> asNumber() {
    return Optional.of(numberValue());
  }

  @Override
  default @NotNull Optional<Byte> asByte() {
    return Optional.of(byteValue());
  }

  @Override
  default @NotNull Optional<Short> asShort() {
    return Optional.of(shortValue());
  }

  @Override
  default @NotNull Optional<Integer> asInt() {
    return Optional.of(intValue());
  }

  @Override
  default @NotNull Optional<Long> asLong() {
    return Optional.of(longValue());
  }

  @Override
  default @NotNull Optional<Float> asFloat() {
    return Optional.of(floatValue());
  }

  @Override
  default @NotNull Optional<Double> asDouble() {
    return Optional.of(doubleValue());
  }

  @Override
  default @NotNull Optional<Boolean> asBoolean() {
    return Optional.of(byteValue() != 0);
  }
}
