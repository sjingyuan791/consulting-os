"""
DEPRECATED: This module is deprecated and will be removed in a future version.
Use core.repos.execution_repo.ExecutionRepo instead.
All data is now persisted in Supabase.
"""
import warnings
import json
import os
from core.models import ExecutionState

# Issue deprecation warning on import
warnings.warn(
    "ExecutionStore is deprecated. Use core.repos.execution_repo.ExecutionRepo instead.",
    DeprecationWarning,
    stacklevel=2
)

class ExecutionStore:
    @staticmethod
    def _get_path(client_id: str) -> str:
        safe_id = "".join([c for c in client_id if c.isalnum() or c in ('-', '_')])
        return f"execution_state_{safe_id}.json"

    @staticmethod
    def load_state(client_id: str) -> ExecutionState:
        path = ExecutionStore._get_path(client_id)
        if not os.path.exists(path):
            return ExecutionState(client_id=client_id)
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return ExecutionState(**data)
        except Exception as e:
            print(f"Error loading execution state: {e}")
            # Ensure robustness: return empty state but don't overwrite corrupt file yet
            return ExecutionState(client_id=client_id)

    @staticmethod
    def save_state(state: ExecutionState):
        path = ExecutionStore._get_path(state.client_id)
        temp_path = f"{path}.tmp"
        
        try:
            # Write to temp file first
            with open(temp_path, 'w', encoding='utf-8') as f:
                # model_dump() -> dict
                d = state.model_dump()
                json.dump(d, f, ensure_ascii=False, indent=2)
            
            # Atomic replace
            if os.path.exists(temp_path):
                os.replace(temp_path, path)
                
        except Exception as e:
            print(f"Error saving execution state: {e}")
            # Clean up temp if exists
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass  # Ignore cleanup errors
