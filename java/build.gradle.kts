plugins {
    `java-library`
    id("com.diffplug.spotless") version "8.10.4"
}

val versionLine = file("../pyproject.toml").readLines().first { it.startsWith("version = ") }
val versionMatch = Regex("[0-9]+\\.[0-9]+\\.[0-9]+").find(versionLine)
    ?: throw GradleException("no X.Y.Z in pyproject.toml: $versionLine")

group = "dev.endstone"
version = versionMatch.value

layout.buildDirectory = file("../build/java")

repositories {
    mavenCentral()
}

dependencies {
    api("org.jspecify:jspecify:1.0.1")
    testImplementation(platform("org.junit:junit-bom:6.1.3"))
    testImplementation("org.junit.jupiter:junit-jupiter")
    testRuntimeOnly("org.junit.platform:junit-platform-launcher")
}

spotless {
    java {
        target("src/**/*.java")
        googleJavaFormat("1.36.1").aosp()
    }
}

tasks.withType<JavaCompile>().configureEach {
    options.release = 21
    options.compilerArgs.addAll(listOf("-Xlint:all", "-Werror", "-Xdoclint:all,-missing"))
}

tasks.test {
    useJUnitPlatform()
}

tasks.jar {
    manifest {
        attributes("Automatic-Module-Name" to "dev.endstone.protocol")
    }
}
