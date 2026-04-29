package it.kor35.wearos.ui

data class StatValue(
    val sigla: String,
    val label: String,
    val current: Int,
    val max: Int,
    val colorHex: String? = null,
)

data class WatchUiState(
    val loading: Boolean = false,
    val pairStatus: String = "",
    val pairingCode: String = "",
    val pairToken: String = "",
    val characterName: String = "-",
    val stats: List<StatValue> = emptyList(),
    val timersLine: String = "Nessun timer",
)
