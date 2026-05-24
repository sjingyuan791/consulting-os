"""
AI Response Validation and Fact Check Engine.
AI回答検証・ファクトチェックエンジン

特徴:
1. AI出力の数値がソースデータに存在するか検証
2. ハルシネーション検出・警告
3. 検証済み/未検証バッジ
4. 人間レビューポイントの自動抽出
"""
from typing import List, Dict, Optional, Any, Tuple, Set
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime
import re
import json


# ==========================================
# 定数
# ==========================================

class VerificationStatus(str, Enum):
    """検証ステータス"""
    VERIFIED = "verified"           # ソースで確認済み
    UNVERIFIED = "unverified"       # 未検証
    MISMATCH = "mismatch"           # 不一致
    SOURCE_MISSING = "source_missing"  # ソースなし
    HALLUCINATION = "hallucination"  # ハルシネーション疑い


class CitationType(str, Enum):
    """引用タイプ"""
    FINANCIAL_DATA = "財務データ"
    BENCHMARK = "業界基準"
    INTERVIEW = "ヒアリング"
    CALCULATION = "計算"
    INFERENCE = "推論"


class SeverityLevel(str, Enum):
    """重要度"""
    CRITICAL = "critical"   # 致命的（数値が大幅に異なる）
    WARNING = "warning"     # 警告（軽微な差異）
    INFO = "info"           # 情報（参考）


# ==========================================
# データモデル
# ==========================================

class ExtractedCitation(BaseModel):
    """抽出された引用"""
    citation_type: CitationType
    content: str
    source_label: str = ""  # 例: "2024年度決算書"
    value: Optional[float] = None
    unit: str = ""
    raw_text: str = ""  # 元のテキスト
    position: int = 0   # テキスト内位置


class VerificationResult(BaseModel):
    """検証結果"""
    citation: ExtractedCitation
    status: VerificationStatus
    source_value: Optional[float] = None
    difference: Optional[float] = None
    difference_percent: Optional[float] = None
    message: str = ""
    severity: SeverityLevel = SeverityLevel.INFO


class FactCheckReport(BaseModel):
    """ファクトチェックレポート"""
    ai_response_id: str = ""
    checked_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    
    # 検証結果
    total_citations: int = 0
    verified_count: int = 0
    unverified_count: int = 0
    mismatch_count: int = 0
    hallucination_count: int = 0
    
    # 詳細
    results: List[VerificationResult] = []
    
    # スコア
    trust_score: float = Field(default=0, ge=0, le=100, description="信頼度スコア 0-100")
    
    # 警告
    warnings: List[str] = []
    critical_issues: List[str] = []
    
    # 人間レビュー
    requires_human_review: bool = False
    review_points: List[str] = []
    
    # サマリー
    summary: str = ""
    recommendation: str = ""


class HumanApprovalRequest(BaseModel):
    """人間承認リクエスト"""
    request_id: str
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    
    # 対象
    content_type: str  # "strategy_proposal", "action_plan", etc.
    content_summary: str
    ai_generated_content: str
    
    # ファクトチェック結果
    fact_check_report: Optional[FactCheckReport] = None
    
    # レビューポイント
    key_decisions: List[str] = []  # 人間が判断すべき点
    assumptions: List[str] = []     # 前提条件
    risks: List[str] = []           # リスク
    
    # ステータス
    status: str = "pending"  # pending, approved, rejected, revised
    reviewer: Optional[str] = None
    reviewed_at: Optional[str] = None
    review_comments: str = ""
    
    # 修正
    was_modified: bool = False
    original_content: str = ""
    modifications: List[Dict[str, str]] = []


class AuditLogEntry(BaseModel):
    """監査ログエントリ"""
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    action: str  # "ai_generated", "human_reviewed", "approved", "rejected", "modified"
    actor: str   # "ai" or user name
    content_type: str
    content_id: str
    summary: str = ""
    details: Dict[str, Any] = {}
    
    # 変更追跡
    before_value: Optional[str] = None
    after_value: Optional[str] = None
    reason: str = ""


# ==========================================
# 引用抽出エンジン
# ==========================================

