package vip.soyspray.home;

import android.content.Context;
import android.os.Handler;
import android.os.Looper;
import android.util.Xml;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.text.ParseException;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;
import org.xmlpull.v1.XmlPullParser;
import org.xmlpull.v1.XmlPullParserException;

/**
 * The live TV lineup and guide from Media Helper, the same catalog Jellyfin
 * uses. Cached copies show at once; fresh ones follow from the network.
 */
final class Live {
    static final String BASE = "https://guide.soyspray.vip";
    static final String FEATURED = "otv-prim";

    static final class Channel {
        final String slug;
        final int number;
        final String name;
        final String guideId;
        /** A direct HLS address the home screen can play, or null. */
        final String hls;

        Channel(String slug, int number, String name, String guideId, String hls) {
            this.slug = slug;
            this.number = number;
            this.name = name;
            this.guideId = guideId;
            this.hls = hls;
        }
    }

    static final class Programme {
        final long start;
        final long stop;
        final String title;

        Programme(long start, long stop, String title) {
            this.start = start;
            this.stop = stop;
            this.title = title;
        }
    }

    static final class Lineup {
        final List<Channel> channels;
        final Map<String, List<Programme>> guide;

        Lineup(List<Channel> channels, Map<String, List<Programme>> guide) {
            this.channels = channels;
            this.guide = guide;
        }

        Channel featured() {
            for (Channel channel : channels) {
                if (channel.slug.equals(FEATURED)) {
                    return channel;
                }
            }
            return channels.isEmpty() ? null : channels.get(0);
        }

        List<Programme> programmes(Channel channel) {
            List<Programme> list = channel == null ? null : guide.get(channel.guideId);
            return list == null ? Collections.emptyList() : list;
        }

        /** The programme on air at TIME, or null. */
        Programme at(Channel channel, long time) {
            for (Programme programme : programmes(channel)) {
                if (programme.start <= time && time < programme.stop) {
                    return programme;
                }
            }
            return null;
        }

        /** The first programme starting after TIME, or null. */
        Programme after(Channel channel, long time) {
            for (Programme programme : programmes(channel)) {
                if (programme.start > time) {
                    return programme;
                }
            }
            return null;
        }
    }

    interface Listener {
        void onLineup(Lineup lineup);
    }

    private Live() {}

    /** Reports the cached lineup, if any, then a fresh one, on the main thread. */
    static void load(Context context, Listener listener) {
        File channelsFile = new File(context.getCacheDir(), "channels.json");
        File guideFile = new File(context.getCacheDir(), "xmltv.xml");
        Handler main = new Handler(Looper.getMainLooper());
        new Thread(() -> {
            try {
                if (channelsFile.exists() && guideFile.exists()) {
                    Lineup cached = parse(Files.readAllBytes(channelsFile.toPath()),
                            Files.readAllBytes(guideFile.toPath()));
                    main.post(() -> listener.onLineup(cached));
                }
            } catch (IOException | JSONException | XmlPullParserException | RuntimeException e) {
                channelsFile.delete();
            }
            try {
                byte[] channels = fetch(BASE + "/api/v1/channels");
                byte[] guide = fetch(BASE + "/xmltv.xml");
                Lineup fresh = parse(channels, guide);
                write(channelsFile, channels);
                write(guideFile, guide);
                main.post(() -> listener.onLineup(fresh));
            } catch (IOException | JSONException | XmlPullParserException | RuntimeException e) {
                // Keep showing the cached lineup; the next refresh tries again.
            }
        }, "lineup").start();
    }

    private static byte[] fetch(String address) throws IOException {
        HttpURLConnection connection = (HttpURLConnection) new URL(address).openConnection();
        connection.setConnectTimeout(8000);
        connection.setReadTimeout(20000);
        try (InputStream in = connection.getInputStream()) {
            if (connection.getResponseCode() != 200) {
                throw new IOException("HTTP " + connection.getResponseCode());
            }
            ByteArrayOutputStream out = new ByteArrayOutputStream();
            byte[] buffer = new byte[16384];
            for (int read; (read = in.read(buffer)) > 0; ) {
                out.write(buffer, 0, read);
            }
            return out.toByteArray();
        } finally {
            connection.disconnect();
        }
    }

    private static void write(File file, byte[] data) throws IOException {
        File temporary = new File(file.getPath() + ".tmp");
        try (FileOutputStream out = new FileOutputStream(temporary)) {
            out.write(data);
        }
        if (!temporary.renameTo(file)) {
            throw new IOException("could not replace " + file);
        }
    }

    static Lineup parse(byte[] channelsJson, byte[] xmltv)
            throws JSONException, IOException, XmlPullParserException {
        JSONArray array = new JSONObject(new String(channelsJson, StandardCharsets.UTF_8))
                .getJSONArray("channels");
        List<Channel> channels = new ArrayList<>();
        for (int i = 0; i < array.length(); i++) {
            JSONObject item = array.getJSONObject(i);
            JSONArray groups = item.optJSONArray("groups");
            boolean liveTv = groups != null && groups.toString().contains("\"Live TV\"");
            if (!item.optBoolean("enabled") || !liveTv) {
                continue;
            }
            String hls = null;
            JSONArray sources = item.optJSONArray("sources");
            for (int s = 0; sources != null && s < sources.length(); s++) {
                JSONObject source = sources.getJSONObject(s);
                if ("direct_hls".equals(source.optString("type"))) {
                    hls = source.optString("url");
                    break;
                }
            }
            JSONObject guide = item.optJSONObject("guide");
            channels.add(new Channel(item.getString("slug"), item.optInt("number"),
                    item.getString("name"), guide == null ? "" : guide.optString("id"), hls));
        }
        channels.sort((a, b) -> Integer.compare(a.number, b.number));
        return new Lineup(channels, programmes(xmltv));
    }

    private static Map<String, List<Programme>> programmes(byte[] xmltv)
            throws IOException, XmlPullParserException {
        SimpleDateFormat format = new SimpleDateFormat("yyyyMMddHHmmss Z", Locale.US);
        long now = System.currentTimeMillis();
        long from = now - 3 * 3600_000L;
        long until = now + 36 * 3600_000L;
        Map<String, List<Programme>> guide = new HashMap<>();
        XmlPullParser parser = Xml.newPullParser();
        parser.setInput(new ByteArrayInputStream(xmltv), "UTF-8");
        String channel = null;
        long start = 0;
        long stop = 0;
        for (int event = parser.getEventType(); event != XmlPullParser.END_DOCUMENT;
                event = parser.next()) {
            if (event != XmlPullParser.START_TAG) {
                continue;
            }
            if ("programme".equals(parser.getName())) {
                channel = parser.getAttributeValue(null, "channel");
                try {
                    start = format.parse(parser.getAttributeValue(null, "start")).getTime();
                    stop = format.parse(parser.getAttributeValue(null, "stop")).getTime();
                } catch (ParseException | NullPointerException e) {
                    channel = null;
                }
            } else if ("title".equals(parser.getName()) && channel != null) {
                String title = parser.nextText();
                if (stop > from && start < until) {
                    guide.computeIfAbsent(channel, key -> new ArrayList<>())
                            .add(new Programme(start, stop, title.trim()));
                }
                channel = null;
            }
        }
        for (List<Programme> list : guide.values()) {
            list.sort((a, b) -> Long.compare(a.start, b.start));
        }
        return guide;
    }
}
