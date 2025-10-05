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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GITHUB_PAT = os.environ.get("GITHUB_PAT")

tools_always_allowed = [
    "get_commit",
    "get_issue",
    "get_issue_comments",
    "get_latest_release",
    "get_pull_request",
    "get_release_by_tag",
    "get_tag",
    "list_branches",
    "list_commits",
    "list_discussion_categories",
    "list_discussions",
    "list_issue_types",
    "list_issues",
    "list_pull_requests",
    "list_releases",
    "list_tags",
    "search_code",
    "search_issues",
    "search_orgs",
    "search_pull_requests",
    "search_repositories",
    "search_users",
]

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
                tool_names=tools_always_allowed
            ),
            require_approval=McpRequireApprovalMcpToolApprovalFilter(
                never=McpRequireApprovalMcpToolApprovalFilterNever(
                    tool_names=tools_always_allowed
                ),
                always=McpRequireApprovalMcpToolApprovalFilterAlways(
                    tool_names=[]
                ),
            ),
        )
    ],
    instructions="Help the user with Github. Speak in ENGLISH only. Be extra nice!",
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
