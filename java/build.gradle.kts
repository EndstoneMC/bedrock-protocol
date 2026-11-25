import com.vanniktech.maven.publish.JavaLibrary
import com.vanniktech.maven.publish.JavadocJar
import com.vanniktech.maven.publish.SourcesJar
import org.gradle.api.tasks.testing.logging.TestExceptionFormat
import org.gradle.api.tasks.testing.logging.TestLogEvent

plugins {
    `java-library`
    id("com.diffplug.spotless") version "8.10.4"
    id("com.vanniktech.maven.publish") version "0.37.0"
}

val release = Regex("""project\(bedrock-protocol VERSION (\S+)""").find(file("../CMakeLists.txt").readText())
    ?.groupValues?.get(1) ?: throw GradleException("no project VERSION in CMakeLists.txt")
val tags = try {
    providers.exec {
        commandLine("git", "tag", "--points-at", "HEAD")
        isIgnoreExitValue = true
    }.standardOutput.asText.get().lines()
} catch (missing: GradleException) {
    emptyList()
}

group = "dev.endstone"
version = if ("v$release" in tags) release else "$release-SNAPSHOT"

layout.buildDirectory = file("../build/java")

repositories {
    mavenCentral()
}

dependencies {
    api("org.jetbrains:annotations:26.0.2")
    api("io.netty:netty-buffer:4.2.19.Final")
    testImplementation(platform("org.junit:junit-bom:6.1.3"))
    testImplementation("org.junit.jupiter:junit-jupiter")
    testImplementation("com.google.code.gson:gson:2.11.0")
    testRuntimeOnly("org.junit.platform:junit-platform-launcher")
}

abstract class GenerateBpc @Inject constructor(private val exec: ExecOperations) : DefaultTask() {
    @get:InputFiles
    @get:PathSensitive(PathSensitivity.RELATIVE)
    abstract val sources: ConfigurableFileCollection

    @get:Input
    abstract val python: Property<String>

    @get:Internal
    abstract val repoRoot: DirectoryProperty

    @get:OutputDirectory
    abstract val outputDir: DirectoryProperty

    @TaskAction
    fun generate() {
        val out = outputDir.get().asFile
        val root = repoRoot.get().asFile
        exec.exec {
            workingDir = root
            environment("PYTHONPATH", root.resolve("compiler/src").absolutePath)
            commandLine(
                python.get(), "-B", "-m", "bedrock_protocol_compiler",
                root.resolve("protocol").absolutePath,
                "--java-out", out.absolutePath,
            )
        }
    }
}

val generateBpc = tasks.register<GenerateBpc>("generateBpc") {
    sources.from(
        fileTree("../protocol") { include("**/*.py"); exclude("**/__pycache__/**") },
        fileTree("../compiler/src") { include("**/*.py"); exclude("**/__pycache__/**") },
    )
    python = providers.gradleProperty("bpc.python").orElse("python3")
    repoRoot = layout.projectDirectory.dir("..")
    outputDir = layout.buildDirectory.dir("generated/sources/bpc")
}

sourceSets.main {
    java.srcDir(generateBpc)
}

spotless {
    java {
        target("src/**/*.java")
        googleJavaFormat("1.36.1")
    }
}

tasks.withType<JavaCompile>().configureEach {
    options.release = 21
    options.isFork = true
    options.forkOptions.memoryMaximumSize = "2g"
    options.compilerArgs.addAll(listOf("-Xlint:all", "-Werror", "-Xdoclint:all,-missing"))
}

tasks.test {
    useJUnitPlatform()
    val goldens = file("../tests/goldens")
    inputs.dir(goldens).withPropertyName("goldens")
    systemProperty("goldens.dir", goldens.absolutePath)
    testLogging {
        events(TestLogEvent.PASSED, TestLogEvent.SKIPPED, TestLogEvent.FAILED)
        exceptionFormat = TestExceptionFormat.FULL
    }
}

tasks.jar {
    manifest {
        attributes("Automatic-Module-Name" to "dev.endstone.protocol")
    }
}

mavenPublishing {
    configure(JavaLibrary(javadocJar = JavadocJar.Javadoc(), sourcesJar = SourcesJar.Sources()))
    publishToMavenCentral()
    if (providers.gradleProperty("signingInMemoryKey").isPresent) {
        signAllPublications()
    }
    pom {
        name = "bedrock-protocol"
        description = "Minecraft: Bedrock Edition network protocol"
        url = "https://github.com/EndstoneMC/bedrock-protocol"
        licenses {
            license {
                name = "MIT License"
                url = "https://opensource.org/license/mit"
            }
        }
        developers {
            developer {
                name = "GlacieTeam"
            }
            developer {
                name = "EndstoneMC"
                email = "hello@endstone.dev"
            }
            developer {
                name = "Vincent Wu"
                email = "magicdroidx@gmail.com"
                roles = listOf("maintainer")
            }
        }
        scm {
            url = "https://github.com/EndstoneMC/bedrock-protocol"
            connection = "scm:git:https://github.com/EndstoneMC/bedrock-protocol.git"
            developerConnection = "scm:git:ssh://git@github.com/EndstoneMC/bedrock-protocol.git"
        }
        issueManagement {
            system = "GitHub"
            url = "https://github.com/EndstoneMC/bedrock-protocol/issues"
        }
    }
}
