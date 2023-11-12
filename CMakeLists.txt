cmake_minimum_required(VERSION 3.10.2)

# Collect parameters to pass to any CMake subprojects
# (https://cmake.org/pipermail/cmake/2018-January/067002.html)
if (NOT EXTPROJ_CMAKE_ARGS)
  get_cmake_property(vars CACHE_VARIABLES)
  foreach(var ${vars})
    get_property(currentHelpString CACHE "${var}" PROPERTY HELPSTRING)
      if("${currentHelpString}" MATCHES "No help, variable specified on the command line." OR "${currentHelpString}" STREQUAL "")
          # message("${var} = [${${var}}]  --  ${currentHelpString}") # uncomment to see the variables being processed
          list(APPEND EXTPROJ_CMAKE_ARGS "-D${var}=${${var}}")
      endif()
  endforeach()
  set(EXTPROJ_CMAKE_ARGS ${EXTPROJ_CMAKE_ARGS} CACHE STRING "comment")
endif()

project(proj LANGUAGES C CXX ASM VERSION 1.0)


## Environment setup
include(ExternalProject)

set(OUTPUT_PREFIX_DIR ${CMAKE_BINARY_DIR}/prefix)
set(CMAKE_BUILD_TYPE "Release" CACHE STRING "Choose the build type" FORCE)

if (CMAKE_CXX_FLAGS)
    # These flags break compilation of certain projects and are set implictly by the android toolchain file
    string(REPLACE "-fstack-protector-strong" "" CMAKE_CXX_FLAGS ${CMAKE_CXX_FLAGS})
    string(REPLACE "-D_FORTIFY_SOURCE=2" "" CMAKE_CXX_FLAGS ${CMAKE_CXX_FLAGS})
    string(REPLACE "-Werror=format-security" "" CMAKE_CXX_FLAGS ${CMAKE_CXX_FLAGS})
    set(CMAKE_C_FLAGS ${CMAKE_CXX_FLAGS})
    set(CMAKE_ASM_FLAGS ${CMAKE_CXX_FLAGS})
endif()

if (CMAKE_CROSSCOMPILING)
  set(CROSS_COMPILER_TARGET_ARG "--target=${CMAKE_CXX_COMPILER_TARGET}")
  set(CROSS_COMPILER_SYSROOT_ARG "--sysroot=${CMAKE_SYSROOT}")
endif()

function(update_cross)
  if (CMAKE_CXX_COMPILER_LAUNCHER)
    set(CMAKE_CXX_COMPILER_LAUNCHER_SPACE "${CMAKE_CXX_COMPILER_LAUNCHER} ")
  endif()
  if (CMAKE_C_COMPILER_LAUNCHER)
    set(CMAKE_C_COMPILER_LAUNCHER_SPACE "${CMAKE_C_COMPILER_LAUNCHER} ")
  endif()

  set(COMPILER_SETTINGS
    # Autotools strips target from CFLAGS so need to use CC instead
    "CXX=${CMAKE_CXX_COMPILER_LAUNCHER_SPACE}${CMAKE_CXX_COMPILER} ${CROSS_COMPILER_TARGET_ARG}"
    "AS=${CMAKE_ASM_COMPILER} ${CROSS_COMPILER_TARGET_ARG}"
    "CPP=${CMAKE_C_COMPILER_LAUNCHER_SPACE}${CMAKE_C_COMPILER} ${CROSS_COMPILER_TARGET_ARG} -E"
    "CC=${CMAKE_C_COMPILER_LAUNCHER_SPACE}${CMAKE_C_COMPILER} ${CROSS_COMPILER_TARGET_ARG}"
    "AR=${CMAKE_AR}"
    "RANLIB=${CMAKE_RANLIB}"
    "NM=${CMAKE_NM}"
    "STRIP=${CMAKE_STRIP}"

    "CFLAGS=${CMAKE_C_FLAGS} ${CMAKE_C_FLAGS_${BUILD_TYPE_UC}} ${CROSS_COMPILER_SYSROOT_ARG}"
    "ASMFLAGS=${CMAKE_ASM_FLAGS} ${CMAKE_ASM_FLAGS_${BUILD_TYPE_UC}} ${CROSS_COMPILER_SYSROOT_ARG}"
    "CPPFLAGS=${CMAKE_C_FLAGS} ${CMAKE_C_FLAGS_${BUILD_TYPE_UC}}"
    "CXXFLAGS=${CMAKE_CXX_FLAGS} ${CMAKE_CXX_FLAGS_${BUILD_TYPE_UC}} ${CROSS_COMPILER_SYSROOT_ARG}"
    "LDFLAGS=${CMAKE_SHARED_LINKER_FLAGS} ${CMAKE_SHARED_LINKER_FLAGS_${BUILD_TYPE_UC}} ${CROSS_COMPILER_SYSROOT_ARG}"
    "PKG_CONFIG_LIBDIR=${OUTPUT_PREFIX_DIR}/lib/pkgconfig:${OUTPUT_PREFIX_DIR}/share/pkgconfig"
    "PKG_CONFIG_PATH=\"\""
    "PKG_CONFIG=pkg-config"
  )

  # Only way to make value accessible in local scope as well as parent scope
  # As setting PARENT_SCOPE would cause local accesses to not be updated
  set(COMPILER_SETTINGS "${COMPILER_SETTINGS}" PARENT_SCOPE)

  set(CROSS_COMMAND ${CMAKE_COMMAND} -E env ${COMPILER_SETTINGS} PARENT_SCOPE)
