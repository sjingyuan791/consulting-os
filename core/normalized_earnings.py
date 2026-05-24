"""
Normalized Earnings Engine for Consulting OS.
Calculates normalized EBITDA and enterprise value for M&A DD and valuation.

正常収益力計算エンジン:
- EBITDA計算
- 正常化調整（一時的項目、役員報酬等）
- 企業価値評価（EV/EBITDAマルチプル）
- M&A DD用分析
"""
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from dataclasses import dataclass
from enum import Enum


# ==========================================
# データモデル
# ==========================================

class AdjustmentType(str, Enum):
    """調整項目タイプ"""
    ONE_TIME_INCOME = "one_time_income"         # 一時的収益（マイナス調整）
    ONE_TIME_EXPENSE = "one_time_expense"       # 一時的費用（プラス調整）
    EXCESS_COMPENSATION = "excess_compensation" # 過大役員報酬（プラス調整）
    RELATED_PARTY = "related_party"             # 関連当事者取引調整
    NON_OPERATING = "non_operating"             # 非経常項目
    CONTINGENT = "contingent"                   # 偶発債務引当


class EBITDAAdjustment(BaseModel):
    """EBITDA調整項目"""
    type: AdjustmentType
    description: str
    amount: float  # プラス=EBITDA増加、マイナス=減少
    evidence: str = ""  # 根拠


class NormalizedEarnings(BaseModel):
    """正常収益力"""
    year: int
    
    # 表面EBITDA
    revenue: float = 0
    operating_profit: float = 0
    depreciation: float = 0
    ebitda: float = Field(default=0, description="営業利益+減価償却費")
    ebitda_margin: float = Field(default=0, description="EBITDAマージン")
    
    # 調整項目
    adjustments: List[EBITDAAdjustment] = Field(default=[])
    total_adjustment: float = 0
    
    # 正常EBITDA
    normalized_ebitda: float = Field(default=0, description="調整後EBITDA")
    normalized_ebitda_margin: float = 0


class EnterpriseValuation(BaseModel):
    """企業価値評価"""
    # 収益ベース
    normalized_ebitda_avg: float = Field(default=0, description="正常EBITDA（平均）")
    multiple: float = Field(default=5.0, description="EV/EBITDAマルチプル")
    enterprise_value: float = Field(default=0, description="企業価値")
    
    # 純有利子負債
    total_debt: float = 0
    cash: float = 0
    net_debt: float = 0
    
    # 株式価値
    equity_value: float = 0
    
    # 感度分析
    ev_range_low: float = 0
    ev_range_high: float = 0
    
    # 評価コメント
    valuation_note: str = ""


class NormalizedEarningsOutput(BaseModel):
    """正常収益力分析出力"""
    years_analyzed: List[int] = []
    earnings_by_year: List[NormalizedEarnings] = []
    valuation: Optional[EnterpriseValuation] = None
    dd_findings: List[str] = []


# ==========================================
# 業種別マルチプル
# ==========================================

INDUSTRY_MULTIPLES = {
    "製造業": {"low": 4.0, "mid": 5.5, "high": 7.0},
    "卸売業": {"low": 3.5, "mid": 4.5, "high": 6.0},
    "小売業": {"low": 4.0, "mid": 5.0, "high": 6.5},
    "飲食業": {"low": 3.0, "mid": 4.0, "high": 5.5},
    "建設業": {"low": 3.5, "mid": 5.0, "high": 6.5},
    "IT・ソフトウェア": {"low": 6.0, "mid": 8.0, "high": 12.0},
    "医療・介護": {"low": 5.0, "mid": 7.0, "high": 9.0},
    "不動産": {"low": 6.0, "mid": 8.0, "high": 10.0},
    "運輸業": {"low": 4.0, "mid": 5.5, "high": 7.0},
    "サービス業": {"low": 4.5, "mid": 6.0, "high": 8.0},
    "その他": {"low": 4.0, "mid": 5.0, "high": 6.5},
}

# 役員報酬の業種別適正水準（万円/年）
REASONABLE_COMPENSATION = {
    "default": 12000000,  # 1,200万円
    "売上1億未満": 8000000,
    "売上1-5億": 15000000,
    "売上5-10億": 20000000,
    "売上10億以上": 30000000,
}


# ==========================================
# 正常収益力計算エンジン
# ==========================================

