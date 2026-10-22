package vip.soyspray.aitv;

import android.app.Activity;
import android.content.SharedPreferences;
import android.graphics.Bitmap;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
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
import android.widget.LinearLayout;
import android.widget.TextView;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import org.json.JSONException;
import org.json.JSONObject;
import org.json.JSONTokener;

/**
 * AI-made television full screen on the living-room TV: fal.live's live
 * channels, Google's Flow TV and the endless sitcom Nothing, Forever. Up and
 * down (or channel up and down) change channel, left and right change network,
 * OK answers the site's entry dialog, Back leaves.
 */
public class MainActivity extends Activity {
    private static final class Network {
        final String name;
        /** The first page to open, or null for the Twitch embed. */
        final String home;
        final String host;

        Network(String name, String home, String host) {
            this.name = name;
            this.home = home;
            this.host = host;
        }
    }

    private static final Network[] NETWORKS = {
        new Network("fal.live", "https://fal.live/", "fal.live"),
        new Network("Flow TV", "https://labs.google/flow/tv", "labs.google"),
        new Network("Nothing, Forever", null, "soyspray.vip"),
    };

    // Twitch plays an embed only inside a page from the domain it names as parent.
    private static final String TWITCH_BASE = "https://soyspray.vip/";
    private static final String TWITCH_PAGE = "<!doctype html><body style=\"margin:0;background:#000\">"
            + "<iframe src=\"https://player.twitch.tv/?channel=watchmeforever&parent=soyspray.vip"
            + "&autoplay=true&muted=false\" allow=\"autoplay; fullscreen\" style=\"position:fixed;"
            + "inset:0;width:100vw;height:100vh;border:0\"></iframe></body>";

    // The sites lay out their large-screen views for desktop browsers.
    private static final String DESKTOP_AGENT =
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
                    + "Chrome/98.0.4758.101 Safari/537.36";

    private static final long SPLASH_LIMIT = 12_000;

    private final Handler handler = new Handler(Looper.getMainLooper());
    private SharedPreferences prefs;
    private String kiosk;
    private WebView web;
    private View splash;
    private TextView splashName;
    private View pill;
    private TextView pillName;
    private TextView pillHint;
    private int network;
    private String channel = "";
    private long loadedAt;
    private boolean revealed;
    private boolean hinted;

    private final Runnable tick = new Runnable() {
        @Override
        public void run() {
            web.evaluateJavascript("window.soyTick ? soyTick() : ''", MainActivity.this::onTick);
            handler.postDelayed(this, 1000);
        }
    };

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        prefs = getPreferences(MODE_PRIVATE);
        kiosk = asset("kiosk.js");
        float dp = getResources().getDisplayMetrics().density;
        FrameLayout root = new FrameLayout(this);
        root.setBackgroundColor(Color.BLACK);

