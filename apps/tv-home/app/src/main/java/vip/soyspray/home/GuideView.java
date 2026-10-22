package vip.soyspray.home;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.RectF;
import android.graphics.Typeface;
import android.text.TextPaint;
import android.text.TextUtils;
import android.text.format.DateFormat;
import android.view.KeyEvent;
import android.view.View;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;

/**
 * A full-screen programme guide drawn in one view: channels down the side,
 * three hours across, a red line at the current time and the focused
 * programme's details on top. The D-pad moves through programmes.
 */
final class GuideView extends View {
    interface OnPick {
        void picked(Live.Channel channel);
    }

    private static final long HALF_HOUR = 30 * 60_000L;
    private static final long SPAN = 6 * HALF_HOUR;

    private final float dp;
    private final OnPick onPick;
    private final Paint scrim = new Paint();
    private final Paint cell = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint nowLine = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final TextPaint heading = text(13, "sans-serif-medium", 0x99FFFFFF);
    private final TextPaint bigTitle = text(30, "sans-serif-light", Color.WHITE);
    private final TextPaint meta = text(16, "sans-serif", 0xB3FFFFFF);
    private final TextPaint hour = text(13, "sans-serif", 0x8CFFFFFF);
    private final TextPaint number = text(13, "sans-serif-medium", 0x80FFFFFF);
    private final TextPaint name = text(17, "sans-serif-medium", Color.WHITE);
    private final TextPaint programme = text(15, "sans-serif", 0xCCFFFFFF);
    private final RectF box = new RectF();
    private Live.Lineup lineup;
    private final List<Live.Channel> rows = new ArrayList<>();
    private int row;
    private int col;
    private long windowStart;

    GuideView(Context context, OnPick onPick) {
        super(context);
        this.onPick = onPick;
        dp = context.getResources().getDisplayMetrics().density;
        scrim.setColor(0xEB07080B);
        nowLine.setColor(0xFFFF2D55);
        nowLine.setStrokeWidth(2 * dp);
        setFocusable(true);
        setFocusableInTouchMode(true);
    }

    private TextPaint text(float sp, String family, int color) {
        TextPaint paint = new TextPaint(Paint.ANTI_ALIAS_FLAG);
        paint.setTextSize(sp * getResources().getDisplayMetrics().density);
        paint.setTypeface(Typeface.create(family, Typeface.NORMAL));
        paint.setColor(color);
        return paint;
    }

    void setLineup(Live.Lineup lineup) {
        this.lineup = lineup;
        rows.clear();
        rows.addAll(lineup.channels);
        focusNow();
    }

    /** Focuses the featured channel's current programme. */
    void focusNow() {
        if (lineup == null) {
            return;
        }
        long now = System.currentTimeMillis();
        windowStart = (now / HALF_HOUR) * HALF_HOUR - HALF_HOUR;
        row = Math.max(0, rows.indexOf(lineup.featured()));
        col = indexAt(row, now);
        invalidate();
    }

    private List<Live.Programme> programmes(int index) {
        return index < rows.size() ? lineup.programmes(rows.get(index)) : new ArrayList<>();
    }

    private int indexAt(int index, long time) {
        List<Live.Programme> list = programmes(index);
        for (int i = 0; i < list.size(); i++) {
            if (list.get(i).stop > time) {
                return i;
            }
        }
        return Math.max(0, list.size() - 1);
    }

    private Live.Programme focused() {
        List<Live.Programme> list = programmes(row);
        return col < list.size() ? list.get(col) : null;
    }

    private void reveal() {
        Live.Programme p = focused();
        if (p == null) {
            return;
        }
        if (p.start < windowStart) {
            windowStart = Math.max((p.start / HALF_HOUR) * HALF_HOUR,
                    (System.currentTimeMillis() / HALF_HOUR) * HALF_HOUR - 2 * HALF_HOUR);
        } else if (Math.min(p.stop, p.start + 2 * HALF_HOUR) > windowStart + SPAN) {
            windowStart = (p.start / HALF_HOUR) * HALF_HOUR - HALF_HOUR;
        }
    }

    @Override
    public boolean onKeyDown(int keyCode, KeyEvent event) {
        if (lineup == null || rows.isEmpty()) {
            return super.onKeyDown(keyCode, event);
        }
        Live.Programme current = focused();
        long anchor = current == null ? windowStart : Math.max(current.start, windowStart);
        switch (keyCode) {
            case KeyEvent.KEYCODE_DPAD_RIGHT:
                if (col + 1 < programmes(row).size()) {
                    col++;
                }
                break;
            case KeyEvent.KEYCODE_DPAD_LEFT:
                if (col > 0 && programmes(row).get(col - 1).stop
                        > System.currentTimeMillis() - 2 * HALF_HOUR) {
                    col--;
                }
                break;
            case KeyEvent.KEYCODE_DPAD_UP:
                if (row > 0) {
                    row--;
                    col = indexAt(row, anchor);
                }
                break;
            case KeyEvent.KEYCODE_DPAD_DOWN:
                if (row + 1 < rows.size()) {
                    row++;
                    col = indexAt(row, anchor);
                }
                break;
            case KeyEvent.KEYCODE_DPAD_CENTER:
            case KeyEvent.KEYCODE_ENTER:
                onPick.picked(rows.get(row));
                return true;
            default:
                return super.onKeyDown(keyCode, event);
        }
        reveal();
        invalidate();
        return true;
    }

