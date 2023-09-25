### Cassiapp Externals

These are externally compiled components of [Cassiapp](https://github.com/cassia-org/cassiapp), unlike Cassia runtimes they aren't user-replaceable and are supposed to be tied to a specific version of the app.

#### Building
* Run `apply-patches.sh` in `deps`
* Run `cmake -GNinja -Bbuild -H. -DCMAKE_TOOLCHAIN_FILE=${ANDROID_NDK_HOME}/build/cmake/android.toolchain.cmake -DANDROID_ABI=arm64-v8a -DANDROID_PLATFORM=android-29 -DANDROID_SDK=${ANDROID_SDK_HOME} -DANDROID_NDK=${ANDROID_NDK_HOME} -DANDROID_ABIS=arm64-v8a && (build && cmake --build . -v || ..)`