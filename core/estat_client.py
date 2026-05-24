"""
estat_client.py — e-Stat API から法人企業統計の業種別経営指標を取得・キャッシュ

使い方:
    client = EStatClient()
    benchmarks = client.get_benchmarks("製造業", "中小企業")
    # -> {"gross_margin": 25.3, "operating_margin": 4.1, ...}

更新:
    client.refresh()  # e-Stat から最新データを取得してSupabaseに保存
"""
from __future__ import annotations

import json
import logging
import requests
from typing import Optional

from core.config import Config

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------ #
#  業種マッピング（e-Stat 法人企業統計 産業分類 → 表示名）
# ------------------------------------------------------------------ #
# e-Stat 法人企業統計 統計表ID（年次・産業別）
ESTAT_STATS_ID = "0003900976"  # 法人企業統計調査（年次別調査）

INDUSTRY_MAP = {
    "製造業":         "D",
    "建設業":         "C",
    "卸売業":         "I",
    "小売業":         "J",
    "不動産業":       "L",
    "情報通信業":     "G",
    "運輸業・郵便業": "H",
    "サービス業":     "R",
    "飲食・宿泊業":   "M",
    "医療・福祉":     "P",
}

# ------------------------------------------------------------------ #
#  フォールバック用静的ベンチマーク
#  出典: 財務省「法人企業統計調査」令和5年度（2023年度実績、全規模合算）
#  URL: https://www.mof.go.jp/pri/reference/ssc/
#  ※ e-Stat API が利用不可の場合のみ使用。数値は全規模平均。
# ------------------------------------------------------------------ #
_FALLBACK: dict[str, dict] = {
    "製造業":         {"gross_margin": 25.5, "operating_margin": 4.3, "ordinary_margin": 4.7, "sga_ratio": 21.2, "cogs_ratio": 74.5},
    "建設業":         {"gross_margin": 22.1, "operating_margin": 3.8, "ordinary_margin": 4.2, "sga_ratio": 18.3, "cogs_ratio": 77.9},
    "卸売業":         {"gross_margin": 15.4, "operating_margin": 2.2, "ordinary_margin": 2.5, "sga_ratio": 13.2, "cogs_ratio": 84.6},
    "小売業":         {"gross_margin": 30.8, "operating_margin": 3.0, "ordinary_margin": 3.3, "sga_ratio": 27.8, "cogs_ratio": 69.2},
    "不動産業":       {"gross_margin": 46.0, "operating_margin": 12.5, "ordinary_margin": 13.0, "sga_ratio": 33.5, "cogs_ratio": 54.0},
    "情報通信業":     {"gross_margin": 40.2, "operating_margin": 7.5, "ordinary_margin": 8.0, "sga_ratio": 32.7, "cogs_ratio": 59.8},
    "運輸業・郵便業": {"gross_margin": 28.8, "operating_margin": 3.6, "ordinary_margin": 4.0, "sga_ratio": 25.2, "cogs_ratio": 71.2},
    "サービス業":     {"gross_margin": 42.5, "operating_margin": 6.0, "ordinary_margin": 6.4, "sga_ratio": 36.5, "cogs_ratio": 57.5},
    "飲食・宿泊業":   {"gross_margin": 65.5, "operating_margin": 2.3, "ordinary_margin": 2.7, "sga_ratio": 63.2, "cogs_ratio": 34.5},
    "医療・福祉":     {"gross_margin": 88.5, "operating_margin": 3.5, "ordinary_margin": 3.8, "sga_ratio": 85.0, "cogs_ratio": 11.5},
    "全産業":         {"gross_margin": 28.5, "operating_margin": 4.2, "ordinary_margin": 4.6, "sga_ratio": 24.3, "cogs_ratio": 71.5},
}


