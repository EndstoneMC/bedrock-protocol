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
        googleJavaFormat("1.36.1").aosp()
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
}

tasks.jar {
    manifest {
        attributes("Automatic-Module-Name" to "dev.endstone.protocol")
    }
}
