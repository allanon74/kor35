package it.kor35.wearos.data;

@kotlin.Metadata(mv = {1, 9, 0}, k = 1, xi = 48, d1 = {"\u0000P\n\u0002\u0018\u0002\n\u0002\u0010\u0000\n\u0000\n\u0002\u0018\u0002\n\u0000\n\u0002\u0018\u0002\n\u0000\n\u0002\u0018\u0002\n\u0000\n\u0002\u0018\u0002\n\u0002\b\u0002\n\u0002\u0010\u0002\n\u0002\b\u0003\n\u0002\u0010\u000e\n\u0000\n\u0002\u0010\b\n\u0002\b\u0002\n\u0002\u0018\u0002\n\u0002\b\u0004\n\u0002\u0018\u0002\n\u0002\b\u0005\n\u0002\u0018\u0002\n\u0000\u0018\u00002\u00020\u0001B%\u0012\u0006\u0010\u0002\u001a\u00020\u0003\u0012\u0006\u0010\u0004\u001a\u00020\u0005\u0012\u0006\u0010\u0006\u001a\u00020\u0007\u0012\u0006\u0010\b\u001a\u00020\t\u00a2\u0006\u0002\u0010\nJ\u000e\u0010\u000b\u001a\u00020\fH\u0086@\u00a2\u0006\u0002\u0010\rJ\u001e\u0010\u000e\u001a\u00020\f2\u0006\u0010\u000f\u001a\u00020\u00102\u0006\u0010\u0011\u001a\u00020\u0012H\u0086@\u00a2\u0006\u0002\u0010\u0013J\u0016\u0010\u0014\u001a\u00020\u00152\u0006\u0010\u0016\u001a\u00020\u0010H\u0086@\u00a2\u0006\u0002\u0010\u0017J\u000e\u0010\u0018\u001a\u00020\u0010H\u0086@\u00a2\u0006\u0002\u0010\rJ\u0016\u0010\u0019\u001a\u00020\u001a2\u0006\u0010\u001b\u001a\u00020\u0010H\u0086@\u00a2\u0006\u0002\u0010\u0017J\u0016\u0010\u001c\u001a\u00020\f2\u0006\u0010\u001d\u001a\u00020\u0010H\u0086@\u00a2\u0006\u0002\u0010\u0017J\u000e\u0010\u001e\u001a\u00020\f2\u0006\u0010\u0016\u001a\u00020\u0010J\u000e\u0010\u001f\u001a\u00020 H\u0086@\u00a2\u0006\u0002\u0010\rR\u000e\u0010\u0002\u001a\u00020\u0003X\u0082\u0004\u00a2\u0006\u0002\n\u0000R\u000e\u0010\u0006\u001a\u00020\u0007X\u0082\u0004\u00a2\u0006\u0002\n\u0000R\u000e\u0010\u0004\u001a\u00020\u0005X\u0082\u0004\u00a2\u0006\u0002\n\u0000R\u000e\u0010\b\u001a\u00020\tX\u0082\u0004\u00a2\u0006\u0002\n\u0000\u00a8\u0006!"}, d2 = {"Lit/kor35/wearos/data/WatchRepository;", "", "api", "Lit/kor35/wearos/data/Kor35ApiService;", "pendingDao", "Lit/kor35/wearos/offline/PendingEventDao;", "appContext", "Landroid/content/Context;", "tokenStore", "Lit/kor35/wearos/data/TokenStore;", "(Lit/kor35/wearos/data/Kor35ApiService;Lit/kor35/wearos/offline/PendingEventDao;Landroid/content/Context;Lit/kor35/wearos/data/TokenStore;)V", "clearPairToken", "", "(Lkotlin/coroutines/Continuation;)Ljava/lang/Object;", "enqueueStatDelta", "statSigla", "", "delta", "", "(Ljava/lang/String;ILkotlin/coroutines/Continuation;)Ljava/lang/Object;", "fetchProfile", "Lit/kor35/wearos/data/WatchProfileResponse;", "pairToken", "(Ljava/lang/String;Lkotlin/coroutines/Continuation;)Ljava/lang/Object;", "loadPairToken", "pollPairingStatus", "Lit/kor35/wearos/data/PairStatusResponse;", "code", "savePairToken", "token", "scheduleFlush", "startPairing", "Lit/kor35/wearos/data/PairStartResponse;", "app_release"})
public final class WatchRepository {
    @org.jetbrains.annotations.NotNull()
    private final it.kor35.wearos.data.Kor35ApiService api = null;
    @org.jetbrains.annotations.NotNull()
    private final it.kor35.wearos.offline.PendingEventDao pendingDao = null;
    @org.jetbrains.annotations.NotNull()
    private final android.content.Context appContext = null;
    @org.jetbrains.annotations.NotNull()
    private final it.kor35.wearos.data.TokenStore tokenStore = null;
    
    public WatchRepository(@org.jetbrains.annotations.NotNull()
    it.kor35.wearos.data.Kor35ApiService api, @org.jetbrains.annotations.NotNull()
    it.kor35.wearos.offline.PendingEventDao pendingDao, @org.jetbrains.annotations.NotNull()
    android.content.Context appContext, @org.jetbrains.annotations.NotNull()
    it.kor35.wearos.data.TokenStore tokenStore) {
        super();
    }
    
    @org.jetbrains.annotations.Nullable()
    public final java.lang.Object startPairing(@org.jetbrains.annotations.NotNull()
    kotlin.coroutines.Continuation<? super it.kor35.wearos.data.PairStartResponse> $completion) {
        return null;
    }
    
    @org.jetbrains.annotations.Nullable()
    public final java.lang.Object fetchProfile(@org.jetbrains.annotations.NotNull()
    java.lang.String pairToken, @org.jetbrains.annotations.NotNull()
    kotlin.coroutines.Continuation<? super it.kor35.wearos.data.WatchProfileResponse> $completion) {
        return null;
    }
    
    @org.jetbrains.annotations.Nullable()
    public final java.lang.Object pollPairingStatus(@org.jetbrains.annotations.NotNull()
    java.lang.String code, @org.jetbrains.annotations.NotNull()
    kotlin.coroutines.Continuation<? super it.kor35.wearos.data.PairStatusResponse> $completion) {
        return null;
    }
    
    @org.jetbrains.annotations.Nullable()
    public final java.lang.Object enqueueStatDelta(@org.jetbrains.annotations.NotNull()
    java.lang.String statSigla, int delta, @org.jetbrains.annotations.NotNull()
    kotlin.coroutines.Continuation<? super kotlin.Unit> $completion) {
        return null;
    }
    
    public final void scheduleFlush(@org.jetbrains.annotations.NotNull()
    java.lang.String pairToken) {
    }
    
    @org.jetbrains.annotations.Nullable()
    public final java.lang.Object savePairToken(@org.jetbrains.annotations.NotNull()
    java.lang.String token, @org.jetbrains.annotations.NotNull()
    kotlin.coroutines.Continuation<? super kotlin.Unit> $completion) {
        return null;
    }
    
    @org.jetbrains.annotations.Nullable()
    public final java.lang.Object loadPairToken(@org.jetbrains.annotations.NotNull()
    kotlin.coroutines.Continuation<? super java.lang.String> $completion) {
        return null;
    }
    
    @org.jetbrains.annotations.Nullable()
    public final java.lang.Object clearPairToken(@org.jetbrains.annotations.NotNull()
    kotlin.coroutines.Continuation<? super kotlin.Unit> $completion) {
        return null;
    }
}