class CitationExtractor:
    """AI回答から引用を抽出"""
    
    # 引用パターン
    PATTERNS = {
        CitationType.FINANCIAL_DATA: r'【財務データ[：:]([^】]+)】([^【]+)',
        CitationType.BENCHMARK: r'【業界基準[：:]([^】]+)】([^【]+)',
        CitationType.INTERVIEW: r'【ヒアリング[：:]?([^】]*)】([^【]+)',
        CitationType.CALCULATION: r'【計算[：:]?([^】]*)】([^【]+)',
        CitationType.INFERENCE: r'【推論[：:]?([^】]*)】([^【]+)',
    }
    
    # 数値パターン
    NUMBER_PATTERN = r'[\d,]+\.?\d*\s*[%％億万円]?'
    
    def extract(self, text: str) -> List[ExtractedCitation]:
        """テキストから引用を抽出"""
        citations = []
        
        for ctype, pattern in self.PATTERNS.items():
            for match in re.finditer(pattern, text):
                source_label = match.group(1).strip()
                content = match.group(2).strip()
                
                # 数値を抽出
                value = self._extract_number(content)
                unit = self._extract_unit(content)
                
                citations.append(ExtractedCitation(
                    citation_type=ctype,
                    content=content,
                    source_label=source_label,
                    value=value,
                    unit=unit,
                    raw_text=match.group(0),
                    position=match.start(),
                ))
        
        return citations
    
    def _extract_number(self, text: str) -> Optional[float]:
        """テキストから数値を抽出"""
        # カンマを除去して数値を探す
        match = re.search(r'([\d,]+\.?\d*)', text)
        if match:
            try:
                return float(match.group(1).replace(',', ''))
            except ValueError:
                return None
        return None
    
    def _extract_unit(self, text: str) -> str:
        """単位を抽出"""
        if '億円' in text:
            return '億円'
        elif '万円' in text:
            return '万円'
        elif '円' in text:
            return '円'
        elif '%' in text or '％' in text:
            return '%'
        return ''


# ==========================================
# ファクトチェックエンジン
# ==========================================

