package it.kor35.wearos.ui

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import it.kor35.wearos.data.NetworkModule
import it.kor35.wearos.data.TokenStore
import it.kor35.wearos.data.WatchRepository
import it.kor35.wearos.offline.OfflineModule
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import retrofit2.HttpException

class WatchViewModel(app: Application) : AndroidViewModel(app) {
    private val repo = WatchRepository(
        api = NetworkModule.apiService(),
        pendingDao = OfflineModule.database(app).pendingEventDao(),
        appContext = app.applicationContext,
        tokenStore = TokenStore(app.applicationContext),
    )

    private val _state = MutableStateFlow(WatchUiState())
    val state: StateFlow<WatchUiState> = _state

    init {
        restoreSession()
    }

    fun startPairing() {
        viewModelScope.launch {
            _state.update { it.copy(loading = true) }
            runCatching { repo.startPairing() }
                .onSuccess { res ->
                    _state.update {
                        it.copy(
                            loading = false,
                            pairingCode = res.pairing_code,
                            pairStatus = "In attesa conferma web...",
                        )
                    }
                    beginPairingPolling(res.pairing_code)
                }
                .onFailure {
                    _state.update { s -> s.copy(loading = false) }
                }
        }
    }

    fun applyDelta(sigla: String, delta: Int) {
        _state.update { s ->
            val updated = s.stats.map { row ->
                if (row.sigla != sigla) return@map row
                row.copy(current = (row.current + delta).coerceIn(0, row.max))
            }
            s.copy(stats = updated)
        }
        viewModelScope.launch {
            repo.enqueueStatDelta(sigla, delta)
            val token = _state.value.pairToken
            if (token.isNotBlank()) {
                repo.scheduleFlush(token)
            }
        }
    }

    fun refreshProfile() {
        val token = _state.value.pairToken
        if (token.isBlank()) return
        viewModelScope.launch {
            runCatching { repo.fetchProfile(token) }
                .onSuccess { profile ->
                    val rows = profile.personaggio?.risorse_pool_ui.orEmpty().map {
                        StatValue(
                            sigla = it.sigla,
                            label = if (it.sigla == "PS") "PG" else it.sigla,
                            current = it.valore_corrente,
                            max = it.valore_max,
                            colorHex = it.colore,
                        )
                    }
                    val timerLabel = profile.timers.firstOrNull()?.nome ?: "Nessun timer"
                    _state.update {
                        it.copy(
                            characterName = profile.personaggio?.nome ?: "-",
                            stats = rows,
                            timersLine = timerLabel,
                        )
                    }
                }
                .onFailure { e ->
                    // Prima errore di rete dopo standby cancellava il token: così chiedeva sempre il pairing.
                    when {
                        e is HttpException && e.code() in listOf(401, 403) -> {
                            _state.update {
                                it.copy(
                                    pairStatus = "Sessione non più valida. Rifai pairing dalla web.",
                                    pairToken = "",
                                )
                            }
                            repo.clearPairToken()
                        }
                        else -> {
                            _state.update { s ->
                                s.copy(
                                    pairStatus = "Rete assente o server non raggiungibile.",
                                )
                            }
                        }
                    }
                }
        }
    }

    /** Chiude la sessione sullo SW (token cancellato). Il pairing va rifatto solo se vuoi ricollegarti. */
    fun disconnectSession() {
        viewModelScope.launch {
            repo.clearPairToken()
            _state.update { WatchUiState(pairStatus = "Sessione chiusa.") }
        }
    }

    private fun restoreSession() {
        viewModelScope.launch {
            val token = repo.loadPairToken()
            if (token.isNotBlank()) {
                _state.update { it.copy(pairToken = token, pairStatus = "Sessione ripristinata") }
                refreshProfile()
            }
        }
    }

    private fun beginPairingPolling(code: String) {
        viewModelScope.launch {
            repeat(60) {
                delay(2000)
                val status = runCatching { repo.pollPairingStatus(code) }.getOrNull() ?: return@repeat
                when (status.status) {
                    "paired" -> {
                        val token = status.pair_token.orEmpty()
                        if (token.isNotBlank()) {
                            repo.savePairToken(token)
                            _state.update {
                                it.copy(
                                    pairToken = token,
                                    pairStatus = "Connesso",
                                )
                            }
                            refreshProfile()
                            return@launch
                        }
                    }
                    "expired" -> {
                        _state.update { it.copy(pairStatus = "Codice scaduto, riprova.") }
                        return@launch
                    }
                    "invalid" -> {
                        _state.update { it.copy(pairStatus = "Codice non valido.") }
                        return@launch
                    }
                    else -> {
                        _state.update { it.copy(pairStatus = "In attesa conferma web...") }
                    }
                }
            }
            _state.update { it.copy(pairStatus = "Timeout pairing, premi Connetti.") }
        }
    }
}
