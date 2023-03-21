object DependenciesVersions {
    const val androidGradlePlugin = "7.4.0"
    const val kotlin = "1.8.0"
    const val jUnit = "4.12"
    const val nexusPublishGradlePlugin = "1.1.0"
    const val jna = "5.13.0"
}

/**
 * To define dependencies
 */
object Dependencies {
    const val junit = "junit:junit:${DependenciesVersions.jUnit}"
    const val jna = "net.java.dev.jna:jna:${DependenciesVersions.jna}@aar"
}