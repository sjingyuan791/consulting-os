"""
共通 pytest フィクスチャ — test_agents_sdk パッケージ
"""
import asyncio
import json
import pytest
from unittest.mock import MagicMock


def call_tool(tool, **kwargs) -> dict:
    """
    FunctionTool (openai-agents @function_tool) を同期的に呼び出すヘルパー。
    戻り値は JSON パース済み dict。
    """
    ctx = MagicMock()
    input_json = json.dumps(kwargs)
    loop = asyncio.new_event_loop()
    try:
        result_str = loop.run_until_complete(tool.on_invoke_tool(ctx, input_json))
    finally:
        loop.close()
    return json.loads(result_str)


@pytest.fixture
def run_async():
    """非同期コルーチンを同期テスト内で実行するヘルパー。"""
    def _run(coro):
        return asyncio.get_event_loop().run_until_complete(coro)
    return _run


@pytest.fixture
def mock_supabase():
    """Supabase クライアントのモック。"""
    mock = MagicMock()
    # デフォルト: 空リスト返却
    mock.table.return_value.select.return_value.eq.return_value\
        .limit.return_value.execute.return_value.data = []
    mock.table.return_value.select.return_value.eq.return_value\
        .order.return_value.limit.return_value.execute.return_value.data = []
    mock.table.return_value.insert.return_value.execute.return_value.data = [
        {"id": "test-checkpoint-id"}
    ]
    return mock


@pytest.fixture
def sample_financials_dict():
    """整合する財務データサンプル。"""
    return {
        "total_assets": 1000.0,
        "total_liabilities": 600.0,
        "net_assets": 400.0,
        "sales": 500.0,
        "cogs": 300.0,
        "gross_profit": 200.0,
        "operating_profit": 50.0,
        "net_income": 30.0,
    }


@pytest.fixture
def broken_financials_dict():
    """BS不一致の財務データ（total_assets ≠ liabilities + equity）。"""
    return {
        "total_assets": 1000.0,
        "total_liabilities": 600.0,
        "net_assets": 350.0,  # 意図的に不一致
        "sales": 500.0,
        "cogs": 300.0,
        "gross_profit": 200.0,
    }
