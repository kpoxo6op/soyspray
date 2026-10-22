plugins {
    id("com.android.application")
}

android {
    namespace = "vip.soyspray.infiniteslop"
    compileSdk = 35

    defaultConfig {
        applicationId = "vip.soyspray.infiniteslop"
        minSdk = 26
        targetSdk = 35
        versionCode = (System.getenv("VERSION_CODE") ?: "1").toInt()
        versionName = System.getenv("VERSION_NAME") ?: "dev"
    }

    // CI signs each build with a throwaway key; the TV operation pins the
    // resulting certificate and reinstalls when it changes.
    signingConfigs {
        create("release") {
            storeFile = file(System.getenv("SIGNING_STORE") ?: "unsigned.jks")
            storePassword = System.getenv("SIGNING_PASSWORD")
            keyAlias = "tile"
            keyPassword = System.getenv("SIGNING_PASSWORD")
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            signingConfig = signingConfigs.getByName("release")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}
