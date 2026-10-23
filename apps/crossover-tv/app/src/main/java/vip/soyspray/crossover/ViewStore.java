package vip.soyspray.crossover;

import android.content.Context;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;

/** The last view from the laptop, in the app's private files. */
final class ViewStore {
    private static final String NAME = "view.json";

    private ViewStore() {}

    static String read(Context context) {
        File file = new File(context.getFilesDir(), NAME);
        if (!file.isFile()) {
            return null;
        }
        try (InputStream in = new FileInputStream(file)) {
            ByteArrayOutputStream out = new ByteArrayOutputStream();
            byte[] buffer = new byte[8192];
            for (int n; (n = in.read(buffer)) > 0; ) {
                out.write(buffer, 0, n);
            }
            return out.toString(StandardCharsets.UTF_8.name());
        } catch (IOException e) {
            return null;
        }
    }

    /** Replaces the view in one step, so the page never reads half a file. */
    static void write(Context context, byte[] json) throws IOException {
        File dir = context.getFilesDir();
        File next = new File(dir, NAME + ".next");
        try (FileOutputStream out = new FileOutputStream(next)) {
            out.write(json);
            out.getFD().sync();
        }
        if (!next.renameTo(new File(dir, NAME))) {
            throw new IOException("could not replace the view");
        }
    }

    static void clear(Context context) {
        new File(context.getFilesDir(), NAME).delete();
    }
}
