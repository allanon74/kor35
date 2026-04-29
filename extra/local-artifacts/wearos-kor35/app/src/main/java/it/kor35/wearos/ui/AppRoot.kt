package it.kor35.wearos.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.produceState
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import kotlinx.coroutines.delay
import java.time.LocalTime
import java.time.format.DateTimeFormatter

@Composable
fun AppRoot(vm: WatchViewModel = viewModel()) {
    val state by vm.state.collectAsState()
    LaunchedEffect(state.pairToken) {
        if (state.pairToken.isNotBlank()) vm.refreshProfile()
    }
    val now by produceState(initialValue = "", key1 = Unit) {
        val fmt = DateTimeFormatter.ofPattern("HH:mm:ss")
        while (true) {
            value = LocalTime.now().format(fmt)
            delay(1000)
        }
    }

    Column(
        modifier = Modifier.fillMaxSize().padding(12.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text(text = now, style = MaterialTheme.typography.titleMedium)
        if (state.pairToken.isBlank()) {
            PairingScreen(
                code = state.pairingCode,
                loading = state.loading,
                onStart = vm::startPairing,
            )
            Text(if (state.pairStatus.isBlank()) "Inserisci il codice nella web app KOR35." else state.pairStatus)
        } else {
            Text("PG: ${state.characterName}")
            GameScreen(
                stats = state.stats,
                onMinus = { vm.applyDelta(it, -1) },
                onPlus = { vm.applyDelta(it, +1) },
            )
            Text("Timer: ${state.timersLine}")
            Button(onClick = vm::refreshProfile) {
                Text("Sync")
            }
        }
    }
}
