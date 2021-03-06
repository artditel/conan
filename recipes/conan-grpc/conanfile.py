from conans import ConanFile, CMake, tools, RunEnvironment
from conans.errors import ConanInvalidConfiguration
import os


class grpcConan(ConanFile):
    name = "grpc"
    version = "1.29.1"
    description = "Google's RPC library and framework."
    topics = ("conan", "grpc", "rpc")
    url = "https://github.com/inexorgame/conan-grpc"
    homepage = "https://github.com/grpc/grpc"
    author = "Bincrafters <bincrafters@gmail.com>"
    license = "Apache-2.0"
    exports = ["LICENSE.md"]
    exports_sources = ["CMakeLists.txt"]
    generators = "cmake"
    short_paths = True  # Otherwise some folders go out of the 260 chars path length scope rapidly (on windows)

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "build_codegen": [True, False],
        "build_csharp_ext": [True, False],
        "build_tests": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
        "build_codegen": True,
        "build_csharp_ext": False,
        "build_tests": False,
    }

    _source_subfolder = "source_subfolder"
    _build_subfolder = "build_subfolder"

    requires = (
        "zlib/1.2.11@conan/stable",
        "OpenSSL/1.1.1f@forwardmeasure/stable",
        "protobuf/3.12.1@forwardmeasure/stable",
        "c-ares/1.15.0@forwardmeasure/stable"
    )

    def configure(self):
        if self.settings.os == "Windows" and self.settings.compiler == "Visual Studio":
            del self.options.fPIC
            compiler_version = int(str(self.settings.compiler.version))
            if compiler_version < 14:
                raise ConanInvalidConfiguration("gRPC can only be built with Visual Studio 2015 or higher.")

    def source(self):
        # I'm sure there are better/more idiomatic ways to do this, but this will do for now
        git_clone_command = (
            "git clone {}.git {} && cd {} && " "git checkout v{} && git submodule update --init --recursive"
        ).format(self.homepage, self._source_subfolder, self._source_subfolder, self.version)
        self.run(git_clone_command)

        source_folder_path = os.path.dirname(os.path.abspath(self._source_subfolder))