class FactCheckEngine:
    """AIアウトプットのファクトチェック"""
    
    # 許容誤差
    TOLERANCE_PERCENT = 1.0  # 1%以内の差異は許容
    CRITICAL_THRESHOLD = 10.0  # 10%以上の差異は致命的
    
    def __init__(self, source_data: Dict[str, Any]):
        """
        Args:
            source_data: 検証元データ（財務データ、ベンチマーク等）
        """
        self.source_data = source_data
        self.extractor = CitationExtractor()
        
        # フラット化したソースデータ
        self._flat_source = self._flatten_source(source_data)
    
    def _flatten_source(self, data: Dict, prefix: str = "") -> Dict[str, float]:
        """ネストされたデータをフラット化"""
        flat = {}
        for key, value in data.items():
            full_key = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                flat.update(self._flatten_source(value, full_key))
            elif isinstance(value, (int, float)):
                flat[key.lower()] = float(value)
                flat[full_key.lower()] = float(value)
        return flat
    
    def check(self, ai_response: str, response_id: str = "") -> FactCheckReport:
        """
        AI回答をファクトチェック。
        
        Args:
            ai_response: AI生成テキスト
            response_id: レスポンスID
        """
        # 引用を抽出
        citations = self.extractor.extract(ai_response)
        
        results = []
        warnings = []
        critical = []
        
        for citation in citations:
            result = self._verify_citation(citation)
            results.append(result)
            
            if result.status == VerificationStatus.MISMATCH:
                if result.severity == SeverityLevel.CRITICAL:
                    critical.append(f"【{citation.citation_type.value}】{citation.content}: {result.message}")
                else:
                    warnings.append(f"【{citation.citation_type.value}】{citation.content}: {result.message}")
            
            elif result.status == VerificationStatus.HALLUCINATION:
                critical.append(f"⚠️ ハルシネーション疑い: {citation.content}")
        
        # 集計
        verified = sum(1 for r in results if r.status == VerificationStatus.VERIFIED)
        unverified = sum(1 for r in results if r.status == VerificationStatus.UNVERIFIED)
        mismatch = sum(1 for r in results if r.status == VerificationStatus.MISMATCH)
        hallucination = sum(1 for r in results if r.status == VerificationStatus.HALLUCINATION)
        
        # 信頼度スコア
        total = len(citations) if citations else 1
        trust_score = (verified / total) * 100 if total > 0 else 50
        trust_score = max(0, trust_score - hallucination * 20 - mismatch * 10)
        
        # 人間レビュー必要判定
        requires_review = hallucination > 0 or len(critical) > 0 or trust_score < 70
        
        # レビューポイント
        review_points = []
        if hallucination > 0:
            review_points.append("ハルシネーションの可能性があります。元データを確認してください。")
        if mismatch > 0:
            review_points.append("数値に不一致があります。AIの計算を確認してください。")
        if unverified > verified:
            review_points.append("未検証の引用が多いです。ソースデータの追加を検討してください。")
        
        # サマリー
        if trust_score >= 90:
            summary = "✅ 高信頼: ほぼ全ての引用が検証済み"
            recommendation = "そのまま使用可能です"
        elif trust_score >= 70:
            summary = "⚠️ 中信頼: 一部未検証の引用あり"
            recommendation = "主要な数値を確認してから使用してください"
        else:
            summary = "❌ 要確認: 信頼性に問題あり"
            recommendation = "人間による詳細確認が必要です"
        
        return FactCheckReport(
            ai_response_id=response_id,
            total_citations=len(citations),
            verified_count=verified,
            unverified_count=unverified,
            mismatch_count=mismatch,
            hallucination_count=hallucination,
            results=results,
            trust_score=round(trust_score, 1),
            warnings=warnings,
            critical_issues=critical,
            requires_human_review=requires_review,
            review_points=review_points,
            summary=summary,
            recommendation=recommendation,
        )
    
    def _verify_citation(self, citation: ExtractedCitation) -> VerificationResult:
        """単一の引用を検証"""
        
        # 計算・推論は検証スキップ
        if citation.citation_type in [CitationType.CALCULATION, CitationType.INFERENCE]:
            return VerificationResult(
                citation=citation,
                status=VerificationStatus.UNVERIFIED,
                message="計算/推論は自動検証対象外",
                severity=SeverityLevel.INFO,
            )
        
        # ヒアリングも検証スキップ
        if citation.citation_type == CitationType.INTERVIEW:
            return VerificationResult(
                citation=citation,
                status=VerificationStatus.UNVERIFIED,
                message="ヒアリング情報は自動検証対象外",
                severity=SeverityLevel.INFO,
            )
        
        # 数値がない場合
        if citation.value is None:
            return VerificationResult(
                citation=citation,
                status=VerificationStatus.UNVERIFIED,
                message="数値が抽出できませんでした",
                severity=SeverityLevel.INFO,
            )
        
        # ソースデータで検索
        source_value = self._find_in_source(citation)
        
        if source_value is None:
            # ソースに見つからない = ハルシネーションの可能性
            return VerificationResult(
                citation=citation,
                status=VerificationStatus.HALLUCINATION,
                message="ソースデータに該当する値が見つかりません",
                severity=SeverityLevel.CRITICAL,
            )
        
        # 値の比較
        diff = citation.value - source_value
        diff_percent = (diff / source_value * 100) if source_value != 0 else 0
        
        if abs(diff_percent) <= self.TOLERANCE_PERCENT:
            return VerificationResult(
                citation=citation,
                status=VerificationStatus.VERIFIED,
                source_value=source_value,
                difference=diff,
                difference_percent=diff_percent,
                message="✓ 検証済み",
                severity=SeverityLevel.INFO,
            )
        elif abs(diff_percent) <= self.CRITICAL_THRESHOLD:
            return VerificationResult(
                citation=citation,
                status=VerificationStatus.MISMATCH,
                source_value=source_value,
                difference=diff,
                difference_percent=diff_percent,
                message=f"軽微な差異: {diff_percent:+.1f}%",
                severity=SeverityLevel.WARNING,
            )
        else:
            return VerificationResult(
                citation=citation,
                status=VerificationStatus.MISMATCH,
                source_value=source_value,
                difference=diff,
                difference_percent=diff_percent,
                message=f"重大な差異: {diff_percent:+.1f}%",
                severity=SeverityLevel.CRITICAL,
            )
    
    def _find_in_source(self, citation: ExtractedCitation) -> Optional[float]:
        """ソースデータから値を検索"""
        # キーワードで検索
        keywords = self._extract_keywords(citation.content)
        
        for keyword in keywords:
            keyword_lower = keyword.lower()
            if keyword_lower in self._flat_source:
                return self._flat_source[keyword_lower]
        
        # 部分一致
        for key, value in self._flat_source.items():
            for keyword in keywords:
                if keyword.lower() in key:
                    return value
        
        return None
    
    def _extract_keywords(self, text: str) -> List[str]:
        """テキストからキーワードを抽出"""
        # 財務用語リスト
        financial_terms = [
            'roa', 'roe', 'roic', '売上', '利益', '資産', '負債',
            '原価率', '粗利', '営業利益', '純利益', '売上高',
            'revenue', 'profit', 'margin', 'ratio',
        ]
        
        keywords = []
        text_lower = text.lower()
        
        for term in financial_terms:
            if term in text_lower:
                keywords.append(term)
        
        # 数値の前後のテキストも抽出
        words = re.findall(r'[a-zA-Zぁ-んァ-ン一-龥]+', text)
        keywords.extend(words[:3])  # 最初の3単語
        
        return keywords


# ==========================================
# 人間承認マネージャー
# ==========================================

