package it.kor35.wearos.data;

@kotlin.Metadata(mv = {1, 9, 0}, k = 1, xi = 48, d1 = {"\u0000,\n\u0002\u0018\u0002\n\u0002\u0010\u0000\n\u0000\n\u0002\u0018\u0002\n\u0002\b\u0002\n\u0002\u0018\u0002\n\u0002\u0010\u000e\n\u0002\b\u0003\n\u0002\u0018\u0002\n\u0000\n\u0002\u0010\u0002\n\u0002\b\u0005\u0018\u00002\u00020\u0001B\r\u0012\u0006\u0010\u0002\u001a\u00020\u0003\u00a2\u0006\u0002\u0010\u0004J\u000e\u0010\f\u001a\u00020\rH\u0086@\u00a2\u0006\u0002\u0010\u000eJ\u0016\u0010\u000f\u001a\u00020\r2\u0006\u0010\u0010\u001a\u00020\u0007H\u0086@\u00a2\u0006\u0002\u0010\u0011R\u000e\u0010\u0002\u001a\u00020\u0003X\u0082\u0004\u00a2\u0006\u0002\n\u0000R\u0017\u0010\u0005\u001a\b\u0012\u0004\u0012\u00020\u00070\u0006\u00a2\u0006\b\n\u0000\u001a\u0004\b\b\u0010\tR\u0014\u0010\n\u001a\b\u0012\u0004\u0012\u00020\u00070\u000bX\u0082\u0004\u00a2\u0006\u0002\n\u0000\u00a8\u0006\u0012"}, d2 = {"Lit/kor35/wearos/data/TokenStore;", "", "appContext", "Landroid/content/Context;", "(Landroid/content/Context;)V", "pairTokenFlow", "Lkotlinx/coroutines/flow/Flow;", "", "getPairTokenFlow", "()Lkotlinx/coroutines/flow/Flow;", "pairTokenKey", "Landroidx/datastore/preferences/core/Preferences$Key;", "clearPairToken", "", "(Lkotlin/coroutines/Continuation;)Ljava/lang/Object;", "savePairToken", "token", "(Ljava/lang/String;Lkotlin/coroutines/Continuation;)Ljava/lang/Object;", "app_release"})
public final class TokenStore {
    @org.jetbrains.annotations.NotNull()
    private final android.content.Context appContext = null;
    @org.jetbrains.annotations.NotNull()
    private final androidx.datastore.preferences.core.Preferences.Key<java.lang.String> pairTokenKey = null;
    @org.jetbrains.annotations.NotNull()
    private final kotlinx.coroutines.flow.Flow<java.lang.String> pairTokenFlow = null;
    
    public TokenStore(@org.jetbrains.annotations.NotNull()
    android.content.Context appContext) {
        super();
    }
    
    @org.jetbrains.annotations.NotNull()
    public final kotlinx.coroutines.flow.Flow<java.lang.String> getPairTokenFlow() {
        return null;
    }
    
    @org.jetbrains.annotations.Nullable()
    public final java.lang.Object savePairToken(@org.jetbrains.annotations.NotNull()
    java.lang.String token, @org.jetbrains.annotations.NotNull()
    kotlin.coroutines.Continuation<? super kotlin.Unit> $completion) {
        return null;
    }
    
    @org.jetbrains.annotations.Nullable()
    public final java.lang.Object clearPairToken(@org.jetbrains.annotations.NotNull()
    kotlin.coroutines.Continuation<? super kotlin.Unit> $completion) {
        return null;
    }
}