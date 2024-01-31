#!/usr/bin/env bash
set -e

helpFunction() {
  echo ""
  echo "Usage: $0 -r -p /Documents/dev/matrix-rust-sdk -m sdk"
  echo -e "\t-p Local path to the rust-sdk repository"
  echo -e "\t-o Optional output path with the expected name of the aar file"
  echo -e "\t-r Flag to build in release mode"
  echo -e "\t-m Option to select the gradle module to build. Default is sdk"
  echo -e "\t-t Option to to select an android target to build against. Default will build for all targets."
  exit 1
}

scripts_dir=$(
  cd "$(dirname "${BASH_SOURCE[0]}")" || exit
  pwd -P
)

is_release='false'
gradle_module='sdk'
only_target=''
output=''

while getopts ':rp:m:t:o:' 'opt'; do
  case ${opt} in
  'r') is_release='true' ;;
  'p') sdk_path="$OPTARG" ;;
  'm') gradle_module="$OPTARG" ;;
  't') only_target="$OPTARG" ;;
  'o') output="$OPTARG" ;;
  ?) helpFunction ;;
  esac
done

if [ -z "$sdk_path" ]; then
  echo "sdk_path is empty, please provide one"
  helpFunction
fi

if [ -z "$only_target" ]; then
  echo "no target provided, build for all targets"
  target_command=()
else
  target_command=("--only-target" "$only_target")
fi

if ${is_release}; then
  profile="release"
else
  profile="reldbg"
fi

if [ "$gradle_module" = "crypto" ]; then
  ## NDK is needed for https://crates.io/crates/olm-sys
  if [ -z "$ANDROID_NDK" ]; then
    echo "please set the ANDROID_NDK environment variable to your Android NDK installation"
    exit 1
  fi
  src_dir="$scripts_dir/../crypto/crypto-android/src/main"
  package="crypto-sdk"
else
  src_dir="$scripts_dir/../sdk/sdk-android/src/main"
  package="full-sdk"
fi

echo "Launching build script with following params:"
echo "sdk_path = $sdk_path"
echo "profile = $profile"
echo "gradle_module = $gradle_module"
echo "src-dir = $src_dir"

pushd "$sdk_path" || exit 1

cargo xtask kotlin build-android-library --profile "$profile" "${target_command[@]}" --src-dir "$src_dir" --package "$package"

pushd "$scripts_dir/.." || exit 1

shift $((OPTIND - 1))

moveFunction() {
  if [ -z "$output" ]; then
    echo "No output path provided, keep the generated path"
  else
    mv "$1" "$output"
  fi
}

## For now, cargo ndk includes all generated so files from the target directory, so makes sure it just includes the one we need.
echo "Clean .so files"
if [ "$gradle_module" = "crypto" ]; then
  find crypto/crypto-android/src/main/jniLibs -type f ! -name 'libmatrix_sdk_crypto_ffi.so' -delete
else
  find sdk/sdk-android/src/main/jniLibs -type f ! -name 'libmatrix_sdk_ffi.so' -delete
fi

if ${is_release}; then
  if [ "$gradle_module" = "sdk" ]; then
    ./gradlew :sdk:sdk-android:assembleRelease
    moveFunction "sdk/sdk-android/build/outputs/aar/sdk-android-release.aar"
  else
    ./gradlew :crypto:crypto-android:assembleRelease
    moveFunction "crypto/crypto-android/build/outputs/aar/crypto-android-release.aar"
  fi
else
  if [ "$gradle_module" = "sdk" ]; then
    ./gradlew :sdk:sdk-android:assembleDebug
    moveFunction "sdk/sdk-android/build/outputs/aar/sdk-android-debug.aar"
  else
    ./gradlew :crypto:crypto-android:assembleDebug
    moveFunction "crypto/crypto-android/build/outputs/aar/crypto-android-debug.aar"
  fi
fi
