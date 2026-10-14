# Copyright 2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.

cmake_minimum_required(VERSION 3.31.8)

# Must precede project(): TRITON_VERSION_NUMERIC is needed to satisfy VERSION below.
list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/cmake")
include(TritonUtils)
include(TritonCompilerCache)

triton_server_read_version("${CMAKE_CURRENT_SOURCE_DIR}/TRITON_VERSION"
                           TRITON_VERSION TRITON_VERSION_NUMERIC)

project(tritonserver VERSION ${TRITON_VERSION_NUMERIC} LANGUAGES C CXX)

# C++ standard is defined once here and inherited by every subdirectory. CACHE is
# required for -DCMAKE_CXX_STANDARD=<n> to take effect: a plain set() would shadow
# the command-line value instead of deferring to it.
set(CMAKE_CXX_STANDARD 20 CACHE STRING
    "The minimum C++ standard which features are requested to build this target.")
set_property(CACHE CMAKE_CXX_STANDARD PROPERTY STRINGS 20 23)
# src/ and the common/core/backend subprojects request the standard per target
# through cxx_std_${TRITON_MIN_CXX_STANDARD}; keep it in step with the above.
set(TRITON_MIN_CXX_STANDARD ${CMAKE_CXX_STANDARD} CACHE STRING
    "The minimum C++ standard which features are requested to build this target.")
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

triton_server_cache_enable_compiler()

# Conan's CMakeDeps configs call check_build_type_defined() and abort when no
# build type is set, so single-config generators need a default here.
get_property(_triton_multi_config GLOBAL PROPERTY GENERATOR_IS_MULTI_CONFIG)
if(NOT _triton_multi_config AND NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release CACHE STRING "Build type" FORCE)
  set_property(CACHE CMAKE_BUILD_TYPE PROPERTY STRINGS
               Debug Release RelWithDebInfo MinSizeRel)
endif()

#
# Feature options
#
option(TRITON_ENABLE_LOGGING "Include logging support in server" ON)
option(TRITON_ENABLE_STATS "Include statistics collections in server" ON)
option(TRITON_ENABLE_TRACING "Include tracing support in server" OFF)
option(TRITON_ENABLE_NVTX "Include NVTX support in server" OFF)
option(TRITON_ENABLE_GPU "Enable GPU support in server" ON)
option(TRITON_ENABLE_MALI_GPU "Enable Arm Mali GPU support in server" OFF)
option(TRITON_IGPU_BUILD "Enable options for iGPU compilation in server" OFF)
option(TRITON_ENABLE_ENSEMBLE "Include ensemble support in server" OFF)

# Endpoints
option(TRITON_ENABLE_HTTP "Include HTTP API in server" ON)
option(TRITON_ENABLE_GRPC "Include GRPC API in server" ON)
option(TRITON_ENABLE_SAGEMAKER "Include AWS SageMaker API in server" OFF)
option(TRITON_ENABLE_VERTEX_AI "Include Vertex AI API in server" OFF)

# Metrics
option(TRITON_ENABLE_METRICS "Include metrics support in server" ON)
option(TRITON_ENABLE_METRICS_GPU "Include GPU metrics support in server" ON)
option(TRITON_ENABLE_METRICS_CPU "Include CPU metrics support in server" ON)

# Cloud storage
option(TRITON_ENABLE_GCS "Include GCS Filesystem support in server" OFF)
option(TRITON_ENABLE_S3 "Include S3 Filesystem support in server" OFF)
option(TRITON_ENABLE_AZURE_STORAGE "Include Azure Storage Filesystem support in server" OFF)

# Backends built in-tree
#
# CI builds each backend as its own CMake project against its own clones of
# common/core/backend, then copies the result into the shared install tree (the
# per-backend sections of issues/TRI-1611/59624282.374114906.cmake_build.sh --
# every one passes the same flags). Building them here instead shares
# repo-common/core/backend with the server and installs straight to
# ${CMAKE_INSTALL_PREFIX}/backends/<name>, so no copy step is needed.
#
# One option per backend, spelled out so they are greppable and appear in
# cmake -LH alongside every other option rather than being conjured by a loop.
option(TRITON_IDENTITY_BACKEND "Build the identity_backend repository as part of the server" OFF)
option(TRITON_REPEAT_BACKEND   "Build the repeat_backend repository as part of the server" OFF)
option(TRITON_TENSORRT_BACKEND "Build the tensorrt_backend repository as part of the server" OFF)
option(TRITON_PYTHON_BACKEND   "Build the python_backend repository as part of the server" OFF)
option(TRITON_DALI_BACKEND     "Build the dali_backend repository as part of the server" OFF)
option(TRITON_FIL_BACKEND      "Build the fil_backend repository as part of the server" OFF)
option(TRITON_ONNXRUNTIME_BACKEND "Build the onnxruntime_backend repository as part of the server" OFF)
option(TRITON_OPENVINO_BACKEND "Build the openvino_backend repository as part of the server" OFF)

