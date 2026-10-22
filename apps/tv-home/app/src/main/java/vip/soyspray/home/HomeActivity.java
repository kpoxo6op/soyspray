package vip.soyspray.home;

import android.app.Activity;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.pm.PackageManager;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.LinearGradient;
import android.graphics.Paint;
import android.graphics.RectF;
import android.graphics.Shader;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.provider.Settings;
import android.text.TextUtils;
import android.text.format.DateFormat;
import android.view.Gravity;
import android.view.KeyEvent;
import android.view.SurfaceView;
import android.view.View;
import android.view.ViewGroup;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.TextView;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;

/**
 * The living-room home screen. ОТВ Прим plays live behind everything, with
 * what is on now and next; below sit Watch live, the guide and the apps.
 * Watch live goes full screen with sound; the guide opens over the video.
 */
public class HomeActivity extends Activity {
    private enum Mode { HOME, FULL, GUIDE }

    private static final long REFRESH = 20 * 60_000L;

    private final Handler handler = new Handler(Looper.getMainLooper());
    private LivePlayer player;
    private Live.Lineup lineup;
    private Live.Channel channel;
    private Mode mode = Mode.HOME;
    private View chrome;
    private TextView channelName;
    private TextView nowTitle;
    private TextView nowTime;
    private Bar nowBar;
    private TextView next;
    private TextView clock;
    private TextView banner;
    private GuideView guide;
    private TileView watch;
    private View guideTile;
    private View lastFocused;

    private final BroadcastReceiver ticks = new BroadcastReceiver() {
        @Override
        public void onReceive(Context context, Intent intent) {
            showNow();
        }
    };

    private final Runnable refresh = new Runnable() {
        @Override
        public void run() {
            Live.load(HomeActivity.this, HomeActivity.this::onLineup);
            handler.postDelayed(this, REFRESH);
        }
    };

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        float dp = getResources().getDisplayMetrics().density;
        FrameLayout root = new FrameLayout(this);
        root.setBackgroundColor(0xFF05060A);
        root.setClipChildren(false);

        SurfaceView video = new SurfaceView(this);
        root.addView(video, match());
        player = new LivePlayer(this, video, () -> { });

        FrameLayout overlay = new FrameLayout(this);
        overlay.setClipChildren(false);
        overlay.addView(new Scrim(this), match());

        LinearLayout info = new LinearLayout(this);
        info.setOrientation(LinearLayout.VERTICAL);
        LinearLayout header = new LinearLayout(this);
        header.setGravity(Gravity.CENTER_VERTICAL);
        TextView live = text(12, "sans-serif-medium", Color.WHITE);
        live.setText("●  LIVE");
        live.setLetterSpacing(0.12f);
        live.setPadding((int) (10 * dp), (int) (4 * dp), (int) (10 * dp), (int) (4 * dp));
        GradientDrawable red = new GradientDrawable();
        red.setColor(0xFFE11D48);
        red.setCornerRadius(6 * dp);
        live.setBackground(red);
        header.addView(live);
        channelName = text(18, "sans-serif-medium", Color.WHITE);
        channelName.setPadding((int) (12 * dp), 0, 0, 0);
        header.addView(channelName);
        info.addView(header);
        nowTitle = text(40, "sans-serif-light", Color.WHITE);
        nowTitle.setSingleLine(true);
        nowTitle.setEllipsize(TextUtils.TruncateAt.END);
        nowTitle.setMaxWidth((int) (600 * dp));
        nowTitle.setPadding(0, (int) (14 * dp), 0, (int) (8 * dp));
        info.addView(nowTitle);
        LinearLayout timing = new LinearLayout(this);
        timing.setGravity(Gravity.CENTER_VERTICAL);
        nowTime = text(16, "sans-serif", 0xCCFFFFFF);
        timing.addView(nowTime);
        nowBar = new Bar(this);
        LinearLayout.LayoutParams barAt = new LinearLayout.LayoutParams((int) (180 * dp),
                (int) (4 * dp));
        barAt.leftMargin = (int) (14 * dp);
        timing.addView(nowBar, barAt);
        info.addView(timing);
        next = text(16, "sans-serif", 0x99FFFFFF);
        next.setSingleLine(true);
        next.setEllipsize(TextUtils.TruncateAt.END);
        next.setMaxWidth((int) (600 * dp));
        next.setPadding(0, (int) (10 * dp), 0, 0);
        info.addView(next);
        overlay.addView(info, at(Gravity.TOP | Gravity.START, 48 * dp, 44 * dp));

