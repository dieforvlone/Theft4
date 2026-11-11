# Builds the five iPhoneOS archives Theft4's iOS target links for its optional
# MoltenVK capability gate (ios/CMakeLists.txt, THEFT4_XENIOS_IOS_LIB_DIR):
#
#   libMoltenVK.a  libMoltenVK_Common.a  libMoltenVK_ShaderConverter.a
#   libspirv-cross.a  libSPIRV-Tools.a
#
# They were previously taken from a sibling XeniOS build. Current XeniOS no
# longer builds MoltenVK for iOS and its iOS configure needs Mesa, a native
# shader-compiler host tool and Apple's Metal Shader Converter, none of which
# these archives use. This project builds them directly from the workspace's
# own pinned sources instead, with the reviewed dependency patches applied by
# tools/setup_repo.py, mirroring thirdparty/MoltenVK/CMakeLists.txt (the
# desktop MoltenVK build) but as static iPhoneOS libraries.
#
# Configure (from the repository root, after tools/setup_repo.py):
#   cmake -S tools/ios-moltenvk -B out/ios-moltenvk -G Xcode \
#     -DCMAKE_SYSTEM_NAME=iOS -DCMAKE_OSX_SYSROOT=iphoneos \
#     -DCMAKE_OSX_ARCHITECTURES=arm64 -DCMAKE_OSX_DEPLOYMENT_TARGET=26.0
#   cmake --build out/ios-moltenvk --config Release --target theft4_ios_moltenvk
# The archives are written to <build>/lib.

cmake_minimum_required(VERSION 3.24)
project(theft4_ios_moltenvk LANGUAGES C CXX OBJC OBJCXX)

if(NOT CMAKE_SYSTEM_NAME STREQUAL "iOS")
    message(FATAL_ERROR "Configure tools/ios-moltenvk with -DCMAKE_SYSTEM_NAME=iOS.")
endif()

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

get_filename_component(THEFT4_ROOT "${CMAKE_CURRENT_LIST_DIR}/../.." ABSOLUTE)
set(MVK_ROOT "${THEFT4_ROOT}/thirdparty/MoltenVK/MoltenVK")
set(SPIRV_CROSS_ROOT "${THEFT4_ROOT}/thirdparty/MoltenVK/SPIRV-Cross")
set(SPIRV_TOOLS_ROOT "${THEFT4_ROOT}/glue/rexglue-sdk-main/thirdparty/spirv-tools")
set(SPIRV_HEADERS_ROOT "${THEFT4_ROOT}/glue/rexglue-sdk-main/thirdparty/spirv-headers")
# The same Vulkan headers the desktop MoltenVK build uses.
set(MVK_VULKAN_HEADERS "${THEFT4_ROOT}/thirdparty/plume/contrib/Vulkan-Headers/include")

foreach(_required
        "${MVK_ROOT}/MoltenVK/MoltenVK/API/mvk_private_api.h"
        "${MVK_ROOT}/MoltenVK/MoltenVK/Commands/MVKMTLBufferRetention.mm"
        "${SPIRV_CROSS_ROOT}/spirv_msl.cpp"
        "${SPIRV_TOOLS_ROOT}/CMakeLists.txt"
        "${SPIRV_HEADERS_ROOT}/include/spirv/unified1/spirv.core.grammar.json"
        "${MVK_VULKAN_HEADERS}/vulkan/vulkan_core.h")
    if(NOT EXISTS "${_required}")
        message(FATAL_ERROR
            "Missing ${_required}. Run python3 tools/setup_repo.py first; it "
            "initializes the pinned submodules and applies the reviewed patches.")
    endif()
endforeach()

# Every archive lands in one directory, without a per-configuration suffix.
set(THEFT4_IOS_LIB_DIR "${CMAKE_BINARY_DIR}/lib")
foreach(_config "" _DEBUG _RELEASE _RELWITHDEBINFO _MINSIZEREL)
    set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY${_config} "${THEFT4_IOS_LIB_DIR}")
endforeach()

# --- Version and revision, as in thirdparty/MoltenVK/CMakeLists.txt ---------
find_package(Git)
set(MVK_GIT_REV "")
if(GIT_FOUND)
    execute_process(COMMAND ${GIT_EXECUTABLE} rev-parse --short HEAD
        OUTPUT_VARIABLE MVK_GIT_REV
        WORKING_DIRECTORY "${MVK_ROOT}"
        ERROR_QUIET OUTPUT_STRIP_TRAILING_WHITESPACE)
endif()
set(MVK_GENERATED_INCLUDES "${CMAKE_CURRENT_BINARY_DIR}/Generated")
file(WRITE "${MVK_GENERATED_INCLUDES}/mvkGitRevDerived.h"
    "static const char* mvkRevString = \"${MVK_GIT_REV}\";")

file(READ "${MVK_ROOT}/MoltenVK/MoltenVK/API/mvk_private_api.h" MVK_PRIVATE_API)
foreach(_part MAJOR MINOR PATCH)
    string(REGEX MATCH "#define MVK_VERSION_${_part}   [0-9]+" _line "${MVK_PRIVATE_API}")
    string(REGEX MATCH "[0-9]+" MVK_VERSION_${_part} "${_line}")
endforeach()
set(MVK_VERSION "${MVK_VERSION_MAJOR}.${MVK_VERSION_MINOR}.${MVK_VERSION_PATCH}")
message(STATUS "MoltenVK ${MVK_VERSION} (${MVK_GIT_REV}) for iPhoneOS")

