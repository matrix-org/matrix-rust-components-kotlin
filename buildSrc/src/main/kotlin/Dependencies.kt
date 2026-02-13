object DependenciesVersions {
    const val androidGradlePlugin = "9.0.1"
    const val kotlin = "1.9.25"
    const val jUnit = "4.13.2"
    const val nexusPublishGradlePlugin = "2.0.0"
    const val jna = "5.18.1"
    const val coroutines = "1.7.3"
    const val annotations = "1.9.1"
}

/**
 * To define dependencies
 */
object Dependencies {
    const val coroutines = "org.jetbrains.kotlinx:kotlinx-coroutines-core:${DependenciesVersions.coroutines}"
    const val junit = "junit:junit:${DependenciesVersions.jUnit}"
    const val jna = "net.java.dev.jna:jna:${DependenciesVersions.jna}@aar"
    const val annotations = "androidx.annotation:annotation:${DependenciesVersions.annotations}"
}
