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
    matches = re.findall(pattern, markdown_content)

    if not matches:
        return markdown_content
    url: str = os.getenv("SUPABASE_URL", "")
    key: str = os.getenv("SUPABASE_KEY", "")

    bucket_id: str = os.getenv("SUPABASE_BUCKET_ID", "")

    supabase: AsyncClient = await acreate_client(url, key)

    for path in matches:
        print(path)
        signed = await supabase.storage.from_(bucket_id).create_signed_url(
            path=path.split(bucket_id)[1], expires_in=expires_in
        )
        markdown_content = markdown_content.replace(
            f"(supabase::{path})", f"({signed['signedURL']})"
        )

    return markdown_content
