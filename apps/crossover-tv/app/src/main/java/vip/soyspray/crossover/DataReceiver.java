package vip.soyspray.crossover;

import android.app.Activity;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.util.Base64;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import org.json.JSONException;
import org.json.JSONObject;

/**
 * Keeps the view the laptop sends over ADB:
 *
 * <pre>
 * adb shell am broadcast -f 32 -n vip.soyspray.crossover/.DataReceiver \
 *     -a vip.soyspray.crossover.VIEW --es view BASE64_JSON
 * </pre>
 *
 * The manifest requires the sender to hold android.permission.DUMP, which only
 * the shell user and the system have. The flag 32 (include stopped packages)
 * reaches the app before it has first been opened. {@code CLEAR} removes the
 * stored view. The result data says what happened, for the sender to check.
 */
public class DataReceiver extends BroadcastReceiver {
    static final String VIEW = "vip.soyspray.crossover.VIEW";
    static final String CLEAR = "vip.soyspray.crossover.CLEAR";

    // A view is a few kilobytes; this is far above any real one.
    private static final int LIMIT = 256 * 1024;

    @Override
    public void onReceive(Context context, Intent intent) {
        String action = intent.getAction();
        if (CLEAR.equals(action)) {
            ViewStore.clear(context);
            answer(Activity.RESULT_OK, "cleared");
            MainActivity.reloadIfShown();
            return;
        }
        if (!VIEW.equals(action)) {
            answer(Activity.RESULT_CANCELED, "unknown action");
            return;
        }
        String encoded = intent.getStringExtra("view");
        if (encoded == null || encoded.length() > LIMIT * 4 / 3 + 4) {
            answer(Activity.RESULT_CANCELED, "no view");
            return;
        }
        try {
            byte[] json = Base64.decode(encoded, Base64.DEFAULT);
            JSONObject view = new JSONObject(new String(json, StandardCharsets.UTF_8));
            if (!"crossover-tv".equals(view.optString("kind")) || view.optInt("schema") != 1) {
                answer(Activity.RESULT_CANCELED, "not a Crossover TV view");
                return;
            }
            ViewStore.write(context, json);
            answer(Activity.RESULT_OK, "stored " + json.length + " bytes");
            MainActivity.reloadIfShown();
        } catch (IllegalArgumentException | JSONException | IOException e) {
            answer(Activity.RESULT_CANCELED, "rejected: " + e.getClass().getSimpleName());
        }
    }

    private void answer(int code, String data) {
        if (isOrderedBroadcast()) {
            setResultCode(code);
            setResultData(data);
        }
    }
}
