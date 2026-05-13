# BedrockProtocol.cmake — bedrock_protocol_generate(), modelled on
# protobuf_generate() from the upstream Protobuf CMake module.
#
# Usage:
#     include(BedrockProtocol)
#     bedrock_protocol_generate(
#         TARGET      my_lib
#         INPUTS      protocol/helloworld/helloworld.py
#         IMPORT_DIRS protocol
#         OUT_VAR     generated_sources)

if(DEFINED _BEDROCK_PROTOCOL_INCLUDED)
    return()
endif()
set(_BEDROCK_PROTOCOL_INCLUDED TRUE)

set(_compiler_dir "${CMAKE_CURRENT_LIST_DIR}/../compiler")

# Re-run codegen when any compiler source or template changes.
file(GLOB_RECURSE _compiler_sources CONFIGURE_DEPENDS
    "${_compiler_dir}/*.py"
    "${_compiler_dir}/templates/*")

# bpc is a uv script (PEP 723 inline deps). The Unix shebang doesn't fire on
# Windows, so generate a tiny wrapper per-platform that always goes through
# `uv run --script`, and point the imported target at it.
find_program(UV_EXECUTABLE uv)
if(NOT UV_EXECUTABLE)
    message(FATAL_ERROR
        "bedrock-protocol: uv is required to run the bpc compiler. "
        "Install it from https://docs.astral.sh/uv/")
endif()

if(WIN32)
    set(_compiler_exe "${CMAKE_BINARY_DIR}/bedrock_protocol_compiler.cmd")
    file(WRITE "${_compiler_exe}"
        "@\"${UV_EXECUTABLE}\" run --script \"${_compiler_dir}/main.py\" %*\r\n")
else()
    set(_compiler_exe "${CMAKE_BINARY_DIR}/bedrock_protocol_compiler")
    file(WRITE "${_compiler_exe}"
        "#!/bin/sh\nexec \"${UV_EXECUTABLE}\" run --script \"${_compiler_dir}/main.py\" \"$@\"\n")
    file(CHMOD "${_compiler_exe}" PERMISSIONS
        OWNER_READ OWNER_WRITE OWNER_EXECUTE
        GROUP_READ GROUP_EXECUTE
        WORLD_READ WORLD_EXECUTE)
endif()

add_executable(bedrock_protocol_compiler IMPORTED GLOBAL)
set_target_properties(bedrock_protocol_compiler PROPERTIES
    IMPORTED_LOCATION "${_compiler_exe}")
add_executable(bedrock::protocol_compiler ALIAS bedrock_protocol_compiler)

function(bedrock_protocol_generate)
    set(_options APPEND_PATH)
    set(_oneValueArgs
        OUT_VAR
        PROTOC_EXE
        PROTOC_OUT_DIR
        TARGET)
    set(_multiValueArgs
        DEPENDENCIES
        INPUTS
        IMPORT_DIRS
        PROTOC_OPTIONS)
    cmake_parse_arguments(BP
        "${_options}" "${_oneValueArgs}" "${_multiValueArgs}" ${ARGN})

    if(NOT BP_PROTOC_OUT_DIR)
        set(BP_PROTOC_OUT_DIR "${CMAKE_CURRENT_BINARY_DIR}")
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
    if(NOT BP_PROTOC_EXE)
        set(BP_PROTOC_EXE bedrock::protocol_compiler)
    endif()
    set(_protoc_dep)
    if(TARGET ${BP_PROTOC_EXE})
        set(_protoc_cmd "$<TARGET_FILE:${BP_PROTOC_EXE}>")
        set(_protoc_dep ${BP_PROTOC_EXE})
    else()
        set(_protoc_cmd ${BP_PROTOC_EXE})
    endif()

    # One custom_command per input keeps the per-file output path simple.
    set(_outputs)
    foreach(p IN LISTS _abs_inputs)
        # Shortest valid subpath under any import_dir wins; otherwise use the
        # basename so the input still produces something.
        set(_rel "")
        foreach(d IN LISTS _import_dirs)
            file(RELATIVE_PATH _cand "${d}" "${p}")
            if(NOT _cand MATCHES "^\\.\\.")
                if(_rel STREQUAL "")
                    set(_rel "${_cand}")
                else()
                    string(LENGTH "${_cand}" _cand_len)
                    string(LENGTH "${_rel}"  _rel_len)
                    if(_cand_len LESS _rel_len)
                        set(_rel "${_cand}")
                    endif()
                endif()
            endif()
        endforeach()
        if(_rel STREQUAL "")
            get_filename_component(_rel "${p}" NAME)
        endif()
        string(REGEX REPLACE "\\.py$" ".hpp" _rel "${_rel}")
        set(_out "${BP_PROTOC_OUT_DIR}/${_rel}")
        get_filename_component(_out_dir "${_out}" DIRECTORY)

        add_custom_command(
            OUTPUT  "${_out}"
            COMMAND ${CMAKE_COMMAND} -E make_directory "${_out_dir}"
            COMMAND ${_protoc_cmd}
                    --out "${_out_dir}" ${BP_PROTOC_OPTIONS} "${p}"
            DEPENDS "${p}" ${BP_DEPENDENCIES} ${_protoc_dep} ${_compiler_sources}
            WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"
            COMMENT "bpc: generating ${_rel}"
            VERBATIM)

        list(APPEND _outputs "${_out}")
    endforeach()

    if(BP_TARGET)
        get_target_property(_target_type ${BP_TARGET} TYPE)
        if(_target_type STREQUAL "INTERFACE_LIBRARY")
            target_sources(${BP_TARGET} INTERFACE ${_outputs})
            target_include_directories(${BP_TARGET} INTERFACE "${BP_PROTOC_OUT_DIR}")
        else()
            target_sources(${BP_TARGET} PRIVATE ${_outputs})
            target_include_directories(${BP_TARGET} PUBLIC "${BP_PROTOC_OUT_DIR}")
        endif()
    endif()
    if(BP_OUT_VAR)
        set(${BP_OUT_VAR} ${_outputs} PARENT_SCOPE)
    endif()
endfunction()
