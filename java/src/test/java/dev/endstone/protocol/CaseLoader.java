package dev.endstone.protocol;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.google.gson.JsonPrimitive;
import dev.endstone.protocol.datastore.DynamicValue;
import dev.endstone.protocol.nbt.ByteArrayTag;
import dev.endstone.protocol.nbt.ByteTag;
import dev.endstone.protocol.nbt.CompoundTag;
import dev.endstone.protocol.nbt.CompoundTagData;
import dev.endstone.protocol.nbt.DoubleTag;
import dev.endstone.protocol.nbt.FloatTag;
import dev.endstone.protocol.nbt.IntArrayTag;
import dev.endstone.protocol.nbt.IntTag;
import dev.endstone.protocol.nbt.ListTag;
import dev.endstone.protocol.nbt.LongTag;
import dev.endstone.protocol.nbt.ShortTag;
import dev.endstone.protocol.nbt.StringTag;
import dev.endstone.protocol.nbt.Tag;
import io.netty.buffer.ByteBuf;
import io.netty.buffer.Unpooled;
import java.lang.reflect.Field;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.lang.reflect.Modifier;
import java.lang.reflect.ParameterizedType;
import java.lang.reflect.Type;
import java.math.BigInteger;
import java.util.ArrayList;
import java.util.BitSet;
import java.util.HashMap;
import java.util.HashSet;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.UUID;
import java.util.regex.Pattern;

/** Builds the message a golden case's value describes, through the generated builders. */
final class CaseLoader {
  private static final Pattern VERSION_SUFFIX = Pattern.compile("_v\\d+$");
  private static final Pattern ESCAPED_BYTES = Pattern.compile("(\\\\x[0-9a-f]{2})*");
  private static final Pattern ESCAPED_BITS = Pattern.compile("0b[01]+");
  private static final Pattern ESCAPED_UUID =
      Pattern.compile("[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}");
  private static final Pattern HEX_PAIRS = Pattern.compile("#([0-9a-f]{2})+");
  private static final Pattern INTEGER = Pattern.compile("-?[0-9]+");
  private static final Pattern FIELD_NAME = Pattern.compile("[a-z_][a-z0-9_]*");
  private static final double FLOAT_LIMIT = Double.longBitsToDouble(0x47EFFFFFD586B834L);
  private static final String CLASS_KEY = "__class__";
  private static final String NOT_SET = "NOT_SET";

  private CaseLoader() {}

  static <T extends Message> T load(int version, Class<T> type, JsonElement value)
      throws ReflectiveOperationException {
    return type.cast(message(version, type, value, type.getSimpleName()));
  }

  private static IllegalArgumentException fail(String path, String message) {
    return new IllegalArgumentException(path + ": " + message);
  }

  private static Method single(List<Method> methods, String name, int arity) {
    Method found = null;
    for (Method method : methods) {
      if (method.getName().equals(name) && method.getParameterCount() == arity) {
        if (found != null) {
          throw new IllegalArgumentException(name + " is overloaded");
        }
        found = method;
      }
    }
    return found;
  }

  private static int renumber(String method, int version, Class<?> cls, int value, String path)
      throws ReflectiveOperationException {
    String name = cls.getName();
    String helper =
        CaseLoader.class.getPackageName()
            + ".internal."
            + name.substring(name.lastIndexOf('.') + 1).replace("$", "")
            + "Numbering";
    if (CaseLoader.class.getClassLoader().getResource(helper.replace('.', '/') + ".class")
        == null) {
      return value;
    }
    try {
      return (Integer)
          Class.forName(helper)
              .getMethod(method, int.class, int.class)
              .invoke(null, version, value);
    } catch (InvocationTargetException e) {
      if (e.getCause() instanceof IllegalArgumentException) {
        throw fail(path, e.getCause().getMessage());
      }
      throw e;
    }
  }

