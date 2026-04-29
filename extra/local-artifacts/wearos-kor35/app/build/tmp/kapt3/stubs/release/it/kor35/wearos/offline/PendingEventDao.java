package it.kor35.wearos.offline;

@kotlin.Metadata(mv = {1, 9, 0}, k = 1, xi = 48, d1 = {"\u0000*\n\u0002\u0018\u0002\n\u0002\u0010\u0000\n\u0000\n\u0002\u0010\u0002\n\u0000\n\u0002\u0010 \n\u0002\u0010\u000e\n\u0002\b\u0002\n\u0002\u0018\u0002\n\u0000\n\u0002\u0010\b\n\u0002\b\u0005\bg\u0018\u00002\u00020\u0001J\u001c\u0010\u0002\u001a\u00020\u00032\f\u0010\u0004\u001a\b\u0012\u0004\u0012\u00020\u00060\u0005H\u00a7@\u00a2\u0006\u0002\u0010\u0007J\u001c\u0010\b\u001a\b\u0012\u0004\u0012\u00020\t0\u00052\u0006\u0010\n\u001a\u00020\u000bH\u00a7@\u00a2\u0006\u0002\u0010\fJ\u0016\u0010\r\u001a\u00020\u00032\u0006\u0010\u000e\u001a\u00020\tH\u00a7@\u00a2\u0006\u0002\u0010\u000f\u00a8\u0006\u0010"}, d2 = {"Lit/kor35/wearos/offline/PendingEventDao;", "", "deleteByIds", "", "ids", "", "", "(Ljava/util/List;Lkotlin/coroutines/Continuation;)Ljava/lang/Object;", "nextBatch", "Lit/kor35/wearos/offline/PendingEventEntity;", "limit", "", "(ILkotlin/coroutines/Continuation;)Ljava/lang/Object;", "upsert", "event", "(Lit/kor35/wearos/offline/PendingEventEntity;Lkotlin/coroutines/Continuation;)Ljava/lang/Object;", "app_release"})
@androidx.room.Dao()
public abstract interface PendingEventDao {
    
    @androidx.room.Insert(onConflict = 1)
    @org.jetbrains.annotations.Nullable()
    public abstract java.lang.Object upsert(@org.jetbrains.annotations.NotNull()
    it.kor35.wearos.offline.PendingEventEntity event, @org.jetbrains.annotations.NotNull()
    kotlin.coroutines.Continuation<? super kotlin.Unit> $completion);
    
    @androidx.room.Query(value = "SELECT * FROM pending_events ORDER BY createdAtEpochMs ASC LIMIT :limit")
    @org.jetbrains.annotations.Nullable()
    public abstract java.lang.Object nextBatch(int limit, @org.jetbrains.annotations.NotNull()
    kotlin.coroutines.Continuation<? super java.util.List<it.kor35.wearos.offline.PendingEventEntity>> $completion);
    
    @androidx.room.Query(value = "DELETE FROM pending_events WHERE id IN (:ids)")
    @org.jetbrains.annotations.Nullable()
    public abstract java.lang.Object deleteByIds(@org.jetbrains.annotations.NotNull()
    java.util.List<java.lang.String> ids, @org.jetbrains.annotations.NotNull()
    kotlin.coroutines.Continuation<? super kotlin.Unit> $completion);
}