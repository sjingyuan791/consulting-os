"""
DX Maturity Diagnostic Module for Consulting OS.
Evaluates digital transformation readiness across 5 dimensions.

DX成熟度診断モジュール:
- デジタル戦略
- デジタル人材
- デジタル基盤
- データ活用
- デジタル文化
"""
from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime


class MaturityLevel(int, Enum):
    """成熟度レベル（1-5）"""
    LEVEL_1 = 1  # 初期/未着手
    LEVEL_2 = 2  # 部分的/試行
    LEVEL_3 = 3  # 標準化/展開中
    LEVEL_4 = 4  # 最適化/定着 
    LEVEL_5 = 5  # 革新/先進


class DimensionScore(BaseModel):
    """評価軸スコア"""
    dimension: str
    dimension_ja: str
    score: int = Field(ge=1, le=5)
    level_description: str = Field(default="")
    strengths: List[str] = Field(default=[])
    gaps: List[str] = Field(default=[])
    recommendations: List[str] = Field(default=[])


class DXMaturityResult(BaseModel):
    """DX成熟度診断結果"""
    company_name: Optional[str] = None
    industry: str = Field(default="")
    assessment_date: str = Field(default_factory=lambda: datetime.now().isoformat()[:10])
    
    # 5軸評価
    digital_strategy: DimensionScore
    digital_talent: DimensionScore
    digital_infrastructure: DimensionScore
    data_utilization: DimensionScore
    digital_culture: DimensionScore
    
    # 総合評価
    overall_score: float = Field(default=0.0, ge=1.0, le=5.0)
    maturity_level: int = Field(default=1, ge=1, le=5)
    maturity_label: str = Field(default="")
    
    # ベンチマーク
    industry_average: float = Field(default=2.5)
    gap_vs_industry: float = Field(default=0.0)
    
    # 優先アクション
    priority_actions: List[str] = Field(default=[])
    quick_wins: List[str] = Field(default=[], description="即効性のある施策")
    
    # ロードマップ
    phase_1_actions: List[str] = Field(default=[], description="短期（3ヶ月）")
    phase_2_actions: List[str] = Field(default=[], description="中期（6ヶ月）")
    phase_3_actions: List[str] = Field(default=[], description="長期（12ヶ月）")
    
    sources: List[str] = Field(default=["経済産業省「DX推進指標」"])