  private static Object message(int version, Class<?> type, JsonElement json, String path)
      throws ReflectiveOperationException {
    Object builder = type.getMethod("newBuilder").invoke(null);
    List<Method> methods = List.of(builder.getClass().getMethods());
    Map<String, List<Method>> unions = new LinkedHashMap<>();
    List<Method> armSetters = new ArrayList<>();
    for (Method getter : methods) {
      String getterName = getter.getName();
      if (getter.getParameterCount() != 0
          || !getter.getReturnType().isEnum()
          || !getterName.startsWith("get")
          || !getterName.endsWith("Case")) {
        continue;
      }
      List<Method> arms = new ArrayList<>();
      for (Object constant : getter.getReturnType().getEnumConstants()) {
        String spelled = ((Enum<?>) constant).name();
        if (spelled.endsWith(NOT_SET)) {
          continue;
        }
        Method arm = null;
        for (Method method : methods) {
          if (method.getParameterCount() == 1
              && method.getName().startsWith("set")
              && method.getName().substring(3).equalsIgnoreCase(spelled.replace("_", ""))) {
            if (arm != null) {
              throw fail(path, "two setters for the arm " + spelled);
            }
            arm = method;
          }
        }
        if (arm == null) {
          throw fail(path, "no setter for the arm " + spelled);
        }
        arms.add(arm);
      }
      unions.put(getterName.substring(3, getterName.length() - 4), arms);
      armSetters.addAll(arms);
    }
    boolean wrapper = !unions.isEmpty();
    for (Method method : methods) {
      if (method.getName().startsWith("set") && !armSetters.contains(method)) {
        wrapper = false;
      }
    }
    if (wrapper && !(json.isJsonObject() && !json.getAsJsonObject().has(CLASS_KEY))) {
      arm(version, builder, armSetters, json, path);
    } else if (json.isJsonPrimitive() && json.getAsJsonPrimitive().isString()) {
      String text = json.getAsString();
      if (!HEX_PAIRS.matcher(text).matches()) {
        throw fail(path, "a message as a string is # and hex pairs");
      }
      Map<Integer, Method> ordered = new TreeMap<>();
      Method selector = type.getDeclaredMethod("codec", int.class);
      selector.setAccessible(true);
      Object codec = selector.invoke(null, version);
      Class<?> channel = null;
      for (Method setter : methods) {
        if (!setter.getName().startsWith("set")) {
          continue;
        }
        Class<?>[] parameters = setter.getParameterTypes();
        if (parameters.length != 1
            || (parameters[0] != int.class && parameters[0] != float.class)) {
          throw fail(path, setter.getName() + " is not a single int or float setter");
        }
        if (channel != null && parameters[0] != channel) {
          throw fail(path, setter.getName() + " takes another type than the other setters");
        }
        channel = parameters[0];
        Object probe = type.getMethod("newBuilder").invoke(null);
        setter.invoke(probe, 1);
        ByteBuf encoded = Unpooled.buffer();
        Codec.class
            .getMethod("encode", Message.class, ByteBuf.class)
            .invoke(codec, probe.getClass().getMethod("build").invoke(probe), encoded);
        int first = 0;
        while (first < encoded.writerIndex() && encoded.getByte(first) == 0) {
          first++;
        }
        if (first == encoded.writerIndex() || ordered.put(first, setter) != null) {
          throw fail(path, setter.getName() + " does not own a byte of its own");
        }
      }
      if (ordered.size() != (text.length() - 1) / 2) {
        throw fail(path, "the pairs and the members differ in number");
      }
      List<Method> members = new ArrayList<>(ordered.values());
      if (channel == float.class) {
        members.addFirst(members.removeLast());
      }
      for (int pair = 0; pair < members.size(); pair++) {
        int read = Integer.parseInt(text.substring(1 + 2 * pair, 3 + 2 * pair), 16);
        members.get(pair).invoke(builder, channel == float.class ? (Object) (read / 255.0f) : read);
      }
    } else {
      if (!json.isJsonObject()) {
        throw fail(path, "expected an object");
      }
      Set<String> seen = new HashSet<>();
      for (Map.Entry<String, JsonElement> entry : json.getAsJsonObject().entrySet()) {
        String key = entry.getKey();
        if (!FIELD_NAME.matcher(key).matches()) {
          throw fail(path, key + " is not a field name");
        }
        StringBuilder spelled = new StringBuilder();
        boolean upper = true;
        for (char c : key.toCharArray()) {
          if (c == '_') {
            upper = true;
            continue;
          }
          spelled.append(upper ? Character.toUpperCase(c) : c);
          upper = Character.isDigit(c);
        }
        String name = spelled.toString();
        if (!seen.add(name)) {
          throw fail(path, key + " repeats a field");
        }
        set(version, type, builder, methods, unions, key, name, entry.getValue(), path + "." + key);
      }
      for (Method clear : methods) {
        String field = clear.getName().substring(Math.min(5, clear.getName().length()));
        if (clear.getName().startsWith("clear")
            && clear.getParameterCount() == 0
            && !field.isEmpty()
            && single(methods, "has" + field, 0) == null
            && !seen.contains(field)) {
          throw fail(path, "missing required field " + field);
        }
      }
    }
    return builder.getClass().getMethod("build").invoke(builder);
  }

