"""Run pinned Speech-to-Phrase without decoding against a replaced vocabulary.

Only connection-triggered training is enabled. Serialize complete turns and
finish an idle cached decoder before a changed vocabulary replaces its files.
The upstream warm decoder is retained when the HA exposure/sentence hash agrees.
"""

import asyncio
import hashlib
import json
import os
import sys
from pathlib import Path

import speech_to_phrase.__main__ as server
import speech_to_phrase.event_handler as handler_module
from speech_to_phrase.hass_api import get_hass_info
from speech_to_phrase.train import TrainingInfo, _get_sentences_hash, train
from wyoming.asr import Transcribe
from wyoming.audio import AudioStop

EXPECTED_HANDLER = "0e36665d3634bac33dc16d361ab7d2821e65407a83887215c50963fef36bd6d3"


class SafePhraseHandler(handler_module.SpeechToPhraseEventHandler):
    turn_lock = None

    async def handle_event(self, event):
        if Transcribe.is_type(event.type):
            await self.turn_lock.acquire()
            self._owns_turn = True
        try:
            return await super().handle_event(event)
        except BaseException:
            self._release_turn()
            raise
        finally:
            if AudioStop.is_type(event.type):
                self._release_turn()

    def _release_turn(self):
        if getattr(self, "_owns_turn", False):
            self._owns_turn = False
            self.turn_lock.release()

    async def disconnect(self):
        try:
            if self.transcribe_task is not None:
                await self.audio_queue.put(None)
                try:
                    async with asyncio.timeout(3):
                        await self.transcribe_task
                except Exception:
                    self.transcribe_task.cancel()
        finally:
            self._release_turn()
            await super().disconnect()

    async def _retrain_model(self, model):
        info = await get_hass_info(
            token=self.settings.hass_token, uri=self.settings.hass_websocket_uri
        )
        expected = TrainingInfo(
            model.version, _get_sentences_hash(model, self.settings), info.things.get_hash()
        )
        path = self.settings.model_training_info_path(model.id)
        previous = TrainingInfo(**json.loads(path.read_text())) if path.exists() else None
        if previous != expected:
            async with self.state.cached_transcriber_lock:
                cached = self.state.cached_transcribers.pop(model.id, None)
            if cached:
                await cached.audio_queue.put(None)
                await cached.task
        await train(model, self.settings, info.things)


if __name__ == "__main__":
    if hashlib.sha256(Path(handler_module.__file__).read_bytes()).hexdigest() != EXPECTED_HANDLER:
        raise RuntimeError("Speech-to-Phrase handler changed; review the vocabulary guard")
    SafePhraseHandler.turn_lock = asyncio.Lock()
    server.SpeechToPhraseEventHandler = SafePhraseHandler
    token = Path("/run/secrets/home-assistant/token").read_text().strip()
    if not token:
        raise RuntimeError("Home Assistant token is empty")
    host, port = (
        os.environ["HOME_ASSISTANT_SERVICE_HOST"],
        os.environ["HOME_ASSISTANT_SERVICE_PORT"],
    )
    sys.argv = [
        "speech-to-phrase",
        "--uri",
        "tcp://0.0.0.0:10300",
        "--models-dir",
        "/data/models",
        "--train-dir",
        "/data/train",
        "--tools-dir",
        "/usr/src/tools",
        "--custom-sentences-dir",
        "/runtime/sentences",
        "--hass-websocket-uri",
        f"ws://{host}:{port}/api/websocket",
        "--hass-token",
        token,
        "--retrain-on-start",
        "--retrain-on-connect",
    ]
    asyncio.run(server.main())
