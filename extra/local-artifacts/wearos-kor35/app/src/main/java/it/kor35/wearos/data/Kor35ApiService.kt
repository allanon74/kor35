package it.kor35.wearos.data

import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.POST
import retrofit2.http.Query

interface Kor35ApiService {
    @POST("/api/personaggi/api/device/watch/pair/start/")
    suspend fun pairStart(@Body body: PairStartRequest): PairStartResponse

    @GET("/api/personaggi/api/device/watch/pair/status/")
    suspend fun pairStatus(
        @Query("device_id") deviceId: String,
        @Query("code") code: String,
    ): PairStatusResponse

    @GET("/api/personaggi/api/device/watch/profile/")
    suspend fun profile(
        @Query("device_id") deviceId: String,
        @Header("X-KOR35-Pair-Token") pairToken: String,
    ): WatchProfileResponse

    @POST("/api/personaggi/api/device/watch/sync/")
    suspend fun sync(
        @Header("X-KOR35-Pair-Token") pairToken: String,
        @Body body: WatchSyncRequest,
    ): WatchSyncResponse
}
