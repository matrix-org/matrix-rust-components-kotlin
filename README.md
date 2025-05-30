# Matrix rust components kotlin

This repository is used for distributing kotlin releases of the Matrix Rust SDK. It'll provide the corresponding aar and also publish them on maven.

## Releasing

There is a ['Release SDK Library (parallel)'](https://github.com/matrix-org/matrix-rust-components-kotlin/actions/workflows/release_sdk_parallel.yml) Github Actions workflow you can run with a parameter for the SDK branch or SHA - tags don't work correctly at the moment - and the new version name to release. 
There is also a 'Release Crypto Library' one that does the same for the crypto library.

If you want to do it manually instead:

You need to set GITHUB_API_TOKEN in your env to let the script be able to commit and push, with this configuration:
- Content: Read and Write;
- Metadata: Read only.

Make sure to also have setup the maven credentials and gpg key in your [env](scripts/publish-root.gradle) 

Whenever a new release of the underlying components is available, we need to tag a new release in this repo to make them available. 
This is done with the release script found in the scripts directory. It'll also push the release to the maven repository.

Usage : 
```
# To build the SDK/crypto library binaries from the matrix-rust-sdk repo:
./scripts/build.sh -p <matrix-rust-sdk-path> -m <sdk/crypto> -r
# To release the built SDK/crypto library binaries to maven:
python3 ./scripts/publish_release.py --version <version> --linkable-ref <sdk-branch/SHA> --module <SDK/CRYPTO>
```

## Testing locally
As the package vendors a pre-built binary of the SDK, all local development is done via the SDK's repo instead of this one.
You can use the build script to generate the AAR file for testing. Be sure to have checked out the matrix-rust-sdk first.


The `-t` argument needs a valid architecture to build. For Android, these are:
- aarch64-linux-android
- armv7-linux-androideabi
- i686-linux-android
- x86_64-linux-android

Alternatively, to build only the host's architecture, you can use the `-l` argument.

Usage:

To build the main crate (eg, for Element-X):
```
./scripts/build.sh -p <matrix-rust-sdk-path> -m sdk -l
```

Or:
```
./scripts/build.sh -p <matrix-rust-sdk-path> -m sdk -t <arch>
```

To build just the crypto crate (eg, for Element Android classic), use this instead:
```
./scripts/build.sh -p <matrix-rust-sdk-path> -m crypto -l
```

Other useful flags:

- `-o OUTPUT_DIR`: Moves the generated AAR file to the dir `OUTPUT_DIR`.
- `-r`: Produces a release build instead of a development one.

You should then import this AAR in your project.

## Prerequisites

* Android NDK
* the Rust toolchain
* cargo-ndk `cargo install cargo-ndk`
* protoc `brew install protobuf` or downloading [here](https://github.com/protocolbuffers/protobuf/releases)
* android targets (e.g. `rustup target add aarch64-linux-android armv7-linux-androideabi x86_64-linux-android i686-linux-android`)


## License

[Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0)
