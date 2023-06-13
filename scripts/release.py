#!/usr/bin/python3

import argparse
import os
import re
import requests
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

def get_linkable_ref(directory, ref):
    result = subprocess.run(
        ["git", "show-ref", "--verify", f"refs/heads/{ref}"],
        cwd=directory,
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        # The reference is a valid branch name, return the corresponding commit hash
        return result.stdout.strip().split()[0]

    # The reference is not a valid branch name, return the reference itself
    return ref


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


def execute_build_script(script_directory: str, sdk_path: str, module: Module):
    print("Execute build script...")
    build_script_path = os.path.join(script_directory, "build.sh")
    subprocess.run(
        ["/bin/bash", build_script_path, "-p", sdk_path, "-m", module.name.lower(), "-r"],
        check=True,
        text=True
    )
    print("Finish executing build script with success")


def override_version_in_build_version_file(file_path: str, new_version: str):
    with open(file_path, 'r') as file:
        content = file.read()

    new_major, new_minor, new_patch = map(int, new_version.split('.'))

    content = re.sub(r"(majorVersion\s*=\s*)(\d+)", rf"\g<1>{new_major}", content)
    content = re.sub(r"(minorVersion\s*=\s*)(\d+)", rf"\g<1>{new_minor}", content)
    content = re.sub(r"(patchVersion\s*=\s*)(\d+)", rf"\g<1>{new_patch}", content)

    with open(file_path, 'w') as file:
        file.write(content)


def commit_and_push_changes(directory: str, message: str):
    try:
        subprocess.run(["git", "add", "."], cwd=directory, check=True)
        subprocess.run(["git", "commit", "-m", message], cwd=directory, check=True)
        subprocess.run(["git", "push"], cwd=directory, check=True)
        print("Changes committed and pushed successfully.")
    except subprocess.CalledProcessError as e:
        print("Failed to commit and push changes.")
        print("Error message:")
        print(e.stderr)


def upload_asset_to_github_release(upload_url: str, asset_path: str, asset_name: str):
    print(f"Uploading {asset_name} to github release..")
    # Build headers with token and content type
    headers = {
        "Authorization": f"token {github_token}",
        "Content-Type": "application/octet-stream"
    }

    # Read asset file as binary content
    with open(asset_path, "rb") as asset_file:
        asset_content = asset_file.read()

    # Set the filename in the request URL
    upload_url = upload_url.replace("{?name,label}", f"?name={asset_name}")

    # Send asset upload request
    response = requests.post(upload_url, headers=headers, data=asset_content)
    if response.status_code == 201:
        print(f"Asset '{asset_name}' uploaded successfully.")
    else:
        print("Failed to upload asset.")
        print("Response:")
        print(response.json())
        exit(1)


def create_github_release(repo_url: str, tag_name: str, release_name: str, release_notes: str):
    print(f"Create github release {tag_name}")
    # Build release payload
    payload = {
        "tag_name": tag_name,
        "name": release_name,
        "body": release_notes,
        "draft": False,
        "prerelease": False
    }

    # Build request headers
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }

    # Send release request
    response = requests.post(f"{repo_url}/releases", headers=headers, json=payload)
    if response.status_code == 201:
        print("Release created successfully.")
        release_data = response.json()
        upload_url = release_data["upload_url"]
        upload_asset_to_github_release(upload_url, asset_path, asset_name)
    else:
        print("Failed to create release.")
        print("Response:")
        print(response.json())
        exit(1)


def get_asset_name(module: Module) -> str:
    if module == Module.SDK:
        return "matrix-android-sdk.aar"
    elif module == Module.CRYPTO:
        return "matrix-android-crypto.aar"
    else:
        raise ValueError(f"Unknown module: {module}")


def get_asset_path(root_project_dir: str, module: Module) -> str:
    if module == Module.SDK:
        return os.path.join(root_project_dir, "sdk/sdk-android/build/outputs/aar",
                            "sdk-android-release.aar")
    elif module == Module.CRYPTO:
        return os.path.join(root_project_dir, "crypto/crypto-android/build/outputs/aar",
                            "crypto-android-release.aar")
    else:
        raise ValueError(f"Unknown module: {module}")


def get_publish_task(module: Module) -> str:
    if module == Module.SDK:
        return ":sdk:sdk-android:publishToSonatype"
    elif module == Module.CRYPTO:
        return ":crypto:crypto-android:publishToSonatype"
    else:
        raise ValueError(f"Unknown module: {module}")


def run_publish_close_and_release_tasks(root_project_dir, publish_task: str):
    gradle_command = f"./gradlew {publish_task} closeAndReleaseStagingRepository"
    result = subprocess.run(gradle_command, shell=True, cwd=root_project_dir, text=True)
    if result.returncode != 0:
        raise Exception(f"Gradle tasks failed with return code {result.returncode}")


github_token = os.environ['GITHUB_API_TOKEN']
if github_token is None:
    print("Please set GITHUB_API_TOKEN environment variable")
    exit(1)

parser = argparse.ArgumentParser()
parser.add_argument("-m", "--module", type=module_type, required=True,
                    help="Choose a module (SDK or CRYPTO)")
parser.add_argument("-v", "--version", type=str, required=True,
                    help="Version as a string (e.g. '1.0.0')")
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

linkable_ref = get_linkable_ref(sdk_path, args.ref)
execute_build_script(current_dir, sdk_path, args.module)

override_version_in_build_version_file(build_version_file_path, args.version)

commit_message = f"Bump {args.module.name} version to {args.version} (matrix-rust-sdk to {linkable_ref})"
commit_and_push_changes(project_root, commit_message)

release_name = f"{args.module.name.lower()}-v{args.version}"
release_notes = f"https://github.com/matrix-org/matrix-rust-sdk/tree/{linkable_ref}"
asset_path = get_asset_path(project_root, args.module)
asset_name = get_asset_name(args.module)

create_github_release("https://api.github.com/repos/matrix-org/matrix-rust-components-kotlin",
                      release_name, release_name, release_notes)

run_publish_close_and_release_tasks(
    project_root,
    get_publish_task(args.module),
)
