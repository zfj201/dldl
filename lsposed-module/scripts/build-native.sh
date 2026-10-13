#!/bin/sh
set -eu
: "${ANDROID_NDK_HOME:?Set ANDROID_NDK_HOME to the official Android NDK directory}"
task_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
task_toolchain="$ANDROID_NDK_HOME/toolchains/llvm/prebuilt/darwin-x86_64"
task_output="$task_root/app/src/main/jniLibs/arm64-v8a"
mkdir -p "$task_output"
"$task_toolchain/bin/aarch64-linux-android29-clang" -shared -fPIC -O2 -Wall -Wextra -Werror \
    -Wl,-z,max-page-size=16384 -Wl,-z,relro,-z,now -Wl,--build-id=sha1 \
    "$task_root/app/src/main/cpp/bridge.c" -o "$task_output/libdldl_bridge.so"