# Repository names, which are also the sibling checkout directories. This drives
# declaration and add_subdirectory in TritonRepos.cmake; the rest is derived from
# each name: the option is TRITON_<REPO> uppercased (identity_backend ->
# TRITON_IDENTITY_BACKEND), the FetchContent content name is repo-<repo> with
# underscores hyphenated (repo-identity-backend), and organisation/tag/local-path
# overrides are generated. INTERNAL because it must stay in step with the options
# above -- adding a backend means one line in each.
set(TRITON_OPTIONAL_BACKENDS identity_backend repeat_backend tensorrt_backend python_backend
                             dali_backend fil_backend onnxruntime_backend openvino_backend
    CACHE INTERNAL "Backend repositories that can be built as part of the server")

# Note these backends link triton-backend-utils from repo-backend, whose
# TRITON_ENABLE_MEMORY_TRACKER option defaults to OFF while CI passes it ON.
# Pass -DTRITON_ENABLE_MEMORY_TRACKER=ON to match; it reaches repo-backend
# directly and needs no forwarding here.

# Testing and diagnostics
option(TRITON_ENABLE_TENSORRT "Include TensorRT backend in server" OFF)
option(TRITON_ENABLE_TESTS "Build unit tests, which require GoogleTest" OFF)
option(TRITON_ENABLE_ASAN "Build with address sanitizer" OFF)

set(TRITON_MIN_COMPUTE_CAPABILITY "7.5" CACHE STRING
    "The minimum CUDA compute capability supported by Triton")

#
# Option consistency
#
# Same constraints the previous root CMakeLists enforced by hand, one call each.
#
triton_server_require_option(TRITON_ENABLE_METRICS TRITON_ENABLE_STATS)
triton_server_require_option(TRITON_ENABLE_TRACING TRITON_ENABLE_STATS)
triton_server_require_option(TRITON_ENABLE_METRICS_CPU TRITON_ENABLE_METRICS)
triton_server_require_option(TRITON_ENABLE_METRICS_GPU TRITON_ENABLE_METRICS)
triton_server_require_option(TRITON_ENABLE_METRICS_GPU TRITON_ENABLE_GPU)
triton_server_forbid_option(TRITON_ENABLE_ASAN TRITON_ENABLE_GPU)

#
# Dependencies
#
# Duplicated from src/CMakeLists.txt. Imported targets created here are inherited
# by add_subdirectory(src), so resolving them at the top level fails fast before
# descending. Guards must stay in sync with the copies in src/.
#
# Packages come from conanfile.py, which installs them and hands CMake a
# toolchain that puts them on CMAKE_PREFIX_PATH. Nothing here talks to Conan.
#
# Threads comes from the toolchain, not Conan; common/CMakeLists.txt:53 needs it.
find_package(Threads REQUIRED)

if(TRITON_ENABLE_GPU)
  # Tied to the host driver; no Conan reference exists.
  find_package(CUDAToolkit REQUIRED)
endif()

if(TRITON_ENABLE_METRICS_GPU)
  # Ships with the datacenter GPU manager and is tied to the host driver, so
  # whatever is installed is the right version. Note the capitalisation: its
  # config is DCGMConfig.cmake and find_package() is case-sensitive.
  find_package(DCGM CONFIG REQUIRED)
endif()

find_package(ZLIB CONFIG REQUIRED)
find_package(OpenSSL CONFIG REQUIRED)

find_package(absl CONFIG REQUIRED)
find_package(Protobuf CONFIG REQUIRED)
find_package(re2 CONFIG REQUIRED)

if(TRITON_ENABLE_GRPC)
  find_package(c-ares CONFIG REQUIRED)
  # The recipe keeps cmake_find_mode=none so gRPC's own gRPCConfig.cmake is
  # used; the recipe's builddirs put it on CMAKE_PREFIX_PATH via the toolchain.
  find_package(gRPC CONFIG REQUIRED)
  message(STATUS "Using gRPC ${gRPC_VERSION} with abseil ${absl_VERSION}, protobuf ${Protobuf_VERSION}")
endif()

find_package(RapidJSON CONFIG REQUIRED)
# RapidJSON's own config exports the all-caps RAPIDJSON_INCLUDE_DIRS; ConanCenter
# generates its config from the package name and exports RapidJSON_INCLUDE_DIRS
# instead. Normalize so consumers can spell it one way -- common/CMakeLists.txt
# does the same for its own subtree.
if(NOT RAPIDJSON_INCLUDE_DIRS)
  set(RAPIDJSON_INCLUDE_DIRS ${RapidJSON_INCLUDE_DIRS})