endfunction()

update_cross()
set(BASE_DEPENDS "")


## Make/Autotools project functions
function(add_make_project name path)
  cmake_parse_arguments(PARSE_ARGV 1 ARG "BUILD_ALWAYS" "MAKE_TARGET;INSTALL_TARGET" "DEPENDS")

  if (NOT DEFINED ARG_INSTALL_TARGET)
    set(ARG_INSTALL_TARGET "install")
  endif()

  ExternalProject_Add(${name}
    INSTALL_DIR         ${OUTPUT_PREFIX_DIR}
    SOURCE_DIR          ${CMAKE_CURRENT_SOURCE_DIR}/${path}
    BUILD_IN_SOURCE     TRUE
    CONFIGURE_COMMAND   ""
    BUILD_COMMAND       ${CROSS_COMMAND} make -j ${ARG_MAKE_TARGET}
    INSTALL_COMMAND     ${CROSS_COMMAND} PREFIX=<INSTALL_DIR> make -j ${ARG_INSTALL_TARGET}
    LOG_BUILD           TRUE
    LOG_INSTALL         TRUE
    BUILD_ALWAYS        ${ARG_BUILD_ALWAYS}
    DEPENDS             ${BASE_DEPENDS} ${ARG_DEPENDS}
  )
endfunction()

function(add_autotools_project name path)
  cmake_parse_arguments(PARSE_ARGV 1 ARG "BUILD_ALWAYS" "MAKE_TARGET;INSTALL_TARGET" "GENERATE_COMMAND;DEPENDS;CONFIGURE_FLAGS")

  if (NOT DEFINED ARG_INSTALL_TARGET)
    set(ARG_INSTALL_TARGET "install")
  endif()

  ExternalProject_Add(${name}
    INSTALL_DIR         ${OUTPUT_PREFIX_DIR}
    SOURCE_DIR          ${CMAKE_CURRENT_SOURCE_DIR}/${path}
    CONFIGURE_COMMAND   <SOURCE_DIR>/configure ${COMPILER_SETTINGS} --prefix=<INSTALL_DIR> --host=${CMAKE_C_COMPILER_TARGET} ${ARG_CONFIGURE_FLAGS}
    BUILD_COMMAND       make -j ${ARG_MAKE_TARGET}
    INSTALL_COMMAND     make prefix=<INSTALL_DIR> -j ${ARG_INSTALL_TARGET}
    LOG_CONFIGURE       TRUE
    LOG_BUILD           TRUE
    LOG_INSTALL         TRUE
    BUILD_ALWAYS        ${ARG_BUILD_ALWAYS}
    DEPENDS             ${BASE_DEPENDS} ${ARG_DEPENDS}
  )
  if (DEFINED ARG_GENERATE_COMMAND)
    ExternalProject_Add_Step(${name} generate
      COMMAND ${CROSS_COMMAND} ${ARG_GENERATE_COMMAND}
      BYPRODUCTS <SOURCE_DIR>/configure
      WORKING_DIRECTORY <SOURCE_DIR>
      DEPENDEES download
      DEPENDERS configure
      ALWAYS FALSE
      LOG TRUE
    )
  endif()
