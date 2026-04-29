package it.kor35.wearos.ui;

@kotlin.Metadata(mv = {1, 9, 0}, k = 1, xi = 48, d1 = {"\u0000>\n\u0002\u0018\u0002\n\u0002\u0018\u0002\n\u0000\n\u0002\u0018\u0002\n\u0002\b\u0002\n\u0002\u0018\u0002\n\u0002\u0018\u0002\n\u0000\n\u0002\u0018\u0002\n\u0000\n\u0002\u0018\u0002\n\u0002\b\u0003\n\u0002\u0010\u0002\n\u0000\n\u0002\u0010\u000e\n\u0000\n\u0002\u0010\b\n\u0002\b\u0006\u0018\u00002\u00020\u0001B\r\u0012\u0006\u0010\u0002\u001a\u00020\u0003\u00a2\u0006\u0002\u0010\u0004J\u0016\u0010\u000e\u001a\u00020\u000f2\u0006\u0010\u0010\u001a\u00020\u00112\u0006\u0010\u0012\u001a\u00020\u0013J\u0010\u0010\u0014\u001a\u00020\u000f2\u0006\u0010\u0015\u001a\u00020\u0011H\u0002J\u0006\u0010\u0016\u001a\u00020\u000fJ\b\u0010\u0017\u001a\u00020\u000fH\u0002J\u0006\u0010\u0018\u001a\u00020\u000fR\u0014\u0010\u0005\u001a\b\u0012\u0004\u0012\u00020\u00070\u0006X\u0082\u0004\u00a2\u0006\u0002\n\u0000R\u000e\u0010\b\u001a\u00020\tX\u0082\u0004\u00a2\u0006\u0002\n\u0000R\u0017\u0010\n\u001a\b\u0012\u0004\u0012\u00020\u00070\u000b\u00a2\u0006\b\n\u0000\u001a\u0004\b\f\u0010\r\u00a8\u0006\u0019"}, d2 = {"Lit/kor35/wearos/ui/WatchViewModel;", "Landroidx/lifecycle/AndroidViewModel;", "app", "Landroid/app/Application;", "(Landroid/app/Application;)V", "_state", "Lkotlinx/coroutines/flow/MutableStateFlow;", "Lit/kor35/wearos/ui/WatchUiState;", "repo", "Lit/kor35/wearos/data/WatchRepository;", "state", "Lkotlinx/coroutines/flow/StateFlow;", "getState", "()Lkotlinx/coroutines/flow/StateFlow;", "applyDelta", "", "sigla", "", "delta", "", "beginPairingPolling", "code", "refreshProfile", "restoreSession", "startPairing", "app_release"})
public final class WatchViewModel extends androidx.lifecycle.AndroidViewModel {
    @org.jetbrains.annotations.NotNull()
    private final it.kor35.wearos.data.WatchRepository repo = null;
    @org.jetbrains.annotations.NotNull()
    private final kotlinx.coroutines.flow.MutableStateFlow<it.kor35.wearos.ui.WatchUiState> _state = null;
    @org.jetbrains.annotations.NotNull()
    private final kotlinx.coroutines.flow.StateFlow<it.kor35.wearos.ui.WatchUiState> state = null;
    
    public WatchViewModel(@org.jetbrains.annotations.NotNull()
    android.app.Application app) {
        super(null);
    }
    
    @org.jetbrains.annotations.NotNull()
    public final kotlinx.coroutines.flow.StateFlow<it.kor35.wearos.ui.WatchUiState> getState() {
        return null;
    }
    
    public final void startPairing() {
    }
    
    public final void applyDelta(@org.jetbrains.annotations.NotNull()
    java.lang.String sigla, int delta) {
    }
    
    public final void refreshProfile() {
    }
    
    private final void restoreSession() {
    }
    
    private final void beginPairingPolling(java.lang.String code) {
    }
}