class EStatClient:
    BASE_URL = "https://api.e-stat.go.jp/rest/3.0/app/json"

    def __init__(self):
        self.api_key = Config.ESTAT_API_KEY
        self._cache: dict = {}

    # ---------------------------------------------------------------- #
    def get_benchmarks(self, industry: str, company_size: str = "中小企業") -> dict:
        """
        業種・規模別の経営指標ベンチマークを返す。
        キャッシュ（Supabase）→ フォールバック の順で取得。
        """
        # 1. Supabaseキャッシュ
        cached = self._load_from_cache(industry)
        if cached:
            return cached

        # 2. フォールバック静的テーブル
        return _FALLBACK.get(industry, _FALLBACK["全産業"])

    # ---------------------------------------------------------------- #
    def refresh(self, industry: str = "全産業") -> dict[str, dict]:
        """
        e-Stat API から最新の法人企業統計を取得してSupabaseにキャッシュ保存。
        戻り値: 取得できた業種ベンチマーク dict
        """
        if not self.api_key:
            raise ValueError("ESTAT_API_KEY が設定されていません")

        results = {}
        try:
            # 統計データ取得 (法人企業統計 年次)
            data = self._fetch_stat_data()
            if data:
                results = self._parse_corporate_stats(data)
                self._save_to_cache(results)
                logger.info("e-Stat ベンチマーク更新完了: %d 業種", len(results))
            else:
                logger.warning("e-Stat からデータを取得できませんでした。フォールバックを使用します。")
                results = _FALLBACK
        except Exception as e:
            logger.error("e-Stat 取得エラー: %s", e)
            results = _FALLBACK

        return results

    # ---------------------------------------------------------------- #
    def _fetch_stat_data(self) -> Optional[dict]:
        """e-Stat API から統計データを取得する。"""
        url = f"{self.BASE_URL}/getStatsData"
        params = {
            "appId":   self.api_key,
            "statsDataId": ESTAT_STATS_ID,
            "metaGetFlg": "Y",
            "cntGetFlg": "N",
            "explanationGetFlg": "N",
            "annotationGetFlg": "N",
            "sectionHeaderFlg": "1",
            "replaceSpChars": "0",
        }
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def _parse_corporate_stats(self, data: dict) -> dict[str, dict]:
        """
        e-Stat レスポンスから業種別ベンチマークを解析する。
        データ構造が複雑なため、取得できた場合は上書き、できなければフォールバック。
        """
        results = dict(_FALLBACK)  # フォールバックをベースに

        try:
            stat_data = data.get("GET_STATS_DATA", {}).get("STATISTICAL_DATA", {})
            data_inf = stat_data.get("DATA_INF", {})
            value_list = data_inf.get("VALUE", [])

            if not value_list:
                return results

            # 業種コード → 業種名 逆引き
            rev_map = {v: k for k, v in INDUSTRY_MAP.items()}

            # 売上高・各利益を集計
            industry_totals: dict[str, dict] = {}
            for item in value_list:
                if not isinstance(item, dict):
                    continue
                ind_code = item.get("@cat01", "")
                ind_name = rev_map.get(ind_code)
                if not ind_name:
                    continue
                metric = item.get("@cat02", "")
                try:
                    val = float(item.get("$", 0))
                except (TypeError, ValueError):
                    continue

                if ind_name not in industry_totals:
                    industry_totals[ind_name] = {}
                industry_totals[ind_name][metric] = val

            # 利益率を計算して results に反映
            for ind_name, metrics in industry_totals.items():
                revenue = metrics.get("売上高", 0)
                if revenue <= 0:
                    continue
                gross_profit = metrics.get("売上総利益", 0)
                op_profit    = metrics.get("営業利益", 0)
                ord_profit   = metrics.get("経常利益", 0)
                cogs         = metrics.get("売上原価", revenue * 0.72)
                sga          = metrics.get("販売費及び一般管理費", revenue * 0.24)

                results[ind_name] = {
                    "gross_margin":      round(gross_profit / revenue * 100, 1),
                    "operating_margin":  round(op_profit    / revenue * 100, 1),
                    "ordinary_margin":   round(ord_profit   / revenue * 100, 1),
                    "cogs_ratio":        round(cogs         / revenue * 100, 1),
                    "sga_ratio":         round(sga          / revenue * 100, 1),
                    "source": "e-Stat法人企業統計",
                }

        except Exception as e:
            logger.warning("e-Stat データ解析エラー: %s — フォールバック使用", e)

        return results

    # ---------------------------------------------------------------- #
    def _load_from_cache(self, industry: str) -> Optional[dict]:
        """Supabase の industry_benchmarks テーブルからキャッシュを読む。"""
        try:
            from core.supabase_client import get_supabase_client
            sb = get_supabase_client()
            res = sb.table("industry_benchmarks").select("data, updated_at") \
                .eq("industry", industry).single().execute()
            if res.data:
                import datetime
                updated = res.data.get("updated_at", "")
                # 6ヶ月以上古ければ無効
                if updated:
                    dt = datetime.datetime.fromisoformat(updated.replace("Z", "+00:00"))
                    age = datetime.datetime.now(datetime.timezone.utc) - dt
                    if age.days > 180:
                        return None
                raw = res.data.get("data")
                return json.loads(raw) if isinstance(raw, str) else raw
        except Exception:
            pass
        return None

    def _save_to_cache(self, results: dict[str, dict]) -> None:
        """Supabase の industry_benchmarks テーブルにキャッシュ保存。"""
        try:
            from core.supabase_client import get_supabase_client
            sb = get_supabase_client()
            for industry, data in results.items():
                sb.table("industry_benchmarks").upsert({
                    "industry": industry,
                    "data": json.dumps(data, ensure_ascii=False),
                }, on_conflict="industry").execute()
        except Exception as e:
            logger.warning("ベンチマークキャッシュ保存失敗: %s", e)

    @staticmethod
    def available_industries() -> list[str]:
        return list(_FALLBACK.keys())
