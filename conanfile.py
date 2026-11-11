import os
import sys

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class BedrockProtocolConan(ConanFile):
    name = "bedrock-protocol"
    settings = "os", "arch", "compiler", "build_type"
    options = {"with_tests": [True, False]}
    default_options = {"with_tests": False}
    exports_sources = (
        "CMakeLists.txt",
        "cmake/*",
        "include/*",
        "compiler/src/*",
        "protocol/*",
        "tests/*",
        "third_party/*",
        "LICENSE",
        "compiler/pyproject.toml",
    )

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.variables["BEDROCK_PROTOCOL_BUILD_TESTS"] = bool(self.options.with_tests)
        tc.cache_variables["BEDROCK_PROTOCOL_COMPILER_PYTHON"] = sys.executable.replace("\\", "/")
        if versions := os.environ.get("BEDROCK_PROTOCOL_PYTHON_VERSIONS"):
            tc.cache_variables["BEDROCK_PROTOCOL_PYTHON_VERSIONS"] = versions
        tc.user_presets_path = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        CMake(self).install()
