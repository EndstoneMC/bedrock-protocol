find_package(OpenSSL REQUIRED COMPONENTS Crypto)
find_package(ZLIB REQUIRED)
find_package(Snappy CONFIG REQUIRED)

add_library(bedrock_protocol_wire STATIC batch.cpp crypto.cpp)
add_library(bedrock::protocol_wire ALIAS bedrock_protocol_wire)
set_target_properties(bedrock_protocol_wire PROPERTIES POSITION_INDEPENDENT_CODE ON EXPORT_NAME protocol_wire)
target_compile_features(bedrock_protocol_wire PUBLIC cxx_std_23)
target_include_directories(bedrock_protocol_wire PUBLIC
    "$<BUILD_INTERFACE:${PROJECT_SOURCE_DIR}/include>"
    "$<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}>")
target_link_libraries(bedrock_protocol_wire PUBLIC OpenSSL::Crypto ZLIB::ZLIB Snappy::snappy)

if (BEDROCK_PROTOCOL_INSTALL)
    install(TARGETS bedrock_protocol_wire EXPORT bedrock-protocol-targets ARCHIVE DESTINATION "${CMAKE_INSTALL_LIBDIR}")
    install(DIRECTORY "${PROJECT_SOURCE_DIR}/include/bedrock/protocol/wire"
        DESTINATION "${CMAKE_INSTALL_INCLUDEDIR}/bedrock/protocol" FILES_MATCHING PATTERN "*.h")
    install(FILES "${CMAKE_CURRENT_SOURCE_DIR}/NOTICE"
        DESTINATION "${CMAKE_INSTALL_DATAROOTDIR}/licenses/bedrock-protocol")
endif ()
