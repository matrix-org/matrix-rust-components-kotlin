#!/usr/bin/python3

import argparse
import json
import os
import requests
import subprocess
from pathlib import Path

github_token = os.environ['GITHUB_TOKEN']

if github_token is None:
    print("Please set GITHUB_TOKEN environment variable")
    exit(1)

parser = argparse.ArgumentParser()
parser.add_argument('--version', type=str, help='Version of the release', required=True)
parser.add_argument('--sdk_path', type=str, default='',
                    help='Path of the matrix-rust-sdk repository (defaults to sibling matrix-rust-sdk folder)',
                    required=False)

args = vars(parser.parse_args())


def remove_suffix(string, suffix):
    if string.endswith(suffix):
        return string[:-len(suffix)]
    return string


# find root directory
root = remove_suffix(Path(os.path.abspath(os.path.dirname(__file__))).parent.__str__(), '/')
version = args['version']
sdk_path = str(args['sdk_path'])
if len(sdk_path) == 0:
    sdk_path = remove_suffix(Path(root).parent.__str__(), '/') + '/matrix-rust-sdk'
else:
    sdk_path = remove_suffix(os.path.realpath(sdk_path), '/')

print("Root path: " + root)
print("SDK path: " + sdk_path)
sdk_generated_aar_path = "/sdk/sdk-android/build/outputs/aar/sdk-android-release.aar"
crypto_generated_aar_path = "/crypto/crypto-android/build/outputs/aar/sdk-android-release.aar"
if os.system("./build.sh -r -m sdk -p " + sdk_path) != 0:
    exit(0)


print("Creating release")


def bump_version(versions):
    major_version = versions[0]
    minor_version = versions[1]
    patch_version = versions[2]

    file = open(root + '/buildSrc/src/main/kotlin/BuildVersions.kt', "w")
    file.write('object BuildVersions {\n')
    file.write('\tconst val majorVersion = ' + major_version + "\n")
    file.write('\tconst val minorVersion = ' + minor_version + "\n")
    file.write('\tconst val patchVersion = ' + patch_version + "\n")
    file.write('}\n')
    file.close()


bump_version(version.split('.'))

sdk_commit_hash = subprocess.getoutput("cat " + sdk_path + "/.git/refs/heads/main")


def commit_and_push_changes():
    print("SDK commit: " + sdk_commit_hash)
    commit_message = "Bump to " + version + " (matrix-rust-sdk " + sdk_commit_hash + ")"
    print("Pushing changes as: " + commit_message)
    os.system("git add " + root + "/buildSrc/src/main/kotlin/BuildVersions.kt")
    os.system("git add " + root + "/sdk/sdk-android/src/main/kotlin")
    os.system("git add " + root + "/crypto/crypto-android/src/main/kotlin")
    os.system("git commit -m '" + commit_message + "'")
    return os.system("git push")


if commit_and_push_changes() != 0:
    exit(0)

response1 = requests.post(
    'https://api.github.com/repos/matrix-org/matrix-rust-components-kotlin/releases',
    headers={
        'Accept': 'application/vnd.github+json',
        'Authorization': 'Bearer ' + github_token,
        'Content-Type': 'application/x-www-form-urlencoded',
    },
    data=json.dumps({
        "tag_name": version,
        "target_commitish": "main",
        "name": version,
        "body": "https://github.com/matrix-org/matrix-rust-sdk/tree/" + sdk_commit_hash,
        "draft": False,
        "prerelease": False,
        "generate_release_notes": False,
        "make_latest": "true"
    }))
creation_response = response1.json()
print("Release created: " + creation_response['html_url'])

print("Uploading release assets")
upload_url = creation_response['upload_url'].split(u"{")[0]
def uploadAsset(file, name):
    upload_asset_response = requests.post(upload_url,
                                          headers={
                                              'Accept': 'application/vnd.github+json',
                                              'Content-Type': 'application/zip',
                                              'Authorization': 'Bearer ' + github_token,
                                          },
                                          params={'name': name},
                                          data=file)

    if upload_asset_response.status_code == 201:
        upload_asset_response_json = upload_asset_response.json()
        print("Upload finished: " + upload_asset_response_json['browser_download_url'])

with open(root + sdk_generated_aar_path, 'rb') as file:
    uploadAsset(file, 'matrix-android-sdk.aar')
