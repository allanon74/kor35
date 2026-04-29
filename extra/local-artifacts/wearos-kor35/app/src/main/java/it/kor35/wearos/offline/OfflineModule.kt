package it.kor35.wearos.offline

import android.content.Context
import androidx.room.Room

object OfflineModule {
    fun database(context: Context): AppDatabase =
        Room.databaseBuilder(context, AppDatabase::class.java, "kor35_wear.db").build()
}
