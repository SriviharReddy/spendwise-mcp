"""Server-Sent Events streaming chat route for SpendWise agent."""

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from backend.agent import stream_agent_lifecycle
from backend.models import ChatStreamRequest

router = APIRouter(prefix="/api/chat", tags=["Agent Chat Stream"])


@router.post("/stream")
async def chat_stream_endpoint(payload: ChatStreamRequest) -> StreamingResponse:
    """Streams real-time agent lifecycle events, tool execution, and token chunks.

    Returns:
        StreamingResponse with text/event-stream content type.
    """
    event_generator = stream_agent_lifecycle(
        message=payload.message,
        thread_id=payload.thread_id,
        provider=payload.provider,
        model=payload.model,
        api_key=payload.api_key,
        base_url=payload.base_url,
    )

    return StreamingResponse(
        event_generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
