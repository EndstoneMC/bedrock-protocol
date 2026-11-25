# bedrock-protocol-compiler

`bpc` compiles the schema in [`protocol/`](../protocol) into the C++ and Java codecs, rewriting only changed files and deleting stale ones.

```shell
uv run --directory compiler bpc ../protocol --out ../build/bpc/cpp --java-out ../build/bpc/java
uv run --directory compiler pytest
uv run --directory compiler mypy
```

MIT, see [LICENSE](LICENSE).