endfunction()


## Android shared memory shims
# This needs to be done early as it's effectively treated as a system library
add_make_project(libandroidshmem deps/libandroid-shmem)
set(CMAKE_SHARED_LINKER_FLAGS "${CMAKE_SHARED_LINKER_FLAGS} -Wl,-L${OUTPUT_PREFIX_DIR}/lib,-landroid-shmem")
update_cross()
set(BASE_DEPENDS ${BASE_DEPENDS} libandroidshmem)


# CMake & Meson project functions
function(add_cmake_project name path)
  cmake_parse_arguments(PARSE_ARGV 1 ARG "BUILD_ALWAYS" "CMAKE_ARGS;DEPENDS" "CONFIGURE_COMMAND;BUILD_COMMAND;INSTALL_COMMAND")

  if (NOT DEFINED ARG_INSTALL_COMMAND)
    set(ARG_INSTALL_COMMAND ${CMAKE_COMMAND} --build . --target install)
  endif()

  ExternalProject_Add(${name}
    INSTALL_DIR         ${OUTPUT_PREFIX_DIR}
    SOURCE_DIR          ${CMAKE_CURRENT_SOURCE_DIR}/${path}
    CONFIGURE_COMMAND   ${CMAKE_COMMAND} -G Ninja -DCMAKE_INSTALL_PREFIX=<INSTALL_DIR> -DCMAKE_TOOLCHAIN_FILE=${CMAKE_TOOLCHAIN_FILE} -DANDROID_ABI=${ANDROID_ABI} -DANDROID_PLATFORM=${ANDROID_PLATFORM} -DANDROID_SDK=${ANDROID_SDK} -DANDROID_NDK=${ANDROID_NDK} ${ARG_CMAKE_ARGS} ${ARG_CONFIGURE_COMMAND} <SOURCE_DIR>
    BUILD_COMMAND       ${CMAKE_COMMAND} --build .
    INSTALL_COMMAND     ${ARG_INSTALL_COMMAND}
    LOG_CONFIGURE       TRUE
    LOG_BUILD           TRUE
    LOG_INSTALL         TRUE
    BUILD_ALWAYS        ${ARG_BUILD_ALWAYS}
    DEPENDS             ${BASE_DEPENDS} ${ARG_DEPENDS}
  )
endfunction()

