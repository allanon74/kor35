package it.kor35.wearos.offline

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import it.kor35.wearos.data.Kor35ApiConfig
import it.kor35.wearos.data.NetworkModule
import it.kor35.wearos.data.WatchSyncEvent
import it.kor35.wearos.data.WatchSyncRequest

class SyncQueueWorker(
    appContext: Context,
    params: WorkerParameters,
) : CoroutineWorker(appContext, params) {

    override suspend fun doWork(): Result {
        val db = OfflineModule.database(applicationContext)
        val dao = db.pendingEventDao()
        val pending = dao.nextBatch(30)
        if (pending.isEmpty()) return Result.success()

        val pairToken = inputData.getString("pairToken") ?: return Result.retry()
        val api = NetworkModule.apiService()

        return try {
            api.sync(
                pairToken = pairToken,
                body = WatchSyncRequest(
                    device_id = Kor35ApiConfig.DEVICE_ID,
                    firmware_version = Kor35ApiConfig.APP_VERSION,
                    events = pending.map {
                        WatchSyncEvent(
                            client_event_id = it.id,
                            stat_sigla = it.statSigla,
                            delta = it.delta,
                        )
                    },
                ),
            )
            dao.deleteByIds(pending.map { it.id })
            Result.success()
        } catch (_: Exception) {
            Result.retry()
        }
    }
}
