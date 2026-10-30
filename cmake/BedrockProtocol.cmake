# BedrockProtocol.cmake
#
# Usage:
#     include(BedrockProtocol)
#     bedrock_protocol_generate(
#         TARGET      bedrock-protocol
#         INPUTS      protocol/packet.py
#         IMPORT_DIRS protocol
#         OUT_VAR     generated_sources)

if(DEFINED _BEDROCK_PROTOCOL_INCLUDED)
    return()
endif()
set(_BEDROCK_PROTOCOL_INCLUDED TRUE)

set(_compiler_dir "${CMAKE_CURRENT_LIST_DIR}/..")

# Re-run codegen when any compiler source or template changes.
file(GLOB_RECURSE _compiler_sources CONFIGURE_DEPENDS
    "${_compiler_dir}/src/bedrock_protocol/*.py"
    "${_compiler_dir}/pyproject.toml")

find_package(Python COMPONENTS Interpreter REQUIRED)
if(WIN32)
    set(_compiler_exe "${CMAKE_BINARY_DIR}/bpc.cmd")
    file(WRITE "${_compiler_exe}"
        "@set \"PYTHONPATH=${_compiler_dir}/src\"\r\n@set PYTHONUTF8=1\r\n@\"${Python_EXECUTABLE}\" -m bedrock_protocol %*\r\n")
else()
    set(_compiler_exe "${CMAKE_BINARY_DIR}/bpc")
    file(WRITE "${_compiler_exe}"
        "#!/bin/sh\nexport PYTHONPATH=\"${_compiler_dir}/src\"\nexec \"${Python_EXECUTABLE}\" -m bedrock_protocol \"$@\"\n")
    file(CHMOD "${_compiler_exe}" PERMISSIONS OWNER_READ OWNER_WRITE OWNER_EXECUTE GROUP_READ GROUP_EXECUTE WORLD_READ WORLD_EXECUTE)
endif()

add_executable(bedrock_protocol_compiler IMPORTED GLOBAL)
set_target_properties(bedrock_protocol_compiler PROPERTIES
    IMPORTED_LOCATION "${_compiler_exe}")
add_executable(bedrock::protocol_compiler ALIAS bedrock_protocol_compiler)