set(MESON_CROSS_FILE ${CMAKE_CURRENT_BINARY_DIR}/meson_cross.txt)
file(WRITE ${MESON_CROSS_FILE}
  "[binaries]\n"
  "c = '${CMAKE_C_COMPILER_LAUNCHER_SPACE}${CMAKE_C_COMPILER}'\n"
  "cpp = '${CMAKE_C_COMPILER_LAUNCHER_SPACE}${CMAKE_CXX_COMPILER}'\n"
  "ar = '${CMAKE_AR}'\n"
  "strip = '${CMAKE_STRIP}'\n"
  "pkgconfig = ['env', 'PKG_CONFIG_LIBDIR=${OUTPUT_PREFIX_DIR}/lib/pkgconfig:${OUTPUT_PREFIX_DIR}/share/pkgconfig', 'pkg-config']\n"
  "cmake = '${CMAKE_COMMAND}'\n"
  "\n"
  "[built-in options]\n"
  "c_args = '${CROSS_COMPILER_TARGET_ARG} ${CMAKE_C_FLAGS} ${CMAKE_C_FLAGS_${BUILD_TYPE_UC}} ${CROSS_COMPILER_SYSROOT_ARG}'\n"
  "cpp_args = '${CROSS_COMPILER_TARGET_ARG} ${CMAKE_CXX_FLAGS} ${CMAKE_CXX_FLAGS_${BUILD_TYPE_UC}} ${CROSS_COMPILER_SYSROOT_ARG}'\n"
  "c_link_args = '${CROSS_COMPILER_TARGET_ARG} ${CMAKE_SHARED_LINKER_FLAGS} ${CMAKE_SHARED_LINKER_FLAGS_${BUILD_TYPE_UC}} ${CROSS_COMPILER_SYSROOT_ARG}'\n"
  "cpp_link_args = '${CROSS_COMPILER_TARGET_ARG} ${CMAKE_SHARED_LINKER_FLAGS} ${CMAKE_SHARED_LINKER_FLAGS_${BUILD_TYPE_UC}} ${CROSS_COMPILER_SYSROOT_ARG}'\n"
  "[properties]\n"
  "pkg_config_libdir = '${OUTPUT_PREFIX_DIR}/lib/pkgconfig:${OUTPUT_PREFIX_DIR}/share/pkgconfig'\n"
  "\n"
  "[cmake]\n"
  "CMAKE_TOOLCHAIN_FILE = '${CMAKE_TOOLCHAIN_FILE}'\n"
  "ANDROID_ABI = '${ANDROID_ABI}'\n"
  "ANDROID_PLATFORM = '${ANDROID_PLATFORM}'\n"
  "ANDROID_SDK = '${ANDROID_SDK}'\n"
  "ANDROID_NDK = '${ANDROID_NDK}'\n"
  "\n"
  "[host_machine]\n"
  "system = 'android'\n"
  "cpu_family = 'aarch64'\n"
  "cpu = 'armv8'\n"
  "endian = 'little'\n"
)

function(add_meson_project name path)
  cmake_parse_arguments(PARSE_ARGV 1 ARG "BUILD_ALWAYS" "" "DEPENDS;CONFIGURE_FLAGS")
  if (NOT DEFINED ARG_BUILD_ALWAYS)
    set(ARG_BUILD_ALWAYS FALSE)
  endif()

  if (NOT DEFINED ARG_CONFIGURE_FLAGS)
    set(ARG_CONFIGURE_FLAGS "")
  endif()

  string(TOLOWER ${CMAKE_BUILD_TYPE} MESON_BUILD_TYPE)
  if (MESON_BUILD_TYPE STREQUAL "relwithdebinfo")
    set(MESON_BUILD_TYPE "debugoptimized")
  elseif (MESON_BUILD_TYPE STREQUAL "minsizerel")
    set(MESON_BUILD_TYPE "release")
  endif()

  ExternalProject_Add(${name}
    INSTALL_DIR         ${OUTPUT_PREFIX_DIR}
    SOURCE_DIR          ${CMAKE_CURRENT_SOURCE_DIR}/${path}
    CONFIGURE_COMMAND   meson setup --strip --buildtype ${MESON_BUILD_TYPE} ${ARG_CONFIGURE_FLAGS} --cross-file=${MESON_CROSS_FILE} --prefix=<INSTALL_DIR> . <SOURCE_DIR>
    BUILD_COMMAND       meson compile
    INSTALL_COMMAND     meson install --no-rebuild
    LOG_CONFIGURE       TRUE
    LOG_BUILD           TRUE
    LOG_INSTALL         TRUE
    BUILD_ALWAYS        ${ARG_BUILD_ALWAYS}
    DEPENDS             ${BASE_DEPENDS} ${ARG_DEPENDS}
  )
endfunction()


# Merge the compilation databases into a single file
add_custom_target(compile_commands
  ALL
  COMMAND find ${CMAKE_BINARY_DIR} -iname "compile_commands.json" | xargs jq -s 'map(.[])' > compile_commands.json
  WORKING_DIRECTORY ${CMAKE_BINARY_DIR}
  COMMENT "Merging compilation databases"
  BYPRODUCTS compile_commands.json
)


## Projects
add_autotools_project(xcbproto deps/xcbproto
                      GENERATE_COMMAND NOCONFIGURE=1 ./autogen.sh)
add_autotools_project(xorgproto deps/xorgproto
                      GENERATE_COMMAND NOCONFIGURE=1 ./autogen.sh)

