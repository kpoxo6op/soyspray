# ОТВ Прим horoscope

ОТВ Прим airs a short daily horoscope that is not in its programme guide. This
app finds it in the live stream and sends the whole episode as a Telegram video.

One pod copies the channel's public HLS stream into one-minute MPEG-TS files in
an `emptyDir` buffer that keeps the last 90 minutes. A baked `faster-whisper`
`small` model transcribes each finished minute in Russian. The detector treats
the twelve zodiac signs read in order (Овен to Рыбы, a few missed words allowed)
as one episode. It starts the clip at the spoken «Гороскоп» title, or the first
sign, minus a 45-second lead-in and ends it a minute after the last sign. The
clip is re-encoded to fit the 50 MB bot upload limit and sent to each chat in
the Secret. A repeat airing within 10 hours is not sent again.

The channel also publishes each day's text, without video, at
<https://otvprim.tv/programs/goroskop/>.

## Normal use

```sh
make check APP=otv-horoscope
kubectl -n otv-horoscope get deploy,pod
kubectl -n otv-horoscope logs deploy/otv-horoscope | grep -E 'heard|horoscope'
kubectl -n otv-horoscope exec deploy/otv-horoscope -- python3 -c \
  "import urllib.request;print(urllib.request.urlopen('http://127.0.0.1:8080/metrics').read().decode())"
```

The log prints every phrase with a sign name and each detected episode with its
Vladivostok airtime. `/healthz` fails when no live segment arrived for five
minutes; `/metrics` counts found, sent and failed episodes.

Tune detection with environment variables on the Deployment:
`LEAD_IN_SECONDS`, `TAIL_SECONDS`, `MIN_SIGNS`, `SIGN_GAP_SECONDS`,
`DEDUP_HOURS` and `BUFFER_MINUTES`.

## Telegram identity

`apps/otv-horoscope/bootstrap.yml` creates the `otv-horoscope-telegram` Secret
with `bot-token` and `chat-ids` (comma-separated numeric ids). Without a supplied
token it reuses the existing Alertmanager bot. Run it with the inventory and
privilege options in AGENTS.md, first with `--check`:

```sh
source soyspray-venv/bin/activate
ansible-playbook -i inventory/soycluster/hosts.yml --become --become-user=root --user ubuntu \
  apps/otv-horoscope/bootstrap.yml -e otv_horoscope_telegram_chat_ids=336642153 --check
```

To add a recipient, rerun it with the new full chat list. The person must first
press Start in the bot, or Telegram refuses the message. The bootstrap never
rotates an existing token; supply `otv_horoscope_telegram_bot_token` from an
off-cluster Ansible Vault file only when the Secret is missing.

## Build, deploy and limits

Source merges publish a tested GHCR image and open a draft digest promotion;
the running pod changes only when that promotion merges. The Argo Application
in `argocd/` is registered in the [root](../../argocd/kustomization.yaml). Roll back by reverting the promotion through
GitHub; do not delete the namespace or Secret.

The app keeps no durable data. A pod restart loses the buffer and the record of
sent episodes, so an episode airing during a restart can be missed or sent twice.
Detection depends on the horoscope being read aloud; a silent or captions-only
version is not recognised. The stream URL is the channel's public CDN address
and may change; `apps/media-helper/app/channels.json` holds the same source.
