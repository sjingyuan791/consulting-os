"""
Strategic Analysis Frameworks for Consulting OS.
Implements Porter's 5 Forces, 3C Analysis, and PEST/PESTLE Analysis.

戦略フレームワーク実装:
- Porter's 5 Forces: 業界構造分析
- 3C Analysis: 市場・顧客・競合分析
- PEST/PESTLE: マクロ環境分析
- Value Chain: バリューチェーン分析
- VRIO: 経営資源評価
"""
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime


# ==========================================
# Porter's 5 Forces
# ==========================================

class ThreatLevel(str, Enum):
    """脅威レベル"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ForceAssessment(BaseModel):
    """1つの競争要因の評価"""
    level: ThreatLevel = Field(..., description="脅威レベル")
    score: int = Field(ge=1, le=5, description="スコア(1=低脅威, 5=高脅威)")
    key_factors: List[str] = Field(default=[], description="主要な要因")
    evidence: List[str] = Field(default=[], description="根拠となる事実")
    implications: str = Field(default="", description="戦略的含意")


class FiveForces(BaseModel):
    """Porter's 5 Forces分析結果"""
    industry: str = Field(..., description="対象業界")
    analysis_date: str = Field(default_factory=lambda: datetime.now().isoformat()[:10])
    
    # 5つの競争要因
    threat_of_new_entrants: ForceAssessment = Field(..., description="新規参入の脅威")
    bargaining_power_of_suppliers: ForceAssessment = Field(..., description="供給業者の交渉力")
    bargaining_power_of_buyers: ForceAssessment = Field(..., description="買い手の交渉力")
    threat_of_substitutes: ForceAssessment = Field(..., description="代替品の脅威")
    competitive_rivalry: ForceAssessment = Field(..., description="業界内競争")
    
    # 総合評価
    overall_attractiveness: str = Field(
        default="medium",
        description="業界魅力度: high/medium/low"
    )
    overall_score: float = Field(default=0.0, description="総合スコア(1-5)")
    
    strategic_recommendations: List[str] = Field(
        default=[], 
        description="戦略的推奨事項"
    )
    sources: List[str] = Field(default=["Porter, M.E. (1979) 'Competitive Strategy'"])

    # Error Handling Fields
    analysis_status: str = Field(default="success", description="success/failure")
    error_message: Optional[str] = Field(default=None, description="エラー詳細")
    
    def calculate_overall(self):
        """総合スコアを計算"""
        forces = [
            self.threat_of_new_entrants,
            self.bargaining_power_of_suppliers,
            self.bargaining_power_of_buyers,
            self.threat_of_substitutes,
            self.competitive_rivalry
        ]
        avg = sum(f.score for f in forces) / len(forces)
        self.overall_score = avg
        
        if avg >= 4.0:
            self.overall_attractiveness = "low"  # 高脅威 = 低魅力度
        elif avg >= 2.5:
            self.overall_attractiveness = "medium"
        else:
            self.overall_attractiveness = "high"


