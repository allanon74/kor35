package it.kor35.wearos.data

data class PairStartRequest(
    val device_id: String,
    val firmware_version: String,
)

data class PairStartResponse(
    val status: String,
    val pairing_code: String,
    val expires_at: String,
    val expires_in_seconds: Int,
)

data class PairStatusResponse(
    val status: String,
    val pair_token: String? = null,
)

data class WatchProfileResponse(
    val status: String,
    val personaggio: WatchCharacter?,
    val timers: List<WatchTimer> = emptyList(),
)

data class WatchCharacter(
    val id: Int,
    val nome: String,
    val risorse_pool_ui: List<WatchPoolStat> = emptyList(),
)

data class WatchPoolStat(
    val sigla: String,
    val nome: String,
    val colore: String? = null,
    val valore_max: Int = 0,
    val valore_corrente: Int = 0,
)

data class WatchTimer(
    val sigla: String? = null,
    val nome: String? = null,
    val next_tick_at: String? = null,
)

data class WatchSyncEvent(
    val client_event_id: String,
    val stat_sigla: String,
    val delta: Int,
)

data class WatchSyncRequest(
    val device_id: String,
    val firmware_version: String,
    val events: List<WatchSyncEvent>,
)

data class WatchSyncResponse(
    val status: String,
    val applied_events: Int = 0,
    val risorse_pool_ui: List<WatchPoolStat> = emptyList(),
)
