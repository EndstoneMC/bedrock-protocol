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
- Publish to PyPI only `bedrock_protocol`'s wheels and sdist, from `release.yml`'s `pypi` environment through trusted publishing; the compiler wheel ships on the GitHub release alone.
- Publish the Java library to Maven Central from `release.yml`'s `maven-central` job and environment with `publishAndReleaseToMavenCentral`, before the `pypi` job; the CI Java job's jar, sources jar and javadoc jar ship on the GitHub release.
- Name a job for its language or purpose, never for its tool.
- Give each phase of a job its own named step, as the Java job's build, formatting and test steps are.