class NormalizedEarningsEngine:
    """正常収益力計算エンジン"""
    
    def analyze(
        self,
        financial_data: List[Dict[str, Any]],
        adjustments: Optional[List[Dict[str, Any]]] = None,
        industry: str = "その他"
    ) -> NormalizedEarningsOutput:
        """
        正常収益力を分析。
        
        Args:
            financial_data: 年度別財務データのリスト
            adjustments: ユーザー指定の調整項目
            industry: 業種（マルチプル選定用）
        
        Returns:
            NormalizedEarningsOutput
        """
        if not financial_data:
            return NormalizedEarningsOutput(dd_findings=["財務データなし"])
        
        earnings_list = []
        dd_findings = []
        
        for data in financial_data:
            year_earnings = self._calculate_year_earnings(data, adjustments)
            earnings_list.append(year_earnings)
            
            # DD発見事項を収集
            if year_earnings.total_adjustment != 0:
                dd_findings.append(
                    f"{year_earnings.year}年度: {abs(year_earnings.total_adjustment):,.0f}万円の調整あり"
                )
        
        # 企業価値評価
        valuation = self._calculate_valuation(
            earnings_list, 
            financial_data[-1] if financial_data else {},
            industry
        )
        
        return NormalizedEarningsOutput(
            years_analyzed=[e.year for e in earnings_list],
            earnings_by_year=earnings_list,
            valuation=valuation,
            dd_findings=dd_findings
        )
    
    def _calculate_year_earnings(
        self,
        data: Dict[str, Any],
        user_adjustments: Optional[List[Dict[str, Any]]] = None
    ) -> NormalizedEarnings:
        """1年分の正常収益力を計算"""
        
        year = int(data.get('year', data.get('年度', 0)))
        revenue = float(data.get('revenue', data.get('売上高', 0)))
        op = float(data.get('operating_profit', data.get('営業利益', 0)))
        depreciation = float(data.get('depreciation', data.get('減価償却費', 0)))
        
        # 表面EBITDA
        ebitda = op + depreciation
        ebitda_margin = ebitda / revenue if revenue > 0 else 0
        
        # 調整項目を収集
        adjustments = []
        
        # 1. 特別利益の除外
        special_income = float(data.get('special_income', data.get('特別利益', 0)))
        if special_income > 0:
            adjustments.append(EBITDAAdjustment(
                type=AdjustmentType.ONE_TIME_INCOME,
                description="特別利益の除外",
                amount=-special_income,
                evidence="PL特別利益"
            ))
        
        # 2. 特別損失の加算
        special_loss = float(data.get('special_loss', data.get('特別損失', 0)))
        if special_loss > 0:
            adjustments.append(EBITDAAdjustment(
                type=AdjustmentType.ONE_TIME_EXPENSE,
                description="特別損失の加算",
                amount=special_loss,
                evidence="PL特別損失"
            ))
        
        # 3. 役員報酬の調整
        exec_comp = float(data.get('executive_compensation', data.get('役員報酬', 0)))
        if exec_comp > 0:
            reasonable = self._get_reasonable_compensation(revenue)
            excess = max(0, exec_comp - reasonable)
            if excess > 0:
                adjustments.append(EBITDAAdjustment(
                    type=AdjustmentType.EXCESS_COMPENSATION,
                    description=f"過大役員報酬調整（適正水準{reasonable/10000:.0f}万円超過分）",
                    amount=excess,
                    evidence=f"役員報酬{exec_comp/10000:.0f}万円 vs 適正{reasonable/10000:.0f}万円"
                ))
        
        # 4. 未払残業代
        unpaid_overtime = float(data.get('unpaid_overtime', data.get('未払残業代', 0)))
        if unpaid_overtime > 0:
            adjustments.append(EBITDAAdjustment(
                type=AdjustmentType.CONTINGENT,
                description="未払残業代引当",
                amount=-unpaid_overtime,  # コストとして認識
                evidence="労務DD"
            ))
        
        # 5. ユーザー指定調整
        if user_adjustments:
            for adj in user_adjustments:
                if adj.get('year') == year or adj.get('year') is None:
                    adjustments.append(EBITDAAdjustment(
                        type=AdjustmentType(adj.get('type', 'non_operating')),
                        description=adj.get('description', '手動調整'),
                        amount=float(adj.get('amount', 0)),
                        evidence=adj.get('evidence', 'ユーザー入力')
                    ))
        
        # 調整合計
        total_adj = sum(a.amount for a in adjustments)
        normalized_ebitda = ebitda + total_adj
        normalized_margin = normalized_ebitda / revenue if revenue > 0 else 0
        
        return NormalizedEarnings(
            year=year,
            revenue=revenue,
            operating_profit=op,
            depreciation=depreciation,
            ebitda=ebitda,
            ebitda_margin=ebitda_margin,
            adjustments=adjustments,
            total_adjustment=total_adj,
            normalized_ebitda=normalized_ebitda,
            normalized_ebitda_margin=normalized_margin
        )
    
    def _get_reasonable_compensation(self, revenue: float) -> float:
        """売上規模に応じた適正役員報酬を返す"""
        if revenue < 100000000:  # 1億未満
            return 8000000
        elif revenue < 500000000:  # 5億未満
            return 15000000
        elif revenue < 1000000000:  # 10億未満
            return 20000000
        else:
            return 30000000
    
    def _calculate_valuation(
        self,
        earnings: List[NormalizedEarnings],
        latest_bs: Dict[str, Any],
        industry: str
    ) -> EnterpriseValuation:
        """企業価値を算定"""
        
        if not earnings:
            return EnterpriseValuation(valuation_note="データ不足")
        
        # 正常EBITDA平均（直近3年または全期間）
        recent = earnings[-3:] if len(earnings) >= 3 else earnings
        avg_ebitda = sum(e.normalized_ebitda for e in recent) / len(recent)
        
        # マルチプル取得
        multiples = INDUSTRY_MULTIPLES.get(industry, INDUSTRY_MULTIPLES["その他"])
        mid_multiple = multiples["mid"]
        
        # EV算定
        ev = avg_ebitda * mid_multiple
        ev_low = avg_ebitda * multiples["low"]
        ev_high = avg_ebitda * multiples["high"]
        
        # 純有利子負債
        def get_val(keys, default=0):
            for k in keys:
                if k in latest_bs:
                    return float(latest_bs[k])
            return default
        
        total_debt = (
            get_val(['short_term_debt', '短期借入金']) +
            get_val(['long_term_debt', '長期借入金']) +
            get_val(['interest_bearing_debt', '有利子負債合計'])
        )
        cash = get_val(['cash', '現預金', '現金及び預金'])
        net_debt = total_debt - cash
        
        # 株式価値
        equity_value = ev - net_debt
        
        # 評価コメント
        note_parts = [
            f"業種: {industry}",
            f"適用マルチプル: {mid_multiple:.1f}x（レンジ: {multiples['low']:.1f}x-{multiples['high']:.1f}x）",
            f"正常EBITDA（{len(recent)}年平均）: {avg_ebitda:,.0f}万円"
        ]
        
        return EnterpriseValuation(
            normalized_ebitda_avg=avg_ebitda,
            multiple=mid_multiple,
            enterprise_value=ev,
            total_debt=total_debt,
            cash=cash,
            net_debt=net_debt,
            equity_value=equity_value,
            ev_range_low=ev_low,
            ev_range_high=ev_high,
            valuation_note="。".join(note_parts)
        )


