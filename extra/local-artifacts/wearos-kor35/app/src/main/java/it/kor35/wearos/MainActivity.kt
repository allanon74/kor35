package it.kor35.wearos

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import it.kor35.wearos.ui.AppRoot

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            AppRoot()
        }
    }
}
