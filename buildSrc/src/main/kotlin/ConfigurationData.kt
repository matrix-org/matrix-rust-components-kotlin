object ConfigurationData {
    const val compileSdk = 34
    const val targetSdk = 33
    const val minSdk = 21
    const val publishGroupId = "org.matrix.rustcomponents"
    const val versionNameCrypto =
        "${BuildVersionsCrypto.majorVersion}.${BuildVersionsCrypto.minorVersion}.${BuildVersionsCrypto.patchVersion}"
    const val versionNameSdk =
        "${BuildVersionsSDK.majorVersion}.${BuildVersionsSDK.minorVersion}.${BuildVersionsSDK.patchVersion}"
}
