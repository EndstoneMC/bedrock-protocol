# Third-party dependencies bundled with this project. Add each vendored
# library as a sibling directory under third_party/ and list it here. The
# top-level CMakeLists.txt pulls this file in before building the
# bedrock_protocol library, so any targets defined here are available to it.

include(FetchContent)

# tl::expected — non-std expected<T,E> backing our std::expected shim on
# pre-C++23 compilers. Exposes the INTERFACE target `tl::expected`.
set(EXPECTED_BUILD_TESTS OFF CACHE BOOL "" FORCE)
FetchContent_Declare(
    tl-expected
    GIT_REPOSITORY https://github.com/TartanLlama/expected.git
    GIT_TAG        v1.1.0)
FetchContent_MakeAvailable(tl-expected)
