package it.kor35.wearos.ui

import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.background
import androidx.compose.foundation.combinedClickable
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp

private val quadrantOrder = listOf(
    listOf("PV", "PA"),
    listOf("PS", "CHA"),
)

private fun colorFromHex(hex: String?): Color {
    if (hex.isNullOrBlank()) return Color.Unspecified
    val s = hex.trim().removePrefix("#")
    val v = runCatching { s.toLong(16) }.getOrNull() ?: return Color.Unspecified
    return Color(if (s.length <= 6) 0xFF000000L or v else v)
}

@OptIn(ExperimentalFoundationApi::class)
@Composable
fun GameScreen(
    stats: List<StatValue>,
    onMinus: (String) -> Unit,
    onPlus: (String) -> Unit,
    modifier: Modifier = Modifier,
) {
    val bySigla = remember(stats) { stats.associateBy { it.sigla } }

    Column(
        modifier = modifier
            .fillMaxSize()
            .padding(vertical = 2.dp),
    ) {
        quadrantOrder.forEach { rowSigle ->
            Row(
                modifier = Modifier
                    .weight(1f, fill = true)
                    .fillMaxWidth(),
            ) {
                rowSigle.forEach { sigla ->
                    StatQuadrant(
                        stat = bySigla[sigla],
                        onMinus = { onMinus(sigla) },
                        onPlus = { onPlus(sigla) },
                        modifier = Modifier
                            .weight(1f)
                            .fillMaxSize()
                            .padding(3.dp),
                    )
                }
            }
        }
    }
}

@OptIn(ExperimentalFoundationApi::class)
@Composable
private fun StatQuadrant(
    stat: StatValue?,
    onMinus: () -> Unit,
    onPlus: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val base = MaterialTheme.colorScheme.surfaceContainerHigh
    val tint = stat?.colorHex?.let { c ->
        val parsed = colorFromHex(c)
        if (parsed == Color.Unspecified) base else parsed.copy(alpha = 0.35f)
    } ?: base

    Box(
        modifier = modifier
            .clip(RoundedCornerShape(14.dp))
            .background(tint)
            .combinedClickable(
                enabled = stat != null,
                onClick = onMinus,
                onLongClick = onPlus,
            )
            .padding(horizontal = 4.dp, vertical = 6.dp),
        contentAlignment = Alignment.Center,
    ) {
        if (stat == null) {
            Text(
                text = "—",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        } else {
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text(
                    text = stat.label,
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurface,
                    textAlign = TextAlign.Center,
                    maxLines = 1,
                )
                Text(
                    text = "${stat.current} / ${stat.max}",
                    style = MaterialTheme.typography.titleMedium,
                    color = MaterialTheme.colorScheme.onSurface,
                    textAlign = TextAlign.Center,
                )
                Text(
                    text = "− tap · lungo +",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f),
                    textAlign = TextAlign.Center,
                )
            }
        }
    }
}
