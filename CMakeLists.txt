cmake_minimum_required(VERSION 3.27)

project(server)
find_library(COMMONLIB common)

if(NOT ${COMMONLIB})
  set(FETCHCONTENT_QUIET OFF)
  include(FetchContent)
  FetchContent_Declare(
    common
    GIT_REPOSITORY https://github.com/mc-nv/common.git
    GIT_TAG        main
  )
  FetchContent_MakeAvailable(common)
  install(TARGETS common DESTINATION ${CMAKE_BINARY_DIR})
endif(NOT ${COMMONLIB})

# find_package(gRPC)

# if(NOT gRPC_FOUND)
#   set(FETCHCONTENT_QUIET OFF)
#   include(FetchContent)
#   FetchContent_Declare(
#     gRPC
#     GIT_REPOSITORY https://github.com/grpc/grpc.git
#     GIT_TAG        v1.52.0
#   )
#   FetchContent_MakeAvailable(gRPC)
#   install(TARGETS grpc DESTINATION ${CMAKE_BINARY_DIR})
# endif(NOT gRPC_FOUND)

set(TESTH "test.h")

function(message_func)
  message("This is a message from the server")
  message("TESTH: ${TESTH}")
endfunction()

find_library(ONNXRUNTIME onnxruntime)

if(NOT ${ONNXRUNTIME})
# Download onnxruntime
  include(download_onnxruntime.cmake)
endif(NOT ${ONNXRUNTIME})
message_func()

add_executable(server server.cpp)

target_link_libraries(server common)


install(TARGETS server DESTINATION ${CMAKE_BINARY_DIR})