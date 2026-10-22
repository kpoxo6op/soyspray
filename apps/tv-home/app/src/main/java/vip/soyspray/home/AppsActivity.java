package vip.soyspray.home;

import android.app.Activity;
import android.content.Intent;
import android.content.pm.ActivityInfo;
import android.content.pm.PackageManager;
import android.content.pm.ResolveInfo;
import android.graphics.Color;
import android.graphics.Outline;
import android.graphics.Typeface;
import android.graphics.drawable.Drawable;
import android.graphics.drawable.GradientDrawable;
import android.os.Bundle;
import android.provider.Settings;
import android.view.Gravity;
import android.view.View;
import android.view.ViewOutlineProvider;
import android.view.animation.DecelerateInterpolator;
import android.widget.FrameLayout;
import android.widget.GridLayout;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import java.util.ArrayList;
import java.util.List;

/** Every launchable app as a grid of cards, for anything not on the home row. */
public class AppsActivity extends Activity {
    private static final int COLUMNS = 5;
    private float dp;

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        dp = getResources().getDisplayMetrics().density;
        LinearLayout page = new LinearLayout(this);
        page.setOrientation(LinearLayout.VERTICAL);
        page.setBackgroundColor(0xFF07080B);
        page.setPadding((int) (56 * dp), (int) (40 * dp), (int) (56 * dp), (int) (24 * dp));
        page.setClipChildren(false);
        TextView heading = new TextView(this);
        heading.setText("Apps");
        heading.setTextSize(34);
        heading.setTextColor(Color.WHITE);
        heading.setTypeface(Typeface.create("sans-serif-light", Typeface.NORMAL));
        page.addView(heading);

        GridLayout grid = new GridLayout(this);
        grid.setColumnCount(COLUMNS);
        grid.setClipChildren(false);
        grid.setPadding(0, (int) (24 * dp), 0, (int) (24 * dp));
        grid.addView(card(null, null, "Settings",
                v -> startActivity(new Intent(Settings.ACTION_SETTINGS))));
        PackageManager pm = getPackageManager();
        for (ResolveInfo app : apps(pm)) {
            ActivityInfo info = app.activityInfo;
            Drawable banner = info.loadBanner(pm);
            if (banner == null) {
                banner = info.applicationInfo.loadBanner(pm);
            }
            Intent launch = new Intent(Intent.ACTION_MAIN)
                    .addCategory(Intent.CATEGORY_LEANBACK_LAUNCHER)
                    .setClassName(info.packageName, info.name)
                    .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            View.OnClickListener open = v -> startActivity(launch);
            grid.addView(banner != null
                    ? card(banner, null, null, open)
                    : card(null, info.loadIcon(pm), String.valueOf(info.loadLabel(pm)), open));
        }
        ScrollView scroll = new ScrollView(this);
        scroll.setClipChildren(false);
        scroll.addView(grid);
        page.addView(scroll);
        setContentView(page);
        grid.getChildAt(0).requestFocus();
    }

    private List<ResolveInfo> apps(PackageManager pm) {
        Intent query = new Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_LEANBACK_LAUNCHER);
        List<ResolveInfo> found = new ArrayList<>();
        for (ResolveInfo info : pm.queryIntentActivities(query, 0)) {
            if (!info.activityInfo.packageName.equals(getPackageName())) {
                found.add(info);
            }
        }
        found.sort((a, b) -> String.valueOf(a.loadLabel(pm))
                .compareToIgnoreCase(String.valueOf(b.loadLabel(pm))));
        return found;
    }

    /** A 16:9 card showing a banner, or an icon and label. */
    private View card(Drawable banner, Drawable icon, String label, View.OnClickListener click) {
        FrameLayout card = new FrameLayout(this);
        GridLayout.LayoutParams size = new GridLayout.LayoutParams();
        size.width = (int) (152 * dp);
        size.height = (int) (86 * dp);
        size.setMargins((int) (8 * dp), (int) (8 * dp), (int) (8 * dp), (int) (8 * dp));
        card.setLayoutParams(size);
        GradientDrawable back = new GradientDrawable();
        back.setColor(0xFF1C1F27);
        back.setCornerRadius(14 * dp);
        card.setBackground(back);
        card.setOutlineProvider(new ViewOutlineProvider() {
            @Override
            public void getOutline(View view, Outline outline) {
                outline.setRoundRect(0, 0, view.getWidth(), view.getHeight(), 14 * dp);
            }
        });
        card.setClipToOutline(true);
        card.setFocusable(true);
        card.setClickable(true);
        card.setAlpha(TileView.REST_ALPHA);
        card.setOnClickListener(click);
        card.setOnFocusChangeListener((view, focused) -> view.animate()
                .scaleX(focused ? 1.1f : 1f).scaleY(focused ? 1.1f : 1f)
                .alpha(focused ? 1f : TileView.REST_ALPHA)
                .translationZ(focused ? 16 * dp : 0)
                .setDuration(150).setInterpolator(new DecelerateInterpolator(1.6f))
                .withLayer().start());
        if (banner != null) {
            ImageView art = new ImageView(this);
            art.setScaleType(ImageView.ScaleType.CENTER_CROP);
            art.setImageDrawable(banner);
            card.addView(art, new FrameLayout.LayoutParams(FrameLayout.LayoutParams.MATCH_PARENT,
                    FrameLayout.LayoutParams.MATCH_PARENT));
        }
        if (icon != null) {
            ImageView art = new ImageView(this);
            art.setScaleType(ImageView.ScaleType.FIT_CENTER);
            art.setImageDrawable(icon);
            FrameLayout.LayoutParams artAt = new FrameLayout.LayoutParams(
                    (int) (40 * dp), (int) (40 * dp), Gravity.CENTER_HORIZONTAL | Gravity.TOP);
            artAt.topMargin = (int) (12 * dp);
            card.addView(art, artAt);
        }
        if (label != null) {
            TextView name = new TextView(this);
            name.setText(label);
            name.setTextColor(Color.WHITE);
            name.setTextSize(13);
            name.setSingleLine(true);
            name.setGravity(Gravity.CENTER);
            FrameLayout.LayoutParams nameAt = new FrameLayout.LayoutParams(
                    FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.WRAP_CONTENT,
                    Gravity.BOTTOM);
            nameAt.bottomMargin = (int) (10 * dp);
            card.addView(name, nameAt);
        }
        return card;
    }
}
