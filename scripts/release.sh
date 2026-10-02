#!/usr/bin/env bash
#
# Builds the SDK AAR and lays out the assets of a GitHub release that can be consumed as an Apache Ivy
# repository: a flat list of files (aar, pom, module, sources...) each with its checksum companions.
#
# It expects the native libraries and FFI bindings to be already in place (see build-rust-for-target.py).
# It never touches the remote: it doesn't commit, tag, push or create a release. The workflow does that
# from the outputs in build/release-assets.

set -euo pipefail

usage() {
    cat >&2 <<'USAGE'
Usage: scripts/release.sh [<version>] [--skip-build]

  <version>     The SDK version to release, as MAJOR.MINOR.PATCH, optionally followed by a suffix
                (i.e. 26.09.28 or 26.09.28-nightly). It's also the git tag.
                If omitted, a nightly version is used: the date of yesterday as YY.MM.DD plus -nightly.
  --skip-build  Only stamp the version, don't run Gradle nor lay out the assets.

Gradle arguments can be passed in the CI_GRADLE_ARG_PROPERTIES environment variable.
USAGE
    exit 64
}

VERSION=""
SKIP_BUILD="no"
while [ $# -gt 0 ]; do
    case "$1" in
        --skip-build) SKIP_BUILD="yes"; shift ;;
        -h | --help) usage ;;
        -*) echo "error: unknown option $1" >&2; usage ;;
        *) [ -z "$VERSION" ] || usage; VERSION="$1"; shift ;;
    esac
done
if [ -z "$VERSION" ]; then
    # The version is year.month.day, so default to the day before this runs
    YESTERDAY="$(date -u -d yesterday +%y.%m.%d 2> /dev/null || date -u -v-1d +%y.%m.%d)"
    VERSION="$YESTERDAY-nightly"
    echo "No version provided, using $VERSION"
fi

if ! [[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.-]+)?$ ]]; then
    echo "error: '$VERSION' is not a MAJOR.MINOR.PATCH[-suffix] version." >&2
    exit 1
fi

cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

VERSIONS_FILE="buildSrc/src/main/kotlin/BuildVersionsSDK.kt"
DIST="build/dist"
ASSETS="build/release-assets"
GRADLE_ARGS=${CI_GRADLE_ARG_PROPERTIES:-}

# --- 1. Stamp the version ---------------------------------------------------------------------------------
IFS=. read -r MAJOR MINOR PATCH <<< "$VERSION"
sed -E \
    -e "s/(majorVersion[[:space:]]*=[[:space:]]*)\".*\"/\1\"$MAJOR\"/" \
    -e "s/(minorVersion[[:space:]]*=[[:space:]]*)\".*\"/\1\"$MINOR\"/" \
    -e "s/(patchVersion[[:space:]]*=[[:space:]]*)\".*\"/\1\"$PATCH\"/" \
    "$VERSIONS_FILE" > "$VERSIONS_FILE.tmp"
mv "$VERSIONS_FILE.tmp" "$VERSIONS_FILE"
grep -q "patchVersion = \"$PATCH\"" "$VERSIONS_FILE" || { echo "error: could not stamp $VERSION in $VERSIONS_FILE" >&2; exit 1; }
echo "Stamped $VERSION into $VERSIONS_FILE"

if [ "$SKIP_BUILD" = "yes" ]; then
    exit 0
fi

# --- 2. Build and publish to the local dist repository ----------------------------------------------------
# The sdk-android module only: the other modules aren't part of this release.
rm -rf "$DIST" "$ASSETS"
# shellcheck disable=SC2086
./gradlew :sdk:sdk-android:publishAllPublicationsToDistRepository $GRADLE_ARGS

# --- 3. Flatten the Maven layout into the release assets --------------------------------------------------
# The Ivy pattern resolves `[artifact]-[revision](-[classifier]).[ext]` files from a single directory, so
# maven-metadata (which is Maven specific) is left out.
mkdir -p "$ASSETS"
find "$DIST" -type f -path "*/$VERSION/*" ! -name 'maven-metadata*' -exec cp {} "$ASSETS/" \;

# --- 4. Make sure every asset has checksum companions -----------------------------------------------------
hash_file() { # <algorithm: md5|sha1|sha256|sha512> <file>
    case "$1" in
        md5) if command -v md5sum > /dev/null; then md5sum "$2" | cut -d' ' -f1; else md5 -q "$2"; fi ;;
        *) if command -v "$1sum" > /dev/null; then "$1sum" "$2" | cut -d' ' -f1; else shasum -a "${1#sha}" "$2" | cut -d' ' -f1; fi ;;
    esac
}

is_checksum() {
    case "$1" in *.md5 | *.sha1 | *.sha256 | *.sha512) return 0 ;; *) return 1 ;; esac
}

for file in "$ASSETS"/*; do
    is_checksum "$file" && continue
    # Ivy needs one of md5/sha1 to verify a download; Gradle also writes sha256/sha512. Fill the gaps.
    for algorithm in md5 sha1 sha256 sha512; do
        if [ ! -f "$file.$algorithm" ]; then
            hash_file "$algorithm" "$file" > "$file.$algorithm"
            echo "Computed $(basename "$file").$algorithm"
        fi
    done
done

ls -l "$ASSETS"
echo "Prepared $VERSION, assets in $ASSETS. Nothing has been pushed."