        LinearLayout corner = new LinearLayout(this);
        corner.setGravity(Gravity.CENTER_VERTICAL);
        corner.setClipChildren(false);
        clock = text(30, "sans-serif-thin", Color.WHITE);
        corner.addView(clock);
        corner.addView(round(Tiles::grid, "Apps",
                v -> startActivity(new Intent(this, AppsActivity.class))), square(44 * dp, 20 * dp));
        corner.addView(round(Tiles::gear, "Settings", v -> openSettings()), square(44 * dp, 12 * dp));
        overlay.addView(corner, at(Gravity.TOP | Gravity.END, 48 * dp, 40 * dp));

        LinearLayout row = new LinearLayout(this);
        row.setClipChildren(false);
        row.setClipToPadding(false);
        row.setGravity(Gravity.BOTTOM);
        for (int i = 0; i < Tiles.ROW.length; i++) {
            Tiles.Tile tile = Tiles.ROW[i];
            TileView card = TileView.card(this, tile);
            card.setOnFocusChangeListener((v, focused) -> {
                if (focused) {
                    lastFocused = v;
                }
            });
            card.setOnClickListener(v -> open(tile, card));
            int width = (int) ((tile.wide ? 210 : 108) * dp);
            LinearLayout.LayoutParams size = new LinearLayout.LayoutParams(width, (int) (108 * dp));
            size.leftMargin = i == 0 ? 0 : (int) (16 * dp);
            row.addView(card, size);
            if (Tiles.WATCH.equals(tile.action)) {
                watch = card;
            } else if (Tiles.GUIDE.equals(tile.action)) {
                guideTile = card;
            }
        }
        FrameLayout.LayoutParams rowAt = new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT,
                Gravity.BOTTOM | Gravity.START);
        rowAt.leftMargin = (int) (48 * dp);
        rowAt.bottomMargin = (int) (44 * dp);
        overlay.addView(row, rowAt);
        root.addView(overlay, match());
        chrome = overlay;

        banner = text(20, "sans-serif-medium", Color.WHITE);
        banner.setPadding((int) (20 * dp), (int) (12 * dp), (int) (20 * dp), (int) (12 * dp));
        GradientDrawable dark = new GradientDrawable();
        dark.setColor(0xB3000000);
        dark.setCornerRadius(16 * dp);
        banner.setBackground(dark);
        banner.setAlpha(0f);
        root.addView(banner, at(Gravity.TOP | Gravity.START, 40 * dp, 32 * dp));

        guide = new GuideView(this, this::picked);
        guide.setVisibility(View.GONE);
        root.addView(guide, match());
        setContentView(root);
    }

    @Override
    protected void onResume() {
        super.onResume();
        showNow();
        IntentFilter filter = new IntentFilter(Intent.ACTION_TIME_TICK);
        filter.addAction(Intent.ACTION_TIME_CHANGED);
        filter.addAction(Intent.ACTION_TIMEZONE_CHANGED);
        registerReceiver(ticks, filter);
        handler.post(refresh);
        player.resume();
        if (mode == Mode.HOME) {
            View target = lastFocused != null ? lastFocused : watch;
            target.post(target::requestFocus);
        }
    }

    @Override
    protected void onPause() {
        unregisterReceiver(ticks);
        handler.removeCallbacks(refresh);
        player.release();
        super.onPause();
    }

    private void onLineup(Live.Lineup fresh) {
        lineup = fresh;
        guide.setLineup(fresh);
        if (channel == null) {
            channel = fresh.featured();
        } else {
            for (Live.Channel c : fresh.channels) {
                if (c.slug.equals(channel.slug)) {
                    channel = c;
                }
            }
        }
        if (channel != null) {
            player.play(channel.hls);
        }
        showNow();
    }

    private void showNow() {
        clock.setText(DateFormat.format("HH:mm", new Date()));
        if (lineup == null || channel == null) {
            channelName.setText("ОТВ Прим");
            return;
        }
        long now = System.currentTimeMillis();
        channelName.setText(channel.name);
        watch.setSubtitle(channel.name);
        Live.Programme on = lineup.at(channel, now);
        Live.Programme after = lineup.after(channel, now);
        nowTitle.setText(on != null ? on.title : channel.name);
        nowTime.setText(on != null ? clock(on.start) + " – " + clock(on.stop) : "");
        nowBar.setFraction(on == null ? -1f : (now - on.start) / (float) (on.stop - on.start));
        next.setText(after != null ? "Next   " + clock(after.start) + "   " + after.title : "");
    }

    private String clock(long time) {
        return DateFormat.format("HH:mm", new Date(time)).toString();
    }

    private void open(Tiles.Tile tile, TileView card) {
        if (Tiles.WATCH.equals(tile.action)) {
            full();
        } else if (Tiles.GUIDE.equals(tile.action)) {
            openGuide();
        } else {
            launch(tile.pkg, card);
        }
    }

    private void full() {
        if (channel == null || channel.hls == null) {
            return;
        }
        mode = Mode.FULL;
        chrome.animate().alpha(0f).setDuration(220).withEndAction(() ->
                chrome.setVisibility(View.INVISIBLE)).start();
        player.setMuted(false);
        flash();
    }

    private void home() {
        mode = Mode.HOME;
        player.setMuted(true);
        guide.animate().cancel();
        guide.setVisibility(View.GONE);
        chrome.setVisibility(View.VISIBLE);
        chrome.animate().alpha(1f).setDuration(220).start();
        View target = lastFocused != null ? lastFocused : watch;
        target.requestFocus();
        showNow();
    }

    private void openGuide() {
        if (lineup == null) {
            return;
        }
        mode = Mode.GUIDE;
        guide.focusNow();
        guide.setAlpha(0f);
        guide.setVisibility(View.VISIBLE);
        guide.animate().alpha(1f).setDuration(200).start();
        guide.requestFocus();
    }

    private void picked(Live.Channel picked) {
        if (picked.hls == null) {
            launch("org.jellyfin.androidtv", null);
            return;
        }
        channel = picked;
        player.play(picked.hls);
        guide.setVisibility(View.GONE);
        full();
        showNow();
    }

    /** Steps through the channels the home screen can play itself. */
    private void tune(int step) {
        if (lineup == null || channel == null) {
            return;
        }
        List<Live.Channel> playable = new ArrayList<>();
        for (Live.Channel c : lineup.channels) {
            if (c.hls != null) {
                playable.add(c);
            }
        }
        int index = playable.indexOf(channel);
        if (playable.isEmpty()) {
            return;
        }
        channel = playable.get((Math.max(index, 0) + step + playable.size()) % playable.size());
        player.play(channel.hls);
        showNow();
        flash();
    }

    /** Names the channel and programme for a few seconds in full screen. */
    private void flash() {
        if (channel == null) {
            return;
        }
        Live.Programme on = lineup == null ? null : lineup.at(channel, System.currentTimeMillis());
        banner.setText(channel.number + "   " + channel.name + (on != null ? "   ·   " + on.title : ""));
        banner.animate().cancel();
        banner.setAlpha(1f);
        banner.animate().alpha(0f).setStartDelay(3500).setDuration(500).start();
    }

    @Override
    public boolean onKeyDown(int keyCode, KeyEvent event) {
        if (keyCode == KeyEvent.KEYCODE_SETTINGS) {
            openSettings();
            return true;
        }
        if (keyCode == KeyEvent.KEYCODE_GUIDE) {
            openGuide();
            return true;
        }
        switch (mode) {
            case FULL:
                switch (keyCode) {
                    case KeyEvent.KEYCODE_BACK:
                        home();
                        return true;
                    case KeyEvent.KEYCODE_DPAD_UP:
                    case KeyEvent.KEYCODE_CHANNEL_UP:
                        tune(1);
                        return true;
                    case KeyEvent.KEYCODE_DPAD_DOWN:
                    case KeyEvent.KEYCODE_CHANNEL_DOWN:
                        tune(-1);
                        return true;
                    case KeyEvent.KEYCODE_DPAD_CENTER:
                    case KeyEvent.KEYCODE_ENTER:
                    case KeyEvent.KEYCODE_DPAD_LEFT:
                    case KeyEvent.KEYCODE_DPAD_RIGHT:
                        flash();
                        return true;
                    default:
                        return super.onKeyDown(keyCode, event);
                }
            case GUIDE:
                if (keyCode == KeyEvent.KEYCODE_BACK) {
                    home();
                    if (guideTile != null) {
                        guideTile.requestFocus();
                    }
                    return true;
                }
                return super.onKeyDown(keyCode, event);
            default:
                if (keyCode == KeyEvent.KEYCODE_BACK) {
                    return true;
                }
                if (keyCode == KeyEvent.KEYCODE_MENU) {
                    startActivity(new Intent(this, AppsActivity.class));
                    return true;
                }
                if (keyCode == KeyEvent.KEYCODE_CHANNEL_UP || keyCode == KeyEvent.KEYCODE_CHANNEL_DOWN) {
                    full();
                    return true;
                }
                return super.onKeyDown(keyCode, event);
        }
    }

    private void launch(String pkg, TileView card) {
        PackageManager pm = getPackageManager();
        Intent intent = pm.getLeanbackLaunchIntentForPackage(pkg);
        if (intent == null) {
            intent = pm.getLaunchIntentForPackage(pkg);
        }
        if (intent == null) {
            if (card != null) {
                card.shake();
            }
            return;
        }
        startActivity(intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
    }

    private void openSettings() {
        startActivity(new Intent(Settings.ACTION_SETTINGS).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
    }

    private TileView round(Tiles.Glyph glyph, String label, View.OnClickListener click) {
        TileView button = TileView.round(this, glyph, label);
        button.setOnClickListener(click);
        return button;
    }

    private TextView text(float sp, String family, int color) {
        TextView view = new TextView(this);
        view.setTextSize(sp);
        view.setTextColor(color);
        view.setTypeface(Typeface.create(family, Typeface.NORMAL));
        view.setIncludeFontPadding(false);
        view.setShadowLayer(12, 0, 2, 0x99000000);
        return view;
    }

    private static FrameLayout.LayoutParams match() {
        return new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT);
    }

    private static FrameLayout.LayoutParams at(int gravity, float side, float top) {
        FrameLayout.LayoutParams params = new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT, gravity);
        params.leftMargin = (int) side;
        params.rightMargin = (int) side;
        params.topMargin = (int) top;
        return params;
    }

    private static LinearLayout.LayoutParams square(float size, float gap) {
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams((int) size, (int) size);
        params.leftMargin = (int) gap;
        return params;
    }

    /** Darkens the video where text sits: the left side, the top and the bottom. */
    private static final class Scrim extends View {
        private final Paint left = new Paint();
        private final Paint bottom = new Paint();
        private final Paint top = new Paint();

        Scrim(Context context) {
            super(context);
        }

        @Override
        protected void onSizeChanged(int w, int h, int oldw, int oldh) {
            left.setShader(new LinearGradient(0, 0, w * 0.68f, 0, 0xD9000000, 0x00000000,
                    Shader.TileMode.CLAMP));
            bottom.setShader(new LinearGradient(0, h, 0, h * 0.45f, 0xF2000000, 0x00000000,
                    Shader.TileMode.CLAMP));
            top.setShader(new LinearGradient(0, 0, 0, h * 0.25f, 0x99000000, 0x00000000,
                    Shader.TileMode.CLAMP));
        }

        @Override
        protected void onDraw(Canvas canvas) {
            canvas.drawPaint(left);
            canvas.drawPaint(bottom);
            canvas.drawPaint(top);
        }
    }

    /** A thin progress line for the programme on now. */
    private static final class Bar extends View {
        private final Paint track = new Paint(Paint.ANTI_ALIAS_FLAG);
        private final Paint fill = new Paint(Paint.ANTI_ALIAS_FLAG);
        private final RectF box = new RectF();
        private float fraction = -1f;

        Bar(Context context) {
            super(context);
            track.setColor(0x4DFFFFFF);
            fill.setColor(0xFFFF2D55);
        }

        void setFraction(float value) {
            fraction = value;
            setVisibility(value < 0 ? View.GONE : View.VISIBLE);
            invalidate();
        }

        @Override
        protected void onDraw(Canvas canvas) {
            float h = getHeight();
            box.set(0, 0, getWidth(), h);
            canvas.drawRoundRect(box, h / 2, h / 2, track);
            box.right = getWidth() * Math.max(0f, Math.min(1f, fraction));
            canvas.drawRoundRect(box, h / 2, h / 2, fill);
        }
    }
}
