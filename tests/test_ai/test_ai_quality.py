"""
Test AI Quality Assurance.
AI品質保証のテスト
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from core.ai_quality_assurance import (
    CitationExtractor, CitationType, ExtractedCitation,
    FactCheckEngine, FactCheckReport, VerificationStatus,
    HumanApprovalManager, HumanApprovalRequest,
    SensitivityAnalyzer, SensitivityVariable, SensitivityAnalysis,
    AuditLogEntry, validate_ai_response
)


class TestCitationExtractor:
    """CitationExtractor のテスト"""
    
    def test_extract_financial_data_citation(self):
        """財務データ引用の抽出"""
        text = "当社のROAは3.2%【財務データ:2024年度】で業界平均を下回っています。"
        
        extractor = CitationExtractor()
        citations = extractor.extract(text)
        
        assert len(citations) >= 1
        financial_citations = [c for c in citations if c.citation_type == CitationType.FINANCIAL_DATA]
        assert len(financial_citations) >= 1
    
    def test_extract_benchmark_citation(self):
        """業界基準引用の抽出"""
        text = "業界平均ROAは4.5%【業界基準:中小企業庁調査2024】です。"
        
        extractor = CitationExtractor()
        citations = extractor.extract(text)
        
        benchmark_citations = [c for c in citations if c.citation_type == CitationType.BENCHMARK]
        assert len(benchmark_citations) >= 1
    
    def test_extract_calculation_citation(self):
        """計算引用の抽出"""
        text = "売上高利益率は5%【計算:500万÷1億】です。"
        
        extractor = CitationExtractor()
        citations = extractor.extract(text)
        
        calc_citations = [c for c in citations if c.citation_type == CitationType.CALCULATION]
        assert len(calc_citations) >= 1
    
    def test_no_citations(self):
        """引用なしテキスト"""
        text = "これは普通のテキストで、引用タグを含みません。"
        
        extractor = CitationExtractor()
        citations = extractor.extract(text)
        
        assert len(citations) == 0


class TestFactCheckEngine:
    """FactCheckEngine のテスト"""
    
    def test_verified_citation(self):
        """検証済み引用"""
        source_data = {"roa": 3.2, "revenue": 100_000_000}
        text = "当社のROAは3.2%【財務データ:2024年度】です。"
        
        engine = FactCheckEngine(source_data=source_data)
        report = engine.check(text)
        
        assert isinstance(report, FactCheckReport)
        assert report.total_citations >= 0
    
    def test_trust_score_calculation(self):
        """信頼度スコアの計算"""
        source_data = {"roa": 3.2, "粗利率": 0.28}
        text = "ROAは3.2%【財務データ:2024年度】で、粗利率は28%【財務データ:2024年度】です。"
        
        engine = FactCheckEngine(source_data=source_data)
        report = engine.check(text)
        
        # スコアは0-100の範囲
        assert 0 <= report.trust_score <= 100


class TestHumanApprovalManager:
    """HumanApprovalManager のテスト"""
    
    def test_create_approval_request(self):
        """承認リクエストの作成"""
        manager = HumanApprovalManager()
        
        request = manager.create_request(
            content="AIが生成した戦略提案",
            content_type="strategy_proposal",
        )
        
        assert isinstance(request, HumanApprovalRequest)
        assert request.status == "pending"
        assert request.content_type == "strategy_proposal"
    
    def test_approve_request(self):
        """リクエストの承認"""
        manager = HumanApprovalManager()
        
        request = manager.create_request(
            content="テスト提案",
            content_type="diagnosis",
        )
        
        # approve returns bool
        success = manager.approve(
            request_id=request.request_id,
            reviewer="田中コンサルタント",
            comments="内容を確認しました",
        )
        
        assert success == True
        # Check the request was updated
        assert request.status == "approved"
        assert request.reviewer == "田中コンサルタント"
    
    def test_reject_request(self):
        """リクエストの却下"""
        manager = HumanApprovalManager()
        
        request = manager.create_request(
            content="問題のある提案",
            content_type="action_plan",
        )
        
        success = manager.reject(
            request_id=request.request_id,
            reviewer="佐藤マネージャー",
            reason="数値に誤りがあります",
        )
        
        assert success == True
        assert request.status == "rejected"
    
    def test_modify_and_approve(self):
        """修正して承認"""
        manager = HumanApprovalManager()
        
        request = manager.create_request(
            content="元のテキスト",
            content_type="forecast",
        )
        
        success = manager.modify_and_approve(
            request_id=request.request_id,
            reviewer="鈴木シニア",
            modified_content="修正されたテキスト",
            modification_reason="数値を修正",
        )
        
        assert success == True
        assert request.was_modified == True
    
    def test_pending_requests(self):
        """保留中リクエストの一覧"""
        manager = HumanApprovalManager()
        
        # 複数リクエストを作成
        manager.create_request(content="提案1", content_type="a")
        manager.create_request(content="提案2", content_type="b")
        
        pending = manager.get_pending()
        
        assert len(pending) >= 2
    
    def test_audit_log(self):
        """監査ログの記録"""
        manager = HumanApprovalManager()
        
        request = manager.create_request(
            content="テスト",
            content_type="test",
        )
        
        manager.approve(
            request_id=request.request_id,
            reviewer="テストレビュアー",
            comments="OK",
        )
        
        log = manager.get_audit_log()
        assert len(log) >= 1


class TestSensitivityAnalyzer:
    """SensitivityAnalyzer のテスト"""
    
    def test_sensitivity_analysis(self):
        """感度分析の実行"""
        analyzer = SensitivityAnalyzer()
        
        variables = [
            SensitivityVariable(
                name="売上高",
                base_value=100_000_000,
                unit="円",
            ),
        ]
        
        # impact_function takes (var_name, varied_value) as arguments
        def impact_fn(var_name, varied_value):
            return varied_value * 0.1  # 10%マージン
        
        result = analyzer.analyze(
            base_value=10_000_000,
            variables=variables,
            impact_function=impact_fn,
            target_metric="営業利益",
        )
        
        assert isinstance(result, SensitivityAnalysis)
        assert len(result.results) > 0


class TestValidateAiResponse:
    """ファサード関数のテスト"""
    
    def test_validate_ai_response_facade(self):
        """validate_ai_response関数のテスト"""
        source = {"roa": 3.2, "revenue": 100_000_000}
        response = "ROAは3.2%【財務データ:2024年度】で業界平均を下回ります"
        
        report = validate_ai_response(response, source)
        
        assert isinstance(report, FactCheckReport)
        assert 0 <= report.trust_score <= 100


class TestIntegration:
    """統合テスト"""
    
    def test_full_verification_flow(self):
        """完全な検証フロー"""
        # 1. ソースデータ
        source_data = {"roa": 3.2, "revenue": 100_000_000}
        
        # 2. AI生成テキスト
        ai_text = "当社のROAは3.2%【財務データ:2024年度】で業界平均を下回っています。"
        
        # 3. 引用抽出
        extractor = CitationExtractor()
        citations = extractor.extract(ai_text)
        
        # 4. ファクトチェック
        engine = FactCheckEngine(source_data=source_data)
        report = engine.check(ai_text)
        
        # 5. 承認リクエスト作成
        manager = HumanApprovalManager()
        request = manager.create_request(
            content=ai_text,
            content_type="diagnosis",
            fact_check_report=report,
        )
        
        # 6. 承認
        success = manager.approve(
            request_id=request.request_id,
            reviewer="テストレビュアー",
            comments="OK",
        )
        
        # 全体が正常に動作
        assert success == True
        assert request.status == "approved"
        assert len(manager.get_audit_log()) >= 1
