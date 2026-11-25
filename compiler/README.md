# bedrock-protocol-compiler

`bpc` compiles the schema in [`protocol/`](../protocol) into the C++, Java and Go codecs, rewriting only changed files and deleting stale ones.

```shell
uv run --directory compiler bpc ../protocol --out ../build/bpc/cpp --java-out ../build/bpc/java --go-out ../build/bpc/go
uv run --directory compiler pytest
uv run --directory compiler mypy
```

The Go backend lays its output out through `gofmt`, so `--go-out` and the tests need it on the `PATH`.

MIT, see [LICENSE](LICENSE).
