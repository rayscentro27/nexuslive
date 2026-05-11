#!/usr/bin/env python3
"""
import_summaries.py
- Reads .summary files from SUMMARY_FOLDER (./strategies by default) OR reads files from a Supabase Storage bucket.
- Ensures a 'research' table exists (attempts to create it via RPC; prints SQL if not possible).
- Upserts records into the research table (title UNIQUE to dedupe).
- Optional Hugging Face embeddings when HF_TOKEN is set (HF_MODEL optional).
- Usage:
    SUPABASE_URL=https://<project-ref>.supabase.co \
    SUPABASE_KEY=<service_role_or_anon_key> \
    SUMMARY_FOLDER=./strategies \
    python import_summaries.py
Environment variables:
- SUPABASE_URL (required)
- SUPABASE_KEY (required) — prefer a service_role key for server-side imports
- HF_TOKEN (optional) — Hugging Face token to enable embeddings
- HF_MODEL (optional) — HF model slug, default: sentence-transformers/all-MiniLM-L6-v2
- SUMMARY_FOLDER (optional) — default ./strategies
- STORAGE_BUCKET (optional) — if set, will read .summary files from this bucket instead of local folder
- DRY_RUN (optional) — if 'true' or '1', don't write to DB
"""
from pathlib import Path
import os
import sys
import json
import time
from typing import Optional, List, Dict, Any

try:
    from dotenv import load_dotenv, find_dotenv
    load_dotenv(find_dotenv(usecwd=False) or os.path.join(os.path.dirname(__file__), '..', '.env'))
except ImportError:
    pass

# You need supabase client: pip install supabase
try:
    from supabase import create_client
except Exception as e:
    print("ERROR: supabase client not installed. Install with: pip install supabase")
    raise

# Optional requests for HF calls and storage downloads
try:
    import requests