class FiveForcesAnalyzer:
    """
    Deprecated: This class uses hardcoded INDUSTRY_DEFAULTS.
    Please use core.framework_evaluator.FrameworkEvaluator for LLM-based analysis.
    """
    """5 Forces分析エンジン"""
    
    # 業界別デフォルト評価（AI分析の初期値として使用）
    INDUSTRY_DEFAULTS = {
        "manufacturing": {
            "new_entrants": 2,
            "suppliers": 3,
            "buyers": 3,
            "substitutes": 2,
            "rivalry": 4
        },
        "retail": {
            "new_entrants": 4,
            "suppliers": 2,
            "buyers": 4,
            "substitutes": 3,
            "rivalry": 5
        },
        "it": {
            "new_entrants": 3,
            "suppliers": 2,
            "buyers": 3,
            "substitutes": 4,
            "rivalry": 4
        },
        "restaurant": {
            "new_entrants": 5,
            "suppliers": 2,
            "buyers": 4,
            "substitutes": 4,
            "rivalry": 5
        },
        "healthcare": {
            "new_entrants": 2,
            "suppliers": 3,
            "buyers": 2,
            "substitutes": 2,
            "rivalry": 3
        }
    }
    
    def analyze(
        self,
        industry: str,
        custom_factors: Optional[Dict[str, Any]] = None
    ) -> FiveForces:
        """5 Forces分析を実行"""
        defaults = self.INDUSTRY_DEFAULTS.get(
            industry.lower(), 
            {"new_entrants": 3, "suppliers": 3, "buyers": 3, "substitutes": 3, "rivalry": 3}
        )
        
        if custom_factors:
            defaults.update(custom_factors)
        
        result = FiveForces(
            industry=industry,
            threat_of_new_entrants=ForceAssessment(
                level=self._score_to_level(defaults["new_entrants"]),
                score=defaults["new_entrants"],
                key_factors=self._get_new_entrants_factors(industry),
                implications="参入障壁の構築/強化が重要"
            ),
            bargaining_power_of_suppliers=ForceAssessment(
                level=self._score_to_level(defaults["suppliers"]),
                score=defaults["suppliers"],
                key_factors=["サプライヤー集中度", "スイッチングコスト", "代替供給源"],
                implications="サプライヤー多様化を検討"
            ),
            bargaining_power_of_buyers=ForceAssessment(
                level=self._score_to_level(defaults["buyers"]),
                score=defaults["buyers"],
                key_factors=["顧客集中度", "製品差別化", "スイッチングコスト"],
                implications="顧客ロックイン戦略が有効"
            ),
            threat_of_substitutes=ForceAssessment(
                level=self._score_to_level(defaults["substitutes"]),
                score=defaults["substitutes"],
                key_factors=["代替品の価格性能比", "スイッチングコスト", "顧客の代替傾向"],
                implications="付加価値向上で差別化"
            ),
            competitive_rivalry=ForceAssessment(
                level=self._score_to_level(defaults["rivalry"]),
                score=defaults["rivalry"],
                key_factors=["競合数", "成長率", "固定費比率", "差別化難易度"],
                implications="コスト優位性またはニッチ戦略"
            )
        )
        
        result.calculate_overall()
        result.strategic_recommendations = self._generate_recommendations(result)
        
        return result
    
    def _score_to_level(self, score: int) -> ThreatLevel:
        if score >= 4:
            return ThreatLevel.HIGH
        elif score >= 3:
            return ThreatLevel.MEDIUM
        return ThreatLevel.LOW
    
    def _get_new_entrants_factors(self, industry: str) -> List[str]:
        factors = {
            "manufacturing": ["設備投資", "規模の経済", "技術ノウハウ", "流通チャネル"],
            "retail": ["立地確保", "初期在庫", "ブランド認知", "EC参入容易性"],
            "it": ["技術力", "人材確保", "初期投資の低さ", "スケーラビリティ"],
            "restaurant": ["初期投資", "立地", "人材確保", "許認可"],
            "healthcare": ["資格・許認可", "設備投資", "信頼構築期間", "保険制度"]
        }
        return factors.get(industry.lower(), ["参入コスト", "規制", "ブランド"])
    
    def _generate_recommendations(self, analysis: FiveForces) -> List[str]:
        recs = []
        
        if analysis.threat_of_new_entrants.level == ThreatLevel.HIGH:
            recs.append("【新規参入対策】独自技術・ブランドによる参入障壁構築")
        
        if analysis.competitive_rivalry.level == ThreatLevel.HIGH:
            recs.append("【競争対策】差別化戦略またはニッチ市場への集中")
        
        if analysis.bargaining_power_of_buyers.level == ThreatLevel.HIGH:
            recs.append("【顧客対策】スイッチングコスト向上、顧客ロックイン施策")
        
        if analysis.overall_attractiveness == "low":
            recs.append("【業界魅力度低】事業ポートフォリオの見直し検討")
        
        return recs


