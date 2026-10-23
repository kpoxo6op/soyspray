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

    static final String WATCH = "watch";
    static final String GUIDE = "guide";

    static final class Tile {
        final String title;
        /** The app to open, or null for WATCH and GUIDE. */
        final String pkg;
        final String action;
        final int from;
        final int to;
        final Glyph glyph;
        final boolean wide;

        Tile(String title, String pkg, String action, int from, int to, Glyph glyph,
                boolean wide) {
            this.title = title;
            this.pkg = pkg;
            this.action = action;
            this.from = from;
            this.to = to;
            this.glyph = glyph;
            this.wide = wide;
        }
    }

    static final Tile[] ROW = {
        new Tile("Watch live", null, WATCH, 0xFFE11D48, 0xFF7A1029, Tiles::live, true),
        new Tile("Guide", null, GUIDE, 0xFF3B4558, 0xFF161B26, Tiles::guide, false),
        new Tile("Jellyfin", "org.jellyfin.androidtv", null, 0xFF4B2FB8, 0xFF0A86C2,
                Tiles::jellyfin, false),
        new Tile("YouTube", "app.smarttube.fdroid", null, 0xFFE0112B, 0xFF6E0614,
                Tiles::youtube, false),
        new Tile("Twitch", "com.fgl27.twitch", null, 0xFF9146FF, 0xFF3F1A87,
                Tiles::twitch, false),
        new Tile("AI TV", "vip.soyspray.aitv", null, 0xFFFF3D6E, 0xFFFF9A3D,
                Tiles::infinity, false),
        new Tile("Crossover", "vip.soyspray.crossover", null, 0xFFB04AA6, 0xFF3A1B3C,
                Tiles::crossing, false),
    };

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

    /** A dot with two broadcast arcs on each side. */
    static void live(Canvas canvas, Paint paint, float s) {
        float c = 0.5f * s;
        paint.setStyle(Paint.Style.FILL);
        canvas.drawCircle(c, c, 0.09f * s, paint);
        paint.setStyle(Paint.Style.STROKE);
        paint.setStrokeWidth(0.07f * s);
        paint.setStrokeCap(Paint.Cap.ROUND);
        for (float r : new float[] {0.22f, 0.36f}) {
            RectF arc = new RectF(c - r * s, c - r * s, c + r * s, c + r * s);
            canvas.drawArc(arc, -40, 80, false, paint);
            canvas.drawArc(arc, 140, 80, false, paint);
        }
    }

    /** Three programme bars of different lengths. */
    static void guide(Canvas canvas, Paint paint, float s) {
        paint.setStyle(Paint.Style.FILL);
        float[] lengths = {0.70f, 0.48f, 0.60f};
        RectF bar = new RectF();
        for (int i = 0; i < 3; i++) {
            float y = (0.22f + 0.22f * i) * s;
            bar.set(0.15f * s, y, (0.15f + lengths[i]) * s, y + 0.12f * s);
            canvas.drawRoundRect(bar, 0.06f * s, 0.06f * s, paint);
        }
    }

    static void youtube(Canvas canvas, Paint paint, float s) {
        paint.setStyle(Paint.Style.FILL);
        RectF body = new RectF(0.08f * s, 0.22f * s, 0.92f * s, 0.78f * s);
        canvas.drawRoundRect(body, 0.16f * s, 0.16f * s, paint);
        Path play = new Path();
        play.moveTo(0.42f * s, 0.36f * s);
        play.lineTo(0.64f * s, 0.50f * s);
        play.lineTo(0.42f * s, 0.64f * s);
        play.close();
        int color = paint.getColor();
        paint.setColor(0xFFB3001B);
        canvas.drawPath(play, paint);
        paint.setColor(color);
    }

    /** A speech bubble with two bars, like Twitch's mark. */
    static void twitch(Canvas canvas, Paint paint, float s) {
        Path bubble = new Path();
        bubble.moveTo(0.20f * s, 0.12f * s);
        bubble.lineTo(0.84f * s, 0.12f * s);
        bubble.lineTo(0.84f * s, 0.58f * s);
        bubble.lineTo(0.66f * s, 0.76f * s);
        bubble.lineTo(0.48f * s, 0.76f * s);
        bubble.lineTo(0.34f * s, 0.90f * s);
        bubble.lineTo(0.34f * s, 0.76f * s);
        bubble.lineTo(0.20f * s, 0.76f * s);
        bubble.close();
        paint.setStyle(Paint.Style.STROKE);
        paint.setStrokeWidth(0.08f * s);
        paint.setStrokeJoin(Paint.Join.ROUND);
        canvas.drawPath(bubble, paint);
        paint.setStyle(Paint.Style.FILL);
        RectF bar = new RectF();
        for (float x : new float[] {0.44f, 0.62f}) {
            bar.set(x * s, 0.30f * s, (x + 0.08f) * s, 0.52f * s);
            canvas.drawRect(bar, paint);
        }
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

    /** A thin line and a thick one crossing at a diamond, as on the Crossover chart. */
    static void crossing(Canvas canvas, Paint paint, float s) {
        paint.setStyle(Paint.Style.STROKE);
        paint.setStrokeCap(Paint.Cap.ROUND);
        paint.setStrokeWidth(0.05f * s);
        canvas.drawLine(0.10f * s, 0.36f * s, 0.90f * s, 0.60f * s, paint);
        paint.setStrokeWidth(0.10f * s);
        canvas.drawLine(0.10f * s, 0.86f * s, 0.90f * s, 0.14f * s, paint);
        float cx = 0.517f * s;
        float cy = 0.485f * s;
        float r = 0.13f * s;
        Path diamond = new Path();
        diamond.moveTo(cx, cy - r);
        diamond.lineTo(cx + r, cy);
        diamond.lineTo(cx, cy + r);
        diamond.lineTo(cx - r, cy);
        diamond.close();
        paint.setStyle(Paint.Style.FILL);
        canvas.drawPath(diamond, paint);
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