        // Lets Chrome DevTools attach over adb when a site changes; only adb's
        // shell user can open the socket.
        WebView.setWebContentsDebuggingEnabled(true);
        web = new WebView(this);
        web.setBackgroundColor(Color.BLACK);
        web.setFocusable(false);
        WebSettings settings = web.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setMediaPlaybackRequiresUserGesture(false);
        settings.setUserAgentString(DESKTOP_AGENT);
        web.setWebChromeClient(new WebChromeClient() {
            // Without this the WebView paints a grey play button over videos
            // that have no frame yet.
            @Override
            public Bitmap getDefaultVideoPoster() {
                return Bitmap.createBitmap(1, 1, Bitmap.Config.ARGB_8888);
            }
        });
        web.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                // Stay on the TV sites; links elsewhere (Discord, terms pages)
                // would strand the remote.
                return request.isForMainFrame() && !onAllowedHost(request.getUrl());
            }

            @Override
            public void onPageCommitVisible(WebView view, String url) {
                view.evaluateJavascript(kiosk, null);
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                view.evaluateJavascript(kiosk, null);
                if (NETWORKS[network].home == null) {
                    handler.postDelayed(MainActivity.this::reveal, 3000);
                }
            }

            @Override
            public void onReceivedError(
                    WebView view, WebResourceRequest request, WebResourceError error) {
                if (request.isForMainFrame()) {
                    handler.postDelayed(() -> open(network), 10_000);
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

        LinearLayout cover = new LinearLayout(this);
        cover.setOrientation(LinearLayout.VERTICAL);
        cover.setGravity(Gravity.CENTER);
        cover.setBackgroundColor(Color.BLACK);
        TextView label = text(15, "sans-serif-medium", 0x80FFFFFF);
        label.setText("AI TV");
        label.setLetterSpacing(0.3f);
        cover.addView(label);
        splashName = text(44, "sans-serif-light", Color.WHITE);
        splashName.setPadding(0, (int) (10 * dp), 0, 0);
        cover.addView(splashName);
        root.addView(cover, new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.MATCH_PARENT));
        splash = cover;

        LinearLayout box = new LinearLayout(this);
        box.setOrientation(LinearLayout.VERTICAL);
        box.setGravity(Gravity.CENTER_HORIZONTAL);
        box.setPadding((int) (28 * dp), (int) (14 * dp), (int) (28 * dp), (int) (14 * dp));
        GradientDrawable back = new GradientDrawable();
        back.setColor(0xCC0B0C10);
        back.setCornerRadius(28 * dp);
        box.setBackground(back);
        pillName = text(22, "sans-serif-medium", Color.WHITE);
        box.addView(pillName);
        pillHint = text(14, "sans-serif", 0xB3FFFFFF);
        pillHint.setText("▲ ▼  channel        ◀ ▶  network");
        pillHint.setPadding(0, (int) (6 * dp), 0, 0);
        box.addView(pillHint);
        box.setAlpha(0f);
        FrameLayout.LayoutParams boxAt = new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.WRAP_CONTENT, FrameLayout.LayoutParams.WRAP_CONTENT,
                Gravity.BOTTOM | Gravity.CENTER_HORIZONTAL);
        boxAt.bottomMargin = (int) (40 * dp);
        root.addView(box, boxAt);
        pill = box;

        setContentView(root);
        open(prefs.getInt("network", 0));
    }

    private String asset(String name) {
        try (InputStream in = getAssets().open(name)) {
            ByteArrayOutputStream out = new ByteArrayOutputStream();
            byte[] buffer = new byte[8192];
            for (int n; (n = in.read(buffer)) > 0; ) {
                out.write(buffer, 0, n);
            }
            return out.toString(StandardCharsets.UTF_8.name());
        } catch (IOException e) {
            throw new IllegalStateException(e);
        }
    }

    private TextView text(float sp, String family, int color) {
        TextView view = new TextView(this);
        view.setTextColor(color);
        view.setTextSize(sp);
        view.setTypeface(Typeface.create(family, Typeface.NORMAL));
        view.setGravity(Gravity.CENTER);
        return view;
    }

    private static boolean onAllowedHost(Uri uri) {
        String host = uri == null ? null : uri.getHost();
        if (host == null) {
            return false;
        }
        for (Network n : NETWORKS) {
            if (host.equals(n.host)) {
                return true;
            }
        }
        return false;
    }

    /** Opens a network on its last page, or its first one. */
    private void open(int index) {
        handler.removeCallbacksAndMessages(null);
        network = (index % NETWORKS.length + NETWORKS.length) % NETWORKS.length;
        prefs.edit().putInt("network", network).apply();
        Network n = NETWORKS[network];
        channel = "";
        revealed = false;
        loadedAt = System.currentTimeMillis();
        splashName.setText(n.name);
        splash.animate().cancel();
        splash.setAlpha(1f);
        splash.setVisibility(View.VISIBLE);
        if (n.home == null) {
            web.loadDataWithBaseURL(TWITCH_BASE, TWITCH_PAGE, "text/html", "utf-8", null);
        } else {
            String last = prefs.getString("page" + network, null);
            boolean usable = last != null && n.host.equals(Uri.parse(last).getHost());
            web.loadUrl(usable ? last : n.home);
        }
        showPill();
        if (!isFinishing()) {
            handler.post(tick);
        }
    }

    private void onTick(String value) {
        JSONObject state;
        try {
            Object text = new JSONTokener(value).nextValue();
            state = text instanceof String && !((String) text).isEmpty()
                    ? new JSONObject((String) text) : null;
        } catch (JSONException e) {
            state = null;
        }
        if (state == null) {
            revealLate();
            return;
        }
        if (state.optBoolean("ready") && (state.optBoolean("playing") || state.optBoolean("gate"))) {
            reveal();
        } else {
            revealLate();
        }
        String name = state.optString("name");
        if (!name.isEmpty() && !name.equals(channel)) {
            channel = name;
            showPill();
        }
        String url = state.optString("url");
        Network n = NETWORKS[network];
        if (n.home != null && n.host.equals(Uri.parse(url).getHost())
                && !url.equals(prefs.getString("page" + network, null))) {
            prefs.edit().putString("page" + network, url).apply();
        }
    }

    /** Shows the page even if it never reports playing, so a broken site is visible. */
    private void revealLate() {
        if (System.currentTimeMillis() - loadedAt > SPLASH_LIMIT) {
            reveal();
        }
    }

    private void reveal() {
        if (revealed) {
            return;
        }
        revealed = true;
        splash.animate().alpha(0f).setDuration(300)
                .withEndAction(() -> splash.setVisibility(View.GONE)).start();
    }

    private void showPill() {
        Network n = NETWORKS[network];
        pillName.setText(channel.isEmpty() ? n.name : n.name + "  ·  " + channel);
        pillHint.setVisibility(hinted ? View.GONE : View.VISIBLE);
        pill.animate().cancel();
        pill.setAlpha(1f);
        pill.animate().alpha(0f).setStartDelay(hinted ? 3000 : 6000).setDuration(600)
                .withEndAction(() -> hinted = true).start();
    }

    @Override
    public boolean dispatchKeyEvent(KeyEvent event) {
        int code = event.getKeyCode();
        switch (code) {
            case KeyEvent.KEYCODE_DPAD_CENTER:
            case KeyEvent.KEYCODE_ENTER:
            case KeyEvent.KEYCODE_DPAD_UP:
            case KeyEvent.KEYCODE_DPAD_DOWN:
            case KeyEvent.KEYCODE_CHANNEL_UP:
            case KeyEvent.KEYCODE_CHANNEL_DOWN:
            case KeyEvent.KEYCODE_DPAD_LEFT:
            case KeyEvent.KEYCODE_DPAD_RIGHT:
                break;
            default:
                return super.dispatchKeyEvent(event);
        }
        if (event.getAction() != KeyEvent.ACTION_DOWN || event.getRepeatCount() > 0) {
            return true;
        }
        switch (code) {
            case KeyEvent.KEYCODE_DPAD_CENTER:
            case KeyEvent.KEYCODE_ENTER:
                web.evaluateJavascript("window.soyOk && soyOk()", null);
                showPill();
                break;
            case KeyEvent.KEYCODE_DPAD_UP:
            case KeyEvent.KEYCODE_CHANNEL_UP:
                step(1);
                break;
            case KeyEvent.KEYCODE_DPAD_DOWN:
            case KeyEvent.KEYCODE_CHANNEL_DOWN:
                step(-1);
                break;
            case KeyEvent.KEYCODE_DPAD_RIGHT:
                open(network + 1);
                break;
            default:
                open(network - 1);
                break;
        }
        return true;
    }

    private void step(int direction) {
        web.evaluateJavascript("window.soyStep && soyStep(" + direction + ")", null);
        showPill();
    }

    @Override
    protected void onResume() {
        super.onResume();
        handler.removeCallbacks(tick);
        handler.post(tick);
    }

    @Override
    protected void onPause() {
        handler.removeCallbacks(tick);
        super.onPause();
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
