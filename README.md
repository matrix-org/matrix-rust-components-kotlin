# Matrix rust components kotlin

This repository is used for distributing kotlin releases of the Matrix Rust SDK. It'll provide the corresponding aar and also publish them on maven.

## Releasing
Whenever a new release of the underlying components is available, we need to tag a new release in this repo to make them available. This is done with the release script found in the tools directory.

## Testing locally
As the package vendors a pre-built binary of the SDK, all local development is done via the SDK's repo instead of this one.

## License

[Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0)
