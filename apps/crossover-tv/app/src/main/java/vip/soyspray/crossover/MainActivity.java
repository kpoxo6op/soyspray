package vip.soyspray.crossover;

import android.app.Activity;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.view.KeyEvent;
import android.webkit.JavascriptInterface;
import android.webkit.RenderProcessGoneDetail;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import java.lang.ref.WeakReference;

/**
 * Crossover on the living-room TV, drawn full screen by a local page in the
 * WebView: a first screen with the mortgage-free line, and the full plan below
 * it (the date, the chart and the stages). The page shows the view the laptop
 * last sent (see {@link DataReceiver}) and nothing else; the app has no network
 * access. OK shows or hides amounts; down and up move between the first screen
 * and the plan. Back leaves, and leaving closes the page, so the next visit
 * starts on the first screen with amounts hidden.
 */
public class MainActivity extends Activity {
    private static final int GROUND = 0xFF1A1D20;

    // The page on screen, for a new view to reach. Main thread only.
    private static WeakReference<MainActivity> shown = new WeakReference<>(null);

    private WebView web;
    private SharedPreferences prefs;

    /** What the page may ask of the app. */
    private final class Bridge {
        /** The last view from the laptop, or null. */
        @JavascriptInterface
        public String view() {
            return ViewStore.read(MainActivity.this);
        }

        /** The date shown on the last visit, for the change since then. */
        @JavascriptInterface
        public String get(String key) {
            return prefs.getString(key, null);
        }

        @JavascriptInterface
        public void put(String key, String value) {
            prefs.edit().putString(key, value).apply();
        }
    }

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        prefs = getSharedPreferences("page", MODE_PRIVATE);

        // Lets Chrome DevTools attach over adb; only adb's shell user can open
        // the socket.
        WebView.setWebContentsDebuggingEnabled(true);
        web = new WebView(this);
        web.setBackgroundColor(GROUND);
        web.setFocusable(false);
        WebSettings settings = web.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setAllowFileAccess(false);
        settings.setAllowContentAccess(false);
        settings.setBlockNetworkLoads(true);
        // The page sizes its type to the screen; the system font scale would
        // break the layout.
        settings.setTextZoom(100);
        web.addJavascriptInterface(new Bridge(), "CrossoverTv");
        web.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                return true;
            }

            @Override
            public boolean onRenderProcessGone(WebView view, RenderProcessGoneDetail detail) {
                recreate();
                return true;
            }
        });
        web.loadUrl("file:///android_asset/index.html");
        setContentView(web);
    }

    @Override
    public boolean dispatchKeyEvent(KeyEvent event) {
        int code = event.getKeyCode();
        boolean first = event.getAction() == KeyEvent.ACTION_DOWN && event.getRepeatCount() == 0;
        if (code == KeyEvent.KEYCODE_DPAD_CENTER || code == KeyEvent.KEYCODE_ENTER
                || code == KeyEvent.KEYCODE_NUMPAD_ENTER) {
            if (first) {
                web.evaluateJavascript("window.crossoverToggle && crossoverToggle()", null);
            }
            return true;
        }
        // The page is not focusable, so the arrows reach it only from here:
        // down shows the plan and up returns.
        String key = arrow(code);
        if (key == null) {
            return super.dispatchKeyEvent(event);
        }
        if (first) {
            web.evaluateJavascript("window.crossoverKey && crossoverKey('" + key + "')", null);
        }
        return true;
    }

    private static String arrow(int code) {
        switch (code) {
            case KeyEvent.KEYCODE_DPAD_UP:
                return "up";
            case KeyEvent.KEYCODE_DPAD_DOWN:
                return "down";
            case KeyEvent.KEYCODE_DPAD_LEFT:
                return "left";
            case KeyEvent.KEYCODE_DPAD_RIGHT:
                return "right";
            default:
                return null;
        }
    }

    @Override
    protected void onResume() {
        super.onResume();
        shown = new WeakReference<>(this);
    }

    @Override
    protected void onPause() {
        if (shown.get() == this) {
            shown = new WeakReference<>(null);
        }
        super.onPause();
    }

    @Override
    protected void onStop() {
        super.onStop();
        finish();
    }

    @Override
    protected void onDestroy() {
        web.destroy();
        super.onDestroy();
    }

    /** Redraws the page on screen, if any, after a new view arrives. */
    static void reloadIfShown() {
        MainActivity activity = shown.get();
        if (activity != null) {
            activity.web.evaluateJavascript("window.crossoverReload && crossoverReload()", null);
        }
    }
}
