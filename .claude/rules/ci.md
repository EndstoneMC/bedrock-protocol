---
paths:
  - ".github/**"
---

# CI

- The C++ job is `build` and matrixes over toolchains.
- Each binding is one job; Python's only matrix axis is the runner OS that cibuildwheel needs.
- Upload every single-file artifact with `archive: false`.
- Coverage goes to Codecov through OIDC.
- Name a job for its language or purpose, never for its tool.
