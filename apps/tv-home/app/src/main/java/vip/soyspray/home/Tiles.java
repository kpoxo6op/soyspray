package vip.soyspray.home;

import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.RectF;

/** The home row and the glyphs drawn on it. Changing the row is a code change. */
final class Tiles {
    /** Draws a white mark inside a SIZE by SIZE square at the canvas origin. */
    interface Glyph {
        void draw(Canvas canvas, Paint paint, float size);
    }

    static final class Tile {
        final String title;
        final String subtitle;
        final String pkg;
        final int from;
        final int to;
        final int glow;
        final Glyph glyph;

        Tile(String title, String subtitle, String pkg, int from, int to, int glow, Glyph glyph) {
            this.title = title;
            this.subtitle = subtitle;
            this.pkg = pkg;
            this.from = from;
            this.to = to;
            this.glow = glow;
            this.glyph = glyph;
        }
    }

    static final Tile[] ROW = {
        new Tile("Jellyfin", "Cartoons and live TV", "org.jellyfin.androidtv",
                0xFF4B2FB8, 0xFF0A86C2, 0xFF6A4CFF, Tiles::jellyfin),
        new Tile("YouTube", "SmartTube, no ads", "app.smarttube.fdroid",
                0xFFE0112B, 0xFF6E0614, 0xFFFF2340, Tiles::play),
        new Tile("Infinite Slop", "Live AI TV", "vip.soyspray.infiniteslop",
                0xFFFF3D6E, 0xFFFF9A3D, 0xFFFF6A45, Tiles::infinity),
    };

    static final int QUIET_GLOW = 0xFF5A6478;

    private Tiles() {}

    static void play(Canvas canvas, Paint paint, float s) {
        Path path = new Path();
        path.moveTo(0.30f * s, 0.18f * s);
        path.lineTo(0.84f * s, 0.50f * s);
        path.lineTo(0.30f * s, 0.82f * s);
        path.close();
        paint.setStyle(Paint.Style.FILL);
        canvas.drawPath(path, paint);
    }

    static void jellyfin(Canvas canvas, Paint paint, float s) {
        Path outer = new Path();
        outer.moveTo(0.50f * s, 0.12f * s);
        outer.lineTo(0.90f * s, 0.84f * s);
        outer.lineTo(0.10f * s, 0.84f * s);
        outer.close();
        paint.setStyle(Paint.Style.STROKE);
        paint.setStrokeWidth(0.10f * s);
        paint.setStrokeJoin(Paint.Join.ROUND);
        canvas.drawPath(outer, paint);
        Path inner = new Path();
        inner.moveTo(0.50f * s, 0.48f * s);
        inner.lineTo(0.64f * s, 0.72f * s);
        inner.lineTo(0.36f * s, 0.72f * s);
        inner.close();
        paint.setStyle(Paint.Style.FILL);
        canvas.drawPath(inner, paint);
    }

    static void infinity(Canvas canvas, Paint paint, float s) {
        float cx = 0.5f * s;
        float cy = 0.5f * s;
        Path path = new Path();
        path.moveTo(cx, cy);
        path.cubicTo(cx + 0.16f * s, cy - 0.22f * s, cx + 0.44f * s, cy - 0.22f * s, cx + 0.44f * s, cy);
        path.cubicTo(cx + 0.44f * s, cy + 0.22f * s, cx + 0.16f * s, cy + 0.22f * s, cx, cy);
        path.cubicTo(cx - 0.16f * s, cy - 0.22f * s, cx - 0.44f * s, cy - 0.22f * s, cx - 0.44f * s, cy);
        path.cubicTo(cx - 0.44f * s, cy + 0.22f * s, cx - 0.16f * s, cy + 0.22f * s, cx, cy);
        paint.setStyle(Paint.Style.STROKE);
        paint.setStrokeWidth(0.10f * s);
        paint.setStrokeCap(Paint.Cap.ROUND);
        canvas.drawPath(path, paint);
    }

    static void grid(Canvas canvas, Paint paint, float s) {
        paint.setStyle(Paint.Style.FILL);
        float cell = 0.30f * s;
        float gap = 0.10f * s;
        float start = (s - 2 * cell - gap) / 2;
        RectF box = new RectF();
        for (int row = 0; row < 2; row++) {
            for (int col = 0; col < 2; col++) {
                float x = start + col * (cell + gap);
                float y = start + row * (cell + gap);
                box.set(x, y, x + cell, y + cell);
                canvas.drawRoundRect(box, 0.08f * s, 0.08f * s, paint);
            }
        }
    }

    static void gear(Canvas canvas, Paint paint, float s) {
        float c = 0.5f * s;
        paint.setStyle(Paint.Style.FILL);
        RectF tooth = new RectF(c - 0.07f * s, 0.10f * s, c + 0.07f * s, 0.30f * s);
        for (int i = 0; i < 8; i++) {
            canvas.save();
            canvas.rotate(45 * i, c, c);
            canvas.drawRoundRect(tooth, 0.03f * s, 0.03f * s, paint);
            canvas.restore();
        }
        paint.setStyle(Paint.Style.STROKE);
        paint.setStrokeWidth(0.12f * s);
        canvas.drawCircle(c, c, 0.22f * s, paint);
    }
}
