package it.kor35.wearos.data

import android.content.Context
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.emptyPreferences
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.map
import java.io.IOException

private val Context.watchDataStore by preferencesDataStore(name = "watch_prefs")

class TokenStore(private val appContext: Context) {
    private val pairTokenKey: Preferences.Key<String> = stringPreferencesKey("pair_token")

    val pairTokenFlow: Flow<String> = appContext.watchDataStore.data
        .catch {
            if (it is IOException) emit(emptyPreferences()) else throw it
        }
        .map { prefs -> prefs[pairTokenKey].orEmpty() }

    suspend fun savePairToken(token: String) {
        appContext.watchDataStore.edit { prefs ->
            prefs[pairTokenKey] = token
        }
    }

    suspend fun clearPairToken() {
        appContext.watchDataStore.edit { prefs ->
            prefs.remove(pairTokenKey)
        }
    }
}