    @Override
    protected void onDraw(Canvas canvas) {
        canvas.drawPaint(scrim);
        if (lineup == null) {
            return;
        }
        float w = getWidth();
        float left = 48 * dp;
        float labels = 176 * dp;
        float gridX = left + labels;
        float gridW = w - gridX - 48 * dp;
        float perMs = gridW / SPAN;
        long now = System.currentTimeMillis();

        canvas.drawText("TV GUIDE", left, 50 * dp, heading);
        Live.Programme p = focused();
        Live.Channel channel = rows.isEmpty() ? null : rows.get(row);
        if (p != null && channel != null) {
            canvas.drawText(TextUtils.ellipsize(p.title, bigTitle, w - 2 * left,
                    TextUtils.TruncateAt.END).toString(), left, 92 * dp, bigTitle);
            String when = clock(p.start) + " – " + clock(p.stop);
            String status = p.start <= now && now < p.stop ? "  ·  On now"
                    : p.stop <= now ? "  ·  Ended" : "";
            String action = channel.hls != null ? "OK to watch" : "OK opens Jellyfin";
            canvas.drawText(channel.name + "  ·  " + when + status + "    " + action,
                    left, 120 * dp, meta);
        }

        float timeline = 162 * dp;
        for (long t = windowStart; t < windowStart + SPAN; t += HALF_HOUR) {
            canvas.drawText(clock(t), gridX + (t - windowStart) * perMs + 6 * dp, timeline, hour);
        }

        float rowTop = 176 * dp;
        float rowH = 58 * dp;
        float gap = 8 * dp;
        for (int r = 0; r < rows.size(); r++) {
            float y = rowTop + r * (rowH + gap);
            if (y + rowH > getHeight()) {
                break;
            }
            Live.Channel c = rows.get(r);
            canvas.drawText(String.valueOf(c.number), left, y + rowH / 2 - 2 * dp, number);
            name.setAlpha(r == row ? 255 : 170);
            canvas.drawText(TextUtils.ellipsize(c.name, name, labels - 16 * dp,
                    TextUtils.TruncateAt.END).toString(), left, y + rowH / 2 + 18 * dp, name);
            List<Live.Programme> list = lineup.programmes(c);
            if (list.isEmpty()) {
                box.set(gridX, y, gridX + gridW, y + rowH);
                cell.setColor(0xFF15181E);
                canvas.drawRoundRect(box, 10 * dp, 10 * dp, cell);
                canvas.drawText("No guide", gridX + 14 * dp, y + rowH / 2 + 6 * dp, programme);
                continue;
            }
            for (int i = 0; i < list.size(); i++) {
                Live.Programme item = list.get(i);
                if (item.stop <= windowStart || item.start >= windowStart + SPAN) {
                    continue;
                }
                float x1 = gridX + Math.max(0, item.start - windowStart) * perMs;
                float x2 = gridX + Math.min(SPAN, item.stop - windowStart) * perMs;
                box.set(x1 + 2 * dp, y, x2 - 2 * dp, y + rowH);
                boolean selected = r == row && i == col;
                boolean onAir = item.start <= now && now < item.stop;
                cell.setColor(selected ? 0xFFE11D48 : onAir ? 0xFF2A303C : 0xFF171A21);
                canvas.drawRoundRect(box, 10 * dp, 10 * dp, cell);
                float room = box.width() - 24 * dp;
                if (room > 12 * dp) {
                    programme.setColor(selected || onAir ? Color.WHITE : 0xB3FFFFFF);
                    canvas.drawText(TextUtils.ellipsize(item.title, programme, room,
                            TextUtils.TruncateAt.END).toString(), box.left + 12 * dp,
                            y + rowH / 2 + 6 * dp, programme);
                }
            }
        }
        if (now >= windowStart && now < windowStart + SPAN) {
            float x = gridX + (now - windowStart) * perMs;
            canvas.drawLine(x, timeline + 6 * dp, x, getHeight() - 24 * dp, nowLine);
            canvas.drawCircle(x, timeline + 6 * dp, 4 * dp, nowLine);
        }
    }

    private String clock(long time) {
        return DateFormat.format("HH:mm", new Date(time)).toString();
    }
}
