package nativeapp.kor35.it;

import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.graphics.Color;
import android.graphics.drawable.ColorDrawable;
import android.os.Build;
import android.os.Bundle;
import android.view.View;
import android.view.ViewGroup;
import androidx.activity.EdgeToEdge;
import androidx.core.graphics.Insets;
import androidx.core.view.ViewCompat;
import androidx.core.view.WindowCompat;
import androidx.core.view.WindowInsetsCompat;
import androidx.core.view.WindowInsetsControllerCompat;
import com.getcapacitor.BridgeActivity;

/**
 * Shell Capacitor: canali FCM + inset di sistema.
 *
 * Su Android 15+ (targetSdk ≥ 35) l'edge-to-edge è forzato: la WebView finisce
 * sotto status/navigation bar. setOverlaysWebView(false) e CSS env(safe-area-*)
 * non bastano. Padding nativo sul content root = fix affidabile.
 */
public class MainActivity extends BridgeActivity {
    public static final String CHANNEL_INCOMING_CALLS = "kor35_incoming_calls";
    public static final String CHANNEL_DEFAULT = "kor35_default";

    private static final int CHROME_COLOR = Color.parseColor("#111827");

    @Override
    public void onCreate(Bundle savedInstanceState) {
        ensureNotificationChannels();
        // L'activity nasce con AppTheme.NoActionBarLaunch (Theme.SplashScreen), il cui
        // background è la splash bianca. Senza il plugin SplashScreen quel tema resta:
        // l'area del padding inset mostrerebbe una banda bianca sotto la status bar.
        setTheme(R.style.AppTheme_NoActionBar);
        // Consistente su API < 35 e ≥ 35: disegna edge-to-edge, poi paddiamo noi.
        EdgeToEdge.enable(this);
        super.onCreate(savedInstanceState);
        applySystemBarInsetsToWebContent();
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

    /**
     * Applica systemBars + displayCutout come padding sul content root
     * (CoordinatorLayout Capacitor). Non sul WebView: lì gli inset arrivano a 0.
     */
    private void applySystemBarInsetsToWebContent() {
        final View content = findViewById(android.R.id.content);
        if (content == null) {
            return;
        }

        // Preferisci il primo figlio (layout bridge) se presente.
        final View target =
            (content instanceof ViewGroup && ((ViewGroup) content).getChildCount() > 0)
                ? ((ViewGroup) content).getChildAt(0)
                : content;

        ViewCompat.setOnApplyWindowInsetsListener(target, (v, windowInsets) -> {
            Insets bars = windowInsets.getInsets(
                WindowInsetsCompat.Type.systemBars() | WindowInsetsCompat.Type.displayCutout()
            );
            v.setPadding(bars.left, bars.top, bars.right, bars.bottom);
            // Azzera solo ciò che abbiamo consumato; lascia passare IME ecc.
            return new WindowInsetsCompat.Builder(windowInsets)
                .setInsets(
                    WindowInsetsCompat.Type.systemBars() | WindowInsetsCompat.Type.displayCutout(),
                    Insets.NONE
                )
                .build();
        });
        ViewCompat.requestApplyInsets(target);
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
