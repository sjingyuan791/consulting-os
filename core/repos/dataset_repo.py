from typing import Dict, Any, Optional
from core.supabase_client import get_supabase_client

class DatasetRepo:
    def __init__(self):
        self.supabase = get_supabase_client()

    def get_or_create_dataset(self, client_id: str, dataset_type: str) -> str:
        """
        Get existing dataset ID or create a new abstract dataset container.
        """
        # Check existence
        res = self.supabase.table("datasets")\
            .select("id")\
            .eq("client_id", client_id)\
            .eq("dataset_type", dataset_type)\
            .execute()
        
        if res.data:
            return res.data[0]['id']
        
        # Create new
        payload = {
            "client_id": client_id,
            "dataset_type": dataset_type,
            "description": f"Main {dataset_type} dataset for client {client_id}"
        }
        res = self.supabase.table("datasets").insert(payload).execute()
        return res.data[0]['id']

    def save_dataset_version(
        self, 
        client_id: str, 
        dataset_type: str, 
        normalized_json: Any, 
        quality_json: Any,
        source_type: str = "upload",
        created_by: Optional[str] = None
    ) -> int:
        """
        Atomic version increment and save.
        Returns the new version number.
        """
        dataset_id = self.get_or_create_dataset(client_id, dataset_type)
        
        # 1. Get current max version (Optimistic locking assumed for now, or just simple query)
        # In a real high-concurrency app, we'd use a DB function for atomicity.
        res = self.supabase.table("dataset_versions")\
            .select("version")\
            .eq("dataset_id", dataset_id)\
            .order("version", desc=True)\
            .limit(1)\
            .execute()
            
        current_max = 0
        if res.data:
            current_max = res.data[0]['version']
            
        new_version = current_max + 1
        
        # 2. Mark old versions as not current
        self.supabase.table("dataset_versions")\
            .update({"is_current": False})\
            .eq("dataset_id", dataset_id)\
            .execute()
            
        # 3. Insert new version
        payload = {
            "dataset_id": dataset_id,
            "version": new_version,
            "is_current": True,
            "source_type": source_type,
            "normalized_json": normalized_json,
            "quality_json": quality_json,
            "created_by": created_by
        }
        
        self.supabase.table("dataset_versions").insert(payload).execute()
        
        # 4. Auto-index to RAG for semantic search
        self._auto_index_to_rag(client_id, dataset_type, normalized_json, new_version)
        
        return new_version
    
    def _auto_index_to_rag(
        self,
        client_id: str,
        dataset_type: str,
        normalized_json: Any,
        version: int
    ) -> None:
        """
        Automatically index dataset content to RAG for semantic search.
        """
        try:
            from core.rag_service import get_rag_service
            import json
            
            # Convert JSON data to searchable text
            if isinstance(normalized_json, dict):
                content = self._json_to_searchable_text(normalized_json, dataset_type)
            elif isinstance(normalized_json, list):
                content = self._json_to_searchable_text({"records": normalized_json}, dataset_type)
            else:
                content = str(normalized_json)
            
            if not content or len(content) < 50:
                return  # Skip if content is too short
            
            rag_service = get_rag_service()
            
            # Index the dataset content
            rag_service.index_document(
                client_id=client_id,
                content=content,
                source_type="csv",
                source_name=f"{dataset_type}_v{version}",
                metadata={
                    "dataset_type": dataset_type,
                    "version": version,
                    "auto_indexed": True
                }
            )
        except ImportError:
            pass  # RAG service not available
        except Exception as e:
            import logging
            logging.warning(f"RAG auto-indexing failed for {dataset_type}: {type(e).__name__}")
    
    def _json_to_searchable_text(self, data: dict, dataset_type: str) -> str:
        """
        Convert JSON data to human-readable searchable text.
        """
        import json
        
        lines = [f"# {dataset_type} データ\n"]
        
        def process_value(key: str, value: Any, indent: int = 0) -> str:
            prefix = "  " * indent
            if isinstance(value, dict):
                result = [f"{prefix}{key}:"]
                for k, v in value.items():
                    result.append(process_value(k, v, indent + 1))
                return "\n".join(result)
            elif isinstance(value, list):
                if not value:
                    return f"{prefix}{key}: (空リスト)"
                if isinstance(value[0], dict):
                    # Table-like data
                    result = [f"{prefix}{key}: {len(value)}件"]
                    for i, item in enumerate(value[:10]):  # Limit to first 10
                        result.append(f"{prefix}  [{i+1}] " + ", ".join(
                            f"{k}={v}" for k, v in list(item.items())[:5]
                        ))
                    if len(value) > 10:
                        result.append(f"{prefix}  ... 他{len(value)-10}件")
                    return "\n".join(result)
                else:
                    return f"{prefix}{key}: {', '.join(str(v) for v in value[:20])}"
            else:
                return f"{prefix}{key}: {value}"
        
        for key, value in data.items():
            lines.append(process_value(key, value))
        
        return "\n".join(lines)

    def get_current_dataset_version(self, client_id: str, dataset_type: str) -> Optional[Dict]:
        """
        Fetches the current active version of a dataset type for a client.
        """
        # Join logic approximated by two queries or knowing the schema.
        # Supabase-py join support is specific. Let's do 2 steps or use the relation if defined.
        # Step 1: Get Dataset ID
        dataset_id_res = self.supabase.table("datasets")\
            .select("id")\
            .eq("client_id", client_id)\
            .eq("dataset_type", dataset_type)\
            .execute()
            
        if not dataset_id_res.data:
            return None
        
        dataset_id = dataset_id_res.data[0]['id']
        
        # Step 2: Get Current Version
        res = self.supabase.table("dataset_versions")\
            .select("*")\
            .eq("dataset_id", dataset_id)\
            .eq("is_current", True)\
            .limit(1)\
            .execute()
            
        if res.data:
            return res.data[0]
        return None

    def get_version_by_id(self, version_id: str) -> Optional[Dict]:
        res = self.supabase.table("dataset_versions").select("*").eq("id", version_id).execute()
        return res.data[0] if res.data else None
