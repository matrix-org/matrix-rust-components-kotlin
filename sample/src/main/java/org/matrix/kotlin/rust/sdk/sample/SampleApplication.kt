package org.matrix.kotlin.rust.sdk.sample

import android.app.Application
import java.io.File

class SampleApplication : Application() {

    override fun onCreate() {
        super.onCreate()
        OlmMachine("@ganfra146:matrix.org", "DEWRCMENGS", File(filesDir, "sample"))
    }

}