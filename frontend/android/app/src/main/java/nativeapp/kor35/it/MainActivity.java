package nativeapp.kor35.it;

import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.graphics.Color;
import android.graphics.drawable.ColorDrawable;
import android.os.Build;
import android.os.Bundle;
import android.view.View;
import android.view.ViewGroup;
import androidx.core.view.WindowCompat;
import androidx.core.view.WindowInsetsControllerCompat;
import com.getcapacitor.BridgeActivity;

/**
 * Shell Capacitor: canali FCM + colori delle barre di sistema.
 *
 * Gli inset NON si applicano come padding nativo: sposterebbero la WebView e
 * lascerebbero una striscia vuota sopra la UI. Su Android 15+ il plugin core
 * SystemBars (insetsHandling = "css") inietta `--safe-area-inset-*` nella pagina
 * e il CSS insetta header/contenuto (vedi index.css, --kor-safe-top).
 */
public class MainActivity extends BridgeActivity {
    public static final String CHANNEL_INCOMING_CALLS = "kor35_incoming_calls";
    public static final String CHANNEL_DEFAULT = "kor35_default";

    private static final int CHROME_COLOR = Color.parseColor("#111827");

    @Override
    public void onCreate(Bundle savedInstanceState) {
        ensureNotificationChannels();
        // L'activity nasce con AppTheme.NoActionBarLaunch (Theme.SplashScreen), il cui
        // background è la splash bianca: senza il plugin SplashScreen quel tema resta
        // e si vedrebbe bianco dietro la WebView durante il caricamento.
        setTheme(R.style.AppTheme_NoActionBar);
        super.onCreate(savedInstanceState);
        applyChromeBackground();
        styleSystemBars();
    }

    /** Fondo scuro anche su window/layout/WebView: nessuna banda chiara ai bordi. */
    private void applyChromeBackground() {
        getWindow().setBackgroundDrawable(new ColorDrawable(CHROME_COLOR));

        View content = findViewById(android.R.id.content);
        if (content != null) {
            content.setBackgroundColor(CHROME_COLOR);
            if (content instanceof ViewGroup && ((ViewGroup) content).getChildCount() > 0) {
                ((ViewGroup) content).getChildAt(0).setBackgroundColor(CHROME_COLOR);
            }
        }

        if (getBridge() != null && getBridge().getWebView() != null) {
            getBridge().getWebView().setBackgroundColor(CHROME_COLOR);
        }
    }

    private void styleSystemBars() {
        getWindow().setStatusBarColor(CHROME_COLOR);
        getWindow().setNavigationBarColor(CHROME_COLOR);
        View decor = getWindow().getDecorView();
        WindowInsetsControllerCompat controller =
            WindowCompat.getInsetsController(getWindow(), decor);
        if (controller != null) {
            controller.setAppearanceLightStatusBars(false);
            controller.setAppearanceLightNavigationBars(false);
        }
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