class DXMaturityAnalyzer:
    """DX成熟度分析エンジン"""
    
    # レベル定義
    LEVEL_DEFINITIONS = {
        1: {"label": "初期段階", "description": "DXの必要性は認識しているが、具体的な取り組みは未着手"},
        2: {"label": "試行段階", "description": "一部の部門で試験的にデジタル化を実施"},
        3: {"label": "展開段階", "description": "全社的にデジタル化を推進、標準化が進行中"},
        4: {"label": "定着段階", "description": "デジタル活用が定着し、継続的な改善を実施"},
        5: {"label": "先進段階", "description": "デジタルを活用した事業変革・新規事業創出"}
    }
    
    # 業界別平均スコア
    INDUSTRY_AVERAGES = {
        "manufacturing": 2.3,
        "retail": 2.5,
        "it": 3.8,
        "services": 2.4,
        "healthcare": 2.2,
        "construction": 2.0,
        "restaurant": 2.1,
        "logistics": 2.4
    }
    
    # 評価項目
    ASSESSMENT_ITEMS = {
        "digital_strategy": {
            "name_ja": "デジタル戦略",
            "questions": [
                "経営戦略にDXが明確に位置づけられているか",
                "DX推進の責任者・体制が明確か",
                "DX投資の予算が確保されているか",
                "デジタルを活用した事業モデル変革のビジョンがあるか"
            ]
        },
        "digital_talent": {
            "name_ja": "デジタル人材",
            "questions": [
                "デジタルスキルを持つ人材が社内にいるか",
                "従業員のITリテラシー教育を実施しているか",
                "外部IT人材との連携体制があるか",
                "デジタル人材の採用・育成計画があるか"
            ]
        },
        "digital_infrastructure": {
            "name_ja": "デジタル基盤",
            "questions": [
                "業務システム(基幹系)が整備されているか",
                "クラウドサービスを活用しているか",
                "セキュリティ対策が実施されているか",
                "システム間のデータ連携ができているか"
            ]
        },
        "data_utilization": {
            "name_ja": "データ活用",
            "questions": [
                "業務データの収集・蓄積ができているか",
                "データに基づく意思決定を行っているか",
                "顧客データを分析・活用しているか",
                "予測分析・AIを活用しているか"
            ]
        },
        "digital_culture": {
            "name_ja": "デジタル文化",
            "questions": [
                "経営層がDX推進にコミットしているか",
                "失敗を許容するチャレンジ文化があるか",
                "部門間のデータ共有・連携ができているか",
                "継続的な改善・学習の仕組みがあるか"
            ]
        }
    }
    
    def assess(
        self,
        strategy_score: int,
        talent_score: int,
        infrastructure_score: int,
        data_score: int,
        culture_score: int,
        industry: str = "manufacturing",
        company_name: Optional[str] = None
    ) -> DXMaturityResult:
        """
        DX成熟度診断を実行。
        各スコアは1-5の整数。
        """
        
        # 各軸の詳細評価
        digital_strategy = self._evaluate_dimension(
            "digital_strategy", strategy_score
        )
        digital_talent = self._evaluate_dimension(
            "digital_talent", talent_score
        )
        digital_infrastructure = self._evaluate_dimension(
            "digital_infrastructure", infrastructure_score
        )
        data_utilization = self._evaluate_dimension(
            "data_utilization", data_score
        )
        digital_culture = self._evaluate_dimension(
            "digital_culture", culture_score
        )
        
        # 総合スコア（加重平均）
        weights = {
            "strategy": 0.25,
            "talent": 0.20,
            "infrastructure": 0.20,
            "data": 0.20,
            "culture": 0.15
        }
        
        overall_score = (
            strategy_score * weights["strategy"] +
            talent_score * weights["talent"] +
            infrastructure_score * weights["infrastructure"] +
            data_score * weights["data"] +
            culture_score * weights["culture"]
        )
        
        maturity_level = round(overall_score)
        maturity_label = self.LEVEL_DEFINITIONS[maturity_level]["label"]
        
        # 業界比較
        industry_avg = self.INDUSTRY_AVERAGES.get(industry.lower(), 2.5)
        gap = overall_score - industry_avg
        
        # 優先アクション生成
        priority_actions, quick_wins = self._generate_priority_actions(
            strategy_score, talent_score, infrastructure_score, 
            data_score, culture_score
        )
        
        # ロードマップ生成
        phase_1, phase_2, phase_3 = self._generate_roadmap(
            strategy_score, talent_score, infrastructure_score,
            data_score, culture_score
        )
        
        return DXMaturityResult(
            company_name=company_name,
            industry=industry,
            digital_strategy=digital_strategy,
            digital_talent=digital_talent,
            digital_infrastructure=digital_infrastructure,
            data_utilization=data_utilization,
            digital_culture=digital_culture,
            overall_score=overall_score,
            maturity_level=maturity_level,
            maturity_label=maturity_label,
            industry_average=industry_avg,
            gap_vs_industry=gap,
            priority_actions=priority_actions,
            quick_wins=quick_wins,
            phase_1_actions=phase_1,
            phase_2_actions=phase_2,
            phase_3_actions=phase_3
        )
    
    def _evaluate_dimension(
        self, 
        dimension: str, 
        score: int
    ) -> DimensionScore:
        """軸ごとの評価を生成"""
        
        config = self.ASSESSMENT_ITEMS.get(dimension, {})
        level_def = self.LEVEL_DEFINITIONS.get(score, self.LEVEL_DEFINITIONS[1])
        
        # スコアに応じた強み・ギャップ・推奨を生成
        strengths = []
        gaps = []
        recommendations = []
        
        if score >= 4:
            strengths.append(f"{config.get('name_ja', dimension)}は高いレベルで整備されています")
        elif score >= 3:
            strengths.append(f"{config.get('name_ja', dimension)}の基盤は整いつつあります")
            gaps.append("更なる高度化・最適化の余地があります")
        elif score >= 2:
            gaps.append(f"{config.get('name_ja', dimension)}はまだ試行段階です")
            recommendations.append(f"{config.get('name_ja', dimension)}の全社展開を推進してください")
        else:
            gaps.append(f"{config.get('name_ja', dimension)}は未着手の状態です")
            recommendations.append(f"まず{config.get('name_ja', dimension)}の基盤構築から着手してください")
        
        return DimensionScore(
            dimension=dimension,
            dimension_ja=config.get("name_ja", dimension),
            score=score,
            level_description=level_def["description"],
            strengths=strengths,
            gaps=gaps,
            recommendations=recommendations
        )
    
    def _generate_priority_actions(self, *scores) -> tuple[List[str], List[str]]:
        """優先アクションとクイックウィンを生成"""
        
        strategy, talent, infra, data, culture = scores
        priority_actions = []
        quick_wins = []
        
        # 最も低いスコアを特定
        min_score = min(scores)
        
        if strategy <= 2:
            priority_actions.append("【戦略】DX推進委員会の設置と責任者の任命")
            quick_wins.append("現状のIT投資・デジタル活用状況の棚卸し")
        
        if talent <= 2:
            priority_actions.append("【人材】ITベンダー/コンサルタントとの連携体制構築")
            quick_wins.append("全従業員向けITリテラシー研修の実施")
        
        if infra <= 2:
            priority_actions.append("【基盤】クラウド活用への移行計画策定")
            quick_wins.append("SaaSツール（Office365、Google Workspace等）の導入")
        
        if data <= 2:
            priority_actions.append("【データ】顧客・売上データの一元管理体制構築")
            quick_wins.append("Excelで管理しているデータのクラウド化")
        
        if culture <= 2:
            priority_actions.append("【文化】経営層によるDX推進メッセージの発信")
            quick_wins.append("デジタル活用の成功事例の社内共有")
        
        return priority_actions[:3], quick_wins[:3]
    
    def _generate_roadmap(self, *scores) -> tuple[List[str], List[str], List[str]]:
        """DXロードマップを生成"""
        
        strategy, talent, infra, data, culture = scores
        phase_1 = []  # 短期（3ヶ月）
        phase_2 = []  # 中期（6ヶ月）
        phase_3 = []  # 長期（12ヶ月）
        
        # Phase 1: 基盤整備
        phase_1.append("DX推進体制の構築（責任者・チーム編成）")
        phase_1.append("現状のIT資産・デジタル活用状況の棚卸し")
        phase_1.append("従業員向けDX意識調査の実施")
        
        # Phase 2: 展開
        if infra <= 2:
            phase_2.append("クラウドサービスへの移行")
        if data <= 2:
            phase_2.append("データ収集・分析基盤の構築")
        phase_2.append("パイロット部門でのデジタル化推進")
        
        # Phase 3: 高度化
        phase_3.append("全社展開と業務プロセス改革")
        phase_3.append("データ分析・AI活用の本格化")
        phase_3.append("デジタルを活用した新規サービス検討")
        
        return phase_1, phase_2, phase_3


def assess_dx_maturity(
    strategy_score: int,
    talent_score: int,
    infrastructure_score: int,
    data_score: int,
    culture_score: int,
    industry: str = "manufacturing",
    company_name: Optional[str] = None
) -> DXMaturityResult:
    """
    DX成熟度診断のファサード関数。
    
    Args:
        strategy_score: デジタル戦略スコア (1-5)
        talent_score: デジタル人材スコア (1-5)
        infrastructure_score: デジタル基盤スコア (1-5)
        data_score: データ活用スコア (1-5)
        culture_score: デジタル文化スコア (1-5)
        industry: 業種
        company_name: 企業名
    
    Returns:
        DXMaturityResult: 診断結果
    
    Example:
        >>> result = assess_dx_maturity(2, 2, 3, 2, 2, "manufacturing")
        >>> print(result.maturity_level)
        2
        >>> print(result.maturity_label)
        "試行段階"
    """
    analyzer = DXMaturityAnalyzer()
    return analyzer.assess(
        strategy_score=strategy_score,
        talent_score=talent_score,
        infrastructure_score=infrastructure_score,
        data_score=data_score,
        culture_score=culture_score,
        industry=industry,
        company_name=company_name
    )
