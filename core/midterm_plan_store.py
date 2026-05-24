"""
Mid-Term Plan Store: Supabase永続化ヘルパー。
中期経営計画ドキュメントをDBに保存・読み込みする。
"""
import json
import logging
from datetime import datetime
from typing import Optional

from core.supabase_client import get_supabase_client
from core.schemas.midterm_plan_schema import MidtermPlanDocument

logger = logging.getLogger(__name__)


def save_midterm_plan(client_id: str, doc: MidtermPlanDocument) -> bool:
    """
    中期経営計画ドキュメントをSupabaseに保存（UPSERT）。
    
    Args:
        client_id: クライアントID
        doc: MidtermPlanDocumentオブジェクト
    Returns:
        成功時True、失敗時False
    """
    try:
        supabase = get_supabase_client()
        doc_json = json.loads(doc.model_dump_json())
        
        # Check if record exists
        existing = supabase.table("midterm_plan_documents") \
            .select("id") \
            .eq("client_id", client_id) \
            .execute()
        
        now = datetime.now().isoformat()
        
        if existing.data:
            # UPDATE
            supabase.table("midterm_plan_documents") \
                .update({
                    "document_json": doc_json,
                    "updated_at": now
                }) \
                .eq("client_id", client_id) \
                .execute()
            logger.info(f"Midterm plan updated for client {client_id}")
        else:
            # INSERT
            supabase.table("midterm_plan_documents") \
                .insert({
                    "client_id": client_id,
                    "document_json": doc_json,
                    "updated_at": now,
                    "created_at": now
                }) \
                .execute()
            logger.info(f"Midterm plan created for client {client_id}")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to save midterm plan: {e}")
        return False


def load_midterm_plan(client_id: str) -> Optional[MidtermPlanDocument]:
    """
    SupabaseからクライアントIDで中期経営計画ドキュメントを読み込む。
    
    Args:
        client_id: クライアントID
    Returns:
        MidtermPlanDocumentオブジェクト、見つからない場合はNone
    """
    try:
        supabase = get_supabase_client()
        result = supabase.table("midterm_plan_documents") \
            .select("document_json") \
            .eq("client_id", client_id) \
            .execute()
        
        if result.data and len(result.data) > 0:
            doc_json = result.data[0]["document_json"]
            doc = MidtermPlanDocument.model_validate(doc_json)
            logger.info(f"Midterm plan loaded for client {client_id}")
            return doc
        
        return None
        
    except Exception as e:
        logger.error(f"Failed to load midterm plan: {e}")
        return None