  private static void set(
      int version,
      Class<?> type,
      Object builder,
      List<Method> methods,
      Map<String, List<Method>> unions,
      String key,
      String name,
      JsonElement value,
      String path)
      throws ReflectiveOperationException {
    if (unions.containsKey(name)) {
      Method clear = single(methods, "clear" + name, 0);
      if (value.isJsonNull() && clear != null) {
        clear.invoke(builder);
      } else {
        arm(version, builder, unions.get(name), value, path);
      }
      return;
    }
    if (value.isJsonNull()) {
      if (single(methods, "has" + name, 0) == null) {
        throw fail(path, "null for a field that is not optional");
      }
      return;
    }
    Method put = single(methods, "put" + name, 2);
    Method add = single(methods, "add" + name, 1);
    Method indexed = single(methods, "set" + name, 2);
    Method plain = single(methods, "set" + name, 1);
    Method coded = single(methods, "set" + name + "Value", 1);
    if (value.isJsonArray()) {
      JsonArray array = value.getAsJsonArray();
      if (put != null) {
        Type[] types = put.getGenericParameterTypes();
        for (int i = 0; i < array.size(); i++) {
          String at = path + "[" + i + "]";
          if (!array.get(i).isJsonObject()
              || array.get(i).getAsJsonObject().size() != 2
              || !array.get(i).getAsJsonObject().has("key")
              || !array.get(i).getAsJsonObject().has("value")) {
            throw fail(at, "expected a key/value object");
          }
          JsonObject pair = array.get(i).getAsJsonObject();
          put.invoke(
              builder,
              convert(version, pair.get("key"), types[0], at + ".key"),
              convert(version, pair.get("value"), types[1], at + ".value"));
        }
      } else if (add != null) {
        for (int i = 0; i < array.size(); i++) {
          call(
              add,
              builder,
              convert(
                  version, array.get(i), add.getGenericParameterTypes()[0], path + "[" + i + "]"));
        }
      } else if (indexed != null) {
        for (int i = 0; i < array.size(); i++) {
          call(
              indexed,
              builder,
              i,
              convert(
                  version,
                  array.get(i),
                  indexed.getGenericParameterTypes()[1],
                  path + "[" + i + "]"));
        }
      } else if (plain != null) {
        plain.invoke(builder, convert(version, value, plain.getGenericParameterTypes()[0], path));
      } else {
        throw fail(path, "no setter for an array");
      }
      return;
    }
    if (add != null
        && plain == null
        && value.isJsonPrimitive()
        && value.getAsJsonPrimitive().isString()) {
      for (byte item : bytes(value, path)) {
        call(add, builder, item & 0xFF);
      }
      return;
    }
    if (value.isJsonObject() && put != null) {
      Type[] types = put.getGenericParameterTypes();
      for (Map.Entry<String, JsonElement> entry : value.getAsJsonObject().entrySet()) {
        String at = path + "." + entry.getKey();
        Object mapKey;
        if (types[0] == String.class) {
          mapKey = entry.getKey();
        } else if (types[0] instanceof Class<?> keyType && keyType.isEnum()) {
          mapKey = convert(version, new JsonPrimitive(entry.getKey()), types[0], at);
        } else {
          mapKey = convert(version, JsonParser.parseString(entry.getKey()), types[0], at);
        }
        put.invoke(builder, mapKey, convert(version, entry.getValue(), types[1], at));
      }
      return;
    }
    if (plain == null && coded == null) {
      String constant = key.replaceFirst("^_+", "").toUpperCase(Locale.ROOT);
      Field literal = null;
      for (Method method : type.getDeclaredMethods()) {
        if (!method.getName().equals("codec") || method.getParameterCount() != 1) {
          continue;
        }
        method.setAccessible(true);
        for (Field field : method.invoke(null, version).getClass().getFields()) {
          if (field.getName().equals(constant) && Modifier.isStatic(field.getModifiers())) {
            literal = field;
          }
        }
      }
      if (literal == null) {
        throw fail(path, "names no field and no constant");
      }
      if (!value.isJsonPrimitive()) {
        throw fail(path, "a constant is a scalar");
      }
      JsonPrimitive given = value.getAsJsonPrimitive();
      literal.setAccessible(true);
      Object expected = literal.get(null);
      boolean equal;
      if (expected instanceof Boolean flag) {
        equal = given.isBoolean() && given.getAsBoolean() == flag;
      } else if (expected instanceof String text) {
        equal = given.isString() && given.getAsString().equals(text);
      } else if (expected instanceof Enum<?> member) {
        Class<?> enumType = member.getDeclaringClass();
        equal =
            given.isNumber()
                && INTEGER.matcher(given.getAsString()).matches()
                && new BigInteger(given.getAsString())
                    .equals(
                        BigInteger.valueOf(
                            renumber(
                                "toNumber",
                                version,
                                enumType,
                                (Integer) enumType.getMethod("getNumber").invoke(member),
                                path)));
      } else {
        throw fail(path, "unsupported constant type " + literal.getType());
      }
      if (!equal) {
        throw fail(path, "differs from the constant " + expected);
      }
      return;
    }
    boolean number =
        value.isJsonPrimitive()
            && value.getAsJsonPrimitive().isNumber()
            && INTEGER.matcher(value.getAsString()).matches();
    if (coded != null && number && (plain == null || plain.getParameterTypes()[0].isEnum())) {
      int given = (Integer) convert(version, value, int.class, path);
      Method getter = single(methods, "get" + name, 0);
      Class<?> enumType =
          plain != null
              ? plain.getParameterTypes()[0]
              : getter != null ? getter.getReturnType() : null;
      if (enumType != null && enumType.isEnum()) {
        given = renumber("fromNumber", version, enumType, given, path);
      }
      call(coded, builder, given);
      return;
    }
    if (plain == null) {
      throw fail(path, "only an integer is accepted");
    }
    call(plain, builder, convert(version, value, plain.getGenericParameterTypes()[0], path));
  }

