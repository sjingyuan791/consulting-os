"""
Subsidy Matcher Module for Consulting OS.
Matches SME businesses with applicable government subsidies and grants.

補助金・助成金マッチングモジュール:
- 適用可能な補助金の自動マッチング
- 申請要件チェック
- 申請スケジュール管理
"""
from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime, date


class SubsidyCategory(str, Enum):
    """補助金カテゴリ"""
    EQUIPMENT = "equipment"         # 設備投資
    IT = "it"                       # IT導入
    INNOVATION = "innovation"       # 革新・研究開発
    RESTRUCTURE = "restructure"     # 事業再構築
    SUCCESSION = "succession"       # 事業承継
    EMPLOYMENT = "employment"       # 雇用
    SUSTAINABILITY = "sustainability"  # SDGs/環境


class SubsidyInfo(BaseModel):
    """補助金情報"""
    subsidy_id: str
    name: str
    category: SubsidyCategory
    
    # 金額
    max_amount: float = Field(description="上限金額（万円）")
    subsidy_rate: float = Field(default=0.5, description="補助率")
    
    # 対象
    target_industries: List[str] = Field(default=["全業種"])
    target_sizes: List[str] = Field(default=["中小企業"])
    
    # 要件
    requirements: List[str] = Field(default=[])
    excluded_cases: List[str] = Field(default=[])
    
    # 申請
    application_period: str = Field(default="")
    deadline: Optional[date] = None
    
    # 難易度
    difficulty: str = Field(default="中", description="申請難易度（低/中/高）")
    approval_rate: Optional[float] = None
    
    # 詳細
    official_url: str = Field(default="")
    notes: str = Field(default="")


class MatchResult(BaseModel):
    """マッチング結果"""
    subsidy: SubsidyInfo
    match_score: float = Field(ge=0.0, le=1.0, description="適合度")
    matched_requirements: List[str] = Field(default=[])
    unmet_requirements: List[str] = Field(default=[])
    recommendation: str = Field(default="")


class SubsidyMatchResult(BaseModel):
    """補助金マッチング全体結果"""
    company_name: Optional[str] = None
    assessment_date: str = Field(default_factory=lambda: datetime.now().isoformat()[:10])
    
    # マッチング結果
    high_match: List[MatchResult] = Field(default=[], description="高適合")
    medium_match: List[MatchResult] = Field(default=[], description="中適合")
    low_match: List[MatchResult] = Field(default=[], description="低適合")
    
    # 推奨
    top_recommendations: List[str] = Field(default=[])
    
    # 合計
    total_potential_amount: float = Field(default=0.0, description="獲得可能総額（万円）")
    
    # 次のアクション
    next_actions: List[str] = Field(default=[])