except Exception:
    requests = None

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
FOLDER = os.getenv("SUMMARY_FOLDER", "./strategies")
TABLE_NAME = os.getenv("TABLE_NAME", "research")
STORAGE_BUCKET = os.getenv("STORAGE_BUCKET")  # if set, read from storage
DRY_RUN = os.getenv("DRY_RUN", "false").lower() in ("1", "true", "yes")
HF_TOKEN = os.getenv("HF_TOKEN")
HF_MODEL = os.getenv("HF_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("ERROR: SUPABASE_URL and SUPABASE_KEY must be set in environment.")
    sys.exit(1)

sb = create_client(SUPABASE_URL, SUPABASE_KEY)

def compute_embedding_huggingface(text: str) -> Optional[List[float]]:
    """
    Compute embedding using local Hugging Face sentence-transformers.
    Returns list[float] or None on failure.
    """
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        print("ERROR: sentence_transformers library not available. Install with: pip install sentence-transformers")
        return None

    try:
        # Use local model for embeddings (no API calls, no costs!)
        model = SentenceTransformer(HF_MODEL)
        embedding = model.encode(text)
        return [float(v) for v in embedding]
    except Exception as e:
        print(f"Embedding computation error: {e}")
        return None

def ensure_table_exists():
    create_sql = f"""
    CREATE TABLE IF NOT EXISTS public.{TABLE_NAME} (
        id BIGSERIAL PRIMARY KEY,
        source TEXT,
        title TEXT UNIQUE,
        content TEXT,
        embedding REAL[],
        created_at TIMESTAMPTZ DEFAULT now()
    );
    CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_title ON public.{TABLE_NAME}(title);
    """
    try:
        # try to run a SQL via RPC if available (some projects support a 'sql' RPC)
        try:
            sb.rpc("sql", {"query": create_sql}).execute()
            print("✅ Ensured table exists via rpc('sql').")
            return
        except Exception:
            # fallback: try direct SQL using PostgREST exec (not always available)
            # We'll attempt to run using the SQL function path if present
            print("⚠️ rpc('sql') not available — if table not present, please create it with the SQL below.")
            print(create_sql)
    except Exception as e:
        print("Error ensuring table exists:", e)
        print(create_sql)

def list_summaries_from_folder(folder: str) -> List[Dict[str, Any]]:
    p = Path(folder)
    if not p.exists() or not p.is_dir():
        print(f"Folder not found: {folder}")
        return []
    records = []
    for file in sorted(p.iterdir()):
        if file.is_file() and file.suffix == ".summary":
            try:
                content = file.read_text(encoding="utf-8")
            except Exception as e:
                print(f"Skipping {file.name}: read error: {e}")
                continue
            records.append({"source": "local", "title": file.stem, "content": content})
    return records

def list_summaries_from_storage(bucket: str) -> List[Dict[str, Any]]:
    """
    Reads files from a Supabase Storage bucket. Expects .summary files at bucket root.
    Requires SUPABASE_KEY to have storage.read rights.
    """
    records: List[Dict[str, Any]] = []
    try:
        res = sb.storage.from_(bucket).list()
    except Exception as e:
        print("Storage list error:", e)
        return []
    # res is typically a dict with 'data' key
    items = res.get("data") if isinstance(res, dict) else None
    if not items:
        print("No items in storage or unexpected response:", res)
        return []
    for it in items:
        name = it.get("name")
        if not name or not name.endswith(".summary"):
            continue
        try:
            dl = sb.storage.from_(bucket).download(name)
            # download returns bytes
            if isinstance(dl, dict) and dl.get("error"):
                print("Error downloading", name, dl.get("error"))
                continue
            if isinstance(dl, (bytes, bytearray)):
                text = dl.decode("utf-8")
            else:
                # sometimes returns a dict wrapper
                text = dl.get("data").decode("utf-8") if isinstance(dl, dict) and dl.get("data") else str(dl)
            records.append({"source": f"storage:{bucket}", "title": Path(name).stem, "content": text})
        except Exception as e:
            print("Download error for", name, e)
    return records

def upsert_records(records: List[Dict[str, Any]]):
    if not records:
        print("No records to insert.")
        return
    for rec in records:
        if not rec.get("title") or not rec.get("content"):
            print("Skipping invalid record:", rec)
            continue
        # Compute embedding if HF_TOKEN is present
        emb = None
        if HF_TOKEN:
            emb = compute_embedding_huggingface(rec["content"])
            if emb:
                print(f"✅ Computed embedding for {rec['title']} ({len(emb)} dims)")
            else:
                print(f"⚠️ Failed to compute embedding for {rec['title']}")

        record = {
            "source": rec.get("source", "unknown"),
            "title": rec["title"],
            "content": rec["content"],
            "embedding": emb
        }

        if DRY_RUN:
            print(f"DRY_RUN: Would upsert {record['title']}")
            continue

        try:
            # Upsert with on_conflict=title to dedupe
            sb.table(TABLE_NAME).upsert(record, on_conflict="title").execute()
            print(f"✅ Upserted: {record['title']}")
        except Exception as e:
            print(f"❌ Error upserting {record['title']}: {e}")

def main():
    print("🧠 Nexus Research Importer")
    print(f"Table: {TABLE_NAME}")
    print(f"Source: {'storage' if STORAGE_BUCKET else 'folder'} ({FOLDER if not STORAGE_BUCKET else STORAGE_BUCKET})")
    if HF_TOKEN:
        print(f"Embeddings: Enabled (HF)")
    else:
        print("⚠️  WARNING: HF_TOKEN not set — embeddings will be NULL for all records.")
        print("   Set HF_TOKEN in .env to enable embeddings. Downstream semantic search will not work.")
    print(f"DRY_RUN: {DRY_RUN}")
    print()

    ensure_table_exists()

    if STORAGE_BUCKET:
        records = list_summaries_from_storage(STORAGE_BUCKET)
    else:
        records = list_summaries_from_folder(FOLDER)

    print(f"Found {len(records)} summary files.")
    if records:
        print("Titles:", [r["title"] for r in records])

    upsert_records(records)
    print("Done.")

if __name__ == "__main__":
    main()