  private static void call(Method setter, Object builder, Object... args)
      throws ReflectiveOperationException {
    try {
      setter.invoke(builder, args);
    } catch (InvocationTargetException e) {
      Object last = args[args.length - 1];
      if (!(e.getCause() instanceof IllegalArgumentException) || !(last instanceof Integer)) {
        throw e;
      }
      int value = (Integer) last;
      int width = value < 1 << 8 ? 8 : 16;
      if (value < 1 << (width - 1) || value >= 1 << width) {
        throw e;
      }
      args[args.length - 1] = value - (1 << width);
      setter.invoke(builder, args);
    }
  }

  private static void arm(
      int version, Object builder, List<Method> arms, JsonElement json, String path)
      throws ReflectiveOperationException {
    if (json.isJsonObject()) {
      JsonObject object = json.getAsJsonObject();
      if (!object.has(CLASS_KEY)
          || !object.get(CLASS_KEY).isJsonPrimitive()
          || !object.get(CLASS_KEY).getAsJsonPrimitive().isString()) {
        throw fail(path, "an object arm needs a string " + CLASS_KEY);
      }
      String name = object.get(CLASS_KEY).getAsString();
      Method chosen = null;
      for (Method arm : arms) {
        if (VERSION_SUFFIX
            .matcher(arm.getParameterTypes()[0].getSimpleName())
            .replaceFirst("")
            .equals(name)) {
          if (chosen != null) {
            throw fail(path, CLASS_KEY + " " + name + " names two arms");
          }
          chosen = arm;
        }
      }
      if (chosen == null) {
        throw fail(path, CLASS_KEY + " " + name + " names no arm");
      }
      JsonObject rest = new JsonObject();
      for (Map.Entry<String, JsonElement> entry : object.entrySet()) {
        if (!entry.getKey().equals(CLASS_KEY)) {
          rest.add(entry.getKey(), entry.getValue());
        }
      }
      chosen.invoke(builder, convert(version, rest, chosen.getGenericParameterTypes()[0], path));
      return;
    }
    for (Method arm : arms) {
      Class<?> armType = arm.getParameterTypes()[0];
      boolean accepted = false;
      if (json.isJsonArray()) {
        accepted = armType == byte[].class || List.class.isAssignableFrom(armType);
      } else if (json.isJsonPrimitive()) {
        JsonPrimitive primitive = json.getAsJsonPrimitive();
        boolean integer =
            primitive.isNumber() && INTEGER.matcher(primitive.getAsString()).matches();
        if (armType == boolean.class || armType == Boolean.class) {
          accepted = primitive.isBoolean();
        } else if (bits(armType) != 0) {
          accepted = integer && fits(new BigInteger(primitive.getAsString()), bits(armType));
        } else if (armType == float.class
            || armType == Float.class
            || armType == double.class
            || armType == Double.class) {
          accepted = primitive.isNumber() || nonFinite(json) != null;
        } else if (armType == String.class) {
          accepted = primitive.isString();
        } else if (armType == UUID.class) {
          accepted =
              primitive.isString() && ESCAPED_UUID.matcher(primitive.getAsString()).matches();
        } else if (armType.isEnum()) {
          accepted = primitive.isString() || integer;
        }
      }
      if (accepted) {
        arm.invoke(builder, convert(version, json, arm.getGenericParameterTypes()[0], path));
        return;
      }
    }
    throw fail(path, "no arm accepts " + json);
  }