add_autotools_project(libxau deps/libxau
                      GENERATE_COMMAND NOCONFIGURE=1 ./autogen.sh
                      DEPENDS xorgproto)
add_autotools_project(libxcb deps/libxcb
                      GENERATE_COMMAND NOCONFIGURE=1 ./autogen.sh
                      DEPENDS xcbproto libxau)
add_autotools_project(libx11 deps/libx11
                      GENERATE_COMMAND NOCONFIGURE=1 ./autogen.sh
                      CONFIGURE_FLAGS --enable-malloc0returnsnull
                      DEPENDS xorgproto libxcb)

add_autotools_project(libffi deps/libffi
                      GENERATE_COMMAND NOCONFIGURE=1 ./autogen.sh)
add_autotools_project(libexpat deps/libexpat/expat
                      GENERATE_COMMAND ./buildconf.sh)
# Required for wayland-scanner and xkbregistry when enabled
# add_autotools_project(libxml2 deps/libxml2
#                       GENERATE_COMMAND NOCONFIGURE=1 ./autogen.sh
#                       CONFIGURE_FLAGS --with-minimum --with-threads --with-valid)
add_meson_project(wayland deps/wayland
                  DEPENDS libffi libexpat
                  CONFIGURE_FLAGS -Dscanner=false -Ddocumentation=false -Dtests=false)
add_meson_project(wayland-protocols deps/wayland-protocols
                  CONFIGURE_FLAGS -Dtests=false)

add_autotools_project(libxfixes deps/libxfixes
                      GENERATE_COMMAND NOCONFIGURE=1 ./autogen.sh
                      DEPENDS libx11 xorgproto)
add_autotools_project(libxdamage deps/libxdamage
                      GENERATE_COMMAND NOCONFIGURE=1 ./autogen.sh
                      DEPENDS libx11 xorgproto libxfixes)
add_autotools_project(libxcomposite deps/libxcomposite
                      GENERATE_COMMAND NOCONFIGURE=1 ./autogen.sh
                      DEPENDS xorgproto libxfixes)
add_autotools_project(libxrender deps/libxrender
                      GENERATE_COMMAND NOCONFIGURE=1 ./autogen.sh
                      CONFIGURE_FLAGS --enable-malloc0returnsnull
                      DEPENDS libx11 xorgproto)
add_autotools_project(libxext deps/libxext
                      GENERATE_COMMAND NOCONFIGURE=1 ./autogen.sh
                      CONFIGURE_FLAGS --enable-malloc0returnsnull
                      DEPENDS libx11 xorgproto)
add_autotools_project(libxxf86vm deps/libxxf86vm
                      GENERATE_COMMAND NOCONFIGURE=1 ./autogen.sh
                      CONFIGURE_FLAGS --enable-malloc0returnsnull
                      DEPENDS xorgproto libxext)
add_autotools_project(libxi deps/libxi
                      GENERATE_COMMAND NOCONFIGURE=1 ./autogen.sh
                      CONFIGURE_FLAGS --enable-malloc0returnsnull
                      DEPENDS libx11 xorgproto libxext)
add_autotools_project(libxtst deps/libxtst
                      GENERATE_COMMAND NOCONFIGURE=1 ./autogen.sh
                      DEPENDS libx11 xorgproto libxext libxi)
add_autotools_project(libxres deps/libxres
                      GENERATE_COMMAND NOCONFIGURE=1 ./autogen.sh
                      CONFIGURE_FLAGS --enable-malloc0returnsnull
                      DEPENDS libx11 xorgproto libxext)
add_autotools_project(libxtrans deps/libxtrans
                      GENERATE_COMMAND NOCONFIGURE=1 ./autogen.sh)
add_autotools_project(libice deps/libice
                      GENERATE_COMMAND NOCONFIGURE=1 ./autogen.sh
                      DEPENDS xorgproto libxtrans)
add_autotools_project(libsm deps/libsm
                      GENERATE_COMMAND NOCONFIGURE=1 ./autogen.sh
                      DEPENDS xorgproto libice libxtrans)
