package vip.soyspray.infiniteslop;

import android.app.Activity;
import android.graphics.Color;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.KeyEvent;
import android.view.WindowManager;
import android.webkit.RenderProcessGoneDetail;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

/** Infinite Slop full screen on the living-room TV, with a stall watchdog. */
public class MainActivity extends Activity {
    private static final String URL = "https://infiniteslop.ai/";

    // The site lays out its large-screen view for desktop browsers.
    private static final String DESKTOP_AGENT =
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
                    + "Chrome/98.0.4758.101 Safari/537.36";

    // Start with sound, hide the splash, the end-of-event banner and the chat
    // and queue panels, and reload when no video has advanced for a minute.
    // OK on the remote toggles the panels.
    private static final String KIOSK = """
            (() => {
              if (window.soyKiosk) return;
              window.soyKiosk = true;
              const byId = (id) => document.getElementById(id);
              const start = () => {
                // The splash is position: fixed, so offsetParent is always null;
                // clicking it removes it.
                const splash = byId('splash');
                if (splash) splash.click();
                const ended = byId('endbanner');
                if (ended) ended.remove();
                const mute = byId('mute');
                if (mute && /unmute/i.test(mute.textContent)) mute.click();
              };
              window.soyToggle = () => { const button = byId('chattoggle'); if (button) button.click(); };
              [1500, 4000, 8000].forEach((ms) => setTimeout(start, ms));
              setTimeout(() => {
                if (!document.body.classList.contains('chat-closed')) window.soyToggle();
              }, 6000);
              let last = '';
              let still = 0;
              setInterval(() => {
                const now = [...document.querySelectorAll('video')]
                  .map((video) => video.currentTime.toFixed(1)).join(',');
                still = now === last ? still + 10 : 0;
                last = now;
                if (still >= 60) location.reload();
                start();
              }, 10000);
            })();
            """;

    private final Handler handler = new Handler(Looper.getMainLooper());
    private WebView web;

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        web = new WebView(this);
        web.setBackgroundColor(Color.BLACK);
        WebSettings settings = web.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setMediaPlaybackRequiresUserGesture(false);
        settings.setUserAgentString(DESKTOP_AGENT);
        web.setWebChromeClient(new WebChromeClient());
        web.setWebViewClient(new WebViewClient() {
            @Override
            public void onPageFinished(WebView view, String url) {
                view.evaluateJavascript(KIOSK, null);
            }

            @Override
            public void onReceivedError(
                    WebView view, WebResourceRequest request, WebResourceError error) {
                if (request.isForMainFrame()) {
                    reloadLater();
                }
            }

            @Override
            public boolean onRenderProcessGone(WebView view, RenderProcessGoneDetail detail) {
                recreate();
                return true;
            }
        });
        setContentView(web);
        web.loadUrl(URL);
    }

    private void reloadLater() {
        handler.removeCallbacksAndMessages(null);
        handler.postDelayed(() -> web.loadUrl(URL), 10_000);
    }

    @Override
    public boolean onKeyDown(int keyCode, KeyEvent event) {
        if (keyCode == KeyEvent.KEYCODE_DPAD_CENTER || keyCode == KeyEvent.KEYCODE_ENTER) {
            web.evaluateJavascript("window.soyToggle && window.soyToggle()", null);
            return true;
        }
        return super.onKeyDown(keyCode, event);
    }

    @Override
    protected void onStop() {
        super.onStop();
        // Leaving the tile stops the stream; opening it again starts fresh.
        finish();
    }

    @Override
    protected void onDestroy() {
        handler.removeCallbacksAndMessages(null);
        web.destroy();
        super.onDestroy();
    }
}