  private static int bits(Class<?> type) {
    if (type == byte.class || type == Byte.class) {
      return 8;
    }
    if (type == short.class || type == Short.class) {
      return 16;
    }
    if (type == int.class || type == Integer.class) {
      return 32;
    }
    if (type == long.class || type == Long.class) {
      return 64;
    }
    return 0;
  }

  private static boolean fits(BigInteger value, int bits) {
    return value.compareTo(BigInteger.ONE.shiftLeft(bits - 1).negate()) >= 0
        && value.compareTo(BigInteger.ONE.shiftLeft(bits)) < 0;
  }

  private static Object convert(int version, JsonElement json, Type type, String path)
      throws ReflectiveOperationException {
    if (type instanceof ParameterizedType generic && generic.getRawType() == List.class) {
      if (!json.isJsonArray()) {
        throw fail(path, "expected an array");
      }
      List<Object> list = new ArrayList<>();
      JsonArray array = json.getAsJsonArray();
      for (int i = 0; i < array.size(); i++) {
        list.add(
            convert(
                version, array.get(i), generic.getActualTypeArguments()[0], path + "[" + i + "]"));
      }
      return list;
    }
    if (!(type instanceof Class<?> cls)) {
      throw fail(path, "unsupported type " + type);
    }
    if (cls == boolean.class || cls == Boolean.class) {
      if (!json.isJsonPrimitive() || !json.getAsJsonPrimitive().isBoolean()) {
        throw fail(path, "expected a boolean");
      }
      return json.getAsBoolean();
    }
    if (bits(cls) != 0) {
      return integer(json, cls, path);
    }
    if (cls == float.class || cls == Float.class) {
      Double special = nonFinite(json);
      if (special != null) {
        return (float) special.doubleValue();
      }
      double narrowed = number(json, path).doubleValue();
      if (Math.abs(narrowed) > FLOAT_LIMIT) {
        throw fail(path, "a float is at most " + FLOAT_LIMIT);
      }
      return (float) narrowed;
    }
    if (cls == double.class || cls == Double.class) {
      Double special = nonFinite(json);
      if (special != null) {
        return special;
      }
      return number(json, path).doubleValue();
    }
    if (cls == String.class) {
      String text = text(json, path);
      if (!ESCAPED_BYTES.matcher(text).matches()) {
        return text;
      }
      byte[] raw = HexFormat.of().parseHex(text.replace("\\x", ""));
      ByteBuf buf = Unpooled.buffer();
      ByteBufCodec.writeUnsignedVarInt(buf, raw.length);
      buf.writeBytes(raw);
      return ByteBufCodec.readString(buf);
    }
    if (cls == UUID.class) {
      String text = text(json, path);
      if (!ESCAPED_UUID.matcher(text).matches()) {
        throw fail(path, "expected a lowercase canonical UUID");
      }
      return UUID.fromString(text);
    }
    if (cls == byte[].class) {
      return bytes(json, path);
    }
    if (cls == BitSet.class) {
      String text = text(json, path);
      if (!ESCAPED_BITS.matcher(text).matches()) {
        throw fail(path, "expected 0b followed by bits");
      }
      BigInteger bits = new BigInteger(text.substring(2), 2);
      BitSet set = new BitSet();
      for (int i = 0; i < bits.bitLength(); i++) {
        set.set(i, bits.testBit(i));
      }
      return set;
    }
    if (cls == CompoundTag.class) {
      return compound(json, path);
    }
    if (cls == CompoundTagData.class) {
      return new CompoundTagData(compound(json, path));
    }
    if (cls == DynamicValue.class) {
      return dynamic(json, path);
    }
    if (cls.isEnum()) {
      JsonPrimitive primitive = primitive(json, path);
      if (primitive.isNumber() || primitive.isBoolean()) {
        Object member =
            cls.getMethod("forNumber", int.class)
                .invoke(
                    null,
                    renumber(
                        "fromNumber",
                        version,
                        cls,
                        primitive.isBoolean()
                            ? (primitive.getAsBoolean() ? 1 : 0)
                            : (Integer) integer(json, int.class, path),
                        path));
        if (member == null) {
          throw fail(path, primitive.getAsString() + " names no member of " + cls);
        }
        return member;
      }
      String wanted = text(json, path);
      Method decoder = null;
      for (Method method : cls.getMethods()) {
        if (method.getName().equals("decode")
            && Modifier.isStatic(method.getModifiers())
            && method.getParameterTypes()[method.getParameterCount() - 1] == ByteBuf.class) {
          decoder = method;
        }
      }
      if (decoder == null) {
        throw fail(path, cls + " has no encoded names");
      }
      ByteBuf buf = Unpooled.buffer();
      ByteBufCodec.writeString(buf, wanted);
      try {
        return decoder.getParameterCount() == 2
            ? decoder.invoke(null, version, buf)
            : decoder.invoke(null, buf);
      } catch (InvocationTargetException e) {
        if (e.getCause() instanceof DecodeException) {
          throw fail(path, wanted + " names no member of " + cls);
        }
        throw e;
      }
    }
    if (Message.class.isAssignableFrom(cls)) {
      return message(version, cls, json, path);
    }
    throw fail(path, "unsupported type " + cls.getName());
  }