class HumanApprovalManager:
    """人間承認フロー管理"""
    
    def __init__(self):
        self._pending_requests: Dict[str, HumanApprovalRequest] = {}
        self._audit_log: List[AuditLogEntry] = []
    
    def create_request(
        self,
        content_type: str,
        content: str,
        fact_check_report: Optional[FactCheckReport] = None,
        key_decisions: List[str] = [],
        assumptions: List[str] = [],
        risks: List[str] = []
    ) -> HumanApprovalRequest:
        """承認リクエストを作成"""
        import uuid
        request_id = str(uuid.uuid4())[:8]
        
        request = HumanApprovalRequest(
            request_id=request_id,
            content_type=content_type,
            content_summary=content[:200] + "..." if len(content) > 200 else content,
            ai_generated_content=content,
            fact_check_report=fact_check_report,
            key_decisions=key_decisions,
            assumptions=assumptions,
            risks=risks,
        )
        
        self._pending_requests[request_id] = request
        self._log("ai_generated", "ai", content_type, request_id, "AI提案を生成")
        
        return request
    
    def approve(
        self,
        request_id: str,
        reviewer: str,
        comments: str = ""
    ) -> bool:
        """承認"""
        if request_id not in self._pending_requests:
            return False
        
        request = self._pending_requests[request_id]
        request.status = "approved"
        request.reviewer = reviewer
        request.reviewed_at = datetime.now().isoformat()
        request.review_comments = comments
        
        self._log("approved", reviewer, request.content_type, request_id, 
                  f"承認: {comments}" if comments else "承認")
        
        return True
    
    def reject(
        self,
        request_id: str,
        reviewer: str,
        reason: str
    ) -> bool:
        """却下"""
        if request_id not in self._pending_requests:
            return False
        
        request = self._pending_requests[request_id]
        request.status = "rejected"
        request.reviewer = reviewer
        request.reviewed_at = datetime.now().isoformat()
        request.review_comments = reason
        
        self._log("rejected", reviewer, request.content_type, request_id, f"却下: {reason}")
        
        return True
    
    def modify_and_approve(
        self,
        request_id: str,
        reviewer: str,
        modified_content: str,
        modification_reason: str
    ) -> bool:
        """修正して承認"""
        if request_id not in self._pending_requests:
            return False
        
        request = self._pending_requests[request_id]
        request.status = "revised"
        request.reviewer = reviewer
        request.reviewed_at = datetime.now().isoformat()
        request.was_modified = True
        request.original_content = request.ai_generated_content
        request.ai_generated_content = modified_content
        request.modifications.append({
            "reviewer": reviewer,
            "reason": modification_reason,
            "timestamp": datetime.now().isoformat(),
        })
        
        self._log(
            "modified", reviewer, request.content_type, request_id,
            f"修正承認: {modification_reason}",
            details={"original_length": len(request.original_content), 
                     "modified_length": len(modified_content)},
            before_value=request.original_content[:100],
            after_value=modified_content[:100],
            reason=modification_reason
        )
        
        return True
    
    def get_pending(self) -> List[HumanApprovalRequest]:
        """保留中のリクエスト一覧"""
        return [r for r in self._pending_requests.values() if r.status == "pending"]
    
    def get_audit_log(self, limit: int = 100) -> List[AuditLogEntry]:
        """監査ログ取得"""
        return self._audit_log[-limit:]
    
    def _log(
        self,
        action: str,
        actor: str,
        content_type: str,
        content_id: str,
        summary: str,
        details: Dict = {},
        before_value: str = None,
        after_value: str = None,
        reason: str = ""
    ):
        """監査ログ記録"""
        entry = AuditLogEntry(
            action=action,
            actor=actor,
            content_type=content_type,
            content_id=content_id,
            summary=summary,
            details=details,
            before_value=before_value,
            after_value=after_value,
            reason=reason,
        )
        self._audit_log.append(entry)


# ==========================================
# 感度分析エンジン
# ==========================================

class SensitivityVariable(BaseModel):
    """感度分析変数"""
    name: str
    base_value: float
    unit: str = ""
    min_value: float = 0
    max_value: float = 0
    step: float = 0


class SensitivityResult(BaseModel):
    """感度分析結果"""
    variable_name: str
    scenario: str  # "base", "-10%", "+10%", etc.
    variable_value: float
    result_value: float
    impact: float = 0  # 基準からの変動額
    impact_percent: float = 0


class SensitivityAnalysis(BaseModel):
    """感度分析"""
    target_metric: str  # "営業利益" etc.
    base_value: float
    variables: List[SensitivityVariable]
    results: List[SensitivityResult]
    
    # サマリー
    most_sensitive_variable: str = ""
    sensitivity_message: str = ""
    risk_factors: List[str] = []


