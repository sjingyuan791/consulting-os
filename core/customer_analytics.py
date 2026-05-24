"""
Customer Analytics Module for Consulting OS.
Provides LTV, RFM, and customer segmentation analysis.

顧客分析モジュール:
- LTV（顧客生涯価値）分析
- RFM分析
- 顧客セグメンテーション
- 顧客ロイヤルティ分析
"""
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime, date
from collections import defaultdict


class RFMSegment(str, Enum):
    """RFMセグメント"""
    CHAMPIONS = "champions"          # 優良顧客
    LOYAL = "loyal"                  # ロイヤル顧客
    POTENTIAL = "potential"          # 有望顧客
    NEW = "new"                      # 新規顧客
    AT_RISK = "at_risk"             # 離反リスク
    HIBERNATING = "hibernating"      # 休眠顧客
    LOST = "lost"                    # 離反顧客


class CustomerRecord(BaseModel):
    """顧客レコード"""
    customer_id: str
    first_purchase_date: Optional[date] = None
    last_purchase_date: Optional[date] = None
    purchase_count: int = Field(default=0)
    total_revenue: float = Field(default=0.0, description="累計売上（円）")
    avg_order_value: float = Field(default=0.0, description="平均購入単価")


class RFMScore(BaseModel):
    """RFMスコア"""
    customer_id: str
    recency_score: int = Field(ge=1, le=5, description="最終購入日スコア")
    frequency_score: int = Field(ge=1, le=5, description="購入頻度スコア")
    monetary_score: int = Field(ge=1, le=5, description="購入金額スコア")
    total_score: int = Field(default=0)
    segment: RFMSegment = Field(default=RFMSegment.POTENTIAL)


class RFMAnalysisResult(BaseModel):
    """RFM分析結果"""
    analysis_date: str = Field(default_factory=lambda: datetime.now().isoformat()[:10])
    total_customers: int = Field(default=0)
    
    # セグメント別集計
    segment_counts: Dict[str, int] = Field(default={})
    segment_revenue: Dict[str, float] = Field(default={})
    segment_avg_value: Dict[str, float] = Field(default={})
    
    # 上位顧客
    top_customers: List[RFMScore] = Field(default=[])
    at_risk_customers: List[RFMScore] = Field(default=[])
    
    # 施策推奨
    recommendations: Dict[str, List[str]] = Field(default={})


class LTVResult(BaseModel):
    """LTV分析結果"""
    # 全体指標
    avg_ltv: float = Field(default=0.0, description="平均LTV（円）")
    median_ltv: float = Field(default=0.0)
    
    # 顧客獲得コスト対比
    cac_ltv_ratio: Optional[float] = None
    
    # セグメント別LTV
    segment_ltv: Dict[str, float] = Field(default={})
    
    # 期間別平均購入額
    year_1_value: float = Field(default=0.0)
    year_2_value: float = Field(default=0.0)
    year_3_value: float = Field(default=0.0)
    
    # 継続率
    retention_rate_year_1: float = Field(default=0.0)
    retention_rate_year_2: float = Field(default=0.0)
    
    # 予測LTV
    predicted_ltv_3yr: float = Field(default=0.0)
    predicted_ltv_5yr: float = Field(default=0.0)


class CustomerSegmentation(BaseModel):
    """顧客セグメンテーション結果"""
    segments: List[Dict[str, Any]] = Field(default=[])
    
    # セグメント定義
    segment_definitions: Dict[str, str] = Field(default={})
    
    # 各セグメントの特徴
    segment_profiles: Dict[str, Dict[str, Any]] = Field(default={})


class CustomerAnalyticsResult(BaseModel):
    """顧客分析総合結果"""
    company_name: Optional[str] = None
    analysis_date: str = Field(default_factory=lambda: datetime.now().isoformat()[:10])
    
    # 基本統計
    total_customers: int = Field(default=0)
    active_customers: int = Field(default=0)
    new_customers_ytd: int = Field(default=0)
    churned_customers_ytd: int = Field(default=0)
    
    # RFM分析
    rfm_analysis: RFMAnalysisResult
    
    # LTV分析
    ltv_analysis: LTVResult
    
    # 推奨アクション
    priority_actions: List[str] = Field(default=[])
    
    sources: List[str] = Field(default=[])


