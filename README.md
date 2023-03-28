# Matrix rust components kotlin

This repository is used for distributing kotlin releases of the Matrix Rust SDK. It'll provide the corresponding aar and also publish them on maven.

## Releasing
Whenever a new release of the underlying components is available, we need to tag a new release in this repo to make them available. 
This is done with the release script found in the scripts directory. It'll also push the release to the maven repository.

Usage : 

`python3 ./scripts/release.py --version 0.1.3 --sdk_path /Users/user/Documents/dev/matrix-rust-sdk --module SDK`


## Testing locally
As the package vendors a pre-built binary of the SDK, all local development is done via the SDK's repo instead of this one.
You can use the build script to generate the aar for testing. Be sure to have checkout the matrix-rust-sdk first.

Usage :

`./scripts/build.sh -p matrix-rust-sdk-path -m sdk -t aarch64-linux-android`

## Prerequisites

* the Rust toolchain
* cargo-ndk
* android targets (e.g. `rustup target add \
  aarch64-linux-android \
  armv7-linux-androideabi \
  x86_64-linux-android \
  i686-linux-android`)


## License

[Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0)
