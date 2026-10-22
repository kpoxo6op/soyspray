package vip.soyspray.aitv;

import android.app.Activity;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.Gravity;
import android.view.KeyEvent;
import android.view.View;
import android.view.WindowManager;
import android.webkit.RenderProcessGoneDetail;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.FrameLayout;
import android.widget.TextView;

/**
 * fal.live's AI channels full screen on the living-room TV. Left and right
 * (or channel up and down) change channel, OK enters with sound, Back leaves.
 */
public class MainActivity extends Activity {
    private static final String URL = "https://fal.live/";
    private static final String[] CHANNELS = {
        "Anime", "Chaos", "Sitcom", "Soap Opera", "Wildlife World",
    };

    // The site lays out its large-screen view for desktop browsers.
    private static final String DESKTOP_AGENT =
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
                    + "Chrome/98.0.4758.101 Safari/537.36";

    // Helpers the remote keys call. soyEnter presses the site's own "Enter
    // with sound" button; soyStage makes the live stage fill the screen once
    // the entry gate is gone; soyWatch reloads when the video stops moving.
    private static final String KIOSK = """
            (() => {
              if (window.soyKiosk) return;
              window.soyKiosk = true;
              const buttons = () => [...document.querySelectorAll('button')];
              const named = (name) => buttons().find((b) =>
                (b.innerText || '').trim().split('\\n')[0] === name);
              window.soyGate = () => !!named('Enter with sound');
              window.soyEnter = () => { const b = named('Enter with sound'); if (b) b.click(); };
              window.soyChannel = (name) => { const b = named(name); if (b) b.click(); };
              window.soyStage = () => {
                if (window.soyGate() || document.getElementById('soytv')) return;
                const style = document.createElement('style');
                style.id = 'soytv';
                style.textContent = 'section#live{position:fixed!important;inset:0!important;'
                  + 'z-index:2147483000!important;background:#000!important}'
                  + 'section#live video{width:100vw!important;height:100vh!important;'
                  + 'object-fit:contain!important}';
                document.head.appendChild(style);
              };
              let last = -1;
              let still = 0;
              setInterval(() => {
                window.soyStage();
                const video = document.querySelector('section#live video');
                const now = video ? video.currentTime : -1;
                still = video && now !== last ? 0 : still + 10;
                last = now;
                if (still >= 60) location.reload();
              }, 10000);
            })();
            """;

    private final Handler handler = new Handler(Looper.getMainLooper());
    private WebView web;
    private TextView banner;
    private TextView hint;
    private int channel;

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        float dp = getResources().getDisplayMetrics().density;
        FrameLayout root = new FrameLayout(this);
        root.setBackgroundColor(Color.BLACK);
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
                handler.postDelayed(MainActivity.this::checkGate, 2500);
            }

            @Override
            public void onReceivedError(
                    WebView view, WebResourceRequest request, WebResourceError error) {
                if (request.isForMainFrame()) {
                    handler.postDelayed(() -> web.loadUrl(URL), 10_000);
                }
            }

            @Override
            public boolean onRenderProcessGone(WebView view, RenderProcessGoneDetail detail) {
                recreate();
                return true;
            }
        });
        root.addView(web, new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.MATCH_PARENT));

        banner = pill(dp, 22);
        FrameLayout.LayoutParams bannerAt = new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.WRAP_CONTENT, FrameLayout.LayoutParams.WRAP_CONTENT,
                Gravity.TOP | Gravity.START);
        bannerAt.setMargins((int) (40 * dp), (int) (32 * dp), 0, 0);
        root.addView(banner, bannerAt);

        hint = pill(dp, 20);
        hint.setText("Press OK to start with sound");
        root.addView(hint, new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.WRAP_CONTENT, FrameLayout.LayoutParams.WRAP_CONTENT,
                Gravity.CENTER));
        setContentView(root);
        web.loadUrl(URL);
        showChannel();
    }

    private TextView pill(float dp, float sp) {
        TextView view = new TextView(this);
        view.setTextColor(Color.WHITE);
        view.setTextSize(sp);
        view.setTypeface(Typeface.create("sans-serif-medium", Typeface.NORMAL));
        view.setPadding((int) (20 * dp), (int) (10 * dp), (int) (20 * dp), (int) (10 * dp));
        GradientDrawable back = new GradientDrawable();
        back.setColor(0xB3000000);
        back.setCornerRadius(24 * dp);
        view.setBackground(back);
        view.setVisibility(View.GONE);
        return view;
    }

    /** Shows the start hint while the site's entry gate is up. */
    private void checkGate() {
        web.evaluateJavascript("window.soyGate && window.soyGate()", value -> {
            boolean gate = "true".equals(value);
            hint.setVisibility(gate ? View.VISIBLE : View.GONE);
            if (!gate) {
                web.evaluateJavascript("window.soyStage && window.soyStage()", null);
            }
        });
    }

    private void showChannel() {
        banner.setText("AI TV  ·  " + CHANNELS[channel]);
        banner.setAlpha(1f);
        banner.setVisibility(View.VISIBLE);
        banner.animate().cancel();
        banner.animate().alpha(0f).setStartDelay(3000).setDuration(600).start();
    }

    private void tune(int step) {
        channel = (channel + step + CHANNELS.length) % CHANNELS.length;
        web.evaluateJavascript(
                "window.soyChannel && window.soyChannel('" + CHANNELS[channel] + "')", null);
        showChannel();
        handler.postDelayed(this::checkGate, 1500);
    }

    @Override
    public boolean onKeyDown(int keyCode, KeyEvent event) {
        switch (keyCode) {
            case KeyEvent.KEYCODE_DPAD_CENTER:
            case KeyEvent.KEYCODE_ENTER:
                web.evaluateJavascript("window.soyEnter && window.soyEnter()", null);
                handler.postDelayed(this::checkGate, 1200);
                showChannel();
                return true;
            case KeyEvent.KEYCODE_DPAD_RIGHT:
            case KeyEvent.KEYCODE_DPAD_UP:
            case KeyEvent.KEYCODE_CHANNEL_UP:
                tune(1);
                return true;
            case KeyEvent.KEYCODE_DPAD_LEFT:
            case KeyEvent.KEYCODE_DPAD_DOWN:
            case KeyEvent.KEYCODE_CHANNEL_DOWN:
                tune(-1);
                return true;
            default:
                return super.onKeyDown(keyCode, event);
        }
    }

    @Override
    protected void onStop() {
        super.onStop();
        // Leaving the app stops the stream; opening it again starts fresh.
        finish();
    }

    @Override
    protected void onDestroy() {
        handler.removeCallbacksAndMessages(null);
        web.destroy();
        super.onDestroy();
    }
}