  private static Double nonFinite(JsonElement json) {
    if (!json.isJsonPrimitive() || !json.getAsJsonPrimitive().isString()) {
      return null;
    }
    return switch (json.getAsString()) {
      case "NaN" -> Double.NaN;
      case "Infinity" -> Double.POSITIVE_INFINITY;
      case "-Infinity" -> Double.NEGATIVE_INFINITY;
      default -> null;
    };
  }

  private static JsonPrimitive primitive(JsonElement json, String path) {
    if (!json.isJsonPrimitive()) {
      throw fail(path, "expected a scalar");
    }
    return json.getAsJsonPrimitive();
  }

  private static String text(JsonElement json, String path) {
    JsonPrimitive primitive = primitive(json, path);
    if (!primitive.isString()) {
      throw fail(path, "expected a string");
    }
    return primitive.getAsString();
  }

  private static Number number(JsonElement json, String path) {
    JsonPrimitive primitive = primitive(json, path);
    if (!primitive.isNumber()) {
      throw fail(path, "expected a number");
    }
    return primitive.getAsNumber();
  }

  private static Object integer(JsonElement json, Class<?> type, String path) {
    JsonPrimitive primitive = primitive(json, path);
    if (!primitive.isNumber() || !INTEGER.matcher(primitive.getAsString()).matches()) {
      throw fail(path, "expected an integer");
    }
    BigInteger value = new BigInteger(primitive.getAsString());
    int bits = bits(type);
    if (!fits(value, bits)) {
      throw fail(path, value + " does not fit " + bits + " bits");
    }
    return switch (bits) {
      case 8 -> value.byteValue();
      case 16 -> value.shortValue();
      case 32 -> value.intValue();
      default -> value.longValue();
    };
  }