add_autotools_project(libxt deps/libxt
                      GENERATE_COMMAND NOCONFIGURE=1 ./autogen.sh
                      CONFIGURE_FLAGS --enable-malloc0returnsnull
                      DEPENDS libx11 xorgproto libsm libice)
add_autotools_project(libxmu deps/libxmu
                      GENERATE_COMMAND NOCONFIGURE=1 ./autogen.sh
                      DEPENDS libx11 xorgproto libxext libxt)

add_meson_project(libxkbcommon deps/libxkbcommon
                  DEPENDS wayland wayland-protocols libx11
                  CONFIGURE_FLAGS -Denable-docs=false -Denable-xkbregistry=false)

add_autotools_project(libxkbfile deps/libxkbfile
                      GENERATE_COMMAND NOCONFIGURE=1 ./autogen.sh
                      DEPENDS libx11 xorgproto)

add_autotools_project(libfontenc deps/libfontenc
                      GENERATE_COMMAND NOCONFIGURE=1 ./autogen.sh
                      DEPENDS xorgproto)

add_autotools_project(freetype deps/freetype
                      GENERATE_COMMAND NOCONFIGURE=1 ./autogen.sh)

add_autotools_project(libxfont deps/libxfont
                      GENERATE_COMMAND NOCONFIGURE=1 ./autogen.sh
                      CONFIGURE_FLAGS --disable-fc
                      DEPENDS xorgproto libxtrans libfontenc freetype)

add_autotools_project(fontutil deps/util
                      GENERATE_COMMAND NOCONFIGURE=1 ./autogen.sh)

add_meson_project(libxcvt deps/libxcvt)

add_autotools_project(nettle deps/nettle
                      GENERATE_COMMAND NOCONFIGURE=1 ./.bootstrap
                      CONFIGURE_FLAGS --disable-documentation)

add_autotools_project(libxshmfence deps/libxshmfence
                      GENERATE_COMMAND NOCONFIGURE=1 ./autogen.sh
                      DEPENDS xorgproto)

add_meson_project(xserver xserver
                  DEPENDS xorgproto libxtrans libx11 libxkbfile libxfont fontutil wayland wayland-protocols libxcvt nettle libxshmfence
                  CONFIGURE_FLAGS -Ddocs=false -Ddevel-docs=false -Dglamor=false -Dxdmcp=false -Dglx=false -Dsecure-rpc=false -Ddri3=false)

# -Da64-neon=disabled is required to avoid a build error on NDK Clang being unable to compile .S files correctly
add_meson_project(pixman deps/pixman
                  CONFIGURE_FLAGS -Dopenmp=disabled -Dgtk=disabled -Dtests=disabled -Da64-neon=disabled)

add_autotools_project(libxcbwm deps/libxcb-wm
                      GENERATE_COMMAND NOCONFIGURE=1 ./autogen.sh
                      DEPENDS libxcb)

add_meson_project(wlroots deps/wlroots
                  DEPENDS wayland wayland-protocols pixman xserver libxcbwm
                  CONFIGURE_FLAGS -Ddefault_library=static -Dexamples=false -Dxwayland=enabled -Dbackends= -Dstub_session=true -Drenderers= -Dallocators=)

add_cmake_project(vulkan-headers deps/Vulkan-Headers
                  CONFIGURE_FLAGS -DBUILD_TESTS=OFF)

# Vulkan headers don't have a pkg-config file so create one
file(WRITE ${OUTPUT_PREFIX_DIR}/lib/pkgconfig/vulkan.pc
  "prefix=${OUTPUT_PREFIX_DIR}\n"
  "includedir=${OUTPUT_PREFIX_DIR}/include\n"
  "\n"
  "Name: Vulkan\n"
  "Description: Vulkan Headers\n"
  "Version: 1.0.0\n"
  "Requires:\n"
  "Conflicts:\n"
  "Libs:\n"
  "Libs.private: \n"
  "Cflags: -I${OUTPUT_PREFIX_DIR}/include\n"
)

add_meson_project(gamescope gamescope
                  DEPENDS wayland wayland-protocols wlroots vulkan-headers libx11 libxdamage libxcomposite libxrender libxext libxxf86vm libxtst libxres libxt libxmu libxkbcommon)