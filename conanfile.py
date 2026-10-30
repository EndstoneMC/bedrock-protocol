from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class BedrockProtocolConan(ConanFile):
    name = "bedrock-protocol"
    settings = "os", "arch", "compiler", "build_type"
    options = {"with_python": [True, False], "with_wire": [True, False], "with_tests": [True, False]}
    default_options = {"with_python": False, "with_wire": False, "with_tests": False}
    exports_sources = (
        "CMakeLists.txt",
        "cmake/*",
        "include/*",
        "src/*",
        "protocol/*",
        "tests/*",
        "third_party/*",
        "LICENSE",
        "pyproject.toml",
    )

    def requirements(self):
        if self.options.with_wire or self.options.with_python:
            self.requires("openssl/3.5.2")
            self.requires("zlib/1.3.1")
            self.requires("snappy/1.2.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.variables["BEDROCK_PROTOCOL_BUILD_PYTHON"] = bool(self.options.with_python)
        tc.variables["BEDROCK_PROTOCOL_BUILD_WIRE"] = bool(self.options.with_wire or self.options.with_python)
        tc.variables["BEDROCK_PROTOCOL_BUILD_TESTS"] = bool(self.options.with_tests)
        tc.user_presets_path = False
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        if self.options.with_python:
            CMake(self).install(component="bedrock_protocol_wheel")
        else:
            CMake(self).install()
