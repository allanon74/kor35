package nativeapp.kor35.it;

import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.os.Build;
import android.os.Bundle;
import androidx.core.view.WindowCompat;
import com.getcapacitor.BridgeActivity;

/**
 * Shell Capacitor: canali FCM + inset di sistema
 * (la WebView non deve finire sotto la status bar).
 */
public class MainActivity extends BridgeActivity {
    public static final String CHANNEL_INCOMING_CALLS = "kor35_incoming_calls";
    public static final String CHANNEL_DEFAULT = "kor35_default";

    @Override
    public void onCreate(Bundle savedInstanceState) {
        ensureNotificationChannels();
        WindowCompat.setDecorFitsSystemWindows(getWindow(), true);
        super.onCreate(savedInstanceState);
    }

    private void ensureNotificationChannels() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) {
            return;
        }
        NotificationManager manager = getSystemService(NotificationManager.class);
        if (manager == null) {
            return;
        }

        NotificationChannel calls = new NotificationChannel(
            CHANNEL_INCOMING_CALLS,
            "Chiamate vocali KOR35",
            NotificationManager.IMPORTANCE_HIGH
        );
        calls.setDescription("Squillo e avvisi per chiamate in arrivo");
        calls.enableVibration(true);
        calls.setLockscreenVisibility(android.app.Notification.VISIBILITY_PUBLIC);
        calls.setBypassDnd(true);

        NotificationChannel defaults = new NotificationChannel(
            CHANNEL_DEFAULT,
            "Notifiche KOR35",
            NotificationManager.IMPORTANCE_DEFAULT
        );
        defaults.setDescription("Messaggi e avvisi generici");

        manager.createNotificationChannel(calls);
        manager.createNotificationChannel(defaults);
    }
}
