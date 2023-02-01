#!/usr/bin/python3

import os
import subprocess
import json
import argparse
from fileinput import FileInput
from pathlib import Path
import requests
import json

github_token = os.environ['GITHUB_TOKEN']

if github_token is None:
    print("Please set GITHUB_TOKEN environment variable")
    exit(1)

parser = argparse.ArgumentParser()
parser.add_argument('--version', type=str, help='Version of the release', required=True)
parser.add_argument('--sdk_path', type=str, default='', help='Path of the matrix-rust-sdk repository (defaults to sibling matrix-rust-sdk folder)', required=False)

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
sdk_generated_aar_path = "/bindings/kotlin/sdk/sdk-android/build/outputs/aar/sdk-android-release.aar"
sdk_generated_source_path = "/bindings/kotlin/sdk/sdk-android/build/generated/source/release/"
os.system("(cd '" + sdk_path + "'; cargo xtask kotlin build-android-library --only-target x86_64-linux-android --release --package full-sdk)")

print("Copy generated files")
os.system("rsync -a '" + sdk_path + sdk_generated_source_path + "' '" + root + "/sources'")

print("Creating release")

sdk_commit_hash = subprocess.getoutput("cat " + sdk_path + "/.git/refs/heads/main")
print("SDK commit: " + sdk_commit_hash)
commit_message = "Bump to " + version + " (matrix-rust-sdk " + sdk_commit_hash + ")"
print("Pushing changes as: " + commit_message)
os.system("git add " + root + "/sources")
os.system("git commit -m '" + commit_message + "'")
os.system("git push")

response1 = requests.post('https://api.github.com/repos/matrix-org/matrix-rust-components-kotlin/releases',
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
with open(sdk_path + sdk_generated_aar_path, 'rb') as file:
    response2 = requests.post(upload_url,
    headers={
        'Accept': 'application/vnd.github+json',
        'Content-Type': 'application/zip',
        'Authorization': 'Bearer ' + github_token,
    },
    params={'name': 'matrix-android-sdk.aar'},
    data=file)

if response2.status_code == 201:
    upload_response = response2.json()
    print("Upload finished: " + upload_response['browser_download_url'])