endif()
find_package(b64 CONFIG REQUIRED)
find_package(Boost REQUIRED)
find_package(GTest CONFIG REQUIRED)

if(TRITON_ENABLE_GPU)
  find_package(cnmem CONFIG REQUIRED)
  # core locates cnmem the old third_party way:
  #   find_library(CNMEM_LIBRARY NAMES cnmem PATHS ${CNMEM_PATH}/lib)
  string(TOUPPER "${CMAKE_BUILD_TYPE}" _triton_cfg)
  if(cnmem_PACKAGE_FOLDER_${_triton_cfg})
    set(CNMEM_PATH "${cnmem_PACKAGE_FOLDER_${_triton_cfg}}" CACHE PATH "cnmem root" FORCE)
  endif()
endif()

if(TRITON_ENABLE_METRICS)
  find_package(prometheus-cpp CONFIG REQUIRED)
endif()

if(TRITON_ENABLE_HTTP OR TRITON_ENABLE_METRICS
    OR TRITON_ENABLE_SAGEMAKER OR TRITON_ENABLE_VERTEX_AI)
  find_package(Libevent CONFIG REQUIRED)
  find_package(libevhtp CONFIG REQUIRED)

  # src/ and src/test/ consume libevent through the module-style
  # LIBEVENT_INCLUDE_DIRS / LIBEVENT_LIBRARIES in four places; Conan exports the
  # libevent::libevent target instead, and the empty variables surface only as
  # "event2/buffer.h: No such file or directory" at compile time.
  if(TARGET libevent::libevent AND NOT LIBEVENT_LIBRARIES)
    string(TOUPPER "${CMAKE_BUILD_TYPE}" _triton_cfg)
    if(libevent_INCLUDE_DIRS_${_triton_cfg})
      set(LIBEVENT_INCLUDE_DIRS "${libevent_INCLUDE_DIRS_${_triton_cfg}}")
    elseif(libevent_PACKAGE_FOLDER_${_triton_cfg})
      set(LIBEVENT_INCLUDE_DIRS "${libevent_PACKAGE_FOLDER_${_triton_cfg}}/include")
    endif()
    set(LIBEVENT_LIBRARIES libevent::libevent)
  endif()
endif()

if(TRITON_ENABLE_TRACING)
  find_package(CURL CONFIG REQUIRED)
  find_package(nlohmann_json CONFIG REQUIRED)
  find_package(opentelemetry-cpp CONFIG REQUIRED)
endif()

if(TRITON_ENABLE_GCS)
  # Triton's recipe preserves upstream's per-component layout, so this is the
  # storage client's own config rather than a consolidated one. Like the gRPC
  # recipe it sets cmake_find_mode=none, meaning CMakeDeps generates nothing and
  # the configs ship inside the package; the recipe's builddirs put them on
  # CMAKE_PREFIX_PATH via the toolchain.
  find_package(google_cloud_cpp_storage REQUIRED)
  find_package(Crc32c CONFIG REQUIRED)
endif()

if(TRITON_ENABLE_S3)
  find_package(AWSSDK REQUIRED COMPONENTS s3)
endif()

if(TRITON_ENABLE_AZURE_STORAGE)
  # One package covers blobs and identity: it exports AzureSDKConfig.cmake, not
  # the per-repo azure-storage-blobs-cpp / azure-identity-cpp configs.
  find_package(AzureSDK CONFIG REQUIRED)
endif()

# src/test asks for GTest in module mode, which looks for GTEST_LIBRARY /
# GTEST_INCLUDE_DIR rather than the config; the old root file did the same
# (CMakeLists.txt.bkp:207).
if(GTest_DIR)
  set(GTEST_ROOT "${GTest_DIR}" CACHE PATH "GoogleTest root for FindGTest" FORCE)
endif()

#
# Triton repositories
#
# Must precede add_subdirectory(src): src/CMakeLists.txt declares and populates
# repo-common, repo-core and repo-backend, and needs these variables set first.
#
include(TritonRepos)

# core defaults TRITON_CORE_HEADERS_ONLY to ON, which builds only the stub
# (core/CMakeLists.txt:34). The old root file set this explicitly
# (CMakeLists.txt.bkp:135); without it libtritonserver.so is a stub and core/src
# -- with its own Boost/Protobuf/AWS/Azure dependencies -- is never configured.
set(TRITON_CORE_HEADERS_ONLY OFF)

triton_server_fetchcontent_declare_repos()

add_subdirectory(src)

# After add_subdirectory(src), which populates repo-common/core/backend that the
# backends link against.
triton_server_add_optional_backends()
