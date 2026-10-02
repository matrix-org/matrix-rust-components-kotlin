#!/usr/bin/env bash
#
# Bumps the Matrix Rust SDK version in element-x-android to the given release, opening a pull request or
# updating the one that is already open from the same branch.
#
# Needs `gh` authenticated (GH_TOKEN) with write access to the target repository. The default GITHUB_TOKEN
# of a workflow can't be used for this as it is scoped to this repository.

set -euo pipefail

usage() {
    cat >&2 <<'USAGE'
Usage: scripts/update_element_x_android.sh <version> [--rust-ref <sha>] [--dry-run]

  <version>        The released SDK version, as published in the GitHub release tag.
  --rust-ref       The matrix-rust-sdk commit the release was built from, linked in the PR description.
  --dry-run        Print the change that would be pushed, without pushing nor opening a pull request.

Environment: TARGET_REPOSITORY (default element-hq/element-x-android), GH_TOKEN.
USAGE
    exit 64
}

VERSION=""
RUST_REF=""
DRY_RUN="no"
while [ $# -gt 0 ]; do
    case "$1" in
        --rust-ref) [ $# -ge 2 ] || usage; RUST_REF="$2"; shift 2 ;;
        --dry-run) DRY_RUN="yes"; shift ;;
        -h | --help) usage ;;
        -*) echo "error: unknown option $1" >&2; usage ;;
        *) [ -z "$VERSION" ] || usage; VERSION="$1"; shift ;;
    esac
done
[ -n "$VERSION" ] || usage

REPOSITORY="${TARGET_REPOSITORY:-element-hq/element-x-android}"
BRANCH="update-matrix-rust-sdk"
CATALOG="gradle/libs.versions.toml"
SOURCE_REPOSITORY="${GITHUB_REPOSITORY:-element-hq/matrix-rust-components-kotlin}"
LABEL="PR-Dependencies"
TITLE="Update Matrix Rust SDK to $VERSION"

BODY="Bumps \`org.matrix.rustcomponents:sdk-android\` to [$VERSION](https://github.com/$SOURCE_REPOSITORY/releases/tag/$VERSION)."
if [ -n "$RUST_REF" ]; then
    BODY="$BODY

Built from https://github.com/matrix-org/matrix-rust-sdk/tree/$RUST_REF"
fi
case "$VERSION" in
*-nightly) BODY="$BODY

This is a nightly pre-release." ;;
esac
BODY="$BODY

_This pull request is opened and updated automatically by the release workflow of $SOURCE_REPOSITORY._"

WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT

gh auth setup-git
# A partial clone keeps the full history (needed to rebase) without downloading every blob, nor the LFS files.
GIT_LFS_SKIP_SMUDGE=1 gh repo clone "$REPOSITORY" "$WORKDIR/repo" -- --filter=blob:none
cd "$WORKDIR/repo"
git config user.name "ElementBot"
git config user.email "android@element.io"
BASE_BRANCH="$(git rev-parse --abbrev-ref HEAD)"

# Check out the branch of the existing PR if there is one, and rebase it on the base branch before adding
# the version bump on top of it. Otherwise start a new branch from the base branch.
if git ls-remote --exit-code --heads origin "$BRANCH" > /dev/null; then
    git fetch --quiet origin "$BRANCH"
    git checkout -B "$BRANCH" "origin/$BRANCH"
    git rebase "origin/$BASE_BRANCH"
else
    git checkout -b "$BRANCH"
fi

if ! grep -qE 'module = "org\.matrix\.rustcomponents:sdk-android"' "$CATALOG"; then
    echo "error: could not find the matrix_sdk entry in $CATALOG" >&2
    exit 1
fi
sed -E '/module = "org\.matrix\.rustcomponents:sdk-android"/ s/(strictly = |version = )"[^"]*"/\1"'"$VERSION"'"/' \
    "$CATALOG" > "$CATALOG.tmp"
mv "$CATALOG.tmp" "$CATALOG"

if git diff --quiet; then
    echo "$REPOSITORY already uses $VERSION, nothing to do."
    exit 0
fi
git --no-pager diff

if [ "$DRY_RUN" = "yes" ]; then
    echo "Dry run: not pushing nor opening a pull request."
    exit 0
fi

git commit -q -a -m "$TITLE"
# Force is needed as the rebase rewrote the history of the existing branch
git push --force-with-lease origin "$BRANCH"

EXISTING="$(gh pr list --repo "$REPOSITORY" --head "$BRANCH" --state open --json number --jq '.[0].number // empty')"
if [ -n "$EXISTING" ]; then
    gh pr edit "$EXISTING" --repo "$REPOSITORY" --title "$TITLE" --body "$BODY" --add-label "$LABEL"
    echo "Updated pull request #$EXISTING"
else
    gh pr create --repo "$REPOSITORY" --base "$BASE_BRANCH" --head "$BRANCH" --title "$TITLE" --body "$BODY" --label "$LABEL"
fi
