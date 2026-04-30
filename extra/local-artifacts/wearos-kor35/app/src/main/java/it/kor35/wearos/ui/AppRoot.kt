package it.kor35.wearos.ui

import android.view.WindowManager
import androidx.activity.ComponentActivity
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.SideEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.produceState
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.compose.ui.unit.dp
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.viewmodel.compose.viewModel
import kotlinx.coroutines.delay
import java.time.LocalTime
import java.time.format.DateTimeFormatter

@Composable
fun AppRoot(vm: WatchViewModel = viewModel()) {
    val state by vm.state.collectAsState()
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current

    // Schermo acceso mentre la sessione è attiva (meno standby automatico durante il gioco).
    SideEffect {
        val token = state.pairToken
        val act = context as? ComponentActivity
        act?.window?.let { w ->
            if (token.isNotBlank()) {
                w.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
            } else {
                w.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
            }
        }
    }

    // Dopo standby / riapertura app: subito un refresh senza attendere il polling.
    DisposableEffect(state.pairToken, lifecycleOwner) {
        if (state.pairToken.isBlank()) {
            return@DisposableEffect onDispose { }
        }
        val obs = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_RESUME) {
                vm.refreshProfile()
            }
        }
        lifecycleOwner.lifecycle.addObserver(obs)
        onDispose { lifecycleOwner.lifecycle.removeObserver(obs) }
    }

    // Polling leggero: lo SW non ha WebSocket; così i PV/PA aggiornati dalla web arrivano senza tasto Sync.
    LaunchedEffect(state.pairToken) {
        if (state.pairToken.isBlank()) return@LaunchedEffect
        while (true) {
            vm.refreshProfile()
            delay(12_000)
        }
    }
    val now by produceState(initialValue = "", key1 = Unit) {
        val fmt = DateTimeFormatter.ofPattern("HH:mm:ss")
        while (true) {
            value = LocalTime.now().format(fmt)
            delay(1000)
        }
    }

    Column(
        modifier = Modifier.fillMaxSize().padding(10.dp),
        verticalArrangement = Arrangement.spacedBy(6.dp),
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
                modifier = Modifier.weight(1f, fill = true),
                stats = state.stats,
                onMinus = { vm.applyDelta(it, -1) },
                onPlus = { vm.applyDelta(it, +1) },
            )
            Text("Timer: ${state.timersLine}")
            val statusLine = state.pairStatus
            if (state.pairToken.isNotBlank() && statusLine.isNotBlank()) {
                Text(
                    text = statusLine,
                    style = MaterialTheme.typography.labelSmall,
                    color = if (statusLine.startsWith("Rete")) {
                        MaterialTheme.colorScheme.error
                    } else {
                        MaterialTheme.colorScheme.onSurfaceVariant
                    },
                )
            }
            Row(
                horizontalArrangement = Arrangement.spacedBy(6.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Button(onClick = vm::refreshProfile) {
                    Text("Sync")
                }
                OutlinedButton(onClick = vm::disconnectSession) {
                    Text("Esci")
                }
            }
        }
    }
}