# ==========================================
# 3C Analysis
# ==========================================

class CustomerAnalysis(BaseModel):
    """顧客分析"""
    target_segments: List[str] = Field(default=[], description="ターゲットセグメント")
    needs: List[str] = Field(default=[], description="主要ニーズ")
    pain_points: List[str] = Field(default=[], description="ペインポイント")
    buying_criteria: List[str] = Field(default=[], description="購買決定基準")
    market_size: Optional[str] = Field(default=None, description="市場規模")
    growth_rate: Optional[str] = Field(default=None, description="市場成長率")


class CompetitorProfile(BaseModel):
    """競合プロファイル"""
    name: str
    market_share: Optional[float] = None
    strengths: List[str] = Field(default=[])
    weaknesses: List[str] = Field(default=[])
    strategy: str = Field(default="")
    threat_level: ThreatLevel = Field(default=ThreatLevel.MEDIUM)


class CompanyAnalysis(BaseModel):
    """自社分析"""
    core_competencies: List[str] = Field(default=[], description="コアコンピタンス")
    strengths: List[str] = Field(default=[])
    weaknesses: List[str] = Field(default=[])
    resources: List[str] = Field(default=[], description="経営資源")
    capabilities: List[str] = Field(default=[], description="ケイパビリティ")


class ThreeCAnalysis(BaseModel):
    """3C分析結果"""
    analysis_date: str = Field(default_factory=lambda: datetime.now().isoformat()[:10])
    
    customer: CustomerAnalysis
    competitor: List[CompetitorProfile] = Field(default=[])
    company: CompanyAnalysis
    
    # KSF (Key Success Factors)
    key_success_factors: List[str] = Field(default=[], description="業界KSF")
    
    # 戦略的含意
    strategic_implications: List[str] = Field(default=[])
    sources: List[str] = Field(default=["大前研一 (1982) '企業参謀'"])


# ==========================================
# PEST/PESTLE Analysis
# ==========================================

class PESTFactor(BaseModel):
    """PEST要因"""
    factor: str = Field(..., description="要因名")
    description: str = Field(default="")
    impact: str = Field(default="medium", description="影響度: high/medium/low")
    trend: str = Field(default="stable", description="トレンド: improving/stable/worsening")
    timeframe: str = Field(default="", description="影響が顕在化する時期")
    opportunity_or_threat: str = Field(default="neutral", description="機会/脅威/中立")


class PESTLEAnalysis(BaseModel):
    """PESTLE分析結果"""
    target_market: str = Field(default="日本")
    analysis_date: str = Field(default_factory=lambda: datetime.now().isoformat()[:10])
    
    political: List[PESTFactor] = Field(default=[], description="政治的要因")
    economic: List[PESTFactor] = Field(default=[], description="経済的要因")
    social: List[PESTFactor] = Field(default=[], description="社会的要因")
    technological: List[PESTFactor] = Field(default=[], description="技術的要因")
    legal: List[PESTFactor] = Field(default=[], description="法的要因")
    environmental: List[PESTFactor] = Field(default=[], description="環境的要因")
    
    key_opportunities: List[str] = Field(default=[])
    key_threats: List[str] = Field(default=[])
    
    sources: List[str] = Field(default=[])
    
    # Error Handling Fields
    analysis_status: str = Field(default="success", description="success/failure")
    error_message: Optional[str] = Field(default=None, description="エラー詳細")