  private static byte[] bytes(JsonElement json, String path) {
    if (json.isJsonArray()) {
      JsonArray array = json.getAsJsonArray();
      byte[] out = new byte[array.size()];
      for (int i = 0; i < out.length; i++) {
        out[i] = (Byte) integer(array.get(i), byte.class, path + "[" + i + "]");
      }
      return out;
    }
    String text = text(json, path);
    if (!ESCAPED_BYTES.matcher(text).matches()) {
      throw fail(path, "expected escaped bytes");
    }
    return HexFormat.of().parseHex(text.replace("\\x", ""));
  }

  private static CompoundTag compound(JsonElement json, String path) {
    if (!(Snbt.parse(text(json, path)) instanceof CompoundTag tag)) {
      throw fail(path, "expected a compound");
    }
    return tag;
  }

  private static DynamicValue dynamic(JsonElement json, String path) {
    if (json.isJsonNull()) {
      return new DynamicValue.NullValue();
    }
    if (json.isJsonArray()) {
      List<DynamicValue> values = new ArrayList<>();
      for (JsonElement item : json.getAsJsonArray()) {
        values.add(dynamic(item, path + "[]"));
      }
      return new DynamicValue.ArrayValue(values);
    }
    if (json.isJsonObject()) {
      Map<String, DynamicValue> entries = new HashMap<>();
      for (Map.Entry<String, JsonElement> entry : json.getAsJsonObject().entrySet()) {
        entries.put(entry.getKey(), dynamic(entry.getValue(), path + "." + entry.getKey()));
      }
      return new DynamicValue.ObjectValue(entries);
    }
    JsonPrimitive primitive = json.getAsJsonPrimitive();
    if (primitive.isBoolean()) {
      return new DynamicValue.BoolValue(primitive.getAsBoolean());
    }
    if (primitive.isString()) {
      return new DynamicValue.StringValue(primitive.getAsString());
    }
    if (INTEGER.matcher(primitive.getAsString()).matches()) {
      return new DynamicValue.IntegerValue(
          new BigInteger(primitive.getAsString()).longValueExact());
    }
    return new DynamicValue.NumberValue(primitive.getAsDouble());
  }

  /** Reads nbtlib's compact SNBT into the runtime's tags. */
  static final class Snbt {
    private static final Pattern BYTE = Pattern.compile("-?[0-9]+[bB]");
    private static final Pattern SHORT = Pattern.compile("-?[0-9]+[sS]");
    private static final Pattern LONG = Pattern.compile("-?[0-9]+[lL]");
    private static final Pattern INT = Pattern.compile("-?[0-9]+");
    private static final Pattern FLOAT =
        Pattern.compile("-?(?:[0-9]+\\.?[0-9]*|\\.[0-9]+)(?:[eE][+-]?[0-9]+)?[fF]");
    private static final Pattern DOUBLE =
        Pattern.compile(
            "-?(?:[0-9]+\\.[0-9]*|\\.[0-9]+)(?:[eE][+-]?[0-9]+)?[dD]?"
                + "|-?[0-9]+(?:[eE][+-]?[0-9]+)[dD]?|-?[0-9]+[dD]");

    private final String text;
    private int cursor;

    private Snbt(String text) {
      this.text = text;
    }

    static Tag parse(String text) {
      Snbt reader = new Snbt(text);
      Tag tag = reader.value();
      reader.skip();
      if (reader.cursor != text.length()) {
        throw reader.fail("trailing text");
      }
      return tag;
    }

    private IllegalArgumentException fail(String message) {
      return new IllegalArgumentException("SNBT at " + cursor + ": " + message + " in " + text);
    }

    private void skip() {
      while (cursor < text.length() && Character.isWhitespace(text.charAt(cursor))) {
        cursor++;
      }
    }

