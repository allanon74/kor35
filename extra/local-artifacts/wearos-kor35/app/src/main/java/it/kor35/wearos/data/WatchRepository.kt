package it.kor35.wearos.data

import android.content.Context
import androidx.work.ExistingWorkPolicy
import androidx.work.OneTimeWorkRequest
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.workDataOf
import androidx.work.WorkManager
import it.kor35.wearos.offline.PendingEventDao
import it.kor35.wearos.offline.PendingEventEntity
import it.kor35.wearos.offline.SyncQueueWorker
import kotlinx.coroutines.flow.firstOrNull
import java.util.UUID

class WatchRepository(
    private val api: Kor35ApiService,
    private val pendingDao: PendingEventDao,
    private val appContext: Context,
    private val tokenStore: TokenStore,
) {
    suspend fun startPairing(): PairStartResponse {
        return api.pairStart(
            PairStartRequest(
                device_id = Kor35ApiConfig.DEVICE_ID,
                firmware_version = Kor35ApiConfig.APP_VERSION,
            )
        )
    }

    suspend fun fetchProfile(pairToken: String): WatchProfileResponse {
        return api.profile(Kor35ApiConfig.DEVICE_ID, pairToken)
    }

    suspend fun pollPairingStatus(code: String): PairStatusResponse {
        return api.pairStatus(Kor35ApiConfig.DEVICE_ID, code)
    }

    suspend fun enqueueStatDelta(statSigla: String, delta: Int) {
        val event = PendingEventEntity(
            id = UUID.randomUUID().toString(),
            statSigla = statSigla,
            delta = delta,
            createdAtEpochMs = System.currentTimeMillis(),
        )
        pendingDao.upsert(event)
    }

    fun scheduleFlush(pairToken: String) {
        val req: OneTimeWorkRequest = OneTimeWorkRequestBuilder<SyncQueueWorker>()
            .setInputData(workDataOf("pairToken" to pairToken))
            .build()
        WorkManager.getInstance(appContext).enqueueUniqueWork(
            "kor35-watch-flush",
            ExistingWorkPolicy.KEEP,
            req,
        )
    }

    suspend fun savePairToken(token: String) {
        tokenStore.savePairToken(token)
    }

    suspend fun loadPairToken(): String {
        return tokenStore.pairTokenFlow.firstOrNull().orEmpty()
    }

    suspend fun clearPairToken() {
        tokenStore.clearPairToken()
    }
}
