plugins {
    `java-library`
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
