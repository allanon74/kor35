import java.io.File

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.kapt")
}

/** Firma release opzionale (installabile su device): env o proprietà Gradle (non committare segreti). */
fun wearEnvOrProp(envVar: String, gradleProp: String): String? =
    System.getenv(envVar)?.trim()?.takeIf { it.isNotEmpty() }
        ?: project.findProperty(gradleProp)?.toString()?.trim()?.takeIf { it.isNotEmpty() }

val wearReleaseStorePath: String? = wearEnvOrProp("WEAR_RELEASE_STORE_FILE", "wear.release.storeFile")
val wearReleaseStorePassword: String? = wearEnvOrProp("WEAR_RELEASE_STORE_PASSWORD", "wear.release.storePassword")
val wearReleaseKeyAlias: String? = wearEnvOrProp("WEAR_RELEASE_KEY_ALIAS", "wear.release.keyAlias")
val wearReleaseKeyPassword: String? = wearEnvOrProp("WEAR_RELEASE_KEY_PASSWORD", "wear.release.keyPassword")

android {
    namespace = "it.kor35.wearos"
    compileSdk = 34

    defaultConfig {
        applicationId = "it.kor35.wearos"
        minSdk = 30
        targetSdk = 34
        versionCode = 1
        versionName = "0.1.0"
    }

    signingConfigs {
        val storePath = wearReleaseStorePath
        val storePass = wearReleaseStorePassword
        val alias = wearReleaseKeyAlias
        if (
            !storePath.isNullOrBlank() &&
            !storePass.isNullOrBlank() &&
            !alias.isNullOrBlank()
        ) {
            create("release") {
                val resolved = File(storePath.trim())
                storeFile = if (resolved.isAbsolute) file(resolved) else rootProject.file(storePath.trim())
                storePassword = storePass
                keyAlias = alias
                keyPassword = wearReleaseKeyPassword?.ifBlank { null } ?: storePass
            }
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
            signingConfigs.findByName("release")?.let { signingConfig = it }
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
    buildFeatures {
        compose = true
    }
    composeOptions {
        kotlinCompilerExtensionVersion = "1.5.14"
    }
    packaging {
        resources {
            excludes += "/META-INF/{AL2.0,LGPL2.1}"
        }
    }
}

dependencies {
    implementation(platform("androidx.compose:compose-bom:2024.06.00"))
    implementation("androidx.activity:activity-compose:1.9.0")
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.compose.material3:material3")
    implementation("com.google.android.material:material:1.12.0")

    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.2")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.2")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.8.1")

    implementation("com.squareup.retrofit2:retrofit:2.11.0")
    implementation("com.squareup.retrofit2:converter-gson:2.11.0")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("com.squareup.okhttp3:logging-interceptor:4.12.0")

    implementation("androidx.room:room-runtime:2.6.1")
    implementation("androidx.room:room-ktx:2.6.1")
    kapt("androidx.room:room-compiler:2.6.1")

    implementation("androidx.datastore:datastore-preferences:1.1.1")
    implementation("androidx.work:work-runtime-ktx:2.9.1")

    debugImplementation("androidx.compose.ui:ui-tooling")
}