class SubsidyDatabase:
    """補助金データベース（2024年版）"""
    
    SUBSIDIES = [
        SubsidyInfo(
            subsidy_id="monozukuri_2024",
            name="ものづくり・商業・サービス生産性向上促進補助金",
            category=SubsidyCategory.EQUIPMENT,
            max_amount=3000,
            subsidy_rate=0.5,
            target_industries=["製造業", "商業", "サービス業"],
            target_sizes=["中小企業", "小規模事業者"],
            requirements=[
                "付加価値額年率3%以上向上",
                "給与支給総額年率1.5%以上向上",
                "事業場内最低賃金が地域別最低賃金＋30円以上"
            ],
            application_period="通年（複数回公募）",
            difficulty="中",
            approval_rate=0.45,
            official_url="https://portal.monodukuri-hojo.jp/",
            notes="省力化・自動化設備、DX関連投資に活用可能"
        ),
        SubsidyInfo(
            subsidy_id="jigyo_saikouchiku_2024",
            name="事業再構築補助金",
            category=SubsidyCategory.RESTRUCTURE,
            max_amount=15000,
            subsidy_rate=0.666,
            target_industries=["全業種"],
            target_sizes=["中小企業", "中堅企業"],
            requirements=[
                "売上高10%以上減少（コロナ前比較）",
                "事業再構築指針に沿った計画",
                "認定経営革新等支援機関と計画策定"
            ],
            application_period="2024年度公募予定",
            difficulty="高",
            approval_rate=0.35,
            official_url="https://jigyou-saikouchiku.go.jp/",
            notes="新分野展開、業態転換、事業再編に活用"
        ),
        SubsidyInfo(
            subsidy_id="it_hojo_2024",
            name="IT導入補助金",
            category=SubsidyCategory.IT,
            max_amount=450,
            subsidy_rate=0.5,
            target_industries=["全業種"],
            target_sizes=["中小企業", "小規模事業者"],
            requirements=[
                "IT導入支援事業者から購入",
                "生産性向上に資するITツール"
            ],
            application_period="通年（複数回公募）",
            difficulty="低",
            approval_rate=0.70,
            official_url="https://www.it-hojo.jp/",
            notes="会計ソフト、顧客管理、ECサイト構築等"
        ),
        SubsidyInfo(
            subsidy_id="shokibo_jizokuka_2024",
            name="小規模事業者持続化補助金",
            category=SubsidyCategory.EQUIPMENT,
            max_amount=200,
            subsidy_rate=0.666,
            target_industries=["全業種"],
            target_sizes=["小規模事業者"],
            requirements=[
                "商工会議所/商工会の支援を受けて計画策定",
                "販路開拓に取り組む"
            ],
            application_period="通年（複数回公募）",
            difficulty="低",
            approval_rate=0.60,
            official_url="https://www.shokokai.or.jp/",
            notes="広告宣伝、展示会出展、新商品開発等"
        ),
        SubsidyInfo(
            subsidy_id="jigyo_shoukei_2024",
            name="事業承継・引継ぎ補助金",
            category=SubsidyCategory.SUCCESSION,
            max_amount=600,
            subsidy_rate=0.666,
            target_industries=["全業種"],
            target_sizes=["中小企業", "小規模事業者"],
            requirements=[
                "事業承継（親族内、従業員、M&A）を実施",
                "経営革新等に取り組む"
            ],
            application_period="通年（複数回公募）",
            difficulty="中",
            approval_rate=0.55,
            official_url="https://jsh.go.jp/",
            notes="事業承継に伴う設備投資、販路開拓に活用"
        ),
        SubsidyInfo(
            subsidy_id="career_up_2024",
            name="キャリアアップ助成金",
            category=SubsidyCategory.EMPLOYMENT,
            max_amount=57,  # 正社員化コース1人当たり
            subsidy_rate=1.0,
            target_industries=["全業種"],
            target_sizes=["全企業"],
            requirements=[
                "非正規雇用労働者の正社員化",
                "キャリアアップ計画の策定"
            ],
            application_period="通年",
            difficulty="低",
            approval_rate=0.80,
            official_url="https://www.mhlw.go.jp/",
            notes="有期→正社員で57万円/人（中小企業）"
        ),
        SubsidyInfo(
            subsidy_id="green_2024",
            name="省エネ補助金（グリーン成長戦略）",
            category=SubsidyCategory.SUSTAINABILITY,
            max_amount=5000,
            subsidy_rate=0.5,
            target_industries=["製造業", "運輸業", "建設業"],
            target_sizes=["中小企業", "中堅企業"],
            requirements=[
                "省エネ効果が見込める設備投資",
                "CO2削減効果の定量化"
            ],
            application_period="不定期公募",
            difficulty="高",
            approval_rate=0.30,
            official_url="https://www.enecho.meti.go.jp/",
            notes="脱炭素設備への投資支援"
        )
    ]


