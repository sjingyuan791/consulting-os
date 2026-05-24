"""
project_context.py — プロジェクト全体コンテキスト集約クラス

各ステップのAI呼び出しで「上流の分析結果」を自動注入するための中核モジュール。

使い方:
    ctx = ProjectContext.load(client_id)
    prompt_text = ctx.to_prompt_text()   # システムプロンプトに末尾追加
    summary = ctx.to_summary_dict()      # UI表示用
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------ #
#  データクラス（各ステップの成果物を格納）
# ------------------------------------------------------------------ #

@dataclass
class FinancialSnapshot:
    """直近の財務サマリー（決算書から）"""
    revenue: Optional[float] = None          # 売上高（最新年度、百万円）
    operating_profit: Optional[float] = None # 営業利益
    net_profit: Optional[float] = None       # 当期純利益
    total_assets: Optional[float] = None     # 総資産
    equity: Optional[float] = None           # 純資産
    operating_margin: Optional[float] = None # 営業利益率（%）
    roa: Optional[float] = None              # ROA（%）
    debt_ratio: Optional[float] = None       # 有利子負債比率（%）
    years: list = field(default_factory=list) # 年度リスト
    raw: dict = field(default_factory=dict)   # 元データ


@dataclass
class ExternalEnvironment:
    """外部環境調査結果"""
    market_size: Optional[str] = None        # 市場規模
    market_growth: Optional[str] = None      # 市場成長率
    key_trends: list = field(default_factory=list)     # 主要トレンド
    competitors: list = field(default_factory=list)    # 競合情報
    pestle_summary: Optional[str] = None     # PEST要約
    competitive_intensity: Optional[str] = None
    raw: dict = field(default_factory=dict)


@dataclass
class InternalCapability:
    """内部環境分析結果"""
    strengths: list = field(default_factory=list)      # 強み
    weaknesses: list = field(default_factory=list)     # 弱み
    core_competencies: list = field(default_factory=list)
    resource_gaps: list = field(default_factory=list)
    raw: dict = field(default_factory=dict)


@dataclass
class VisionMission:
    """理念・ビジョン・ミッション"""
    philosophy: Optional[str] = None  # 経営理念
    vision: Optional[str] = None      # ビジョン
    mission: Optional[str] = None     # ミッション
    values: Optional[str] = None      # バリュー


@dataclass
class SWOTResult:
    """SWOT分析結果"""
    strengths: list = field(default_factory=list)
    weaknesses: list = field(default_factory=list)
    opportunities: list = field(default_factory=list)
    threats: list = field(default_factory=list)
    so_strategies: list = field(default_factory=list)  # SO戦略
    st_strategies: list = field(default_factory=list)  # ST戦略
    wo_strategies: list = field(default_factory=list)  # WO戦略
    wt_strategies: list = field(default_factory=list)  # WT戦略


@dataclass
class RootCause:
    """真因分析結果"""
    root_issue: Optional[str] = None
    primary_symptom: Optional[str] = None
    likely_root_causes: list = field(default_factory=list)


@dataclass
class StrategyHypothesis:
    """全社戦略仮説"""
    selected_strategy_name: Optional[str] = None
    selected_strategy_description: Optional[str] = None
    selected_strategy_rationale: Optional[str] = None
    all_options: list = field(default_factory=list)
    context_summary: Optional[str] = None


@dataclass
class DomainPositioning:
    """ドメイン設定・ポジショニング"""
    domain_statement: Optional[str] = None
    customer: Optional[str] = None
    value_prop: Optional[str] = None
    method: Optional[str] = None
    competitive_source: Optional[str] = None


# ------------------------------------------------------------------ #
#  ProjectContext メインクラス
# ------------------------------------------------------------------ #

@dataclass
class ProjectContext:
    """
    プロジェクト全体のコンテキストを保持するクラス。
    各ステップのAI呼び出しにシステムプロンプトとして注入する。
    """
    # 基本情報
    client_id: str = ""
    company_name: str = ""
    industry: str = ""
    location: str = ""

    # 各ステップの成果物（Noneは「まだ実施していない」を意味する）
    financial: Optional[FinancialSnapshot] = None
    external: Optional[ExternalEnvironment] = None
    internal: Optional[InternalCapability] = None
    vision_mission: Optional[VisionMission] = None
    swot: Optional[SWOTResult] = None
    root_cause: Optional[RootCause] = None
    strategy: Optional[StrategyHypothesis] = None
    domain: Optional[DomainPositioning] = None

    # 完了済みステップ
    completed_steps: list = field(default_factory=list)

    # ----------------------------------------------------------------
    @classmethod
    def load(cls, client_id: str) -> "ProjectContext":
        """Supabaseから全データを集約して返す。"""
        ctx = cls(client_id=client_id)
        try:
            ctx._load_basic_info()
            ctx._load_notes_data()
            ctx._load_financial_data()
            ctx._load_strategy_run()
        except Exception as e:
            logger.warning("ProjectContext.load partial failure: %s", e)
        return ctx

    # ----------------------------------------------------------------
    def _load_basic_info(self):
        from core.supabase_client import get_supabase_client
        sb = get_supabase_client()
        res = sb.table("clients").select("name, industry, location, notes").eq("id", self.client_id).single().execute()
        if res.data:
            self.company_name = res.data.get("name", "")
            self.industry = res.data.get("industry", "")
            self.location = res.data.get("location", "")
            self._notes_raw = json.loads(res.data.get("notes") or "{}")
        else:
            self._notes_raw = {}

    def _load_notes_data(self):
        """clients.notes から vision_mission, domain_positioning, pipeline_steps を読む。"""
        notes = getattr(self, "_notes_raw", {})

        # 完了済みステップ
        steps = notes.get("pipeline_steps", {})
        self.completed_steps = [int(k) for k, v in steps.items() if v == "done"]

        # 理念・ビジョン
        vm = notes.get("vision_mission", {})
        if any(vm.values()):
            self.vision_mission = VisionMission(
                philosophy=vm.get("philosophy"),
                vision=vm.get("vision"),
                mission=vm.get("mission"),
                values=vm.get("values"),
            )

        # ドメイン
        dp = notes.get("domain_positioning", {})
        if dp.get("domain_statement") or dp.get("customer"):
            self.domain = DomainPositioning(
                domain_statement=dp.get("domain_statement"),
                customer=dp.get("customer"),
                value_prop=dp.get("value_prop"),
                method=dp.get("method"),
                competitive_source=dp.get("competitive_source"),
            )

        # 外部環境（external_environment ページで手動入力したデータ）
        ee = notes.get("external_environment", {})
        if ee:
            mkt = ee.get("market_overview", {})
            forces = ee.get("five_forces", {})
            comps_raw = ee.get("competitors", [])

            # PESTからトレンド・機会・脅威を抽出
            pest = ee.get("pest", {})
            key_trends = list(mkt.get("key_trends", []))
            opp_items, threat_items = [], []
            for cat_rows in pest.values():
                for row in (cat_rows or []):
                    fact = row.get("事実・観察事項", "")
                    if not fact:
                        continue
                    t = row.get("機会/脅威", "機会")
                    if t == "機会":
                        opp_items.append(fact)
                    elif t == "脅威":
                        threat_items.append(fact)

            comp_names = [
                f"{c.get('name','')}（シェア{c.get('share','')}）" if c.get("share") else c.get("name","")
                for c in comps_raw if c.get("name")
            ]

            # 5フォースの総合評価
            ci = forces.get("overall_attractiveness", "")

            # PEST サマリーテキスト
            pestle_parts = []
            for cat_key in ("political", "economic", "social", "technological", "environmental", "legal"):
                rows = [r for r in pest.get(cat_key, []) if r.get("事実・観察事項")]
                if rows:
                    pestle_parts.append(
                        f"{cat_key}: " + "; ".join(r["事実・観察事項"] for r in rows[:2])
                    )

            self.external = ExternalEnvironment(
                market_size=mkt.get("size", ""),
                market_growth=mkt.get("growth_rate", ""),
                key_trends=key_trends + opp_items[:3],
                competitors=comp_names,
                pestle_summary="\n".join(pestle_parts),
                competitive_intensity=ci,
                raw=ee,
            )

        # SWOT（手動入力・AI生成保存分）— strategy_run より優先
        sm = notes.get("swot_manual", {})
        if sm.get("strengths") or sm.get("weaknesses"):
            self.swot = SWOTResult(
                strengths=_to_list(sm.get("strengths")),
                weaknesses=_to_list(sm.get("weaknesses")),
                opportunities=_to_list(sm.get("opportunities")),
                threats=_to_list(sm.get("threats")),
                so_strategies=[sm.get("so_strategy", "")] if sm.get("so_strategy") else [],
                st_strategies=[sm.get("st_strategy", "")] if sm.get("st_strategy") else [],
                wo_strategies=[sm.get("wo_strategy", "")] if sm.get("wo_strategy") else [],
                wt_strategies=[sm.get("wt_strategy", "")] if sm.get("wt_strategy") else [],
            )

    def _load_financial_data(self):
        """datasets / dataset_versions から財務データを読む。"""
        try:
            from core.repos.dataset_repo import DatasetRepo
            repo = DatasetRepo()
            v = repo.get_current_dataset_version(self.client_id, "financial")
            if not v:
                return
            data = v.get("normalized_json") or {}
            if isinstance(data, str):
                data = json.loads(data)

            snap = FinancialSnapshot(raw=data)

            # 主要指標を抽出（CSVフォーマットは年度ごとのリスト想定）
            records = data.get("records", []) or (data if isinstance(data, list) else [])
            if records:
                latest = records[-1] if isinstance(records, list) else {}
                snap.revenue = _safe_float(latest.get("売上") or latest.get("revenue") or latest.get("売上高"))
                snap.operating_profit = _safe_float(latest.get("営業利益") or latest.get("operating_profit"))
                snap.net_profit = _safe_float(latest.get("当期純利益") or latest.get("net_income"))
                snap.total_assets = _safe_float(latest.get("総資産") or latest.get("total_assets"))
                snap.equity = _safe_float(latest.get("純資産") or latest.get("equity"))
                snap.years = [r.get("年度") or r.get("year") for r in records if r.get("年度") or r.get("year")]
                # 計算
                if snap.revenue and snap.operating_profit:
                    snap.operating_margin = round(snap.operating_profit / snap.revenue * 100, 1)
                if snap.net_profit and snap.total_assets and snap.total_assets > 0:
                    snap.roa = round(snap.net_profit / snap.total_assets * 100, 1)
            self.financial = snap
        except Exception as e:
            logger.debug("Financial load failed: %s", e)

    def _load_strategy_run(self):
        """strategy_runs から SWOT・真因・戦略仮説・外部環境・内部能力を読む。"""
        try:
            from core.repos.strategy_run_repo import StrategyRunRepo
            repo = StrategyRunRepo()
            run = repo.get_current_strategy_run(self.client_id)
            if not run:
                return

            pkg = run.get("final_strategy_package_json") or {}
            if isinstance(pkg, str):
                pkg = json.loads(pkg)

            # 外部環境（notes由来のデータが既にある場合はスキップ）
            mkt = pkg.get("market_structure") or {}
            if mkt and self.external is None:
                self.external = ExternalEnvironment(
                    market_size=str(mkt.get("market_size_tam", "")),
                    market_growth=str(mkt.get("market_growth_rate", "")),
                    key_trends=_to_list(mkt.get("key_trends")),
                    competitors=_parse_competitors(mkt.get("competitors", [])),
                    pestle_summary=_dict_to_text(mkt.get("pestle_analysis", {})),
                    competitive_intensity=str(mkt.get("competitive_intensity", "")),
                    raw=mkt,
                )

            # 内部能力
            cap = pkg.get("internal_capability") or {}
            if cap:
                self.internal = InternalCapability(
                    strengths=_to_list(cap.get("strengths")),
                    weaknesses=_to_list(cap.get("weaknesses")),
                    core_competencies=_to_list(cap.get("core_competencies")),
                    resource_gaps=_to_list(cap.get("resource_gaps")),
                    raw=cap,
                )

            # SWOT
            swot = pkg.get("swot") or {}
            if swot and self.swot is None:
                self.swot = SWOTResult(
                    strengths=_to_list(swot.get("strengths")),
                    weaknesses=_to_list(swot.get("weaknesses")),
                    opportunities=_to_list(swot.get("opportunities")),
                    threats=_to_list(swot.get("threats")),
                    so_strategies=_to_list(swot.get("so_strategies")),
                    st_strategies=_to_list(swot.get("st_strategies")),
                    wo_strategies=_to_list(swot.get("wo_strategies")),
                    wt_strategies=_to_list(swot.get("wt_strategies")),
                )

            # 真因分析
            issue = pkg.get("issue_tree") or pkg.get("root_cause") or {}
            if issue:
                self.root_cause = RootCause(
                    root_issue=issue.get("root_issue"),
                    primary_symptom=issue.get("primary_symptom"),
                    likely_root_causes=_to_list(issue.get("likely_root_causes")),
                )

            # 戦略仮説
            opts = pkg.get("strategy_options") or {}
            if opts:
                options_list = opts.get("options", []) if isinstance(opts, dict) else []
                rec_idx = opts.get("recommended_option_index", 0) if isinstance(opts, dict) else 0
                selected = options_list[rec_idx] if options_list and rec_idx < len(options_list) else {}
                self.strategy = StrategyHypothesis(
                    selected_strategy_name=selected.get("name"),
                    selected_strategy_description=selected.get("description"),
                    selected_strategy_rationale=selected.get("rationale"),
                    all_options=[o.get("name", "") for o in options_list],
                    context_summary=opts.get("selected_context_summary") if isinstance(opts, dict) else None,
                )

        except Exception as e:
            logger.debug("Strategy run load failed: %s", e)

    # ----------------------------------------------------------------
    def to_prompt_text(self, scope: str = "full") -> str:
        """
        AIシステムプロンプトに注入するコンテキスト文字列を生成する。

        Args:
            scope: "full" | "financial_only" | "strategy_only" | "vision_only"
        """
        if not self.company_name:
            return ""

        lines = [
            "",
            "═══════════════════════════════════════════",
            "【プロジェクトコンテキスト（自動注入）】",
            f"企業名: {self.company_name}",
            f"業種: {self.industry or '未設定'}",
            f"所在地: {self.location or '未設定'}",
            f"完了済みステップ: {sorted(self.completed_steps)}",
        ]

        # 財務データ
        if self.financial and scope in ("full", "financial_only"):
            f = self.financial
            lines += ["", "▼ 財務サマリー（最新年度）"]
            if f.revenue:
                lines.append(f"  売上高: {f.revenue:,.0f}百万円")
            if f.operating_profit:
                lines.append(f"  営業利益: {f.operating_profit:,.0f}百万円")
            if f.operating_margin is not None:
                lines.append(f"  営業利益率: {f.operating_margin}%")
            if f.roa is not None:
                lines.append(f"  ROA: {f.roa}%")
            if f.total_assets:
                lines.append(f"  総資産: {f.total_assets:,.0f}百万円")

        # 外部環境
        if self.external and scope in ("full", "strategy_only"):
            e = self.external
            lines += ["", "▼ 外部環境"]
            if e.market_size:
                lines.append(f"  市場規模: {e.market_size}")
            if e.market_growth:
                lines.append(f"  市場成長率: {e.market_growth}")
            if e.key_trends:
                lines.append(f"  主要トレンド: {'; '.join(str(t) for t in e.key_trends[:3])}")
            if e.competitors:
                lines.append(f"  主要競合: {', '.join(str(c) for c in e.competitors[:4])}")
            if e.competitive_intensity:
                lines.append(f"  競争強度: {e.competitive_intensity}")

        # 内部能力
        if self.internal and scope in ("full", "strategy_only"):
            i = self.internal
            lines += ["", "▼ 内部能力"]
            if i.strengths:
                lines.append(f"  強み: {'; '.join(str(s) for s in i.strengths[:3])}")
            if i.weaknesses:
                lines.append(f"  弱み: {'; '.join(str(w) for w in i.weaknesses[:3])}")

        # 理念・ビジョン
        if self.vision_mission and scope in ("full", "vision_only", "strategy_only"):
            vm = self.vision_mission
            lines += ["", "▼ 理念・ビジョン"]
            if vm.philosophy:
                lines.append(f"  経営理念: {vm.philosophy}")
            if vm.vision:
                lines.append(f"  ビジョン: {vm.vision}")
            if vm.mission:
                lines.append(f"  ミッション: {vm.mission}")

        # SWOT
        if self.swot and scope in ("full", "strategy_only"):
            s = self.swot
            lines += ["", "▼ SWOT分析"]
            if s.strengths:
                lines.append(f"  S（強み）: {'; '.join(str(x) for x in s.strengths[:2])}")
            if s.weaknesses:
                lines.append(f"  W（弱み）: {'; '.join(str(x) for x in s.weaknesses[:2])}")
            if s.opportunities:
                lines.append(f"  O（機会）: {'; '.join(str(x) for x in s.opportunities[:2])}")
            if s.threats:
                lines.append(f"  T（脅威）: {'; '.join(str(x) for x in s.threats[:2])}")

        # 真因分析
        if self.root_cause and scope in ("full", "strategy_only"):
            rc = self.root_cause
            lines += ["", "▼ 真因分析"]
            if rc.root_issue:
                lines.append(f"  主課題: {rc.root_issue}")
            if rc.primary_symptom:
                lines.append(f"  主症状: {rc.primary_symptom}")
            if rc.likely_root_causes:
                lines.append(f"  根本原因: {'; '.join(str(x) for x in rc.likely_root_causes[:3])}")

        # 戦略仮説
        if self.strategy and scope in ("full", "strategy_only"):
            st = self.strategy
            lines += ["", "▼ 全社戦略仮説（選定済み）"]
            if st.selected_strategy_name:
                lines.append(f"  戦略名: {st.selected_strategy_name}")
            if st.selected_strategy_description:
                lines.append(f"  内容: {st.selected_strategy_description[:150]}...")
            if st.selected_strategy_rationale:
                lines.append(f"  根拠: {st.selected_strategy_rationale[:150]}...")

        # ドメイン
        if self.domain and scope in ("full", "strategy_only"):
            d = self.domain
            lines += ["", "▼ 事業ドメイン"]
            if d.domain_statement:
                lines.append(f"  ドメイン文: {d.domain_statement}")
            if d.customer:
                lines.append(f"  顧客: {d.customer}")
            if d.value_prop:
                lines.append(f"  提供価値: {d.value_prop}")

        lines.append("═══════════════════════════════════════════")
        lines.append("上記のコンテキストを踏まえた上で回答・分析してください。")

        return "\n".join(lines)

    def to_summary_dict(self) -> dict:
        """UI表示用サマリー辞書を返す。"""
        return {
            "company": self.company_name,
            "industry": self.industry,
            "completed_steps": len(self.completed_steps),
            "has_financial": self.financial is not None,
            "has_external": self.external is not None,
            "has_internal": self.internal is not None,
            "has_vision": self.vision_mission is not None,
            "has_swot": self.swot is not None,
            "has_root_cause": self.root_cause is not None,
            "has_strategy": self.strategy is not None,
            "has_domain": self.domain is not None,
        }

    def available_context_label(self) -> str:
        """現在注入されるコンテキストの一覧を返す（UI表示用）。"""
        items = []
        if self.financial:
            items.append("財務データ")
        if self.external:
            items.append("外部環境")
        if self.internal:
            items.append("内部能力")
        if self.vision_mission and self.vision_mission.vision:
            items.append("理念・ビジョン")
        if self.swot:
            items.append("SWOT")
        if self.root_cause:
            items.append("真因分析")
        if self.strategy:
            items.append("戦略仮説")
        if self.domain:
            items.append("ドメイン")
        return "、".join(items) if items else "なし（基本情報のみ）"


# ------------------------------------------------------------------ #
#  ユーティリティ
# ------------------------------------------------------------------ #

def _safe_float(v) -> Optional[float]:
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def _to_list(v) -> list:
    if isinstance(v, list):
        return v
    if isinstance(v, str) and v:
        return [v]
    return []


def _parse_competitors(raw: list) -> list:
    """競合データをシンプルな文字列リストに変換。"""
    result = []
    for c in raw:
        if isinstance(c, dict):
            name = c.get("name", "")
            share = c.get("market_share", "")
            result.append(f"{name}（シェア{share}）" if share else name)
        elif isinstance(c, str):
            result.append(c)
    return result


def _dict_to_text(d: dict) -> str:
    if not d:
        return ""
    return "; ".join(f"{k}: {v}" for k, v in d.items() if v)
