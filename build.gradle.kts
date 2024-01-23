// Top-level build file where you can add configuration options common to all sub-projects/modules.
buildscript {
    repositories {
        maven("https://plugins.gradle.org/m2/")
        google()
        mavenCentral()
    }
}

plugins {
    id("com.android.library") version DependenciesVersions.androidGradlePlugin apply false
    id("org.jetbrains.kotlin.android") version DependenciesVersions.kotlin apply false
    id("org.jetbrains.kotlin.jvm") version DependenciesVersions.kotlin apply false
    id("io.github.gradle-nexus.publish-plugin") version DependenciesVersions.nexusPublishGradlePlugin
}

apply(from = "${rootDir}/scripts/publish-root.gradle")


tasks.register<Delete>("clean").configure {
    delete(rootProject.layout.buildDirectory)
 }
