package vip.soyspray.home;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.LinearGradient;
import android.graphics.Outline;
import android.graphics.Paint;
import android.graphics.Rect;
import android.graphics.RectF;
import android.graphics.Shader;
import android.graphics.Typeface;
import android.view.View;
import android.view.ViewOutlineProvider;
import android.view.animation.DecelerateInterpolator;

/**
 * A focusable card: a gradient tile with a glyph, title and subtitle, or a small
 * round button with only a glyph. Focus lifts it with a scale, shadow and
 * outline; only view properties animate, so the GPU does the work.
 */
final class TileView extends View {
    interface OnFocus {
        void focused(TileView view);
    }

    static final float REST_ALPHA = 0.74f;

    final int glow;
    private final Tiles.Glyph glyph;
    private final String title;
    private final String subtitle;
    private final int from;
    private final int to;
    private final boolean round;
    private final float dp;
    private final float radius;
    private final Paint fill = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint gloss = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint ring = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint mark = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint titlePaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint subtitlePaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final RectF box = new RectF();
    private OnFocus listener;
    private boolean lifted;

    static TileView card(Context context, Tiles.Tile tile) {
        return new TileView(context, tile.glyph, tile.title, tile.subtitle, tile.from, tile.to,
                tile.glow, false);
    }

    static TileView round(Context context, Tiles.Glyph glyph, String label) {
        return new TileView(context, glyph, label, null, 0xFF262A33, 0xFF181B22,
                Tiles.QUIET_GLOW, true);
    }

    private TileView(Context context, Tiles.Glyph glyph, String title, String subtitle,
            int from, int to, int glow, boolean round) {
        super(context);
        this.glyph = glyph;
        this.title = title;
        this.subtitle = subtitle;
        this.from = from;
        this.to = to;
        this.glow = glow;
        this.round = round;
        dp = context.getResources().getDisplayMetrics().density;
        radius = round ? 0 : 20 * dp;
        setFocusable(true);
        setClickable(true);
        setContentDescription(title);
        setAlpha(REST_ALPHA);
        ring.setStyle(Paint.Style.STROKE);
        ring.setStrokeWidth(2.5f * dp);
        ring.setColor(0xE6FFFFFF);
        mark.setColor(Color.WHITE);
        titlePaint.setColor(Color.WHITE);
        titlePaint.setTextSize(23 * dp);
        titlePaint.setTypeface(Typeface.create("sans-serif-medium", Typeface.NORMAL));
        subtitlePaint.setColor(0xC8FFFFFF);
        subtitlePaint.setTextSize(13 * dp);
        subtitlePaint.setTypeface(Typeface.create("sans-serif", Typeface.NORMAL));
        setOutlineProvider(new ViewOutlineProvider() {
            @Override
            public void getOutline(View view, Outline outline) {
                if (round) {
                    outline.setOval(0, 0, view.getWidth(), view.getHeight());
                } else {
                    outline.setRoundRect(new Rect(0, 0, view.getWidth(), view.getHeight()), radius);
                }
            }
        });
    }

    void setOnFocus(OnFocus listener) {
        this.listener = listener;
    }

    @Override
    protected void onSizeChanged(int w, int h, int oldw, int oldh) {
        box.set(0, 0, w, h);
        fill.setShader(new LinearGradient(0, 0, w, h, from, to, Shader.TileMode.CLAMP));
        gloss.setShader(new LinearGradient(0, 0, 0, h * 0.55f, 0x2EFFFFFF, 0x00FFFFFF,
                Shader.TileMode.CLAMP));
    }

    @Override
    protected void onDraw(Canvas canvas) {
        float w = getWidth();
        float h = getHeight();
        if (round) {
            canvas.drawCircle(w / 2, h / 2, w / 2, fill);
            canvas.drawCircle(w / 2, h / 2, w / 2, gloss);
            float size = w * 0.46f;
            canvas.save();
            canvas.translate((w - size) / 2, (h - size) / 2);
            glyph.draw(canvas, mark, size);
            canvas.restore();
            if (lifted) {
                canvas.drawCircle(w / 2, h / 2, w / 2 - ring.getStrokeWidth() / 2, ring);
            }
            return;
        }
        canvas.drawRoundRect(box, radius, radius, fill);
        canvas.drawRoundRect(box, radius, radius, gloss);
        float pad = 20 * dp;
        float size = 34 * dp;
        canvas.save();
        canvas.translate(pad, pad);
        glyph.draw(canvas, mark, size);
        canvas.restore();
        canvas.drawText(title, pad, h - pad - 20 * dp, titlePaint);
        if (subtitle != null) {
            canvas.drawText(subtitle, pad, h - pad, subtitlePaint);
        }
        if (lifted) {
            float inset = ring.getStrokeWidth() / 2;
            canvas.drawRoundRect(inset, inset, w - inset, h - inset, radius, radius, ring);
        }
    }

    @Override
    protected void onFocusChanged(boolean gained, int direction, Rect previous) {
        super.onFocusChanged(gained, direction, previous);
        lifted = gained;
        invalidate();
        animate()
                .scaleX(gained ? 1.12f : 1f)
                .scaleY(gained ? 1.12f : 1f)
                .alpha(gained ? 1f : REST_ALPHA)
                .translationZ(gained ? 24 * dp : 0)
                .setDuration(170)
                .setInterpolator(new DecelerateInterpolator(1.6f))
                .withLayer()
                .start();
        if (gained && listener != null) {
            listener.focused(this);
        }
    }

    /** A quick side-to-side shake when a tile's app is missing. */
    void shake() {
        animate().translationX(10 * dp).setDuration(60).withEndAction(() ->
                animate().translationX(-8 * dp).setDuration(80).withEndAction(() ->
                        animate().translationX(0).setDuration(60).start()).start()).start();
    }
}
