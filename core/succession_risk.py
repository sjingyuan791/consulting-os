"""
Business Succession Risk Assessment for SME.
Evaluates succession planning status and key-person dependencies.

中小企業向け事業承継リスク評価モジュール。
後継者状況、キーパーソン依存度、承継タイムラインを分析。
"""
from typing import List, Optional, Dict
from pydantic import BaseModel, Field
from enum import Enum
from datetime import date


class SuccessorStatus(str, Enum):
    """後継者状況"""
    IDENTIFIED_AND_TRAINED = "identified_and_trained"  # 後継者確定・育成中
    IDENTIFIED_NOT_TRAINED = "identified_not_trained"  # 後継者候補あり・未育成
    SEARCHING = "searching"  # 後継者探索中
    NONE = "none"  # 後継者なし
    UNDECIDED = "undecided"  # 未定


class SuccessionType(str, Enum):
    """承継形態"""
    FAMILY = "family"  # 親族内承継
    INTERNAL = "internal"  # 従業員承継（MBO含む）
    EXTERNAL = "external"  # 第三者承継（M&A）
    UNDECIDED = "undecided"


class RiskFactor(BaseModel):
    """リスク要因"""
    factor_name: str
    severity: str  # "high", "medium", "low"
    description: str
    mitigation: str
    score_impact: int  # リスクスコアへの影響（0-20）


class KeyPersonAnalysis(BaseModel):
    """キーパーソン分析"""
    owner_handles_sales: bool = Field(
        default=False, 
        description="オーナーが主要な営業を担当"
    )
    owner_handles_technical: bool = Field(
        default=False, 
        description="オーナーが主要な技術・製造を担当"
    )
    owner_handles_management: bool = Field(
        default=True, 
        description="オーナーが経営全般を担当"
    )
    key_customer_relationships: bool = Field(
        default=False, 
        description="オーナーが主要顧客との関係を独占"
    )
    dependency_score: float = Field(
        default=0.0, 
        ge=0.0, 
        le=1.0, 
        description="キーパーソン依存度スコア（0-1）"
    )


class SuccessionTimeline(BaseModel):
    """承継タイムライン"""
    owner_current_age: int
    target_retirement_age: int = Field(default=70)
    years_until_succession: int = Field(default=0)
    urgency_level: str = Field(default="medium")  # "critical", "high", "medium", "low"
    
    recommended_start_timing: str = Field(
        default="", 
        description="承継準備開始推奨時期"
    )


class SuccessionRiskAssessment(BaseModel):
    """事業承継リスク評価完全結果"""
    company_name: Optional[str] = None
    assessment_date: str = Field(default_factory=lambda: date.today().isoformat())
    
    # 基本情報
    owner_age: int
    successor_status: SuccessorStatus
    succession_type: SuccessionType
    
    # 分析結果
    key_person_analysis: KeyPersonAnalysis
    timeline: SuccessionTimeline
    
    # リスク評価
    risk_score: int = Field(
        default=0, 
        ge=0, 
        le=100, 
        description="総合リスクスコア（0=低リスク、100=高リスク）"
    )
    risk_factors: List[RiskFactor] = Field(default=[])
    
    # 推奨事項
    recommendations: List[str] = Field(default=[])
    immediate_actions: List[str] = Field(default=[], description="即座に着手すべきアクション")
    
    # 銀行目線
    banker_view: str = Field(default="", description="金融機関視点での評価")
    
    # 出典情報
    sources: List[str] = Field(default=["中小企業庁 事業承継ガイドライン 2024年版"])


