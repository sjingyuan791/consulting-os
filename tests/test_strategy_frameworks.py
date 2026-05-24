"""
Test Strategy Frameworks.
戦略フレームワークのテスト（5Forces, 3C, PESTLE）
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.strategy_frameworks import (
    FiveForcesAnalyzer, FiveForces, ForceAssessment, ThreatLevel,
    CustomerAnalysis, CompetitorProfile, CompanyAnalysis, ThreeCAnalysis,
    PESTFactor, PESTLEAnalysis, PESTLEAnalyzer,
    run_five_forces, run_pestle, create_3c_template
)


class TestFiveForcesAnalyzer:
    """FiveForcesAnalyzer のテスト"""
    
    def test_analyzer_creation(self):
        """アナライザーの作成"""
        analyzer = FiveForcesAnalyzer()
        
        assert analyzer is not None
        assert hasattr(analyzer, 'INDUSTRY_DEFAULTS')
    
    def test_analyze_manufacturing(self):
        """製造業の分析"""
        analyzer = FiveForcesAnalyzer()
        
        result = analyzer.analyze(industry="manufacturing")
        
        assert isinstance(result, FiveForces)
        assert result.industry == "manufacturing"
        assert result.threat_of_new_entrants is not None
        assert result.bargaining_power_of_suppliers is not None
        assert result.bargaining_power_of_buyers is not None
        assert result.threat_of_substitutes is not None
        assert result.competitive_rivalry is not None
    
    def test_analyze_retail(self):
        """小売業の分析"""
        analyzer = FiveForcesAnalyzer()
        
        result = analyzer.analyze(industry="retail")
        
        assert isinstance(result, FiveForces)
        assert result.industry == "retail"
    
    def test_analyze_with_custom_factors(self):
        """カスタム要因での分析"""
        analyzer = FiveForcesAnalyzer()
        
        custom = {
            "new_entrants": 4,
            "suppliers": 2,
        }
        
        result = analyzer.analyze(industry="manufacturing", custom_factors=custom)
        
        # カスタム値が反映される
        assert result.threat_of_new_entrants.score == 4
        assert result.bargaining_power_of_suppliers.score == 2
    
    def test_overall_score_calculation(self):
        """総合スコアの計算"""
        analyzer = FiveForcesAnalyzer()
        
        result = analyzer.analyze(industry="manufacturing")
        
        # calculate_overallが呼ばれてスコアが設定されている
        assert result.overall_score > 0
        # 総合スコアは1-5の範囲
        assert 1 <= result.overall_score <= 5
    
    def test_recommendations_generated(self):
        """推奨事項の生成"""
        analyzer = FiveForcesAnalyzer()
        
        result = analyzer.analyze(industry="manufacturing")
        
        # 推奨事項が生成される
        assert isinstance(result.strategic_recommendations, list)


class TestForceAssessment:
    """ForceAssessment モデルのテスト"""
    
    def test_force_assessment_creation(self):
        """評価モデルの作成"""
        assessment = ForceAssessment(
            level=ThreatLevel.HIGH,
            score=4,
            key_factors=["参入障壁が低い", "資本要件が小さい"],
            evidence=["新規参入企業3社"],
            implications="差別化戦略が必要"
        )
        
        assert assessment.level == ThreatLevel.HIGH
        assert assessment.score == 4
        assert len(assessment.key_factors) == 2
    
    def test_threat_levels(self):
        """脅威レベルの列挙"""
        assert ThreatLevel.HIGH == "high"
        assert ThreatLevel.MEDIUM == "medium"
        assert ThreatLevel.LOW == "low"


class TestThreeCAnalysis:
    """3C分析のテスト"""
    
    def test_customer_analysis_model(self):
        """顧客分析モデル"""
        customer = CustomerAnalysis(
            target_segments=["中小企業", "スタートアップ"],
            needs=["コスト削減", "効率化"],
            buying_criteria=["価格", "サポート"],
            market_size="1兆円"
        )
        
        assert len(customer.target_segments) == 2
        assert customer.market_size == "1兆円"
    
    def test_competitor_profile_model(self):
        """競合プロファイルモデル"""
        competitor = CompetitorProfile(
            name="競合A社",
            market_share=0.25,
            strengths=["ブランド力", "販売網"],
            weaknesses=["価格が高い"],
            strategy="差別化戦略",
            threat_level=ThreatLevel.HIGH
        )
        
        assert competitor.name == "競合A社"
        assert competitor.market_share == 0.25
        assert competitor.threat_level == ThreatLevel.HIGH
    
    def test_company_analysis_model(self):
        """自社分析モデル"""
        company = CompanyAnalysis(
            core_competencies=["技術力", "顧客サービス"],
            strengths=["品質が高い"],
            weaknesses=["認知度が低い"],
            resources=["熟練エンジニア", "特許"],
            capabilities=["カスタマイズ対応"]
        )
        
        assert len(company.core_competencies) == 2
        assert "品質が高い" in company.strengths
    
    def test_three_c_template_creation(self):
        """3Cテンプレート作成"""
        analysis = create_3c_template()
        
        assert isinstance(analysis, ThreeCAnalysis)
        assert analysis.customer is not None
        assert analysis.company is not None


class TestPESTLEAnalysis:
    """PESTLE分析のテスト"""
    
    def test_pest_factor_model(self):
        """PEST要因モデル"""
        factor = PESTFactor(
            factor="少子高齢化",
            description="労働人口の減少",
            impact="high",
            trend="worsening",
            timeframe="2025-2030",
            opportunity_or_threat="threat"
        )
        
        assert factor.factor == "少子高齢化"
        assert factor.impact == "high"
        assert factor.opportunity_or_threat == "threat"
    
    def test_pestle_analyzer(self):
        """PESTLEアナライザー"""
        analyzer = PESTLEAnalyzer()
        
        result = analyzer.analyze(target_market="日本")
        
        assert isinstance(result, PESTLEAnalysis)
        assert len(result.political) > 0
        assert len(result.economic) > 0
    
    def test_pestle_facade_function(self):
        """PESTLE関数"""
        result = run_pestle(target_market="日本")
        
        assert isinstance(result, PESTLEAnalysis)
        assert result.target_market == "日本"


class TestFacadeFunctions:
    """ファサード関数のテスト"""
    
    def test_run_five_forces(self):
        """run_five_forces関数"""
        result = run_five_forces("manufacturing")
        
        assert isinstance(result, FiveForces)
        assert result.industry == "manufacturing"


class TestIndustryVariations:
    """業種別バリエーションのテスト"""
    
    def test_service_industry(self):
        """サービス業の分析（デフォルト使用）"""
        analyzer = FiveForcesAnalyzer()
        
        result = analyzer.analyze(industry="service")
        
        assert result is not None
        assert result.industry == "service"
    
    def test_it_industry(self):
        """IT業の分析"""
        analyzer = FiveForcesAnalyzer()
        
        result = analyzer.analyze(industry="it")
        
        assert result is not None
    
    def test_restaurant_industry(self):
        """飲食業の分析"""
        analyzer = FiveForcesAnalyzer()
        
        result = analyzer.analyze(industry="restaurant")
        
        assert result is not None
        # 飲食業は新規参入脅威が高い
        assert result.threat_of_new_entrants.score == 5
    
    def test_unknown_industry_uses_default(self):
        """未知の業種はデフォルト値を使用"""
        analyzer = FiveForcesAnalyzer()
        
        result = analyzer.analyze(industry="unknown_industry")
        
        # エラーなく処理される
        assert result is not None
        assert result.industry == "unknown_industry"
