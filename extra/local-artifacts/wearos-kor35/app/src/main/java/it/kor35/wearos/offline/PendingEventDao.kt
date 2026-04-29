package it.kor35.wearos.offline

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query

@Dao
interface PendingEventDao {
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsert(event: PendingEventEntity)

    @Query("SELECT * FROM pending_events ORDER BY createdAtEpochMs ASC LIMIT :limit")
    suspend fun nextBatch(limit: Int): List<PendingEventEntity>

    @Query("DELETE FROM pending_events WHERE id IN (:ids)")
    suspend fun deleteByIds(ids: List<String>)
}
