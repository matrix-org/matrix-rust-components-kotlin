#!/usr/bin/python3

import argparse
import os
import re
import subprocess
from enum import Enum, auto
from tempfile import TemporaryDirectory

class Module(Enum):
    SDK = auto()
    CRYPTO = auto()

def module_type(value):
    try:
        return Module[value.upper()]
    except KeyError:
        raise argparse.ArgumentTypeError(
            f"Invalid module choice: {value}. Available options: SDK, CRYPTO")


def get_build_version_file_path(module: Module, project_root: str) -> str:
    if module == Module.SDK:
        return os.path.join(project_root, 'buildSrc/src/main/kotlin', 'BuildVersionsSDK.kt')
    elif module == Module.CRYPTO:
        return os.path.join(project_root, 'buildSrc/src/main/kotlin', 'BuildVersionsCrypto.kt')
    else:
        raise ValueError(f"Unknown module: {module}")


def read_version_numbers_from_kotlin_file(file_path):
    with open(file_path, "r") as file:
        content = file.read()

    major_version = int(re.search(r"majorVersion\s*=\s*(\d+)", content).group(1))
    minor_version = int(re.search(r"minorVersion\s*=\s*(\d+)", content).group(1))
    patch_version = int(re.search(r"patchVersion\s*=\s*(\d+)", content).group(1))

    return major_version, minor_version, patch_version


def clone_repo_and_checkout_ref(directory, git_url, ref):
    # Clone the repo
    subprocess.run(
        ["git", "clone", git_url, directory],
        check=True,
        text=True,
    )
    # Checkout the specified ref (commit hash, tag, or branch)
    subprocess.run(
        ["git", "checkout", ref],
        cwd=directory,
        check=True,
        text=True,
    )

def is_provided_version_higher(major: int, minor: int, patch: int, provided_version: str) -> bool:
    provided_major, provided_minor, provided_patch = map(int, provided_version.split('.'))
    if provided_major > major:
        return True
    elif provided_major == major:
        if provided_minor > minor:
            return True
        elif provided_minor == minor:
            return provided_patch > patch
    return False


def execute_build_script(script_directory: str, sdk_path: str, module: Module, target: str):
    print("Execute build script...")
    build_script_path = os.path.join(script_directory, "build-rust-for-target.sh")
    subprocess.run(
        ["/bin/bash", build_script_path, "-p", sdk_path, "-m", module.name.lower(), "-t", target, "-r"],
        check=True,
        text=True
    )
    print("Finish executing build script with success")

parser = argparse.ArgumentParser()
parser.add_argument("-m", "--module", type=module_type, required=True,
                    help="Choose a module (SDK or CRYPTO)")
parser.add_argument("-v", "--version", type=str, required=True,
                    help="Version as a string (e.g. '1.0.0')")
parser.add_argument("-t", "--target", type=str, required=True,
                    help="Choose a target (\"aarch64-linux-android\", \"armv7-linux-androideabi\", \"i686-linux-android\", \"x86_64-linux-android\")")
parser.add_argument("-r", "--ref", type=str, required=True,
                    help="Ref to the git matrix-rust-sdk (branch name, commit or tag)")
parser.add_argument("-p", "--path-to-sdk", type=str, required=False,
                    help="Choose a module (SDK or CRYPTO)")
parser.add_argument("-s", "--skip-clone", action="store_true", required=False,
                    help="Skip cloning the Rust SDK repository")

args = parser.parse_args()

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir).rstrip(os.sep)
sdk_git_url = "https://github.com/matrix-org/matrix-rust-sdk.git"

if args.path_to_sdk:
    sdk_path = args.path_to_sdk
else:
    sdk_path = TemporaryDirectory().name

skip_clone = args.skip_clone

print(f"Project Root Directory: {project_root}")
print(f"Selected module: {args.module}")
print(f"Version: {args.version}")
print(f"SDK git ref: {args.ref}")

build_version_file_path = get_build_version_file_path(args.module, project_root)
major, minor, patch = read_version_numbers_from_kotlin_file(build_version_file_path)
if is_provided_version_higher(major, minor, patch, args.version):
    print(
        f"The provided version ({args.version}) is higher than the previous version ({major}.{minor}.{patch}) so we can start the release process")
else:
    print(
        f"The provided version ({args.version}) is not higher than the previous version ({major}.{minor}.{patch}) so bump the version before retrying.")
    exit(0)

if skip_clone is False:
    clone_repo_and_checkout_ref(sdk_path, sdk_git_url, args.ref)

execute_build_script(current_dir, sdk_path, args.module, args.target)

# Export Rust SDK path for next steps, if running in GitHub Actions
env_file_path = os.getenv('GITHUB_ENV')
if os.path.exists(env_file_path):
    with open(env_file_path, "a") as file:
        file.write(f"RUST_SDK_PATH={sdk_path}")