#        cleanup_command = "rm -rf {}/source_subfolder/third_party/{{protobuf,cares,zlib*,*ssl*}}".format(source_folder_path)
        cleanup_command = ("rm -rf {}/source_subfolder/third_party/protobuf; "
                           "rm -rf {}/source_subfolder/third_party/cares; "
                           "rm -rf {}/source_subfolder/third_party/zlib; "
                           "rm -rf {}/source_subfolder/third_party/*ssl*; ").format(source_folder_path,source_folder_path,source_folder_path,source_folder_path)
        self.run(cleanup_command)

    def source_old(self):
        archive_url = "https://github.com/grpc/grpc/archive/v{}.zip".format(self.version)
        tools.get(archive_url, sha256="b0d3b876d85e4e4375aa211a52a33b7e8ca9f9d6d97a60c3c844070a700f0ea3")
        os.rename("grpc-{}".format(self.version), self._source_subfolder)

        # cmake_name = "{}/CMakeLists.txt".format(self._source_subfolder)

        # Parts which should be options:
        # grpc_cronet
        # grpc++_cronet
        # grpc_unsecure (?)
        # grpc++_unsecure (?)
        # grpc++_reflection
        # gen_hpack_tables (?)
        # gen_legal_metadata_characters (?)
        # grpc_csharp_plugin
        # grpc_node_plugin
        # grpc_objective_c_plugin
        # grpc_php_plugin
        # grpc_python_plugin
        # grpc_ruby_plugin

    def build_requirements(self):
        if self.options.build_tests:
            self.build_requires("benchmark/1.4.1@forwardmeasure/stable")
            self.build_requires("gflags/2.2.1@forwardmeasure/stable")

    def _configure_cmake(self):
        cmake = CMake(self)

        # This doesn't work yet as one would expect, because the install target builds everything
        # and we need the install target because of the generated CMake files
        #
        #   enable_mobile=False # Enables iOS and Android support
        #   non_cpp_plugins=False # Enables plugins such as --java-out and --py-out (if False, only --cpp-out is possible)
        #
        # cmake.definitions['CONAN_ADDITIONAL_PLUGINS'] = "ON" if self.options.build_csharp_ext else "OFF"
        #
        # Doesn't work yet for the same reason as above
        #
        # cmake.definitions['CONAN_ENABLE_MOBILE'] = "ON" if self.options.build_csharp_ext else "OFF"
        cmake.definitions["gRPC_BUILD_CODEGEN"] = "ON" if self.options.build_codegen else "OFF"
        cmake.definitions["gRPC_BUILD_CSHARP_EXT"] = "ON" if self.options.build_csharp_ext else "OFF"
        cmake.definitions["gRPC_BUILD_TESTS"] = "ON" if self.options.build_tests else "OFF"

        # We need the generated cmake/ files (bc they depend on the list of targets, which is dynamic)
        cmake.definitions["gRPC_INSTALL"] = "ON"

        # tell grpc to use the find_package versions
        cmake.definitions["gRPC_CARES_PROVIDER"] = "package"
        cmake.definitions["gRPC_ZLIB_PROVIDER"] = "package"
        cmake.definitions["gRPC_SSL_PROVIDER"] = "package"
        cmake.definitions["gRPC_PROTOBUF_PROVIDER"] = "package"

        # Workaround for https://github.com/grpc/grpc/issues/11068
        if self.options.build_tests:
            cmake.definitions["gRPC_GFLAGS_PROVIDER"] = "package"
            cmake.definitions["gRPC_BENCHMARK_PROVIDER"] = "package"
        else:
            cmake.definitions["gRPC_GFLAGS_PROVIDER"] = ""
            cmake.definitions["gRPC_BENCHMARK_PROVIDER"] = ""

        cmake.configure(build_folder=self._build_subfolder)
        return cmake

    #   def build(self):
    #       env_build = RunEnvironment(self)
    #       with tools.environment_append(env_build.vars):
    #           cmake = self._configure_cmake()
    #           self.run('cmake "%s" %s' % (self.source_folder, cmake.command_line), run_environment=True)
    #           self.run('cmake --build . %s' % cmake.build_config, run_environment=True)

    def package(self):
        env_build = RunEnvironment(self)
        with tools.environment_append(env_build.vars):
            cmake = self._configure_cmake()
            self.run('cmake "%s" %s' % (self.source_folder, cmake.command_line), run_environment=True)
            self.run("cmake --build . %s" % cmake.build_config, run_environment=True)
            self.run("cmake --build . --target install", run_environment=True)

        self.copy(pattern="LICENSE", dst="licenses")
        self.copy("*", dst="include", src="{}/include".format(self._source_subfolder))
        self.copy("*.cmake", dst="lib", src="{}/lib".format(self._build_subfolder), keep_path=True)
        self.copy("*.lib", dst="lib", src="", keep_path=False)
        self.copy("*.a", dst="lib", src="", keep_path=False)
        self.copy("*", dst="bin", src="bin")
        self.copy("*.dll", dst="bin", keep_path=False)
        self.copy("*.so", dst="lib", keep_path=False)
        self.copy("*.dylib", dst="lib", keep_path=False)

    def package_info(self):
        self.env_info.path.append(os.path.join(self.package_folder, "bin"))
        self.cpp_info.libs = [
            "grpc",
            "grpc++",
            "grpc_unsecure",
            "grpc++_unsecure",
            "grpc_cli",
            "gpr",
            "address_sorting",
            "grpc_node_plugin",
            "grpc_python_plugin",
        ]
        if self.settings.compiler == "Visual Studio":
            self.cpp_info.libs += ["wsock32", "ws2_32"]
