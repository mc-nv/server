# Copyright 2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.

from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout

from conan import ConanFile


class TritonServerConan(ConanFile):
    """Dependencies of the server build, and the entry point that drives it.

        conan build . --build=missing -o "&:metrics_gpu=False"

    Each option below selects the packages a feature needs and sets the
    matching TRITON_* CMake option, so the two cannot disagree. CMake options
    that pull in no package are passed to CMake directly.
    """

    settings = "os", "compiler", "build_type", "arch"

    # Option name -> CMake cache variable it sets.
    _cmake_options = {
        "gpu": "TRITON_ENABLE_GPU",
        "http": "TRITON_ENABLE_HTTP",
        "metrics": "TRITON_ENABLE_METRICS",
        "metrics_gpu": "TRITON_ENABLE_METRICS_GPU",
        "sagemaker": "TRITON_ENABLE_SAGEMAKER",
        "vertex_ai": "TRITON_ENABLE_VERTEX_AI",
        "tracing": "TRITON_ENABLE_TRACING",
        "gcs": "TRITON_ENABLE_GCS",
        "s3": "TRITON_ENABLE_S3",
        "azure_storage": "TRITON_ENABLE_AZURE_STORAGE",
        "python_backend": "TRITON_PYTHON_BACKEND",
        "development_local": "TRITON_DEVELOPMENT_LOCAL",
    }
    options = {name: [True, False] for name in _cmake_options}
    # Same defaults as the option() calls in CMakeLists.txt.
    default_options = {
        "gpu": True,
        "http": True,
        "metrics": True,
        "metrics_gpu": True,
        "sagemaker": False,
        "vertex_ai": False,
        "tracing": False,
        "gcs": False,
        "s3": False,
        "azure_storage": False,
        "python_backend": False,
        "development_local": False,
        "boost/*:header_only": True,
        # Triton uses the OTLP *HTTP* exporter only; the gRPC one would pull a
        # second gRPC and, with it, a second abseil.
        "opentelemetry-cpp/*:with_otlp_grpc": False,
        "opentelemetry-cpp/*:with_otlp_http": True,
        # Mirrors third_party (-DBUILD_ONLY=s3 -DMINIMIZE_SIZE=ON). Leaving
        # text-to-speech on pulls pulseaudio and, through it, X11.
        "aws-sdk-cpp/*:s3": True,
        "aws-sdk-cpp/*:text-to-speech": False,
        "aws-sdk-cpp/*:min_size": True,
    }

    def configure(self):
        # http_server.cc reads request timing fields that evhtp.h declares only
        # when the package itself was built with tracing.
        self.options["libevhtp"].enable_tracing = self.options.tracing

    def requirements(self):
        # gRPC and the packages it is built against, at the versions gRPC
        # v1.81.1 vendors. Triton's grpc and google-cloud-cpp recipes live on
        # the triton-conan remote, which must come before conancenter:
        # ConanCenter's grpc/1.81.1 pairs it with an abseil it does not compile
        # against and an re2 that conflicts with the pin below, and its
        # google-cloud-cpp asks for grpc/1.54.3.
        self.requires("grpc/1.81.1")
        self.requires("abseil/20250512.1")
        self.requires("protobuf/6.33.5")
        self.requires("re2/20230301")
        self.requires("c-ares/1.34.6")
        self.requires("rapidjson/cci.20230929")
        self.requires("b64/2.0.0.1")
        self.requires("boost/1.85.0")
        self.requires("gtest/1.14.0")

        o = self.options
        if o.python_backend:
            # pb_env.cc unpacks conda environments.
            self.requires("libarchive/3.7.6")
        if o.gpu:
            self.requires("cnmem/1.0.0")
        if o.metrics:
            self.requires("prometheus-cpp/1.2.4")
        if o.http or o.metrics or o.sagemaker or o.vertex_ai:
            self.requires("libevent/2.1.12")
            self.requires("libevhtp/1.2.18")
        if o.tracing:
            self.requires("libcurl/8.18.0")
            self.requires("nlohmann_json/3.11.3")
            # 1.22.0, not third_party's v1.13.0: that declares
            # cmake_minimum_required(3.1), which CMake 4 refuses.
            self.requires("opentelemetry-cpp/1.22.0")
        if o.gcs:
            self.requires("google-cloud-cpp/2.28.0")
            self.requires("crc32c/1.1.2")
        if o.s3:
            self.requires("aws-sdk-cpp/1.11.692")
        if o.azure_storage:
            self.requires("azure-sdk-for-cpp/1.16.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        # The profile's cppstd says how the packages were built (gnu17, which
        # the published binaries' IDs depend on). Triton's own sources set
        # their standard in CMakeLists.txt; do not let the toolchain override it.
        tc.blocks.remove("cppstd")
        for name, variable in self._cmake_options.items():
            tc.cache_variables[variable] = bool(self.options.get_safe(name))
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