# --- Cereal headers at the revision this MoltenVK pin expects ---------------
include(FetchContent)
file(STRINGS "${MVK_ROOT}/ExternalRevisions/cereal_repo_revision"
    MVK_CEREAL_REVISION LIMIT_COUNT 1)
FetchContent_Declare(mvk_cereal
    GIT_REPOSITORY https://github.com/USCiLab/cereal.git
    GIT_TAG "${MVK_CEREAL_REVISION}"
    SOURCE_SUBDIR include)
FetchContent_MakeAvailable(mvk_cereal)

# --- libspirv-cross.a: core + GLSL + MSL + reflection in one archive --------
add_library(spirv-cross STATIC
    "${SPIRV_CROSS_ROOT}/spirv_cross.cpp"
    "${SPIRV_CROSS_ROOT}/spirv_cross_parsed_ir.cpp"
    "${SPIRV_CROSS_ROOT}/spirv_parser.cpp"
    "${SPIRV_CROSS_ROOT}/spirv_cfg.cpp"
    "${SPIRV_CROSS_ROOT}/spirv_cross_util.cpp"
    "${SPIRV_CROSS_ROOT}/spirv_glsl.cpp"
    "${SPIRV_CROSS_ROOT}/spirv_msl.cpp"
    "${SPIRV_CROSS_ROOT}/spirv_reflect.cpp")
target_include_directories(spirv-cross PUBLIC "${SPIRV_CROSS_ROOT}")
target_compile_options(spirv-cross PRIVATE -w)

# --- libSPIRV-Tools.a --------------------------------------------------------
set(SPIRV-Headers_SOURCE_DIR "${SPIRV_HEADERS_ROOT}" CACHE INTERNAL "")
set(SPIRV_SKIP_TESTS ON CACHE INTERNAL "")
set(SPIRV_SKIP_EXECUTABLES ON CACHE INTERNAL "")
set(SKIP_SPIRV_TOOLS_INSTALL ON CACHE INTERNAL "")
set(SPIRV_WERROR OFF CACHE INTERNAL "")
set(SPIRV_BUILD_FUZZER OFF CACHE INTERNAL "")
add_subdirectory("${SPIRV_TOOLS_ROOT}" spirv-tools EXCLUDE_FROM_ALL)

# --- libMoltenVK_Common.a ----------------------------------------------------
file(GLOB_RECURSE MVK_COMMON_SOURCES CONFIGURE_DEPENDS
    "${MVK_ROOT}/Common/*.cpp"
    "${MVK_ROOT}/Common/*.m"
    "${MVK_ROOT}/Common/*.mm")
add_library(MoltenVK_Common STATIC ${MVK_COMMON_SOURCES})
target_include_directories(MoltenVK_Common PUBLIC "${MVK_ROOT}/Common")
target_compile_options(MoltenVK_Common PRIVATE -w)

# --- libMoltenVK_ShaderConverter.a ------------------------------------------
set(MVK_SC_DIR "${MVK_ROOT}/MoltenVKShaderConverter")
file(GLOB_RECURSE MVK_SC_SOURCES CONFIGURE_DEPENDS
    "${MVK_SC_DIR}/MoltenVKShaderConverter/*.cpp"
    "${MVK_SC_DIR}/MoltenVKShaderConverter/*.m"
    "${MVK_SC_DIR}/MoltenVKShaderConverter/*.mm")
add_library(MoltenVK_ShaderConverter STATIC ${MVK_SC_SOURCES})
target_include_directories(MoltenVK_ShaderConverter PUBLIC
    "${MVK_SC_DIR}" "${MVK_SC_DIR}/include")
target_compile_options(MoltenVK_ShaderConverter PRIVATE -w)
target_link_libraries(MoltenVK_ShaderConverter PRIVATE spirv-cross MoltenVK_Common)
# Same as the desktop build: SPIR-V disassembly logging is not compiled in.
target_compile_definitions(MoltenVK_ShaderConverter PRIVATE MVK_EXCLUDE_SPIRV_TOOLS=1)

# --- libMoltenVK.a -----------------------------------------------------------
set(MVK_DIR "${MVK_ROOT}/MoltenVK")
file(GLOB_RECURSE MVK_SOURCES CONFIGURE_DEPENDS
    "${MVK_DIR}/MoltenVK/*.cpp"
    "${MVK_DIR}/MoltenVK/*.m"
    "${MVK_DIR}/MoltenVK/*.mm")
file(GLOB MVK_SRC_INCLUDES LIST_DIRECTORIES ON "${MVK_DIR}/MoltenVK/*")
add_library(MoltenVK STATIC ${MVK_SOURCES})
target_include_directories(MoltenVK PRIVATE
    ${MVK_SRC_INCLUDES}
    "${MVK_GENERATED_INCLUDES}"
    "${MVK_DIR}/include"
    "${MVK_VULKAN_HEADERS}"
    "${mvk_cereal_SOURCE_DIR}/include")
target_compile_options(MoltenVK PRIVATE -w -Wno-elaborated-enum-base)
target_link_libraries(MoltenVK PRIVATE spirv-cross MoltenVK_Common MoltenVK_ShaderConverter)
target_compile_definitions(MoltenVK PRIVATE
    MVK_FRAMEWORK_VERSION=${MVK_VERSION} MVK_USE_CEREAL=1)

# One target that produces all five archives.
add_custom_target(theft4_ios_moltenvk ALL
    DEPENDS MoltenVK MoltenVK_Common MoltenVK_ShaderConverter spirv-cross SPIRV-Tools-static)
