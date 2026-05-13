# bpc — Bedrock-Protocol Compiler

The `protoc` of this project. Parses Python-DSL packet definitions and emits
C++ `<Packet>.h` / `<Packet>.cpp` via Jinja2 templates.

## Install

```sh
pip install -r requirements.txt
```

## Run

Invoke as a Python module from the directory containing this package:

```sh
python -m bpc --out <output_dir> <packet.py> [<packet.py> ...]
```

Flags:

- `--header-only` — emit only `.h` files.
- `--list-outputs` — print the file paths that *would* be generated, without
  writing anything (used by the CMake glue at configure time).

## Layout

| Path             | What it is                                |
| ---------------- | ----------------------------------------- |
| `__main__.py`    | CLI entry point (`python -m bpc`)         |
| `dsl.py`         | DSL schema + AST-based parser             |
| `templates/`     | Jinja2 templates for `.h` / `.cpp` emit   |
