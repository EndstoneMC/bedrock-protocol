---
paths:
  - ".github/**"
---

# CI

- The C++ job is `build` and matrixes over toolchains.
- Each binding is one job; Python's only matrix axis is the runner OS that cibuildwheel needs.
- Upload every single-file artifact with `archive: false`.
- Name a C++ package `bedrock-protocol-<version>-<triple>`, with no commit hash.
- Coverage and test results go to Codecov through OIDC.
- Name a job for its language or purpose, never for its tool.
- Give each phase of a job its own named step, as the Java job's build, formatting and test steps are.
