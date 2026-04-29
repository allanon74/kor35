package it.kor35.wearos.ui

import androidx.compose.material3.Button
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable

@Composable
fun PairingScreen(
    code: String,
    loading: Boolean,
    onStart: () -> Unit,
) {
    Button(onClick = onStart, enabled = !loading) {
        Text(if (loading) "Connessione..." else "Connetti")
    }
    if (code.isNotBlank()) {
        Text("Codice: $code")
    }
}
