message(NOTICE "Downloading onnxruntime")

# Define the download and extraction paths)
set(DOWNLOAD_PATH "${CMAKE_BINARY_DIR}/downloads/onnxruntime.zip")
set(EXTRACT_DIR "${CMAKE_BINARY_DIR}/onnxruntime")

# Download the file
file(DOWNLOAD $ENV{TRITON_ONNXRUNTIME_PACKAGE_URL} ${DOWNLOAD_PATH} SHOW_PROGRESS STATUS DOWNLOAD_STATUS)

# Check the download status
list(GET DOWNLOAD_STATUS 0 DOWNLOAD_RESULT)
if(NOT DOWNLOAD_RESULT EQUAL 0)
    message(SEND_ERROR "Failed to download ${ONNXRUNTIME_PACKAGE_URL}")
else()
    message(NOTICE "Download successful: ${DOWNLOAD_PATH}" )

    # Extract the downloaded file
    file(ARCHIVE_EXTRACT INPUT ${DOWNLOAD_PATH} DESTINATION ${EXTRACT_DIR} VERBOSE )

    # Make the extracted directory searchable for CMake
    list(APPEND CMAKE_PREFIX_PATH ${EXTRACT_DIR})

    # Find a specific library in the extracted folder
    find_library(ONNXRUNTIME_LIB onnxruntime PATHS ${EXTRACT_DIR} NO_DEFAULT_PATH)

    if(ONNXRUNTIME_LIB)
        message(NOTICE "Found onnxruntime library: ${ONNXRUNTIME_LIB}")
    else()
        message(SEND_ERROR "onnxruntime library not found in ${EXTRACT_DIR}")
    endif()
endif()