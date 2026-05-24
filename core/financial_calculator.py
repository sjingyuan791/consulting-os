"""
financial_calculator.py — 財務指標の純粋計算関数群。
GPT-4o 不使用。すべて決定論的な算術演算。
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional


# ------------------------------------------------------------------ #
#  ヘルパー
# ------------------------------------------------------------------ #

def _v(d: dict, key: str) -> float:
    """JSONB field dict から value を安全に取得する。"""
    raw = d.get(key, {})
    if isinstance(raw, dict):
        return float(raw.get("value") or 0)
    try:
        return float(raw or 0)
    except (TypeError, ValueError):
        return 0.0


def _safe_div(numerator: float, denominator: float, default: float = 0.0) -> float:
    if denominator == 0:
        return default
    return numerator / denominator


# ------------------------------------------------------------------ #
#  PL 指標
# ------------------------------------------------------------------ #

def calc_pl_ratios(pl: dict) -> dict:
    """
    PL フィールド辞書から主要比率を計算する。
    pl: {売上高: {value:...}, 売上原価: {value:...}, ...} 形式
    """
    revenue          = _v(pl, "revenue")
    cogs             = _v(pl, "cogs")
    gross_profit     = _v(pl, "gross_profit") or (revenue - cogs)
    sga              = _v(pl, "sga")
    operating_profit = _v(pl, "operating_profit") or (gross_profit - sga)
    ordinary_profit  = _v(pl, "ordinary_profit")
    net_profit       = _v(pl, "net_profit")
    depreciation     = _v(pl, "depreciation")

    return {
        "revenue":           revenue,
        "gross_profit":      gross_profit,
        "operating_profit":  operating_profit,
        "ordinary_profit":   ordinary_profit,
        "net_profit":        net_profit,
        "depreciation":      depreciation,
        "gross_margin":      round(_safe_div(gross_profit, revenue) * 100, 2),
        "operating_margin":  round(_safe_div(operating_profit, revenue) * 100, 2),
        "ordinary_margin":   round(_safe_div(ordinary_profit, revenue) * 100, 2),
        "net_margin":        round(_safe_div(net_profit, revenue) * 100, 2),
        "cogs_ratio":        round(_safe_div(cogs, revenue) * 100, 2),
        "sga_ratio":         round(_safe_div(sga, revenue) * 100, 2),
        "depreciation_ratio": round(_safe_div(depreciation, revenue) * 100, 2),
    }


# ------------------------------------------------------------------ #
#  BS 指標
# ------------------------------------------------------------------ #

def calc_bs_ratios(bs: dict, pl_ratios: dict) -> dict:
    """BS フィールド辞書から主要比率を計算する。"""
    cash             = _v(bs, "cash")
    receivables      = _v(bs, "receivables")
    inventory        = _v(bs, "inventory")
    current_assets   = _v(bs, "current_assets")
    fixed_assets     = _v(bs, "fixed_assets")
    total_assets     = _v(bs, "total_assets") or (current_assets + fixed_assets)
    payables         = _v(bs, "payables")
    short_term_loans = _v(bs, "short_term_loans")
    long_term_loans  = _v(bs, "long_term_loans")
    total_loans      = _v(bs, "total_loans") or (short_term_loans + long_term_loans)
    total_liabilities = _v(bs, "total_liabilities")
    equity           = _v(bs, "equity")

    revenue = pl_ratios.get("revenue", 0)
    monthly_revenue = _safe_div(revenue, 12)

    return {
        "cash":              cash,
        "receivables":       receivables,
        "inventory":         inventory,
        "total_assets":      total_assets,
        "total_loans":       total_loans,
        "equity":            equity,
        "equity_ratio":      round(_safe_div(equity, total_assets) * 100, 2),
        "current_ratio":     round(_safe_div(current_assets, _v(bs, "current_liabilities") or (total_liabilities - long_term_loans)) * 100, 2),
        "debt_ratio":        round(_safe_div(total_loans, total_assets) * 100, 2),
        "cash_months":       round(_safe_div(cash, monthly_revenue), 2) if monthly_revenue else 0,
    }


# ------------------------------------------------------------------ #
#  簡易 CF
# ------------------------------------------------------------------ #

def calc_simple_cf(
    net_profit: float,
    depreciation: float,
    total_annual_principal: float,
) -> dict:
    """
    簡易CF = 当期純利益 + 減価償却費 - 年間元金返済額合計
    """
    simple_cf = net_profit + depreciation - total_annual_principal
    return {
        "net_profit":            net_profit,
        "depreciation":          depreciation,
        "total_annual_principal": total_annual_principal,
        "simple_cf":             round(simple_cf, 2),
        "is_positive":           simple_cf >= 0,
    }


# ------------------------------------------------------------------ #
#  CCC（キャッシュ・コンバージョン・サイクル）
# ------------------------------------------------------------------ #

def calc_ccc(
    revenue: float,
    cogs: float,
    receivables: float,
    inventory: float,
    payables: float,
) -> dict:
    """CCC = 売掛金回収日数 + 在庫日数 - 買掛金支払日数"""
    daily_revenue = _safe_div(revenue, 365)
    daily_cogs    = _safe_div(cogs, 365)

    receivables_days = round(_safe_div(receivables, daily_revenue), 1) if daily_revenue else 0
    inventory_days   = round(_safe_div(inventory, daily_cogs), 1)      if daily_cogs else 0
    payables_days    = round(_safe_div(payables, daily_cogs), 1)        if daily_cogs else 0
    ccc              = receivables_days + inventory_days - payables_days

    return {
        "receivables_days": receivables_days,
        "inventory_days":   inventory_days,
        "payables_days":    payables_days,
        "ccc":              round(ccc, 1),
    }


# ------------------------------------------------------------------ #
#  損益分岐点（BEP）
# ------------------------------------------------------------------ #

def calc_bep(
    fixed_costs: float,
    gross_margin_rate: float,
    annual_principal: float = 0.0,
) -> dict:
    """
    BEP（通常）= 固定費 ÷ 粗利率
    BEP（返済込み）= (固定費 + 年間返済額) ÷ 粗利率
    """
    bep_standard   = round(_safe_div(fixed_costs, gross_margin_rate / 100), 0) if gross_margin_rate else 0
    bep_with_repay = round(_safe_div(fixed_costs + annual_principal, gross_margin_rate / 100), 0) if gross_margin_rate else 0

    return {
        "fixed_costs":     fixed_costs,
        "gross_margin_rate": gross_margin_rate,
        "bep_standard":    bep_standard,
        "bep_with_repay":  bep_with_repay,
    }


# ------------------------------------------------------------------ #
#  ROA ツリー分解
# ------------------------------------------------------------------ #

def calc_roa_tree(
    ordinary_profit: float,
    total_assets: float,
    revenue: float,
) -> dict:
    """ROA = 売上高利益率 × 総資産回転率"""
    roa              = _safe_div(ordinary_profit, total_assets) * 100
    profit_margin    = _safe_div(ordinary_profit, revenue) * 100
    asset_turnover   = _safe_div(revenue, total_assets)

    return {
        "roa":            round(roa, 2),
        "profit_margin":  round(profit_margin, 2),
        "asset_turnover": round(asset_turnover, 3),
        "ordinary_profit": ordinary_profit,
        "total_assets":   total_assets,
        "revenue":        revenue,
    }


# ------------------------------------------------------------------ #
#  平年化補正後利益
# ------------------------------------------------------------------ #

def calc_normalized_profit(
    ordinary_profit: float,
    adjustments: List[dict],
) -> dict:
    """
    採用済み補正を加減算した平年化補正後経常利益を計算する。
    adjustments: [{amount, adjustment_direction, adoption_status}, ...]
    """
    total_add_back = 0.0
    total_exclude  = 0.0
    applied = []

    for adj in adjustments:
        if adj.get("adoption_status") != "adopted":
            continue
        amount    = float(adj.get("amount") or 0)
        direction = adj.get("adjustment_direction", "")
        if direction == "add_back":
            total_add_back += amount
            applied.append({"item": adj.get("item_name", ""), "direction": "add_back", "amount": amount})
        elif direction == "exclude":
            total_exclude += amount
            applied.append({"item": adj.get("item_name", ""), "direction": "exclude", "amount": amount})

    normalized = ordinary_profit + total_add_back - total_exclude

    return {
        "original_ordinary_profit": ordinary_profit,
        "total_add_back":           total_add_back,
        "total_exclude":            total_exclude,
        "normalized_profit":        round(normalized, 2),
        "applied_adjustments":      applied,
    }


# ------------------------------------------------------------------ #
#  統合計算（1 年度分を一括処理）
# ------------------------------------------------------------------ #

def calc_all(
    pl: dict,
    bs: dict,
    loans: List[dict],
    adjustments: Optional[List[dict]] = None,
) -> dict:
    """
    1年度分のPL/BS/借入から全指標を一括計算する。
    pl/bs: fin_statements の pl/bs JSONB フィールド
    loans: fin_loans テーブルの行リスト
    adjustments: fin_adjustments テーブルの行リスト
    """
    pl_ratios = calc_pl_ratios(pl)
    bs_ratios = calc_bs_ratios(bs, pl_ratios)

    total_principal = sum(float(ln.get("annual_principal") or 0) for ln in loans)
    cf = calc_simple_cf(
        pl_ratios["net_profit"],
        pl_ratios["depreciation"],
        total_principal,
    )

    revenue  = pl_ratios["revenue"]
    cogs_raw = _v(pl, "cogs")
    ccc = calc_ccc(
        revenue,
        cogs_raw,
        _v(bs, "receivables"),
        _v(bs, "inventory"),
        _v(bs, "payables"),
    )

    gross_margin_rate = pl_ratios["gross_margin"]
    # 固定費 = 販管費 + 人件費（PLに含まれる場合）を近似: 販管費で代用
    sga = _v(pl, "sga")
    bep = calc_bep(sga, gross_margin_rate, total_principal)

    roa_tree = calc_roa_tree(
        pl_ratios["ordinary_profit"],
        bs_ratios["total_assets"],
        revenue,
    )

    normalized = calc_normalized_profit(
        pl_ratios["ordinary_profit"],
        adjustments or [],
    )

    return {
        "pl_ratios":       pl_ratios,
        "bs_ratios":       bs_ratios,
        "simple_cf":       cf,
        "ccc":             ccc,
        "bep":             bep,
        "roa_tree":        roa_tree,
        "normalized":      normalized,
        "total_annual_principal": total_principal,
    }