function(bedrock_protocol_generate)
    set(_options APPEND_PATH)
    set(_oneValueArgs
        OUT_VAR
        COMPILER_EXE
        COMPILER_OUT_DIR
        TARGET)
    set(_multiValueArgs
        DEPENDENCIES
        INPUTS
        IMPORT_DIRS
        COMPILER_OPTIONS)
    cmake_parse_arguments(BP
        "${_options}" "${_oneValueArgs}" "${_multiValueArgs}" ${ARGN})

    if(NOT BP_COMPILER_OUT_DIR)
        set(BP_COMPILER_OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}")
    endif()

    # INPUTS defaults to the TARGET's .py sources.
    if(NOT BP_INPUTS)
        if(NOT BP_TARGET)
            message(FATAL_ERROR
                "bedrock_protocol_generate: INPUTS or TARGET (with .py sources) is required")
        endif()
        get_target_property(_tgt_sources ${BP_TARGET} SOURCES)
        if(_tgt_sources)
            foreach(s IN LISTS _tgt_sources)
                if(s MATCHES "\\.py$")
                    list(APPEND BP_INPUTS "${s}")
                endif()
            endforeach()
        endif()
        if(NOT BP_INPUTS)
            message(FATAL_ERROR
                "bedrock_protocol_generate: target '${BP_TARGET}' has no .py sources")
        endif()
    endif()

    # Absolutise inputs and import dirs.
    set(_abs_inputs)
    foreach(p IN LISTS BP_INPUTS)
        if(NOT IS_ABSOLUTE "${p}")
            set(p "${CMAKE_CURRENT_SOURCE_DIR}/${p}")
        endif()
        get_filename_component(p "${p}" ABSOLUTE)
        list(APPEND _abs_inputs "${p}")
    endforeach()

    set(_import_dirs)
    foreach(d IN LISTS BP_IMPORT_DIRS)
        if(NOT IS_ABSOLUTE "${d}")
            set(d "${CMAKE_CURRENT_SOURCE_DIR}/${d}")
        endif()
        get_filename_component(d "${d}" ABSOLUTE)
        list(APPEND _import_dirs "${d}")
    endforeach()
    if(BP_APPEND_PATH)
        foreach(p IN LISTS _abs_inputs)
            get_filename_component(_dir "${p}" DIRECTORY)
            list(APPEND _import_dirs "${_dir}")
        endforeach()
    endif()
    if(_import_dirs)
        list(REMOVE_DUPLICATES _import_dirs)
    endif()

    # Resolve the compiler invocation.
    if(NOT BP_COMPILER_EXE)
        set(BP_COMPILER_EXE bedrock::protocol_compiler)
    endif()
    set(_compiler_dep)
    if(TARGET ${BP_COMPILER_EXE})
        set(_compiler_cmd "$<TARGET_FILE:${BP_COMPILER_EXE}>")
        set(_compiler_dep ${BP_COMPILER_EXE})
    else()
        set(_compiler_cmd ${BP_COMPILER_EXE})
    endif()

    # Pass each import dir to bpc as --import-path so it can resolve
    # `from X.Y import ...` references between inputs when invoked one
    # input at a time. Mirrors protoc's --proto_path.
    set(_import_args)
    foreach(d IN LISTS _import_dirs)
        list(APPEND _import_args --import-path "${d}")
    endforeach()

    # One parse supplies all per-schema translation units.
    set(_generated)
    foreach(p IN LISTS _abs_inputs)
        # Every input lands directly in COMPILER_OUT_DIR, which is the one
        # directory the emitted `#include <bedrock/protocol/...>` lines name.
        get_filename_component(_stem "${p}" NAME_WE)
        # The generated header pairs with a compiled .cpp, so it is `.h`, not
        # `.hpp` (which is reserved for the header-only runtime support).
        set(_out_hdr "${BP_COMPILER_OUT_DIR}/${_stem}.h")
        set(_out_cpp "${BP_COMPILER_OUT_DIR}/${_stem}.cpp")

        # protobuf_generate keeps one flat list of every generated file (both
        # the .h and the .cpp), not separate header/source lists.
        list(APPEND _generated "${_out_hdr}" "${_out_cpp}")
    endforeach()

    add_custom_command(
        OUTPUT ${_generated}
        COMMAND ${CMAKE_COMMAND} -E make_directory "${BP_COMPILER_OUT_DIR}"
        COMMAND ${_compiler_cmd} --language cpp --out "${BP_COMPILER_OUT_DIR}" ${_import_args}
                ${BP_COMPILER_OPTIONS} ${_abs_inputs}
        DEPENDS ${_abs_inputs} ${BP_DEPENDENCIES} ${_compiler_dep} ${_compiler_sources}
        WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"
        COMMENT "bpc: generating C++ schema"
        VERBATIM)

    if(BP_TARGET)
        get_target_property(_target_type ${BP_TARGET} TYPE)
        if(_target_type STREQUAL "INTERFACE_LIBRARY")
            # custom_command OUTPUTs are directory-scoped; wrap them in a
            # custom_target (which is global) so consumers in sibling dirs
            # can reach the codegen rule.
            add_custom_target(${BP_TARGET}_codegen DEPENDS ${_generated})
            add_dependencies(${BP_TARGET} ${BP_TARGET}_codegen)
        else()
            # The .cpp bodies compile into the library; the paired .h rides
            # along for IDE / dependency tracking, as protobuf_generate does.
            target_sources(${BP_TARGET} PRIVATE ${_generated})
        endif()
    endif()
    if(BP_OUT_VAR)
        set(${BP_OUT_VAR} ${_generated} PARENT_SCOPE)
    endif()
endfunction()
