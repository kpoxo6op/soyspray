package vip.soyspray.home;

import android.app.Activity;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.pm.PackageManager;
import android.graphics.Typeface;
import android.os.Bundle;
import android.provider.Settings;
import android.text.format.DateFormat;
import android.view.Gravity;
import android.view.KeyEvent;
import android.view.View;
import android.view.ViewGroup;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.TextView;
import java.util.Date;

/**
 * The living-room home screen: a clock, three large tiles and two small
 * buttons over a glow that follows focus. Everything is drawn with plain
 * views, so it starts instantly and animates on the GPU.
 */
public class HomeActivity extends Activity {
    private AuraView aura;
    private TextView clock;
    private TextView date;
    private View firstTile;
    private View lastFocused;

    private final BroadcastReceiver ticks = new BroadcastReceiver() {
        @Override
        public void onReceive(Context context, Intent intent) {
            showTime();
        }
    };

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        float dp = getResources().getDisplayMetrics().density;
        FrameLayout root = new FrameLayout(this);
        root.setClipChildren(false);
        aura = new AuraView(this);
        root.addView(aura, match());

        clock = text(78, "sans-serif-thin", 0xFFFFFFFF);
        clock.setLetterSpacing(-0.02f);
        date = text(17, "sans-serif-light", 0xA6FFFFFF);
        LinearLayout time = new LinearLayout(this);
        time.setOrientation(LinearLayout.VERTICAL);
        time.addView(clock);
        time.addView(date);
        root.addView(time, at(Gravity.TOP | Gravity.START, 56 * dp, 36 * dp));

        LinearLayout corner = new LinearLayout(this);
        corner.setClipChildren(false);
        corner.addView(round(Tiles::grid, "Apps",
                v -> startActivity(new Intent(this, AppsActivity.class))), square(52 * dp, 0));
        corner.addView(round(Tiles::gear, "Settings", v -> openSettings()), square(52 * dp, 18 * dp));
        root.addView(corner, at(Gravity.TOP | Gravity.END, 56 * dp, 52 * dp));

        LinearLayout row = new LinearLayout(this);
        row.setClipChildren(false);
        row.setClipToPadding(false);
        for (int i = 0; i < Tiles.ROW.length; i++) {
            Tiles.Tile tile = Tiles.ROW[i];
            TileView card = TileView.card(this, tile);
            card.setOnFocus(this::follow);
            card.setOnClickListener(v -> launch(tile.pkg, card));
            LinearLayout.LayoutParams size = new LinearLayout.LayoutParams(
                    (int) (240 * dp), (int) (135 * dp));
            size.leftMargin = i == 0 ? 0 : (int) (32 * dp);
            row.addView(card, size);
            if (i == 0) {
                firstTile = card;
            }
        }
        FrameLayout.LayoutParams rowAt = new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT,
                Gravity.BOTTOM | Gravity.CENTER_HORIZONTAL);
        rowAt.bottomMargin = (int) (104 * dp);
        root.addView(row, rowAt);
        setContentView(root);
    }

    @Override
    protected void onResume() {
        super.onResume();
        showTime();
        IntentFilter filter = new IntentFilter(Intent.ACTION_TIME_TICK);
        filter.addAction(Intent.ACTION_TIME_CHANGED);
        filter.addAction(Intent.ACTION_TIMEZONE_CHANGED);
        registerReceiver(ticks, filter);
        View target = lastFocused != null ? lastFocused : firstTile;
        target.post(target::requestFocus);
    }

    @Override
    protected void onPause() {
        unregisterReceiver(ticks);
        super.onPause();
    }

    @Override
    public boolean onKeyDown(int keyCode, KeyEvent event) {
        switch (keyCode) {
            case KeyEvent.KEYCODE_BACK:
                return true;
            case KeyEvent.KEYCODE_SETTINGS:
                openSettings();
                return true;
            case KeyEvent.KEYCODE_MENU:
                startActivity(new Intent(this, AppsActivity.class));
                return true;
            default:
                return super.onKeyDown(keyCode, event);
        }
    }

    private void follow(TileView view) {
        lastFocused = view;
        int[] at = new int[2];
        view.getLocationInWindow(at);
        aura.glowAt(at[0] + view.getWidth() / 2f, at[1] + view.getHeight() / 2f, view.glow);
    }

    private void launch(String pkg, TileView card) {
        PackageManager pm = getPackageManager();
        Intent intent = pm.getLeanbackLaunchIntentForPackage(pkg);
        if (intent == null) {
            intent = pm.getLaunchIntentForPackage(pkg);
        }
        if (intent == null) {
            card.shake();
            return;
        }
        startActivity(intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
    }

    private void openSettings() {
        startActivity(new Intent(Settings.ACTION_SETTINGS).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
    }

    private void showTime() {
        Date now = new Date();
        clock.setText(DateFormat.getTimeFormat(this).format(now));
        date.setText(DateFormat.format("EEEE d MMMM", now));
    }

    private TileView round(Tiles.Glyph glyph, String label, View.OnClickListener click) {
        TileView button = TileView.round(this, glyph, label);
        button.setOnFocus(this::follow);
        button.setOnClickListener(click);
        return button;
    }

    private TextView text(float sp, String family, int color) {
        TextView view = new TextView(this);
        view.setTextSize(sp);
        view.setTextColor(color);
        view.setTypeface(Typeface.create(family, Typeface.NORMAL));
        view.setIncludeFontPadding(false);
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
}
