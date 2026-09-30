import inspect
import os
import re

from dotenv import load_dotenv
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)
from supabase import AsyncClient, acreate_client

from backend.db.models import Messages

load_dotenv()


def db_messages_to_model_messages(messages: list[Messages]) -> list[ModelMessage]:
    model_messages: list[ModelMessage] = []

    for msg in sorted(messages, key=lambda m: m.sequence_no):
        if msg.role == "User":
            model_messages.append(
                ModelRequest(parts=[UserPromptPart(content=msg.message_content)])
            )
        elif msg.role == "Agent":
            model_messages.append(
                ModelResponse(parts=[TextPart(content=msg.message_content)])
            )
        # any other role (e.g. "system") — extend here if you ever store those

    return model_messages


async def attach_signed_url(markdown_content: str, expires_in: int = 900) -> str:
    """Replace supabase:: placeholders with fresh signed URLs before serving."""
    pattern = r"\(supabase::([^)]+)\)"
    # A diagram can be referenced more than once in a report, so resolve each
    # distinct object path once instead of once per occurrence.
    paths = set(re.findall(pattern, markdown_content))

    if not paths:
        return markdown_content
    url: str = os.getenv("SUPABASE_URL", "")
    key: str = os.getenv("SUPABASE_KEY", "")

    bucket_id: str = os.getenv("SUPABASE_BUCKET_ID", "")

    supabase: AsyncClient = await acreate_client(url, key)

    try:
        signed_urls: dict[str, str] = {}
        for path in paths:
            # upload_to_bucket stores "<bucket>/Diagrams/..."; strip the bucket
            # to get the object key create_signed_url expects. Tolerate a
            # placeholder that never had the bucket prefix rather than raising.
            object_path = path.removeprefix(bucket_id).lstrip("/")
            signed = await supabase.storage.from_(bucket_id).create_signed_url(
                path=object_path, expires_in=expires_in
            )
            signed_urls[f"(supabase::{path})"] = f"({signed['signedURL']})"

        for placeholder, signed_url in signed_urls.items():
            markdown_content = markdown_content.replace(placeholder, signed_url)
    finally:
        # AsyncClient exposes the httpx transports directly; close whichever
        # were actually created (acreate_client builds storage + postgrest).
        for attr in ("storage", "postgrest"):
            client = getattr(supabase, attr, None)
            closer = getattr(client, "aclose", None) or getattr(client, "close", None)
            if closer is not None:
                result = closer()
                if inspect.isawaitable(result):
                    await result

    return markdown_content
