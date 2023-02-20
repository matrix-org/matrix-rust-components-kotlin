#!/usr/bin/env bash
set -e

helpFunction() {
  echo ""
  echo "Usage: $0 -r -p /Documents/dev/matrix-rust-sdk -m sdk"
  echo -e "\t-p Local path to the rust-sdk repository"
  echo -e "\t-o The output path with the expected name of the aar file"
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

if [ -z "$output" ]; then
  echo "output path is empty, please provide one"
  helpFunction
fi

if [ -z "$only_target" ]; then
  echo "no target provided, build for all targets"
  target_command=()
else
  target_command=("--only-target" "$only_target")
fi

if ${is_release}; then
  release_command="--release"
fi

if [ "$gradle_module" = "crypto" ]; then
  src_dir="$scripts_dir/../crypto/crypto-android/src/main"
  package="crypto-sdk"
else
  src_dir="$scripts_dir/../sdk/sdk-android/src/main"
  package="full-sdk"
fi

pushd "$sdk_path" || exit

cargo xtask kotlin build-android-library ${release_command:+"$release_command"} "${target_command[@]}" --src-dir "$src_dir" --package "$package"

pushd "$scripts_dir/.." || exit

shift $((OPTIND - 1))

if ${is_release}; then
  if [ "$gradle_module" = "sdk" ]; then
    ./gradlew :sdk:sdk-android:assembleRelease
    mv "sdk/sdk-android/build/outputs/aar/sdk-android-release.aar" "$output"
  else
    ./gradlew :crypto:crypto-android:assembleRelease
    mv "crypto/crypto-android/build/outputs/aar/crypto-android-release.aar" "$output"
  fi
else
  if [ "$gradle_module" = "sdk" ]; then
    ./gradlew :sdk:sdk-android:assembleDebug
    mv "sdk/sdk-android/build/outputs/aar/sdk-android-debug.aar" "$output"
  else
    ./gradlew :crypto:crypto-android:assembleDebug
    mv "crypto/crypto-android/build/outputs/aar/crypto-android-debug.aar" "$output"
  fi
fi

