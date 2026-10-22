package vip.soyspray.home;

import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.ColorFilter;
import android.graphics.Paint;
import android.graphics.PixelFormat;
import android.graphics.Rect;
import android.graphics.drawable.Drawable;

/** One of the home screen's glyphs as a drawable, for the app drawer. */
final class GlyphDrawable extends Drawable {
    private final Tiles.Glyph glyph;
    private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);

    GlyphDrawable(Tiles.Glyph glyph) {
        this.glyph = glyph;
        paint.setColor(Color.WHITE);
    }

    @Override
    public void draw(Canvas canvas) {
        Rect bounds = getBounds();
        float size = Math.min(bounds.width(), bounds.height());
        canvas.save();
        canvas.translate(bounds.left + (bounds.width() - size) / 2, bounds.top + (bounds.height() - size) / 2);
        glyph.draw(canvas, paint, size);
        canvas.restore();
    }

    @Override
    public void setAlpha(int alpha) {
        paint.setAlpha(alpha);
    }

    @Override
    public void setColorFilter(ColorFilter filter) {
        paint.setColorFilter(filter);
    }

    @Override
    public int getOpacity() {
        return PixelFormat.TRANSLUCENT;
    }
}
