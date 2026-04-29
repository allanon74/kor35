package it.kor35.wearos.ui

import androidx.compose.foundation.combinedClickable
import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier

@OptIn(ExperimentalFoundationApi::class)
@Composable
fun GameScreen(
    stats: List<StatValue>,
    onMinus: (String) -> Unit,
    onPlus: (String) -> Unit,
) {
    stats.filter { it.sigla in setOf("PV", "PA", "PS", "CHA") }.forEach { stat ->
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .combinedClickable(
                    onClick = { onMinus(stat.sigla) },
                    onLongClick = { onPlus(stat.sigla) },
                ),
            horizontalArrangement = Arrangement.SpaceBetween,
        ) {
            Text(stat.label)
            Text("${stat.current}/${stat.max}")
        }
    }
}
