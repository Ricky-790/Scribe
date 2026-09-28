import os

from dotenv import load_dotenv
from supabase import AsyncClient, acreate_client

load_dotenv()

url: str = os.getenv("SUPABASE_URL", "")
key: str = os.getenv("SUPABASE_KEY", "")

bucket_id: str = os.getenv("SUPABASE_BUCKET_ID", "")


async def upload_to_bucket(file_path: str, file_bytes: bytearray) -> str:
    supabase: AsyncClient = await acreate_client(url, key)
    try:
        response = await supabase.storage.from_(bucket_id).upload(
            path=f"Diagrams/{file_path}",
            file=bytes(file_bytes),
            file_options={"cache-control": "3600", "upsert": "true"},
        )
        return f"supabase::{response.full_path}"

    finally:
        await supabase.postgrest.aclose()