    private char peek() {
      skip();
      if (cursor == text.length()) {
        throw fail("unexpected end");
      }
      return text.charAt(cursor);
    }

    private Tag value() {
      char first = peek();
      if (first == '{') {
        cursor++;
        CompoundTag tag = new CompoundTag();
        if (peek() == '}') {
          cursor++;
          return tag;
        }
        while (true) {
          char lead = peek();
          String key = lead == '"' || lead == '\'' ? quoted() : word();
          if (peek() != ':') {
            throw fail("expected :");
          }
          cursor++;
          tag.put(key, value());
          char next = peek();
          cursor++;
          if (next == '}') {
            return tag;
          }
          if (next != ',') {
            throw fail("expected , or }");
          }
        }
      }
      if (first == '[') {
        cursor++;
        if (text.startsWith("B;", cursor)) {
          cursor += 2;
          List<String> items = words();
          byte[] data = new byte[items.size()];
          for (int i = 0; i < data.length; i++) {
            data[i] = Byte.parseByte(items.get(i).replaceAll("[bB]$", ""));
          }
          return new ByteArrayTag(data);
        }
        if (text.startsWith("I;", cursor)) {
          cursor += 2;
          List<String> items = words();
          int[] data = new int[items.size()];
          for (int i = 0; i < data.length; i++) {
            data[i] = Integer.parseInt(items.get(i));
          }
          return new IntArrayTag(data);
        }
        if (text.startsWith("L;", cursor)) {
          throw fail("a long array has no tag");
        }
        List<Tag> elements = new ArrayList<>();
        if (peek() == ']') {
          cursor++;
          return new ListTag();
        }
        while (true) {
          Tag element = value();
          if (!elements.isEmpty() && elements.get(0).getId() != element.getId()) {
            throw fail("a list holds one kind of tag");
          }
          elements.add(element);
          char next = peek();
          cursor++;
          if (next == ']') {
            return new ListTag(elements);
          }
          if (next != ',') {
            throw fail("expected , or ]");
          }
        }
      }
      if (first == '"' || first == '\'') {
        return StringTag.valueOf(quoted());
      }
      String word = word();
      String digits = word.substring(0, word.length() - 1);
      if (word.equals("true") || word.equals("false")) {
        return ByteTag.valueOf(word.equals("true"));
      }
      if (BYTE.matcher(word).matches()) {
        return ByteTag.valueOf(Byte.parseByte(digits));
      }
      if (SHORT.matcher(word).matches()) {
        return ShortTag.valueOf(Short.parseShort(digits));
      }
      if (LONG.matcher(word).matches()) {
        return LongTag.valueOf(Long.parseLong(digits));
      }
      if (INT.matcher(word).matches()) {
        return IntTag.valueOf(Integer.parseInt(word));
      }
      if (FLOAT.matcher(word).matches()) {
        return FloatTag.valueOf(Float.parseFloat(digits));
      }
      if (DOUBLE.matcher(word).matches()) {
        return DoubleTag.valueOf(Double.parseDouble(word));
      }
      return StringTag.valueOf(word);
    }

    private List<String> words() {
      List<String> items = new ArrayList<>();
      if (peek() == ']') {
        cursor++;
        return items;
      }
      while (true) {
        items.add(word());
        char next = peek();
        cursor++;
        if (next == ']') {
          return items;
        }
        if (next != ',') {
          throw fail("expected , or ]");
        }
      }
    }

    private String quoted() {
      char quote = text.charAt(cursor++);
      StringBuilder out = new StringBuilder();
      while (true) {
        if (cursor == text.length()) {
          throw fail("unterminated string");
        }
        char c = text.charAt(cursor++);
        if (c == quote) {
          return out.toString();
        }
        if (c == '\\') {
          if (cursor == text.length()) {
            throw fail("unterminated string");
          }
          c = text.charAt(cursor++);
        }
        out.append(c);
      }
    }

    private String word() {
      peek();
      int start = cursor;
      while (cursor < text.length() && ",:]}\"' \t\r\n".indexOf(text.charAt(cursor)) < 0) {
        cursor++;
      }
      if (start == cursor) {
        throw fail("expected a value");
      }
      return text.substring(start, cursor);
    }
  }
}
