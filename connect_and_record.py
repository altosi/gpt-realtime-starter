import asyncio
import logging
import queue
from base64 import b64encode
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import numpy as np
from openai.resources.realtime.realtime import AsyncRealtimeConnection
from openai.types.realtime import (
    InputAudioBufferAppendEvent,
    ResponseAudioTranscriptDoneEvent,
    RealtimeSessionCreateRequestParam,
)
from sounddevice import CallbackFlags, InputStream
from connect import connect_to_realtime_api, basic_session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SAMPLE_RATE: int = 24000
CHANNELS: int = 1
FORMAT = np.int16

record_queue: queue.Queue[np.ndarray] = queue.Queue()


def audio_callback(indata: np.ndarray, frames: int, time, status: CallbackFlags) -> None:
    record_queue.put_nowait(indata.copy())


async def recording_task(connection: AsyncRealtimeConnection) -> None:
    while True:
        chunk = await asyncio.to_thread(record_queue.get)

        await connection.send(
            InputAudioBufferAppendEvent(
                type="input_audio_buffer.append",
                audio=b64encode(chunk.tobytes()).decode("ascii"),
            )
        )


input_stream = InputStream(
    channels=CHANNELS,
    samplerate=SAMPLE_RATE,
    dtype=FORMAT,
    callback=audio_callback,
)


@asynccontextmanager
async def connect_and_start_recording(
    session: RealtimeSessionCreateRequestParam,
) -> AsyncGenerator[AsyncRealtimeConnection, None]:
    async with connect_to_realtime_api(session) as connection:
        asyncio.create_task(recording_task(connection))
        input_stream.start()

        yield connection


async def main() -> None:
    async with connect_and_start_recording(basic_session) as connection:
        async for event in connection:
            match event:
                case ResponseAudioTranscriptDoneEvent():
                    logger.info(f"Assistant: {event.transcript}")
                case _:
                    pass


if __name__ == "__main__":
    asyncio.run(main())