class PESTLEAnalyzer:
    """PESTLE分析エンジン"""
    
    # 日本市場のデフォルト要因（2024年版）
    JAPAN_DEFAULTS = {
        "political": [
            PESTFactor(
                factor="政権安定性",
                description="自民党政権の継続",
                impact="low",
                trend="stable"
            ),
            PESTFactor(
                factor="中小企業支援策",
                description="事業承継税制、ものづくり補助金等",
                impact="medium",
                trend="improving",
                opportunity_or_threat="opportunity"
            )
        ],
        "economic": [
            PESTFactor(
                factor="円安傾向",
                description="USD/JPY 150円前後",
                impact="high",
                trend="stable",
                opportunity_or_threat="threat"
            ),
            PESTFactor(
                factor="人件費上昇",
                description="最低賃金引上げ、人手不足",
                impact="high",
                trend="worsening",
                opportunity_or_threat="threat"
            ),
            PESTFactor(
                factor="インバウンド回復",
                description="訪日観光客増加",
                impact="medium",
                trend="improving",
                opportunity_or_threat="opportunity"
            )
        ],
        "social": [
            PESTFactor(
                factor="少子高齢化",
                description="労働人口減少、シニア市場拡大",
                impact="high",
                trend="worsening"
            ),
            PESTFactor(
                factor="働き方改革",
                description="リモートワーク定着、ワークライフバランス重視",
                impact="medium",
                trend="stable"
            )
        ],
        "technological": [
            PESTFactor(
                factor="生成AI普及",
                description="ChatGPT等の業務活用",
                impact="high",
                trend="improving",
                opportunity_or_threat="opportunity"
            ),
            PESTFactor(
                factor="DX推進",
                description="デジタル化投資増加",
                impact="high",
                trend="improving",
                opportunity_or_threat="opportunity"
            )
        ],
        "legal": [
            PESTFactor(
                factor="インボイス制度",
                description="適格請求書保存方式",
                impact="medium",
                trend="stable"
            ),
            PESTFactor(
                factor="個人情報保護強化",
                description="改正個人情報保護法",
                impact="medium",
                trend="stable"
            )
        ],
        "environmental": [
            PESTFactor(
                factor="カーボンニュートラル",
                description="2050年CN目標、脱炭素要請",
                impact="high",
                trend="worsening",
                timeframe="2030年以降本格化"
            ),
            PESTFactor(
                factor="サプライチェーンESG",
                description="取引先からのESG要請増加",
                impact="medium",
                trend="worsening"
            )
        ]
    }
    
    def analyze(
        self,
        target_market: str = "日本",
        industry: Optional[str] = None,
        custom_factors: Optional[Dict[str, List[PESTFactor]]] = None
    ) -> PESTLEAnalysis:
        """PESTLE分析を実行"""
        
        # デフォルト値を使用
        factors = self.JAPAN_DEFAULTS.copy()
        
        # カスタム要因があれば追加
        if custom_factors:
            for category, items in custom_factors.items():
                if category in factors:
                    factors[category].extend(items)
                else:
                    factors[category] = items
        
        result = PESTLEAnalysis(
            target_market=target_market,
            political=factors.get("political", []),
            economic=factors.get("economic", []),
            social=factors.get("social", []),
            technological=factors.get("technological", []),
            legal=factors.get("legal", []),
            environmental=factors.get("environmental", [])
        )
        
        # 機会と脅威を抽出
        all_factors = (
            result.political + result.economic + result.social +
            result.technological + result.legal + result.environmental
        )
        
        result.key_opportunities = [
            f.factor for f in all_factors 
            if f.opportunity_or_threat == "opportunity"
        ]
        result.key_threats = [
            f.factor for f in all_factors 
            if f.opportunity_or_threat == "threat"
        ]
        
        result.sources = [
            "内閣府「経済財政白書」2024年版",
            "経済産業省「通商白書」2024年版",
            "中小企業庁「中小企業白書」2024年版"
        ]
        
        return result


# ==========================================
# Value Chain Analysis
# ==========================================

class ValueChainActivity(BaseModel):
    """バリューチェーン活動"""
    activity_name: str
    description: str = ""
    cost_percentage: float = Field(default=0.0, description="総コストに占める割合")
    competitive_advantage: str = Field(
        default="neutral", 
        description="competitive/neutral/disadvantage"
    )
    improvement_potential: str = Field(default="medium", description="high/medium/low")
    key_issues: List[str] = Field(default=[])