class SensitivityAnalyzer:
    """感度分析エンジン"""
    
    # デフォルト変動幅
    DEFAULT_VARIATIONS = [-20, -10, -5, 0, 5, 10, 20]  # %
    
    def analyze(
        self,
        base_value: float,
        variables: List[SensitivityVariable],
        impact_function: callable,
        target_metric: str = "営業利益"
    ) -> SensitivityAnalysis:
        """
        感度分析を実行。
        
        Args:
            base_value: 基準値
            variables: 分析対象変数
            impact_function: 変動→結果を計算する関数
            target_metric: 対象指標名
        """
        results = []
        max_impact = 0
        most_sensitive = ""
        
        for var in variables:
            # 各変動幅で計算
            for pct in self.DEFAULT_VARIATIONS:
                varied_value = var.base_value * (1 + pct / 100)
                
                # 境界チェック
                if var.min_value and varied_value < var.min_value:
                    varied_value = var.min_value
                if var.max_value and varied_value > var.max_value:
                    varied_value = var.max_value
                
                # 結果計算
                result_value = impact_function(var.name, varied_value)
                impact = result_value - base_value
                impact_pct = (impact / base_value * 100) if base_value != 0 else 0
                
                results.append(SensitivityResult(
                    variable_name=var.name,
                    scenario=f"{pct:+d}%" if pct != 0 else "基準",
                    variable_value=varied_value,
                    result_value=result_value,
                    impact=impact,
                    impact_percent=impact_pct,
                ))
                
                # 最も感度が高い変数を特定
                if abs(impact) > max_impact:
                    max_impact = abs(impact)
                    most_sensitive = var.name
        
        # リスク要因
        risk_factors = []
        for var in variables:
            worst_case = min([r for r in results if r.variable_name == var.name], 
                            key=lambda x: x.result_value)
            if worst_case.impact_percent < -10:
                risk_factors.append(
                    f"{var.name}が{worst_case.scenario}変動すると、"
                    f"{target_metric}が{worst_case.impact_percent:.1f}%減少"
                )
        
        return SensitivityAnalysis(
            target_metric=target_metric,
            base_value=base_value,
            variables=variables,
            results=results,
            most_sensitive_variable=most_sensitive,
            sensitivity_message=f"最も感度が高いのは「{most_sensitive}」です",
            risk_factors=risk_factors,
        )


# ==========================================
# ファサード関数
# ==========================================

def validate_ai_response(
    ai_response: str,
    source_data: Dict[str, Any],
    response_id: str = ""
) -> FactCheckReport:
    """
    AI回答をファクトチェック。
    
    Example:
        >>> source = {"roa": 3.2, "revenue": 100000000}
        >>> response = "ROAは3.2%【財務データ:2024年度】で業界平均を下回ります"
        >>> report = validate_ai_response(response, source)
        >>> print(report.trust_score)
    """
    engine = FactCheckEngine(source_data)
    return engine.check(ai_response, response_id)


def create_approval_request(
    content_type: str,
    content: str,
    source_data: Optional[Dict] = None
) -> HumanApprovalRequest:
    """
    人間承認リクエストを作成。
    """
    fact_check = None
    if source_data:
        fact_check = validate_ai_response(content, source_data)
    
    manager = HumanApprovalManager()
    return manager.create_request(
        content_type=content_type,
        content=content,
        fact_check_report=fact_check,
    )


def format_fact_check_report(report: FactCheckReport) -> str:
    """ファクトチェックレポートをテキスト形式で出力"""
    lines = [
        "=" * 60,
        "ファクトチェックレポート",
        "=" * 60,
        f"信頼度スコア: {report.trust_score}/100",
        f"検証済み: {report.verified_count} / 未検証: {report.unverified_count} / 不一致: {report.mismatch_count}",
        "",
        f"【サマリー】{report.summary}",
        f"【推奨】{report.recommendation}",
    ]
    
    if report.critical_issues:
        lines.append("")
        lines.append("【⚠️ 重大な問題】")
        for issue in report.critical_issues:
            lines.append(f"  ❌ {issue}")
    
    if report.warnings:
        lines.append("")
        lines.append("【警告】")
        for warning in report.warnings:
            lines.append(f"  ⚠️ {warning}")
    
    if report.review_points:
        lines.append("")
        lines.append("【人間確認ポイント】")
        for point in report.review_points:
            lines.append(f"  📋 {point}")
    
    lines.append("")
    lines.append("=" * 60)
    
    return "\n".join(lines)
