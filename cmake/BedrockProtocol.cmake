# BedrockProtocol.cmake — provides bedrock_protocol_generate(), the moral
# equivalent of protobuf_generate() for our DSL/codegen.
#
# Usage:
#     include(BedrockProtocol)
#     add_executable(my_app main.cpp)
#     bedrock_protocol_generate(
#         TARGET   my_app
#         PACKETS  packets/disconnect_packet.py
#         OUT_DIR  ${CMAKE_CURRENT_BINARY_DIR}/bedrock_generated   # optional
#     )

if(DEFINED _BEDROCK_PROTOCOL_INCLUDED)
    return()
endif()
set(_BEDROCK_PROTOCOL_INCLUDED TRUE)

find_package(Python3 REQUIRED COMPONENTS Interpreter)

# Directory that contains the `bpc` Python package — added to PYTHONPATH
# whenever we invoke `python -m bpc`.
set(BEDROCK_PROTOCOL_PACKAGE_ROOT
    "${CMAKE_CURRENT_LIST_DIR}/.."
    CACHE PATH "Directory containing the bpc Python package")

set(_bpc_package_dir "${BEDROCK_PROTOCOL_PACKAGE_ROOT}/bpc")
set(_bpc_sources
    "${_bpc_package_dir}/__main__.py"
    "${_bpc_package_dir}/dsl.py"
    "${_bpc_package_dir}/templates/packet.h.j2"
    "${_bpc_package_dir}/templates/packet.cpp.j2")

function(bedrock_protocol_generate)
    set(options HEADER_ONLY)
    set(oneValueArgs TARGET OUT_DIR)
    set(multiValueArgs PACKETS)
    cmake_parse_arguments(BP "${options}" "${oneValueArgs}" "${multiValueArgs}" ${ARGN})

    if(NOT BP_TARGET)
        message(FATAL_ERROR "bedrock_protocol_generate: TARGET is required")
    endif()
    if(NOT BP_PACKETS)
        message(FATAL_ERROR "bedrock_protocol_generate: PACKETS is required")
    endif()
    if(NOT BP_OUT_DIR)
        set(BP_OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}/bedrock_generated")
    endif()
    file(MAKE_DIRECTORY "${BP_OUT_DIR}")

    # Resolve packet inputs to absolute paths.
    set(_packet_inputs)
    foreach(p IN LISTS BP_PACKETS)
        if(NOT IS_ABSOLUTE "${p}")
            set(p "${CMAKE_CURRENT_SOURCE_DIR}/${p}")
        endif()
        list(APPEND _packet_inputs "${p}")
    endforeach()

    set(_codegen_flags)
    if(BP_HEADER_ONLY)
        list(APPEND _codegen_flags "--header-only")
    endif()

    set(_bpc_invocation
        ${CMAKE_COMMAND} -E env "PYTHONPATH=${BEDROCK_PROTOCOL_PACKAGE_ROOT}"
        "${Python3_EXECUTABLE}" -m bpc)

    # Enumerate generated outputs at configure time so we can hand them to
    # add_custom_command() / target_sources().
    execute_process(
        COMMAND ${_bpc_invocation}
                --out "${BP_OUT_DIR}" --list-outputs ${_codegen_flags}
                ${_packet_inputs}
        OUTPUT_VARIABLE _outputs_raw
        RESULT_VARIABLE _outputs_rc
        ERROR_VARIABLE  _outputs_err
        OUTPUT_STRIP_TRAILING_WHITESPACE)
    if(NOT _outputs_rc EQUAL 0)
        message(FATAL_ERROR
            "bedrock_protocol_generate: failed to enumerate outputs\n${_outputs_err}")
    endif()
    string(REPLACE "\n" ";" _generated "${_outputs_raw}")

    add_custom_command(
        OUTPUT  ${_generated}
        COMMAND ${_bpc_invocation}
                --out "${BP_OUT_DIR}" ${_codegen_flags} ${_packet_inputs}
        DEPENDS ${_packet_inputs} ${_bpc_sources}
        WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"
        COMMENT "bpc: generating bedrock-protocol sources for ${BP_TARGET}"
        VERBATIM)

    target_sources(${BP_TARGET} PRIVATE ${_generated})
    target_include_directories(${BP_TARGET} PUBLIC "${BP_OUT_DIR}")
endfunction()