# ==========================================
# ファサード関数
# ==========================================

def calculate_normalized_ebitda(
    financial_data: List[Dict[str, Any]],
    industry: str = "その他",
    adjustments: Optional[List[Dict[str, Any]]] = None
) -> NormalizedEarningsOutput:
    """
    正常EBITDAを計算。
    
    Args:
        financial_data: 年度別財務データのリスト
        industry: 業種
        adjustments: 追加調整項目
    
    Returns:
        NormalizedEarningsOutput
    """
    engine = NormalizedEarningsEngine()
    return engine.analyze(financial_data, adjustments, industry)


def calculate_enterprise_value(
    financial_data: List[Dict[str, Any]],
    industry: str = "その他"
) -> Dict[str, Any]:
    """
    企業価値を算定。
    
    Returns:
        企業価値サマリー
    """
    result = calculate_normalized_ebitda(financial_data, industry)
    
    if not result.valuation:
        return {"error": "評価不可"}
    
    v = result.valuation
    return {
        "normalized_ebitda": v.normalized_ebitda_avg,
        "multiple": v.multiple,
        "enterprise_value": v.enterprise_value,
        "net_debt": v.net_debt,
        "equity_value": v.equity_value,
        "ev_range": f"{v.ev_range_low:,.0f} - {v.ev_range_high:,.0f}",
        "note": v.valuation_note
    }


def get_industry_multiples() -> Dict[str, Dict[str, float]]:
    """業種別マルチプル一覧を返す"""
    return INDUSTRY_MULTIPLES