class ValueChainAnalysis(BaseModel):
    """バリューチェーン分析"""
    
    # 主活動
    inbound_logistics: ValueChainActivity = Field(
        default=ValueChainActivity(activity_name="購買物流")
    )
    operations: ValueChainActivity = Field(
        default=ValueChainActivity(activity_name="製造/オペレーション")
    )
    outbound_logistics: ValueChainActivity = Field(
        default=ValueChainActivity(activity_name="出荷物流")
    )
    marketing_sales: ValueChainActivity = Field(
        default=ValueChainActivity(activity_name="マーケティング・営業")
    )
    service: ValueChainActivity = Field(
        default=ValueChainActivity(activity_name="サービス")
    )
    
    # 支援活動
    firm_infrastructure: ValueChainActivity = Field(
        default=ValueChainActivity(activity_name="全般管理")
    )
    human_resource_management: ValueChainActivity = Field(
        default=ValueChainActivity(activity_name="人事・労務管理")
    )
    technology_development: ValueChainActivity = Field(
        default=ValueChainActivity(activity_name="技術開発")
    )
    procurement: ValueChainActivity = Field(
        default=ValueChainActivity(activity_name="調達")
    )
    
    competitive_advantages: List[str] = Field(default=[])
    improvement_priorities: List[str] = Field(default=[])
    
    sources: List[str] = Field(default=["Porter, M.E. (1985) 'Competitive Advantage'"])


# ==========================================
# VRIO Analysis
# ==========================================

class VRIOResource(BaseModel):
    """VRIO評価対象リソース"""
    resource_name: str
    valuable: bool = Field(default=False, description="価値があるか")
    rare: bool = Field(default=False, description="希少か")
    imitable: bool = Field(default=False, description="模倣困難か")
    organized: bool = Field(default=False, description="組織的に活用できるか")
    
    @property
    def competitive_implication(self) -> str:
        """競争上の含意を返す"""
        if not self.valuable:
            return "競争劣位"
        if not self.rare:
            return "競争均衡"
        if not self.imitable:
            return "一時的競争優位"
        if not self.organized:
            return "未活用の潜在優位"
        return "持続的競争優位"


class VRIOAnalysis(BaseModel):
    """VRIO分析結果"""
    resources: List[VRIOResource] = Field(default=[])
    
    sustained_advantages: List[str] = Field(default=[], description="持続的優位性")
    temporary_advantages: List[str] = Field(default=[], description="一時的優位性")
    parity_resources: List[str] = Field(default=[], description="競争均衡リソース")
    
    strategic_recommendations: List[str] = Field(default=[])
    sources: List[str] = Field(default=["Barney, J.B. (1991) 'Firm Resources and Sustained Competitive Advantage'"])


# ==========================================
# Facade Functions
# ==========================================

def run_five_forces(industry: str) -> FiveForces:
    """5 Forces分析を実行"""
    analyzer = FiveForcesAnalyzer()
    return analyzer.analyze(industry)


def run_pestle(target_market: str = "日本", industry: Optional[str] = None) -> PESTLEAnalysis:
    """PESTLE分析を実行"""
    analyzer = PESTLEAnalyzer()
    return analyzer.analyze(target_market, industry)


def create_3c_template() -> ThreeCAnalysis:
    """3C分析テンプレートを生成"""
    return ThreeCAnalysis(
        customer=CustomerAnalysis(),
        competitor=[],
        company=CompanyAnalysis()
    )


def create_value_chain_template() -> ValueChainAnalysis:
    """バリューチェーン分析テンプレートを生成"""
    return ValueChainAnalysis()


def create_vrio_template(resources: List[str]) -> VRIOAnalysis:
    """VRIO分析テンプレートを生成"""
    return VRIOAnalysis(
        resources=[VRIOResource(resource_name=r) for r in resources]
    )
