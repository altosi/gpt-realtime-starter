import asyncio
import base64
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import numpy as np
from openai.resources.realtime.realtime import AsyncRealtimeConnection
from openai.types.realtime import (
    ResponseAudioDeltaEvent,
    RealtimeSessionCreateRequestParam,
)
from sounddevice import OutputStream

from connect import basic_session
from connect_and_record import (
    FORMAT,
    CHANNELS,
    SAMPLE_RATE,
    connect_and_start_recording,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

play_queue: asyncio.Queue[np.ndarray] = asyncio.Queue()

output_stream = OutputStream(
    channels=CHANNELS,
    samplerate=SAMPLE_RATE,
    dtype=FORMAT,
)


async def playback_task() -> None:
    while True:
        data = await play_queue.get()
        try:
            await asyncio.to_thread(output_stream.write, data)
        finally:
            play_queue.task_done()


@asynccontextmanager
async def connect_and_start_recording_and_playback(
    session: RealtimeSessionCreateRequestParam,
) -> AsyncGenerator[AsyncRealtimeConnection, None]:
    async with connect_and_start_recording(session) as connection:
        asyncio.create_task(playback_task())
        output_stream.start()

        yield connection


async def handle_audio_delta(delta: str) -> None:
    data = np.frombuffer(base64.b64decode(delta), dtype=FORMAT)

    await play_queue.put(data)


async def main() -> None:
    async with connect_and_start_recording_and_playback(basic_session) as connection:
        async for event in connection:
            if "delta" not in event.type:
                logger.info("Received a %s event", event.type)

            match event:
                case ResponseAudioDeltaEvent():
                    await handle_audio_delta(event.delta)
                case _:
                    pass


if __name__ == "__main__":
    asyncio.run(main())