class CustomerAnalyzer:
    """顧客分析エンジン"""
    
    # RFMセグメント定義
    SEGMENT_RULES = {
        # (R, F, M) スコア範囲 -> セグメント
        "champions": {"r": (4, 5), "f": (4, 5), "m": (4, 5)},
        "loyal": {"r": (3, 5), "f": (3, 5), "m": (3, 5)},
        "potential": {"r": (3, 5), "f": (1, 3), "m": (1, 3)},
        "new": {"r": (4, 5), "f": (1, 1), "m": (1, 5)},
        "at_risk": {"r": (1, 3), "f": (3, 5), "m": (3, 5)},
        "hibernating": {"r": (1, 2), "f": (1, 3), "m": (1, 3)},
        "lost": {"r": (1, 1), "f": (1, 2), "m": (1, 2)}
    }
    
    SEGMENT_RECOMMENDATIONS = {
        "champions": [
            "VIPプログラムへの招待",
            "新商品の先行案内",
            "紹介プログラムの案内"
        ],
        "loyal": [
            "ロイヤルティプログラムの強化",
            "クロスセル施策",
            "定期購入のご案内"
        ],
        "potential": [
            "購買頻度向上施策",
            "関連商品のレコメンド",
            "期間限定オファー"
        ],
        "new": [
            "オンボーディング施策",
            "フォローアップメール",
            "2回目購入インセンティブ"
        ],
        "at_risk": [
            "リテンションキャンペーン（緊急）",
            "パーソナライズオファー",
            "アンケート・ヒアリング"
        ],
        "hibernating": [
            "再活性化キャンペーン",
            "特別割引オファー",
            "新商品情報の配信"
        ],
        "lost": [
            "ウィンバックキャンペーン",
            "大幅割引オファー",
            "リスト整理の検討"
        ]
    }
    
    def analyze_rfm(
        self,
        customers: List[CustomerRecord],
        reference_date: Optional[date] = None
    ) -> RFMAnalysisResult:
        """RFM分析を実行"""
        
        if not reference_date:
            reference_date = date.today()
        
        if not customers:
            return RFMAnalysisResult()
        
        # 各指標の分布を計算
        recencies = []
        frequencies = []
        monetaries = []
        
        for c in customers:
            if c.last_purchase_date:
                days_since = (reference_date - c.last_purchase_date).days
                recencies.append(days_since)
            frequencies.append(c.purchase_count)
            monetaries.append(c.total_revenue)
        
        # 五分位数を計算
        recency_quintiles = self._calculate_quintiles(recencies, reverse=True)
        frequency_quintiles = self._calculate_quintiles(frequencies)
        monetary_quintiles = self._calculate_quintiles(monetaries)
        
        # 各顧客にスコアを付与
        rfm_scores: List[RFMScore] = []
        segment_counts = defaultdict(int)
        segment_revenue = defaultdict(float)
        
        for c in customers:
            if c.last_purchase_date:
                days_since = (reference_date - c.last_purchase_date).days
                r_score = self._get_quintile_score(days_since, recency_quintiles, reverse=True)
            else:
                r_score = 1
            
            f_score = self._get_quintile_score(c.purchase_count, frequency_quintiles)
            m_score = self._get_quintile_score(c.total_revenue, monetary_quintiles)
            
            segment = self._determine_segment(r_score, f_score, m_score)
            
            score = RFMScore(
                customer_id=c.customer_id,
                recency_score=r_score,
                frequency_score=f_score,
                monetary_score=m_score,
                total_score=r_score + f_score + m_score,
                segment=segment
            )
            rfm_scores.append(score)
            
            segment_counts[segment.value] += 1
            segment_revenue[segment.value] += c.total_revenue
        
        # セグメント別平均
        segment_avg = {}
        for seg, count in segment_counts.items():
            if count > 0:
                segment_avg[seg] = segment_revenue[seg] / count
        
        # トップ顧客と離反リスク顧客
        top_customers = sorted(
            rfm_scores, 
            key=lambda x: x.total_score, 
            reverse=True
        )[:10]
        
        at_risk = [s for s in rfm_scores if s.segment == RFMSegment.AT_RISK][:10]
        
        return RFMAnalysisResult(
            total_customers=len(customers),
            segment_counts=dict(segment_counts),
            segment_revenue=dict(segment_revenue),
            segment_avg_value=segment_avg,
            top_customers=top_customers,
            at_risk_customers=at_risk,
            recommendations=self.SEGMENT_RECOMMENDATIONS
        )
    
    def analyze_ltv(
        self,
        customers: List[CustomerRecord],
        avg_customer_lifespan_years: float = 3.0,
        customer_acquisition_cost: Optional[float] = None
    ) -> LTVResult:
        """LTV分析を実行"""
        
        if not customers:
            return LTVResult()
        
        # 平均購入額と頻度から計算
        total_revenues = [c.total_revenue for c in customers]
        avg_revenue = sum(total_revenues) / len(total_revenues)
        median_revenue = sorted(total_revenues)[len(total_revenues) // 2]
        
        avg_order_values = [c.avg_order_value for c in customers if c.avg_order_value > 0]
        avg_order_value = sum(avg_order_values) / len(avg_order_values) if avg_order_values else 0
        
        purchase_counts = [c.purchase_count for c in customers if c.purchase_count > 0]
        avg_purchase_frequency = sum(purchase_counts) / len(purchase_counts) if purchase_counts else 0
        
        # 簡易LTV = 平均購入額 × 平均購入回数 × 顧客寿命（年）
        predicted_ltv_3yr = avg_order_value * avg_purchase_frequency * 3
        predicted_ltv_5yr = avg_order_value * avg_purchase_frequency * 5
        
        # CAC比率
        cac_ltv_ratio = None
        if customer_acquisition_cost and predicted_ltv_3yr > 0:
            cac_ltv_ratio = customer_acquisition_cost / predicted_ltv_3yr
        
        return LTVResult(
            avg_ltv=avg_revenue,
            median_ltv=median_revenue,
            cac_ltv_ratio=cac_ltv_ratio,
            predicted_ltv_3yr=predicted_ltv_3yr,
            predicted_ltv_5yr=predicted_ltv_5yr
        )
    
    def analyze(
        self,
        customers: List[CustomerRecord],
        company_name: Optional[str] = None,
        customer_acquisition_cost: Optional[float] = None
    ) -> CustomerAnalyticsResult:
        """総合顧客分析を実行"""
        
        reference_date = date.today()
        
        # アクティブ顧客（過去1年に購入）
        active = [
            c for c in customers 
            if c.last_purchase_date and (reference_date - c.last_purchase_date).days <= 365
        ]
        
        # RFM分析
        rfm_result = self.analyze_rfm(customers, reference_date)
        
        # LTV分析
        ltv_result = self.analyze_ltv(customers, 3.0, customer_acquisition_cost)
        
        # 優先アクション
        priority_actions = []
        
        at_risk_count = rfm_result.segment_counts.get("at_risk", 0)
        if at_risk_count > 0:
            priority_actions.append(
                f"【緊急】離反リスク顧客{at_risk_count}件へのリテンション施策"
            )
        
        champions_count = rfm_result.segment_counts.get("champions", 0)
        if champions_count > 0:
            priority_actions.append(
                f"優良顧客{champions_count}件へのVIPプログラム展開"
            )
        
        if ltv_result.cac_ltv_ratio and ltv_result.cac_ltv_ratio > 0.33:
            priority_actions.append(
                "CAC/LTV比率改善：獲得コスト削減またはLTV向上施策"
            )
        
        return CustomerAnalyticsResult(
            company_name=company_name,
            total_customers=len(customers),
            active_customers=len(active),
            rfm_analysis=rfm_result,
            ltv_analysis=ltv_result,
            priority_actions=priority_actions,
            sources=["顧客データ分析"]
        )
    
    def _calculate_quintiles(self, values: List[float], reverse: bool = False) -> List[float]:
        """五分位数を計算"""
        if not values:
            return [0, 0, 0, 0, 0]
        
        sorted_vals = sorted(values, reverse=reverse)
        n = len(sorted_vals)
        return [
            sorted_vals[int(n * 0.2)],
            sorted_vals[int(n * 0.4)],
            sorted_vals[int(n * 0.6)],
            sorted_vals[int(n * 0.8)],
            sorted_vals[-1]
        ]
    
    def _get_quintile_score(
        self, 
        value: float, 
        quintiles: List[float],
        reverse: bool = False
    ) -> int:
        """五分位数に基づきスコア（1-5）を返す"""
        if reverse:
            # Recency: 小さいほど良い
            if value <= quintiles[0]:
                return 5
            elif value <= quintiles[1]:
                return 4
            elif value <= quintiles[2]:
                return 3
            elif value <= quintiles[3]:
                return 2
            else:
                return 1
        else:
            # Frequency/Monetary: 大きいほど良い
            if value >= quintiles[3]:
                return 5
            elif value >= quintiles[2]:
                return 4
            elif value >= quintiles[1]:
                return 3
            elif value >= quintiles[0]:
                return 2
            else:
                return 1
    
    def _determine_segment(self, r: int, f: int, m: int) -> RFMSegment:
        """RFMスコアからセグメントを判定"""
        if r >= 4 and f >= 4 and m >= 4:
            return RFMSegment.CHAMPIONS
        elif r >= 3 and f >= 3 and m >= 3:
            return RFMSegment.LOYAL
        elif r >= 4 and f == 1:
            return RFMSegment.NEW
        elif r <= 2 and f >= 3:
            return RFMSegment.AT_RISK
        elif r <= 2 and f <= 2:
            return RFMSegment.HIBERNATING
        elif r == 1 and f <= 2 and m <= 2:
            return RFMSegment.LOST
        else:
            return RFMSegment.POTENTIAL


def analyze_customers(
    customers: List[Dict[str, Any]],
    company_name: Optional[str] = None,
    customer_acquisition_cost: Optional[float] = None
) -> CustomerAnalyticsResult:
    """
    顧客分析のファサード関数。
    
    Args:
        customers: 顧客レコードのリスト（dict形式）
            必須キー: customer_id, purchase_count, total_revenue
            オプション: last_purchase_date, avg_order_value
        company_name: 企業名
        customer_acquisition_cost: 顧客獲得コスト（円）
    
    Example:
        >>> customers = [
        ...     {"customer_id": "C001", "purchase_count": 5, "total_revenue": 50000,
        ...      "last_purchase_date": "2024-01-15", "avg_order_value": 10000},
        ...     {"customer_id": "C002", "purchase_count": 1, "total_revenue": 8000,
        ...      "last_purchase_date": "2023-06-01", "avg_order_value": 8000}
        ... ]
        >>> result = analyze_customers(customers)
        >>> print(result.rfm_analysis.segment_counts)
    """
    
    # dict -> CustomerRecord変換
    records = []
    for c in customers:
        last_date = None
        if "last_purchase_date" in c and c["last_purchase_date"]:
            if isinstance(c["last_purchase_date"], str):
                last_date = date.fromisoformat(c["last_purchase_date"])
            else:
                last_date = c["last_purchase_date"]
        
        first_date = None
        if "first_purchase_date" in c and c["first_purchase_date"]:
            if isinstance(c["first_purchase_date"], str):
                first_date = date.fromisoformat(c["first_purchase_date"])
            else:
                first_date = c["first_purchase_date"]
        
        records.append(CustomerRecord(
            customer_id=c.get("customer_id", ""),
            first_purchase_date=first_date,
            last_purchase_date=last_date,
            purchase_count=c.get("purchase_count", 0),
            total_revenue=c.get("total_revenue", 0),
            avg_order_value=c.get("avg_order_value", 0)
        ))
    
    analyzer = CustomerAnalyzer()
    return analyzer.analyze(
        customers=records,
        company_name=company_name,
        customer_acquisition_cost=customer_acquisition_cost
    )
