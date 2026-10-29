import java.util.Properties

plugins { id("com.android.application") }
android {
    namespace = "com.zfj.dldlextension"
    compileSdk = 37
    defaultConfig {
        applicationId = "com.zfj.dldlextension"
        minSdk = 29
        targetSdk = 35
        versionCode = 10
        versionName = "0.6.2"
        buildConfigField("int", "PROBE_STAGE", providers.gradleProperty("probeStage").getOrElse("5"))
    }
    buildFeatures { buildConfig = true }
    // Modern LSPosed resolves module libraries from base.apk!/lib/<abi>.
    packaging { jniLibs { useLegacyPackaging = false } }
    compileOptions { sourceCompatibility = JavaVersion.VERSION_11; targetCompatibility = JavaVersion.VERSION_11 }
}
dependencies { compileOnly("io.github.libxposed:api:102.0.0") }

val buildPayload by tasks.registering(Exec::class) {
    workingDir(rootProject.projectDir)
    commandLine("python3", "scripts/build-payload.py")
}
val buildNative by tasks.registering(Exec::class) {
    workingDir(rootProject.projectDir)
    val local = Properties().apply {
        val file = rootProject.file("local.properties")
        if (file.isFile) file.inputStream().use { load(it) }
    }
    environment("ANDROID_NDK_HOME", System.getenv("ANDROID_NDK_HOME") ?: local.getProperty("ndk.dir", ""))
    commandLine("sh", "scripts/build-native.sh")
}
buildPayload { dependsOn(buildNative) }
tasks.named("preBuild") { dependsOn(buildPayload) }
