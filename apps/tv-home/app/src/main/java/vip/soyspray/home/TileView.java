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
 * A focusable card: a wide tile with a glyph, title and subtitle, a square
 * tile with a centred glyph and title, or a small round button. Focus lifts it
 * with scale, shadow and an outline; only view properties animate, so the GPU
 * does the work.
 */
final class TileView extends View {
    enum Shape { WIDE, SQUARE, ROUND }

    static final float REST_ALPHA = 0.80f;

    private final Tiles.Glyph glyph;
    private final String title;
    private String subtitle;
    private final int from;
    private final int to;
    private final Shape shape;
    private final float dp;
    private final float radius;
    private final Paint fill = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint gloss = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint ring = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint mark = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint titlePaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint subtitlePaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final RectF box = new RectF();
    private boolean lifted;

    static TileView card(Context context, Tiles.Tile tile) {
        return new TileView(context, tile.glyph, tile.title, tile.from, tile.to,
                tile.wide ? Shape.WIDE : Shape.SQUARE);
    }

    static TileView round(Context context, Tiles.Glyph glyph, String label) {
        return new TileView(context, glyph, label, 0xCC262A33, 0xCC181B22, Shape.ROUND);
    }

    private TileView(Context context, Tiles.Glyph glyph, String title, int from, int to,
            Shape shape) {
        super(context);
        this.glyph = glyph;
        this.title = title;
        this.from = from;
        this.to = to;
        this.shape = shape;
        dp = context.getResources().getDisplayMetrics().density;
        radius = shape == Shape.ROUND ? 0 : 18 * dp;
        setFocusable(true);
        setClickable(true);
        setContentDescription(title);
        setAlpha(REST_ALPHA);
        ring.setStyle(Paint.Style.STROKE);
        ring.setStrokeWidth(2.5f * dp);
        ring.setColor(0xF2FFFFFF);
        mark.setColor(Color.WHITE);
        titlePaint.setColor(Color.WHITE);
        titlePaint.setTextSize((shape == Shape.WIDE ? 21 : 15) * dp);
        titlePaint.setTypeface(Typeface.create("sans-serif-medium", Typeface.NORMAL));
        titlePaint.setTextAlign(shape == Shape.SQUARE ? Paint.Align.CENTER : Paint.Align.LEFT);
        subtitlePaint.setColor(0xD9FFFFFF);
        subtitlePaint.setTextSize(13 * dp);
        subtitlePaint.setTypeface(Typeface.create("sans-serif", Typeface.NORMAL));
        setOutlineProvider(new ViewOutlineProvider() {
            @Override
            public void getOutline(View view, Outline outline) {
                if (shape == Shape.ROUND) {
                    outline.setOval(0, 0, view.getWidth(), view.getHeight());
                } else {
                    outline.setRoundRect(new Rect(0, 0, view.getWidth(), view.getHeight()), radius);
                }
            }
        });
    }

    void setSubtitle(String text) {
        subtitle = text;
        invalidate();
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
        if (shape == Shape.ROUND) {
            canvas.drawCircle(w / 2, h / 2, w / 2, fill);
            canvas.drawCircle(w / 2, h / 2, w / 2, gloss);
            glyphAt(canvas, (w - w * 0.46f) / 2, (h - w * 0.46f) / 2, w * 0.46f);
            if (lifted) {
                canvas.drawCircle(w / 2, h / 2, w / 2 - ring.getStrokeWidth() / 2, ring);
            }
            return;
        }
        canvas.drawRoundRect(box, radius, radius, fill);
        canvas.drawRoundRect(box, radius, radius, gloss);
        if (shape == Shape.WIDE) {
            float pad = 18 * dp;
            glyphAt(canvas, pad, pad, 30 * dp);
            canvas.drawText(title, pad, h - pad - (subtitle != null ? 19 * dp : 0), titlePaint);
            if (subtitle != null) {
                canvas.drawText(subtitle, pad, h - pad, subtitlePaint);
            }
        } else {
            float size = w * 0.40f;
            glyphAt(canvas, (w - size) / 2, h * 0.17f, size);
            canvas.drawText(title, w / 2, h - 14 * dp, titlePaint);
        }
        if (lifted) {
            float inset = ring.getStrokeWidth() / 2;
            canvas.drawRoundRect(inset, inset, w - inset, h - inset, radius, radius, ring);
        }
    }

    private void glyphAt(Canvas canvas, float x, float y, float size) {
        canvas.save();
        canvas.translate(x, y);
        glyph.draw(canvas, mark, size);
        canvas.restore();
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
    }

    /** A quick side-to-side shake when a tile's app is missing. */
    void shake() {
        animate().translationX(10 * dp).setDuration(60).withEndAction(() ->
                animate().translationX(-8 * dp).setDuration(80).withEndAction(() ->
                        animate().translationX(0).setDuration(60).start()).start()).start();
    }
}