class SubsidyMatcher:
    """補助金マッチングエンジン"""
    
    def __init__(self):
        self.database = SubsidyDatabase.SUBSIDIES
    
    def match(
        self,
        industry: str,
        company_size: str,  # "small", "medium", "large"
        annual_revenue: float,  # 百万円
        employee_count: int,
        investment_plans: List[str] = [],  # 投資計画カテゴリ
        has_revenue_decline: bool = False,
        is_succession_planned: bool = False,
        company_name: Optional[str] = None
    ) -> SubsidyMatchResult:
        """補助金マッチングを実行"""
        
        matched_results: List[MatchResult] = []
        
        for subsidy in self.database:
            score, matched_reqs, unmet_reqs = self._calculate_match_score(
                subsidy=subsidy,
                industry=industry,
                company_size=company_size,
                employee_count=employee_count,
                investment_plans=investment_plans,
                has_revenue_decline=has_revenue_decline,
                is_succession_planned=is_succession_planned
            )
            
            if score > 0:
                recommendation = self._generate_recommendation(subsidy, score)
                matched_results.append(MatchResult(
                    subsidy=subsidy,
                    match_score=score,
                    matched_requirements=matched_reqs,
                    unmet_requirements=unmet_reqs,
                    recommendation=recommendation
                ))
        
        # スコア順にソート
        matched_results.sort(key=lambda x: x.match_score, reverse=True)
        
        # 分類
        high_match = [r for r in matched_results if r.match_score >= 0.7]
        medium_match = [r for r in matched_results if 0.4 <= r.match_score < 0.7]
        low_match = [r for r in matched_results if r.match_score < 0.4]
        
        # 推奨
        top_recommendations = []
        for result in high_match[:3]:
            top_recommendations.append(
                f"【{result.subsidy.name}】最大{result.subsidy.max_amount:.0f}万円（適合度{result.match_score*100:.0f}%）"
            )
        
        # 獲得可能総額
        total_potential = sum(r.subsidy.max_amount for r in high_match)
        
        # 次のアクション
        next_actions = []
        if high_match:
            next_actions.append(f"{high_match[0].subsidy.name}の申請要件確認")
        if any(r.subsidy.category == SubsidyCategory.IT for r in high_match):
            next_actions.append("IT導入支援事業者の選定")
        if any(r.subsidy.category == SubsidyCategory.EQUIPMENT for r in matched_results):
            next_actions.append("商工会議所への相談")
        
        return SubsidyMatchResult(
            company_name=company_name,
            high_match=high_match,
            medium_match=medium_match,
            low_match=low_match,
            top_recommendations=top_recommendations,
            total_potential_amount=total_potential,
            next_actions=next_actions
        )
    
    def _calculate_match_score(
        self,
        subsidy: SubsidyInfo,
        industry: str,
        company_size: str,
        employee_count: int,
        investment_plans: List[str],
        has_revenue_decline: bool,
        is_succession_planned: bool
    ) -> tuple[float, List[str], List[str]]:
        """マッチングスコアを計算"""
        
        score = 0.0
        matched = []
        unmet = []
        
        # 業種チェック
        industry_ja = self._get_industry_ja(industry)
        if "全業種" in subsidy.target_industries or industry_ja in subsidy.target_industries:
            score += 0.3
            matched.append("対象業種")
        else:
            unmet.append("対象業種外")
            return 0, matched, unmet  # 業種外は除外
        
        # 企業規模チェック
        size_ja = "小規模事業者" if employee_count <= 20 else "中小企業"
        if size_ja in subsidy.target_sizes or "全企業" in subsidy.target_sizes:
            score += 0.2
            matched.append("対象規模")
        else:
            unmet.append("対象規模外")
        
        # カテゴリマッチ
        category_match = False
        if subsidy.category == SubsidyCategory.IT and "it" in investment_plans:
            category_match = True
        elif subsidy.category == SubsidyCategory.EQUIPMENT and "equipment" in investment_plans:
            category_match = True
        elif subsidy.category == SubsidyCategory.RESTRUCTURE and has_revenue_decline:
            category_match = True
        elif subsidy.category == SubsidyCategory.SUCCESSION and is_succession_planned:
            category_match = True
        elif subsidy.category == SubsidyCategory.EMPLOYMENT:
            category_match = True  # 雇用系は常にマッチ可能性あり
        
        if category_match:
            score += 0.3
            matched.append("投資計画との適合")
        
        # 難易度調整
        if subsidy.difficulty == "低":
            score += 0.1
        elif subsidy.difficulty == "高":
            score -= 0.05
        
        # 採択率調整
        if subsidy.approval_rate and subsidy.approval_rate >= 0.5:
            score += 0.1
        
        return min(1.0, max(0, score)), matched, unmet
    
    def _get_industry_ja(self, industry: str) -> str:
        mapping = {
            "manufacturing": "製造業",
            "retail": "小売業",
            "services": "サービス業",
            "it": "情報通信業",
            "construction": "建設業",
            "restaurant": "飲食業",
            "healthcare": "医療・介護"
        }
        return mapping.get(industry.lower(), industry)
    
    def _generate_recommendation(self, subsidy: SubsidyInfo, score: float) -> str:
        if score >= 0.7:
            return f"申請を強く推奨。{subsidy.notes}"
        elif score >= 0.4:
            return f"要件確認の上、検討推奨。{subsidy.notes}"
        else:
            return f"条件によっては適用可能。詳細確認を。"


def match_subsidies(
    industry: str,
    employee_count: int,
    annual_revenue: float,
    investment_plans: List[str] = [],
    has_revenue_decline: bool = False,
    is_succession_planned: bool = False,
    company_name: Optional[str] = None
) -> SubsidyMatchResult:
    """
    補助金マッチングのファサード関数。
    
    Args:
        industry: 業種（manufacturing, retail, etc.）
        employee_count: 従業員数
        annual_revenue: 年間売上高（百万円）
        investment_plans: 投資計画カテゴリ ["it", "equipment", "dx"]
        has_revenue_decline: 売上減少あり
        is_succession_planned: 事業承継予定あり
    
    Example:
        >>> result = match_subsidies(
        ...     industry="manufacturing",
        ...     employee_count=30,
        ...     annual_revenue=300,
        ...     investment_plans=["equipment", "it"]
        ... )
        >>> print(len(result.high_match))
    """
    matcher = SubsidyMatcher()
    company_size = "small" if employee_count <= 20 else "medium"
    
    return matcher.match(
        industry=industry,
        company_size=company_size,
        annual_revenue=annual_revenue,
        employee_count=employee_count,
        investment_plans=investment_plans,
        has_revenue_decline=has_revenue_decline,
        is_succession_planned=is_succession_planned,
        company_name=company_name
    )
