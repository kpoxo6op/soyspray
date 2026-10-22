package vip.soyspray.home;

import android.content.Context;
import android.os.Handler;
import android.os.Looper;
import android.view.SurfaceView;
import androidx.media3.common.MediaItem;
import androidx.media3.common.PlaybackException;
import androidx.media3.common.Player;
import androidx.media3.exoplayer.ExoPlayer;

/**
 * One live HLS channel on a SurfaceView. Errors retry with a growing delay, and
 * falling behind the live window jumps back to the live edge.
 */
final class LivePlayer {
    interface Listener {
        void onFirstFrame();
    }

    private final Context context;
    private final SurfaceView surface;
    private final Listener listener;
    private final Handler handler = new Handler(Looper.getMainLooper());
    private ExoPlayer player;
    private String url;
    private boolean muted = true;
    private int failures;

    LivePlayer(Context context, SurfaceView surface, Listener listener) {
        this.context = context;
        this.surface = surface;
        this.listener = listener;
    }

    void play(String address) {
        if (address == null) {
            return;
        }
        if (address.equals(url) && player != null) {
            return;
        }
        url = address;
        failures = 0;
        start();
    }

    private void start() {
        handler.removeCallbacksAndMessages(null);
        if (player == null) {
            player = new ExoPlayer.Builder(context).build();
            player.setVideoSurfaceView(surface);
            player.addListener(new Player.Listener() {
                @Override
                public void onRenderedFirstFrame() {
                    failures = 0;
                    listener.onFirstFrame();
                }

                @Override
                public void onPlayerError(PlaybackException error) {
                    if (error.errorCode == PlaybackException.ERROR_CODE_BEHIND_LIVE_WINDOW) {
                        player.seekToDefaultPosition();
                        player.prepare();
                        return;
                    }
                    long delay = Math.min(30_000L, 2000L << Math.min(failures++, 4));
                    handler.postDelayed(LivePlayer.this::start, delay);
                }
            });
        }
        player.setVolume(muted ? 0f : 1f);
        player.setMediaItem(MediaItem.fromUri(url));
        player.prepare();
        player.setPlayWhenReady(true);
    }

    void setMuted(boolean muted) {
        this.muted = muted;
        if (player != null) {
            player.setVolume(muted ? 0f : 1f);
        }
    }

    /** Stops and frees the decoder, for when another app takes the screen. */
    void release() {
        handler.removeCallbacksAndMessages(null);
        if (player != null) {
            player.release();
            player = null;
        }
    }

    /** Starts again after release(), on the last channel. */
    void resume() {
        if (url != null && player == null) {
            start();
        }
    }
}
