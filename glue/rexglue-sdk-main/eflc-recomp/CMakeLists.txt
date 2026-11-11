cmake_minimum_required(VERSION 3.25)
project(eflc_recomp LANGUAGES CXX)

# Separate application for the standalone Xbox 360 Episodes from Liberty City
# disc. It shares the RexGlue runtime with gta4-recomp but none of its title
# hooks, installer or identity. Enable with -DREXGLUE_BUILD_EFLC_RECOMP=ON.

set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

if(TARGET rex::rexglue)
    add_custom_target(eflc_codegen
        COMMAND $<TARGET_FILE:rex::rexglue> codegen
                ${CMAKE_CURRENT_SOURCE_DIR}/eflc_manifest.toml
        WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
        COMMENT "Generating recompiled code for Episodes from Liberty City"
        VERBATIM
    )
endif()

if(NOT EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/generated/sources.cmake")
    message(WARNING
        "eflc-recomp generated sources are missing, so the EFLC app is not "
        "configured. Place your own executable at eflc-recomp/assets/"
        "default_eflc.xex and build the 'eflc_codegen' target (or run "
        "'rexglue codegen eflc_manifest.toml' in eflc-recomp/), then reconfigure.")
    return()
endif()

include(generated/sources.cmake)

add_executable(EFLCRecomp
    src/main.cpp
    ${GENERATED_SOURCES}
)

target_include_directories(EFLCRecomp PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/src
    ${CMAKE_CURRENT_SOURCE_DIR}/generated
)

target_link_libraries(EFLCRecomp PRIVATE rex::runtime)

# First boot uses the generic Xenos renderer only. Add the gta4-native plugin
# after its title-specific hooks have been ported to the EFLC executable.
rexglue_configure_target(EFLCRecomp GPU_PLUGINS xenos)

set_target_properties(EFLCRecomp PROPERTIES
    OUTPUT_NAME "EFLC Recompiled"
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/EFLCRecomp"
)
