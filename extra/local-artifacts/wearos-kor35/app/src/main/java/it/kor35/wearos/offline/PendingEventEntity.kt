package it.kor35.wearos.offline

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "pending_events")
data class PendingEventEntity(
    @PrimaryKey val id: String,
    val statSigla: String,
    val delta: Int,
    val createdAtEpochMs: Long,
)
