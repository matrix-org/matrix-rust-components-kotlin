#!/usr/bin/python3

import argparse
import os
import re
import requests
import subprocess
from enum import Enum, auto


class Module(Enum):
    SDK = auto()
    CRYPTO = auto()


def module_type(value):
    try:
        return Module[value.upper()]
    except KeyError:
        raise argparse.ArgumentTypeError(
            f"Invalid module choice: {value}. Available options: SDK, CRYPTO")


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
        subprocess.run(
            ["git", "add", "."],
            cwd=directory,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", message],
            cwd=directory,
            check=True,
            capture_output=True,
        )
        subprocess.run(["git", "push"], cwd=directory, check=True, capture_output=True)
        print("Changes committed and pushed successfully.")
    except subprocess.CalledProcessError as e:
        print("Failed to commit and push changes.")
        print("Error message:")
        print(e.stderr)
        raise e


def upload_asset_to_github_release(
        github_token: str,
        upload_url: str,
        asset_path: str,
        asset_name: str,
):
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


def create_github_release(
        github_token: str,
        repo_url: str,
        tag_name: str,
        release_name: str,
        release_notes: str,
        asset_path: str,
        asset_name: str,
):
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
        upload_asset_to_github_release(
            github_token,
            upload_url,
            asset_path,
            asset_name,
        )
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


def get_build_version_file_path(module: Module, project_root: str) -> str:
    if module == Module.SDK:
        return os.path.join(project_root, 'buildSrc/src/main/kotlin', 'BuildVersionsSDK.kt')
    elif module == Module.CRYPTO:
        return os.path.join(project_root, 'buildSrc/src/main/kotlin', 'BuildVersionsCrypto.kt')
    else:
        raise ValueError(f"Unknown module: {module}")


def build_aar_files(script_directory: str, module: Module):
    print("Execute build script...")
    build_script_path = os.path.join(script_directory, "build-aar.sh")
    subprocess.run(
        ["/bin/bash", build_script_path, "-m", module.name.lower(), "-r"],
        check=True,
        text=True
    )
    print("Finish executing build script with success")


def main(args: argparse.Namespace):
    github_token = os.environ['GITHUB_API_TOKEN']
    if github_token is None:
        print("Please set GITHUB_API_TOKEN environment variable")
        exit(1)

    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir).rstrip(os.sep)

    print(f"Project Root Directory: {project_root}")
    print(f"Selected module: {args.module}")
    print(f"Version: {args.version}")

    build_version_file_path = get_build_version_file_path(args.module, project_root)

    build_aar_files(current_dir, args.module)

    override_version_in_build_version_file(build_version_file_path, args.version)

    # First release on Maven
    run_publish_close_and_release_tasks(
        project_root,
        get_publish_task(args.module),
    )

    # Success, commit and push changes, then create github release
    commit_message = f"Bump {args.module.name} version to {args.version} (matrix-rust-sdk to {args.linkable_ref})"
    print(f"Commit message: {commit_message}")
    commit_and_push_changes(project_root, commit_message)

    release_name = f"{args.module.name.lower()}-v{args.version}"
    release_notes = f"https://github.com/matrix-org/matrix-rust-sdk/tree/{args.linkable_ref}"
    asset_path = get_asset_path(project_root, args.module)
    asset_name = get_asset_name(args.module)
    create_github_release(
        github_token,
        "https://api.github.com/repos/matrix-org/matrix-rust-components-kotlin",
        release_name,
        release_name,
        release_notes,
        asset_path,
        asset_name,
    )


parser = argparse.ArgumentParser()
parser.add_argument("-m", "--module", type=module_type, required=True,
                    help="Choose a module (SDK or CRYPTO)")
parser.add_argument("-v", "--version", type=str, required=True,
                    help="Version as a string (e.g. '1.0.0')")
parser.add_argument("-l", "--linkable-ref", type=str, required=True,
                    help="The git ref to link to in the matrix-rust-sdk project")
args = parser.parse_args()

main(args)