class SuccessionRiskAnalyzer:
    """事業承継リスク分析エンジン"""
    
    # 年齢別緊急度マッピング
    AGE_URGENCY = {
        (0, 55): "low",
        (55, 60): "medium",
        (60, 65): "high",
        (65, 100): "critical"
    }
    
    def analyze(
        self,
        owner_age: int,
        successor_status: SuccessorStatus,
        succession_type: SuccessionType = SuccessionType.UNDECIDED,
        owner_handles_sales: bool = False,
        owner_handles_technical: bool = False,
        key_customer_relationships: bool = False,
        target_retirement_age: int = 70,
        company_name: Optional[str] = None
    ) -> SuccessionRiskAssessment:
        """
        事業承継リスク評価を実行。
        
        Args:
            owner_age: 経営者年齢
            successor_status: 後継者状況
            succession_type: 承継形態
            owner_handles_sales: オーナーが営業担当
            owner_handles_technical: オーナーが技術担当
            key_customer_relationships: オーナーが主要顧客関係保有
            target_retirement_age: 目標引退年齢
            company_name: 企業名
        
        Returns:
            SuccessionRiskAssessment: 完全な評価結果
        """
        # キーパーソン分析
        dependency_score = self._calculate_dependency_score(
            owner_handles_sales,
            owner_handles_technical,
            key_customer_relationships
        )
        
        key_person = KeyPersonAnalysis(
            owner_handles_sales=owner_handles_sales,
            owner_handles_technical=owner_handles_technical,
            key_customer_relationships=key_customer_relationships,
            dependency_score=dependency_score
        )
        
        # タイムライン分析
        years_until = max(0, target_retirement_age - owner_age)
        urgency = self._get_urgency_level(owner_age)
        
        timeline = SuccessionTimeline(
            owner_current_age=owner_age,
            target_retirement_age=target_retirement_age,
            years_until_succession=years_until,
            urgency_level=urgency,
            recommended_start_timing=self._get_recommended_timing(years_until, successor_status)
        )
        
        # リスク要因特定
        risk_factors = self._identify_risk_factors(
            owner_age, successor_status, succession_type, 
            dependency_score, years_until
        )
        
        # 総合リスクスコア計算
        risk_score = self._calculate_risk_score(
            owner_age, successor_status, dependency_score, years_until
        )
        
        # 推奨事項生成
        recommendations, immediate_actions = self._generate_recommendations(
            successor_status, succession_type, urgency, 
            dependency_score, years_until
        )
        
        # 銀行目線評価
        banker_view = self._generate_banker_view(
            risk_score, successor_status, years_until
        )
        
        return SuccessionRiskAssessment(
            company_name=company_name,
            owner_age=owner_age,
            successor_status=successor_status,
            succession_type=succession_type,
            key_person_analysis=key_person,
            timeline=timeline,
            risk_score=risk_score,
            risk_factors=risk_factors,
            recommendations=recommendations,
            immediate_actions=immediate_actions,
            banker_view=banker_view
        )
    
    def _calculate_dependency_score(
        self,
        handles_sales: bool,
        handles_technical: bool,
        key_customers: bool
    ) -> float:
        """キーパーソン依存度スコアを計算"""
        score = 0.3  # 基本スコア（経営全般）
        if handles_sales:
            score += 0.25
        if handles_technical:
            score += 0.20
        if key_customers:
            score += 0.25
        return min(1.0, score)
    
    def _get_urgency_level(self, age: int) -> str:
        """年齢から緊急度を決定"""
        for (min_age, max_age), level in self.AGE_URGENCY.items():
            if min_age <= age < max_age:
                return level
        return "critical"
    
    def _get_recommended_timing(
        self, 
        years_until: int, 
        status: SuccessorStatus
    ) -> str:
        """推奨開始タイミングを決定"""
        if status == SuccessorStatus.NONE:
            return "今すぐ後継者探索を開始すべきです"
        elif status == SuccessorStatus.SEARCHING:
            return "早急に後継者を確定させる必要があります"
        elif status == SuccessorStatus.IDENTIFIED_NOT_TRAINED:
            if years_until <= 5:
                return "直ちに後継者育成プログラムを開始してください"
            else:
                return "1-2年以内に計画的な育成を開始してください"
        elif status == SuccessorStatus.IDENTIFIED_AND_TRAINED:
            if years_until <= 3:
                return "権限移譲と実務引継ぎを加速してください"
            else:
                return "計画通り進めてください"
        return "状況を確認し、専門家に相談することを推奨します"
    
    def _identify_risk_factors(
        self,
        owner_age: int,
        successor_status: SuccessorStatus,
        succession_type: SuccessionType,
        dependency_score: float,
        years_until: int
    ) -> List[RiskFactor]:
        """リスク要因を特定"""
        factors = []
        
        # 年齢リスク
        if owner_age >= 65:
            factors.append(RiskFactor(
                factor_name="経営者高齢化",
                severity="high" if owner_age >= 70 else "medium",
                description=f"経営者が{owner_age}歳であり、事業継続リスクが高い",
                mitigation="早急な承継計画の策定と実行",
                score_impact=20 if owner_age >= 70 else 15
            ))
        
        # 後継者不在リスク
        if successor_status == SuccessorStatus.NONE:
            factors.append(RiskFactor(
                factor_name="後継者不在",
                severity="critical",
                description="後継者が確定しておらず、事業継続の見通しが立たない",
                mitigation="M&A仲介会社への相談、従業員承継の検討",
                score_impact=25
            ))
        elif successor_status == SuccessorStatus.SEARCHING:
            factors.append(RiskFactor(
                factor_name="後継者未確定",
                severity="high",
                description="後継者候補を探索中だが確定していない",
                mitigation="候補者の絞り込みと意思確認の加速",
                score_impact=20
            ))
        
        # キーパーソン依存リスク
        if dependency_score > 0.7:
            factors.append(RiskFactor(
                factor_name="キーパーソン依存",
                severity="high",
                description=f"経営者への依存度が{dependency_score*100:.0f}%と高い",
                mitigation="権限委譲、ナンバー2の育成、業務の標準化",
                score_impact=18
            ))
        elif dependency_score > 0.5:
            factors.append(RiskFactor(
                factor_name="キーパーソン依存（中程度）",
                severity="medium",
                description=f"経営者への依存度が{dependency_score*100:.0f}%",
                mitigation="段階的な権限移譲の実施",
                score_impact=12
            ))
        
        # 準備期間不足リスク
        if years_until <= 3 and successor_status != SuccessorStatus.IDENTIFIED_AND_TRAINED:
            factors.append(RiskFactor(
                factor_name="準備期間不足",
                severity="high",
                description=f"目標引退まで{years_until}年しかなく、十分な準備期間がない",
                mitigation="引退時期の延長または承継プロセスの加速",
                score_impact=15
            ))
        
        return factors
    
    def _calculate_risk_score(
        self,
        owner_age: int,
        successor_status: SuccessorStatus,
        dependency_score: float,
        years_until: int
    ) -> int:
        """総合リスクスコアを計算（0-100）"""
        score = 0
        
        # 年齢要因（0-25点）
        if owner_age >= 70:
            score += 25
        elif owner_age >= 65:
            score += 20
        elif owner_age >= 60:
            score += 12
        elif owner_age >= 55:
            score += 5
        
        # 後継者状況要因（0-30点）
        successor_scores = {
            SuccessorStatus.IDENTIFIED_AND_TRAINED: 0,
            SuccessorStatus.IDENTIFIED_NOT_TRAINED: 10,
            SuccessorStatus.SEARCHING: 20,
            SuccessorStatus.UNDECIDED: 25,
            SuccessorStatus.NONE: 30
        }
        score += successor_scores.get(successor_status, 25)
        
        # キーパーソン依存要因（0-25点）
        score += int(dependency_score * 25)
        
        # 準備期間要因（0-20点）
        if years_until <= 2:
            score += 20
        elif years_until <= 5:
            score += 12
        elif years_until <= 10:
            score += 5
        
        return min(100, score)
    
    def _generate_recommendations(
        self,
        successor_status: SuccessorStatus,
        succession_type: SuccessionType,
        urgency: str,
        dependency_score: float,
        years_until: int
    ) -> tuple[List[str], List[str]]:
        """推奨事項と即座アクションを生成"""
        recommendations = []
        immediate_actions = []
        
        # 後継者状況に応じた推奨
        if successor_status == SuccessorStatus.NONE:
            immediate_actions.append(
                "【即座】事業承継・引継ぎ支援センターに相談（無料）"
            )
            immediate_actions.append(
                "【即座】M&A仲介会社への打診（企業価値算定）"
            )
            recommendations.append(
                "従業員承継（MBO/EBO）の可能性を検討してください"
            )
        elif successor_status == SuccessorStatus.SEARCHING:
            immediate_actions.append(
                "【今月中】後継者候補リストの作成と優先順位付け"
            )
            recommendations.append(
                "外部人材の招聘も視野に入れてください"
            )
        elif successor_status == SuccessorStatus.IDENTIFIED_NOT_TRAINED:
            immediate_actions.append(
                "【3ヶ月以内】後継者育成計画の策定"
            )
            recommendations.append(
                "後継者への段階的な権限移譲スケジュールを作成してください"
            )
        
        # キーパーソン依存対策
        if dependency_score > 0.5:
            recommendations.append(
                f"【キーパーソンリスク軽減】"
                f"経営者への依存度({dependency_score*100:.0f}%)を下げるため、"
                "マニュアル整備と権限委譲を進めてください【出典:中小企業庁ガイドライン】"
            )
        
        # 緊急度に応じた推奨
        if urgency == "critical":
            immediate_actions.append(
                "【緊急】顧問税理士・弁護士との承継計画策定ミーティング設定"
            )
        elif urgency == "high":
            recommendations.append(
                "1年以内に具体的な承継計画を策定してください"
            )
        
        return recommendations, immediate_actions
    
    def _generate_banker_view(
        self,
        risk_score: int,
        successor_status: SuccessorStatus,
        years_until: int
    ) -> str:
        """金融機関視点での評価"""
        comments = []
        
        if risk_score >= 70:
            comments.append(
                "事業承継リスクが高く、長期融資の審査において"
                "慎重な評価となる可能性があります。"
            )
        elif risk_score >= 50:
            comments.append(
                "事業承継リスクは中程度です。"
                "承継計画の策定状況について確認される可能性があります。"
            )
        else:
            comments.append(
                "事業承継リスクは低く、融資審査に大きな影響はありません。"
            )
        
        if successor_status in [SuccessorStatus.NONE, SuccessorStatus.UNDECIDED]:
            comments.append(
                "後継者未定は融資審査においてマイナス要因となります。"
            )
        
        if years_until <= 5 and successor_status != SuccessorStatus.IDENTIFIED_AND_TRAINED:
            comments.append(
                "経営者保証解除の観点からも、早期の後継者確定が推奨されます。"
            )
        
        return " ".join(comments)


def assess_succession_risk(
    owner_age: int,
    successor_status: str,  # "identified_and_trained", "none", etc.
    owner_handles_sales: bool = False,
    owner_handles_technical: bool = False,
    key_customer_relationships: bool = False,
    succession_type: str = "undecided",
    target_retirement_age: int = 70,
    company_name: Optional[str] = None
) -> SuccessionRiskAssessment:
    """
    事業承継リスク評価のファサード関数。
    
    Example:
        >>> result = assess_succession_risk(
        ...     owner_age=65,
        ...     successor_status="searching",
        ...     owner_handles_sales=True,
        ...     key_customer_relationships=True
        ... )
        >>> print(result.risk_score)
        72
    """
    analyzer = SuccessionRiskAnalyzer()
    return analyzer.analyze(
        owner_age=owner_age,
        successor_status=SuccessorStatus(successor_status),
        succession_type=SuccessionType(succession_type),
        owner_handles_sales=owner_handles_sales,
        owner_handles_technical=owner_handles_technical,
        key_customer_relationships=key_customer_relationships,
        target_retirement_age=target_retirement_age,
        company_name=company_name
    )
