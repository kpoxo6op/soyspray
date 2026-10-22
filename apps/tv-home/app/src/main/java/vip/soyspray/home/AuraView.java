package vip.soyspray.home;

import android.animation.ValueAnimator;
import android.content.Context;
import android.graphics.Canvas;
import android.graphics.LinearGradient;
import android.graphics.Paint;
import android.graphics.RadialGradient;
import android.graphics.Shader;
import android.view.View;
import android.view.animation.DecelerateInterpolator;

/**
 * The background: a dark gradient with a soft coloured glow that slides to the
 * focused tile and fades into its colour. Glow shaders are built once per
 * colour, so animation frames allocate nothing.
 */
final class AuraView extends View {
    private final Paint base = new Paint();
    private final Paint glowPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final java.util.Map<Integer, Shader> glows = new java.util.HashMap<>();
    private final ValueAnimator move = ValueAnimator.ofFloat(0f, 1f);
    private float radius;
    private float fromX;
    private float fromY;
    private float toX;
    private float toY;
    private int fromColor;
    private int toColor;
    private float progress = 1f;

    AuraView(Context context) {
        super(context);
        move.setDuration(420);
        move.setInterpolator(new DecelerateInterpolator(1.8f));
        move.addUpdateListener(animation -> {
            progress = (float) animation.getAnimatedValue();
            invalidate();
        });
    }

    @Override
    protected void onSizeChanged(int w, int h, int oldw, int oldh) {
        base.setShader(new LinearGradient(0, 0, 0, h, 0xFF0D0F14, 0xFF040506, Shader.TileMode.CLAMP));
        radius = w * 0.42f;
        glows.clear();
    }

    /** Slides the glow to (x, y) and crossfades it to COLOR. */
    void glowAt(float x, float y, int color) {
        float t = progress;
        fromX = fromX + (toX - fromX) * t;
        fromY = fromY + (toY - fromY) * t;
        if (toColor == 0) {
            fromX = x;
            fromY = y;
        }
        fromColor = t < 0.5f ? fromColor : toColor;
        toX = x;
        toY = y;
        toColor = color;
        move.cancel();
        progress = 0f;
        move.start();
    }

    private Shader glow(int color) {
        Shader shader = glows.get(color);
        if (shader == null) {
            int core = (color & 0x00FFFFFF) | 0x8C000000;
            int mid = (color & 0x00FFFFFF) | 0x26000000;
            shader = new RadialGradient(0, 0, radius, new int[] {core, mid, 0x00000000},
                    new float[] {0f, 0.45f, 1f}, Shader.TileMode.CLAMP);
            glows.put(color, shader);
        }
        return shader;
    }

    @Override
    protected void onDraw(Canvas canvas) {
        canvas.drawPaint(base);
        if (toColor == 0) {
            return;
        }
        float x = fromX + (toX - fromX) * progress;
        float y = fromY + (toY - fromY) * progress;
        if (fromColor != 0 && progress < 1f) {
            drawGlow(canvas, fromColor, x, y, 1f - progress);
        }
        drawGlow(canvas, toColor, x, y, progress);
    }

    private void drawGlow(Canvas canvas, int color, float x, float y, float strength) {
        glowPaint.setShader(glow(color));
        glowPaint.setAlpha((int) (255 * strength));
        canvas.save();
        canvas.translate(x, y);
        canvas.drawCircle(0, 0, radius, glowPaint);
        canvas.restore();
    }
}
