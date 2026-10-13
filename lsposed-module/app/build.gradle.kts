plugins { id("com.android.application") }
android {
    namespace = "com.zfj.dldlextension"
    compileSdk = 37
    defaultConfig {
        applicationId = "com.zfj.dldlextension"
        minSdk = 29
        targetSdk = 35
        versionCode = 1
        versionName = "0.1.0-probe"
        buildConfigField("int", "PROBE_STAGE", providers.gradleProperty("probeStage").getOrElse("1"))
    }
    buildFeatures { buildConfig = true }
    // Modern LSPosed resolves module libraries from base.apk!/lib/<abi>.
    packaging { jniLibs { useLegacyPackaging = false } }
    compileOptions { sourceCompatibility = JavaVersion.VERSION_11; targetCompatibility = JavaVersion.VERSION_11 }
}
dependencies { compileOnly("io.github.libxposed:api:102.0.0") }
