package it.kor35.wearos.offline;

import android.database.Cursor;
import android.os.CancellationSignal;
import androidx.annotation.NonNull;
import androidx.room.CoroutinesRoom;
import androidx.room.EntityInsertionAdapter;
import androidx.room.RoomDatabase;
import androidx.room.RoomSQLiteQuery;
import androidx.room.util.CursorUtil;
import androidx.room.util.DBUtil;
import androidx.room.util.StringUtil;
import androidx.sqlite.db.SupportSQLiteStatement;
import java.lang.Class;
import java.lang.Exception;
import java.lang.Object;
import java.lang.Override;
import java.lang.String;
import java.lang.StringBuilder;
import java.lang.SuppressWarnings;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.concurrent.Callable;
import javax.annotation.processing.Generated;
import kotlin.Unit;
import kotlin.coroutines.Continuation;

@Generated("androidx.room.RoomProcessor")
@SuppressWarnings({"unchecked", "deprecation"})
public final class PendingEventDao_Impl implements PendingEventDao {
  private final RoomDatabase __db;

  private final EntityInsertionAdapter<PendingEventEntity> __insertionAdapterOfPendingEventEntity;

  public PendingEventDao_Impl(@NonNull final RoomDatabase __db) {
    this.__db = __db;
    this.__insertionAdapterOfPendingEventEntity = new EntityInsertionAdapter<PendingEventEntity>(__db) {
      @Override
      @NonNull
      protected String createQuery() {
        return "INSERT OR REPLACE INTO `pending_events` (`id`,`statSigla`,`delta`,`createdAtEpochMs`) VALUES (?,?,?,?)";
      }

      @Override
      protected void bind(@NonNull final SupportSQLiteStatement statement,
          @NonNull final PendingEventEntity entity) {
        if (entity.getId() == null) {
          statement.bindNull(1);
        } else {
          statement.bindString(1, entity.getId());
        }
        if (entity.getStatSigla() == null) {
          statement.bindNull(2);
        } else {
          statement.bindString(2, entity.getStatSigla());
        }
        statement.bindLong(3, entity.getDelta());
        statement.bindLong(4, entity.getCreatedAtEpochMs());
      }
    };
  }

  @Override
  public Object upsert(final PendingEventEntity event,
      final Continuation<? super Unit> $completion) {
    return CoroutinesRoom.execute(__db, true, new Callable<Unit>() {
      @Override
      @NonNull
      public Unit call() throws Exception {
        __db.beginTransaction();
        try {
          __insertionAdapterOfPendingEventEntity.insert(event);
          __db.setTransactionSuccessful();
          return Unit.INSTANCE;
        } finally {
          __db.endTransaction();
        }
      }
    }, $completion);
  }

  @Override
  public Object nextBatch(final int limit,
      final Continuation<? super List<PendingEventEntity>> $completion) {
    final String _sql = "SELECT * FROM pending_events ORDER BY createdAtEpochMs ASC LIMIT ?";
    final RoomSQLiteQuery _statement = RoomSQLiteQuery.acquire(_sql, 1);
    int _argIndex = 1;
    _statement.bindLong(_argIndex, limit);
    final CancellationSignal _cancellationSignal = DBUtil.createCancellationSignal();
    return CoroutinesRoom.execute(__db, false, _cancellationSignal, new Callable<List<PendingEventEntity>>() {
      @Override
      @NonNull
      public List<PendingEventEntity> call() throws Exception {
        final Cursor _cursor = DBUtil.query(__db, _statement, false, null);
        try {
          final int _cursorIndexOfId = CursorUtil.getColumnIndexOrThrow(_cursor, "id");
          final int _cursorIndexOfStatSigla = CursorUtil.getColumnIndexOrThrow(_cursor, "statSigla");
          final int _cursorIndexOfDelta = CursorUtil.getColumnIndexOrThrow(_cursor, "delta");
          final int _cursorIndexOfCreatedAtEpochMs = CursorUtil.getColumnIndexOrThrow(_cursor, "createdAtEpochMs");
          final List<PendingEventEntity> _result = new ArrayList<PendingEventEntity>(_cursor.getCount());
          while (_cursor.moveToNext()) {
            final PendingEventEntity _item;
            final String _tmpId;
            if (_cursor.isNull(_cursorIndexOfId)) {
              _tmpId = null;
            } else {
              _tmpId = _cursor.getString(_cursorIndexOfId);
            }
            final String _tmpStatSigla;
            if (_cursor.isNull(_cursorIndexOfStatSigla)) {
              _tmpStatSigla = null;
            } else {
              _tmpStatSigla = _cursor.getString(_cursorIndexOfStatSigla);
            }
            final int _tmpDelta;
            _tmpDelta = _cursor.getInt(_cursorIndexOfDelta);
            final long _tmpCreatedAtEpochMs;
            _tmpCreatedAtEpochMs = _cursor.getLong(_cursorIndexOfCreatedAtEpochMs);
            _item = new PendingEventEntity(_tmpId,_tmpStatSigla,_tmpDelta,_tmpCreatedAtEpochMs);
            _result.add(_item);
          }
          return _result;
        } finally {
          _cursor.close();
          _statement.release();
        }
      }
    }, $completion);
  }

  @Override
  public Object deleteByIds(final List<String> ids, final Continuation<? super Unit> $completion) {
    return CoroutinesRoom.execute(__db, true, new Callable<Unit>() {
      @Override
      @NonNull
      public Unit call() throws Exception {
        final StringBuilder _stringBuilder = StringUtil.newStringBuilder();
        _stringBuilder.append("DELETE FROM pending_events WHERE id IN (");
        final int _inputSize = ids.size();
        StringUtil.appendPlaceholders(_stringBuilder, _inputSize);
        _stringBuilder.append(")");
        final String _sql = _stringBuilder.toString();
        final SupportSQLiteStatement _stmt = __db.compileStatement(_sql);
        int _argIndex = 1;
        for (String _item : ids) {
          if (_item == null) {
            _stmt.bindNull(_argIndex);
          } else {
            _stmt.bindString(_argIndex, _item);
          }
          _argIndex++;
        }
        __db.beginTransaction();
        try {
          _stmt.executeUpdateDelete();
          __db.setTransactionSuccessful();
          return Unit.INSTANCE;
        } finally {
          __db.endTransaction();
        }
      }
    }, $completion);
  }

  @NonNull
  public static List<Class<?>> getRequiredConverters() {
    return Collections.emptyList();
  }
}
