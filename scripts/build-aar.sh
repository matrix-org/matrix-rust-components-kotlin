#!/usr/bin/env bash
set -e

is_release='false'
gradle_module='sdk'
output=''

helpFunction() {
  echo ""
  echo "Usage: $0 -r -m sdk"
  echo -e "\t-o Optional output path with the expected name of the aar file"
  echo -e "\t-r Flag to build in release mode"
  echo -e "\t-m Option to select the gradle module to build. Default is sdk"
  exit 1
}

while getopts ':rm:o:' 'opt'; do
  case ${opt} in
  'r') is_release='true' ;;
  'm') gradle_module="$OPTARG" ;;
  'o') output="$OPTARG" ;;
  ?) helpFunction ;;
  esac
done

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
