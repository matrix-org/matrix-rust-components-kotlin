#!/usr/bin/python3

import argparse
import os
import re
import requests
import subprocess

print("START OF FILE")

def get_build_version_file_path(project_root: str) -> str:
    return os.path.join(project_root, 'buildSrc/src/main/kotlin', 'BuildVersionsCrypto.kt')


def read_version_numbers_from_kotlin_file(file_path):
    with open(file_path, "r") as file:
        content = file.read()

    major_version = int(re.search(r"majorVersion\s*=\s*(\d+)", content).group(1))
    minor_version = int(re.search(r"minorVersion\s*=\s*(\d+)", content).group(1))
    patch_version = int(re.search(r"patchVersion\s*=\s*(\d+)", content).group(1))

    return major_version, minor_version, patch_version


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

def override_version_in_build_version_file(file_path: str, new_version: str):
    with open(file_path, 'r') as file:
        content = file.read()

    new_major, new_minor, new_patch = map(int, new_version.split('.'))

    content = re.sub(r"(majorVersion\s*=\s*)(\d+)", rf"\g<1>{new_major}", content)
    content = re.sub(r"(minorVersion\s*=\s*)(\d+)", rf"\g<1>{new_minor}", content)
    content = re.sub(r"(patchVersion\s*=\s*)(\d+)", rf"\g<1>{new_patch}", content)

    with open(file_path, 'w') as file:
        file.write(content)


def get_git_hash(directory: str) -> str:
    try:
        result = subprocess.run(["git", "rev-parse", "HEAD"],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                cwd=directory,
                                check=True,
                                text=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return "unknown"


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


def get_asset_name() -> str:
        return "matrix-android-crypto.aar"


def get_asset_path(root_project_dir: str) -> str:
    return os.path.join(root_project_dir, "crypto/crypto-android/build/outputs/aar",
                            "crypto-android-release.aar")

def get_publish_task() -> str:
    return ":crypto:crypto-android:publishToSonatype"

def run_publish_close_and_release_tasks(root_project_dir, publish_task: str):
    gradle_command = f"./gradlew {publish_task} closeAndReleaseStagingRepository"
    result = subprocess.run(gradle_command, shell=True, cwd=root_project_dir, text=True)
    if result.returncode != 0:
        raise Exception(f"Gradle tasks failed with return code {result.returncode}")

print("BEFORE GITHUB TOKEN")

github_token = os.environ['GITHUB_API_TOKEN']

if github_token is None:
    print("Please set GITHUB_TOKEN environment variable")
    exit(1)

parser = argparse.ArgumentParser()
parser.add_argument("-v", "--version", type=str, required=True,
                    help="Version as a string (e.g. '1.0.0')")
parser.add_argument("-p", "--sdk_path", type=str, required=True, help="Path to the SDK")

args = parser.parse_args()

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir).rstrip(os.sep)
sdk_path = args.sdk_path.rstrip(os.sep)
print(f"Project Root Directory: {project_root}")
print(f"Version: {args.version}")
print(f"SDK Path: {sdk_path}")

build_version_file_path = get_build_version_file_path(project_root)
major, minor, patch = read_version_numbers_from_kotlin_file(build_version_file_path)
if is_provided_version_higher(major, minor, patch, args.version):
    print(
        f"The provided version ({args.version}) is higher than the previous version ({major}.{minor}.{patch}) so we can start the release process")
else:
    print(
        f"The provided version ({args.version}) is not higher than the previous version ({major}.{minor}.{patch}) so bump the version before retrying.")
    exit(0)

override_version_in_build_version_file(build_version_file_path, args.version)

sdk_commit_hash = get_git_hash(sdk_path)
commit_message = f"Bump crypto version to {args.version} (matrix-rust-crypto-sdk {sdk_commit_hash})"
commit_and_push_changes(project_root, commit_message)

release_name = f"crypto-v{args.version}"
release_notes = f"https://github.com/matrix-org/matrix-rust-sdk/tree/{sdk_commit_hash}"
asset_path = get_asset_path(project_root)
asset_name = get_asset_name()

create_github_release("https://api.github.com/repos/matrix-org/matrix-rust-components-kotlin",
                      release_name, release_name, release_notes)

run_publish_close_and_release_tasks(
    project_root,
    get_publish_task(),
)
