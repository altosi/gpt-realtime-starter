import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from openai import AsyncOpenAI
from openai.resources.realtime.realtime import AsyncRealtimeConnection
from openai.types.realtime import (
    RealtimeSessionCreateRequestParam,
    RealtimeAudioConfigOutputParam,
    RealtimeAudioConfigParam,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

basic_session = RealtimeSessionCreateRequestParam(
    type="realtime",
    tracing=None,
    audio=RealtimeAudioConfigParam(
        output=RealtimeAudioConfigOutputParam(voice="marin")
    ),
    instructions="Help the user with their projects. Speak in ENGLISH only. Be extra nice!",
)


@asynccontextmanager
async def connect_to_realtime_api(
    session: RealtimeSessionCreateRequestParam,
) -> AsyncGenerator[AsyncRealtimeConnection, None]:
    async with AsyncOpenAI(api_key=OPENAI_API_KEY).realtime.connect(
        model="gpt-realtime"
    ) as connection:
        logger.info("Connected to OpenAI Realtime API")
        await connection.session.update(session=session)
        logger.info("Session updated")
        yield connection


async def main() -> None:
    async with connect_to_realtime_api(basic_session) as connection:
        async for event in connection:
            logger.info("Received event: %s", event.type)


if __name__ == "__main__":
    asyncio.run(main())
