import asyncio
import logging
import os
import secrets
import string

from openai.types.realtime import (
    ResponseAudioDeltaEvent,
    RealtimeSessionCreateRequestParam,
    RealtimeAudioConfigParam,
    RealtimeAudioConfigOutputParam,
    ConversationItemDone,
    ResponseCreateEvent,
    ResponseAudioTranscriptDoneEvent,
    RealtimeErrorEvent,
    RealtimeClientEvent,
    RealtimeServerEvent,
    RealtimeMcpToolCall,
    RealtimeMcpApprovalRequest,
    ConversationItemCreateEvent,
    RealtimeMcpApprovalResponse,
    ConversationItem,
    ResponseDoneEvent,
)
from openai.types.realtime.realtime_tools_config_param import (
    Mcp,
    McpRequireApprovalMcpToolApprovalFilter,
    McpRequireApprovalMcpToolApprovalFilterNever,
    McpAllowedToolsMcpToolFilter,
    McpRequireApprovalMcpToolApprovalFilterAlways,
)
from connect_record_and_playback import (
    connect_and_start_recording_and_playback,
    handle_audio_delta,
)
from connect_and_use_a_tool import tools_always_allowed

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GITHUB_PAT = os.environ.get("GITHUB_PAT")

tools_allowed_with_approval = ["create_repository"]

session_with_mcp = RealtimeSessionCreateRequestParam(
    type="realtime",
    tracing=None,
    audio=RealtimeAudioConfigParam(
        output=RealtimeAudioConfigOutputParam(voice="marin")
    ),
    tools=[
        Mcp(
            type="mcp",
            server_label="github_mcp",
            server_url="https://api.githubcopilot.com/mcp/",
            authorization=GITHUB_PAT,
            allowed_tools=McpAllowedToolsMcpToolFilter(
                tool_names=tools_always_allowed + tools_allowed_with_approval
            ),
            require_approval=McpRequireApprovalMcpToolApprovalFilter(
                never=McpRequireApprovalMcpToolApprovalFilterNever(
                    tool_names=tools_always_allowed
                ),
                always=McpRequireApprovalMcpToolApprovalFilterAlways(
                    tool_names=tools_allowed_with_approval
                ),
            ),
        )
    ],
    instructions="Help the user with Github. Speak in ENGLISH only. Be extra nice!",
)


def generate_id() -> str:
    return "".join(
        secrets.choice(string.ascii_letters + string.digits) for _ in range(21)
    )


async def handle_conversation_item_done(
    item: ConversationItem,
) -> list[RealtimeClientEvent]:
    match item:
        case RealtimeMcpToolCall():
            logger.info(
                "MCP tool call %s(%s) completed with output: %s",
                item.name,
                item.arguments,
                item.output,
            )
            return [ResponseCreateEvent(type="response.create")]
        case RealtimeMcpApprovalRequest():
            prompt = f"Agent requests: {item.name}({item.arguments}). Approve? [y/N]: "
            try:
                approval_response = await asyncio.wait_for(
                    asyncio.to_thread(input, prompt), timeout=30
                )
            except asyncio.TimeoutError:
                approval_response = "n"  # default deny

            return [
                ConversationItemCreateEvent(
                    type="conversation.item.create",
                    item=RealtimeMcpApprovalResponse(
                        id=f"mcp_rsp_{generate_id()}",
                        type="mcp_approval_response",
                        approve=(approval_response.lower() == "y"),
                        approval_request_id=item.id,
                    ),
                )
            ]
        case _:
            logger.info("Conversation item of type %s received", item.type)
            return []


async def handle_server_event(event: RealtimeServerEvent) -> list[RealtimeClientEvent]:
    if "delta" not in event.type:
        logger.info("Received a %s event", event.type)

    match event:
        case ResponseAudioDeltaEvent():
            await handle_audio_delta(event.delta)
        case ResponseDoneEvent():
            for item in event.response.output:
                match item:
                    case RealtimeMcpToolCall():
                        logger.info("MCP tool call %s(%s)", item.name, item.arguments)
        case ConversationItemDone():
            return await handle_conversation_item_done(event.item)
        case ResponseAudioTranscriptDoneEvent():
            logger.info("Assistant: %s", event.transcript)
        case RealtimeErrorEvent():
            logger.error("Error: %s", event.error.message)
    return []


async def main() -> None:
    try:
        async with connect_and_start_recording_and_playback(
            session_with_mcp
        ) as connection:
            async for server_event in connection:
                for client_event in await handle_server_event(server_event):
                    await connection.send(client_event)
    except KeyboardInterrupt:
        logger.info("Shutting down...")


if __name__ == "__main__":
    asyncio.run(main())
