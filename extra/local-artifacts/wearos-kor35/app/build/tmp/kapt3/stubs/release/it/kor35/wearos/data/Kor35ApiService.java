package it.kor35.wearos.data;

@kotlin.Metadata(mv = {1, 9, 0}, k = 1, xi = 48, d1 = {"\u0000:\n\u0002\u0018\u0002\n\u0002\u0010\u0000\n\u0000\n\u0002\u0018\u0002\n\u0000\n\u0002\u0018\u0002\n\u0002\b\u0002\n\u0002\u0018\u0002\n\u0000\n\u0002\u0010\u000e\n\u0002\b\u0003\n\u0002\u0018\u0002\n\u0002\b\u0002\n\u0002\u0018\u0002\n\u0002\u0018\u0002\n\u0002\b\u0002\bf\u0018\u00002\u00020\u0001J\u0018\u0010\u0002\u001a\u00020\u00032\b\b\u0001\u0010\u0004\u001a\u00020\u0005H\u00a7@\u00a2\u0006\u0002\u0010\u0006J\"\u0010\u0007\u001a\u00020\b2\b\b\u0001\u0010\t\u001a\u00020\n2\b\b\u0001\u0010\u000b\u001a\u00020\nH\u00a7@\u00a2\u0006\u0002\u0010\fJ\"\u0010\r\u001a\u00020\u000e2\b\b\u0001\u0010\t\u001a\u00020\n2\b\b\u0001\u0010\u000f\u001a\u00020\nH\u00a7@\u00a2\u0006\u0002\u0010\fJ\"\u0010\u0010\u001a\u00020\u00112\b\b\u0001\u0010\u000f\u001a\u00020\n2\b\b\u0001\u0010\u0004\u001a\u00020\u0012H\u00a7@\u00a2\u0006\u0002\u0010\u0013\u00a8\u0006\u0014"}, d2 = {"Lit/kor35/wearos/data/Kor35ApiService;", "", "pairStart", "Lit/kor35/wearos/data/PairStartResponse;", "body", "Lit/kor35/wearos/data/PairStartRequest;", "(Lit/kor35/wearos/data/PairStartRequest;Lkotlin/coroutines/Continuation;)Ljava/lang/Object;", "pairStatus", "Lit/kor35/wearos/data/PairStatusResponse;", "deviceId", "", "code", "(Ljava/lang/String;Ljava/lang/String;Lkotlin/coroutines/Continuation;)Ljava/lang/Object;", "profile", "Lit/kor35/wearos/data/WatchProfileResponse;", "pairToken", "sync", "Lit/kor35/wearos/data/WatchSyncResponse;", "Lit/kor35/wearos/data/WatchSyncRequest;", "(Ljava/lang/String;Lit/kor35/wearos/data/WatchSyncRequest;Lkotlin/coroutines/Continuation;)Ljava/lang/Object;", "app_release"})
public abstract interface Kor35ApiService {
    
    @retrofit2.http.POST(value = "/api/personaggi/api/device/watch/pair/start/")
    @org.jetbrains.annotations.Nullable()
    public abstract java.lang.Object pairStart(@retrofit2.http.Body()
    @org.jetbrains.annotations.NotNull()
    it.kor35.wearos.data.PairStartRequest body, @org.jetbrains.annotations.NotNull()
    kotlin.coroutines.Continuation<? super it.kor35.wearos.data.PairStartResponse> $completion);
    
    @retrofit2.http.GET(value = "/api/personaggi/api/device/watch/pair/status/")
    @org.jetbrains.annotations.Nullable()
    public abstract java.lang.Object pairStatus(@retrofit2.http.Query(value = "device_id")
    @org.jetbrains.annotations.NotNull()
    java.lang.String deviceId, @retrofit2.http.Query(value = "code")
    @org.jetbrains.annotations.NotNull()
    java.lang.String code, @org.jetbrains.annotations.NotNull()
    kotlin.coroutines.Continuation<? super it.kor35.wearos.data.PairStatusResponse> $completion);
    
    @retrofit2.http.GET(value = "/api/personaggi/api/device/watch/profile/")
    @org.jetbrains.annotations.Nullable()
    public abstract java.lang.Object profile(@retrofit2.http.Query(value = "device_id")
    @org.jetbrains.annotations.NotNull()
    java.lang.String deviceId, @retrofit2.http.Header(value = "X-KOR35-Pair-Token")
    @org.jetbrains.annotations.NotNull()
    java.lang.String pairToken, @org.jetbrains.annotations.NotNull()
    kotlin.coroutines.Continuation<? super it.kor35.wearos.data.WatchProfileResponse> $completion);
    
    @retrofit2.http.POST(value = "/api/personaggi/api/device/watch/sync/")
    @org.jetbrains.annotations.Nullable()
    public abstract java.lang.Object sync(@retrofit2.http.Header(value = "X-KOR35-Pair-Token")
    @org.jetbrains.annotations.NotNull()
    java.lang.String pairToken, @retrofit2.http.Body()
    @org.jetbrains.annotations.NotNull()
    it.kor35.wearos.data.WatchSyncRequest body, @org.jetbrains.annotations.NotNull()
    kotlin.coroutines.Continuation<? super it.kor35.wearos.data.WatchSyncResponse> $completion);
}