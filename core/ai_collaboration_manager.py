"""
AI Response Wrapper with Quality Assurance.
AIレスポンスラッパー - ファクトチェック統合版

LLMクライアントの出力を自動検証し、信頼度スコア付きで返す。
"""
from typing import List, Dict, Optional, Any, Tuple
from pydantic import BaseModel, Field
from datetime import datetime
import json

from core.ai_quality_assurance import (
    FactCheckEngine,
    FactCheckReport,
    HumanApprovalManager,
    HumanApprovalRequest,
    AuditLogEntry,
    SensitivityAnalyzer,
    SensitivityVariable,
    SensitivityAnalysis,
    validate_ai_response,
)


# ==========================================
# 検証済みレスポンスモデル
# ==========================================

class VerifiedAIResponse(BaseModel):
    """検証済みAIレスポンス"""
    # 元のレスポンス
    content: str
    content_type: str
    generated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    
    # ファクトチェック結果
    fact_check: Optional[FactCheckReport] = None
    trust_score: float = Field(default=50, ge=0, le=100)
    
    # 検証ステータス
    is_verified: bool = False
    is_approved: bool = False
    approval_request_id: Optional[str] = None
    
    # 表示制御
    show_to_client: bool = False  # クライアントに見せてよいか
    requires_human_review: bool = True
    
    # バッジ
    badges: List[str] = []  # ["verified", "human_approved", "fact_checked"]
    
    # 警告
    warnings: List[str] = []
    
    # メタデータ
    model_used: str = ""
    processing_time_ms: int = 0


class AICollaborationSession(BaseModel):
    """AI協働セッション"""
    session_id: str
    started_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    
    # コンテキスト
    source_data: Dict[str, Any] = {}
    
    # 履歴
    responses: List[VerifiedAIResponse] = []
    approval_requests: List[HumanApprovalRequest] = []
    audit_log: List[AuditLogEntry] = []
    
    # 統計
    total_responses: int = 0
    approved_responses: int = 0
    rejected_responses: int = 0
    modified_responses: int = 0
    average_trust_score: float = 0


# ==========================================
# AI協働マネージャー
# ==========================================

class AICollaborationManager:
    """
    AI×人間協働マネージャー
    
    特徴:
    1. AI回答を自動ファクトチェック
    2. 信頼度に応じて人間レビューを要求
    3. 承認フローを管理
    4. 監査ログを記録
    """
    
    # 自動承認の閾値
    AUTO_APPROVE_THRESHOLD = 90  # 信頼度90%以上は自動承認可能
    REQUIRE_REVIEW_THRESHOLD = 70  # 70%未満は必須レビュー
    
    def __init__(self, source_data: Dict[str, Any], session_id: str = None):
        """
        Args:
            source_data: ソースデータ（財務データ等）
            session_id: セッションID
        """
        import uuid
        self.session_id = session_id or str(uuid.uuid4())[:8]
        self.source_data = source_data
        self.fact_checker = FactCheckEngine(source_data)
        self.approval_manager = HumanApprovalManager()
        
        self._responses: List[VerifiedAIResponse] = []
    
    def process_response(
        self,
        ai_content: str,
        content_type: str = "strategy_proposal",
        model_used: str = "",
        auto_approve_if_safe: bool = False
    ) -> VerifiedAIResponse:
        """
        AI回答を処理し、検証済みレスポンスを返す。
        
        Args:
            ai_content: AI生成コンテンツ
            content_type: コンテンツタイプ
            model_used: 使用モデル
            auto_approve_if_safe: 高信頼度なら自動承認
        """
        import time
        start_time = time.time()
        
        # 1. ファクトチェック
        fact_check = self.fact_checker.check(ai_content, response_id=f"{self.session_id}_{len(self._responses)}")
        
        # 2. 信頼度判定
        trust_score = fact_check.trust_score
        requires_review = trust_score < self.REQUIRE_REVIEW_THRESHOLD or fact_check.requires_human_review
        
        # 3. バッジ生成
        badges = []
        if fact_check.verified_count > 0:
            badges.append("fact_checked")
        if trust_score >= self.AUTO_APPROVE_THRESHOLD:
            badges.append("high_trust")
        elif trust_score >= self.REQUIRE_REVIEW_THRESHOLD:
            badges.append("medium_trust")
        else:
            badges.append("low_trust")
        
        # 4. 警告収集
        warnings = fact_check.warnings + fact_check.critical_issues
        
        # 5. 人間レビュー判定
        is_approved = False
        show_to_client = False
        approval_request_id = None
        
        if auto_approve_if_safe and trust_score >= self.AUTO_APPROVE_THRESHOLD:
            is_approved = True
            show_to_client = True
            badges.append("auto_approved")
        elif requires_review:
            # 承認リクエスト作成
            request = self.approval_manager.create_request(
                content_type=content_type,
                content=ai_content,
                fact_check_report=fact_check,
                key_decisions=fact_check.review_points,
            )
            approval_request_id = request.request_id
        
        # 6. レスポンス作成
        processing_time = int((time.time() - start_time) * 1000)
        
        response = VerifiedAIResponse(
            content=ai_content,
            content_type=content_type,
            fact_check=fact_check,
            trust_score=trust_score,
            is_verified=fact_check.verified_count > 0,
            is_approved=is_approved,
            approval_request_id=approval_request_id,
            show_to_client=show_to_client,
            requires_human_review=requires_review,
            badges=badges,
            warnings=warnings,
            model_used=model_used,
            processing_time_ms=processing_time,
        )
        
        self._responses.append(response)
        
        return response
    
    def approve_response(
        self,
        approval_request_id: str,
        reviewer: str,
        comments: str = ""
    ) -> bool:
        """レスポンスを承認"""
        success = self.approval_manager.approve(approval_request_id, reviewer, comments)
        
        if success:
            # 対応するレスポンスを更新
            for resp in self._responses:
                if resp.approval_request_id == approval_request_id:
                    resp.is_approved = True
                    resp.show_to_client = True
                    resp.badges.append("human_approved")
                    break
        
        return success
    
    def reject_response(
        self,
        approval_request_id: str,
        reviewer: str,
        reason: str
    ) -> bool:
        """レスポンスを却下"""
        return self.approval_manager.reject(approval_request_id, reviewer, reason)
    
    def modify_and_approve(
        self,
        approval_request_id: str,
        reviewer: str,
        modified_content: str,
        reason: str
    ) -> VerifiedAIResponse:
        """レスポンスを修正して承認"""
        success = self.approval_manager.modify_and_approve(
            approval_request_id, reviewer, modified_content, reason
        )
        
        if success:
            # 修正済みレスポンスを再処理
            modified_response = self.process_response(
                modified_content,
                content_type="modified_proposal",
                auto_approve_if_safe=True
            )
            modified_response.badges.append("human_modified")
            return modified_response
        
        return None
    
    def get_pending_approvals(self) -> List[HumanApprovalRequest]:
        """保留中の承認リクエスト"""
        return self.approval_manager.get_pending()
    
    def get_session_summary(self) -> Dict[str, Any]:
        """セッションサマリー"""
        approved = sum(1 for r in self._responses if r.is_approved)
        avg_trust = sum(r.trust_score for r in self._responses) / len(self._responses) if self._responses else 0
        
        return {
            "session_id": self.session_id,
            "total_responses": len(self._responses),
            "approved_responses": approved,
            "pending_approvals": len(self.approval_manager.get_pending()),
            "average_trust_score": round(avg_trust, 1),
            "audit_log_entries": len(self.approval_manager.get_audit_log()),
        }
    
    def export_audit_log(self) -> List[Dict]:
        """監査ログをエクスポート"""
        return [entry.model_dump() for entry in self.approval_manager.get_audit_log()]


# ==========================================
# ファサード関数
# ==========================================

def create_collaboration_session(
    source_data: Dict[str, Any]
) -> AICollaborationManager:
    """
    AI協働セッションを作成。
    
    Example:
        >>> source = {"roa": 3.2, "revenue": 100000000}
        >>> session = create_collaboration_session(source)
        >>> response = session.process_response("ROAは3.2%【財務データ:2024年度】です")
        >>> print(response.trust_score)
    """
    return AICollaborationManager(source_data)


def quick_validate(ai_content: str, source_data: Dict) -> Dict[str, Any]:
    """
    簡易バリデーション。
    
    Returns:
        {"trust_score": float, "is_safe": bool, "warnings": List[str]}
    """
    report = validate_ai_response(ai_content, source_data)
    
    return {
        "trust_score": report.trust_score,
        "is_safe": report.trust_score >= 70 and report.hallucination_count == 0,
        "warnings": report.warnings + report.critical_issues,
        "requires_review": report.requires_human_review,
        "summary": report.summary,
    }


def format_verified_response_for_ui(response: VerifiedAIResponse) -> Dict[str, Any]:
    """UI表示用にフォーマット"""
    # バッジカラー
    badge_colors = {
        "high_trust": "green",
        "medium_trust": "yellow",
        "low_trust": "red",
        "human_approved": "blue",
        "auto_approved": "teal",
        "fact_checked": "purple",
        "human_modified": "orange",
    }
    
    # ステータスアイコン
    if response.is_approved:
        status_icon = "✅"
        status_text = "承認済み"
    elif response.requires_human_review:
        status_icon = "⏳"
        status_text = "レビュー待ち"
    else:
        status_icon = "⚠️"
        status_text = "未承認"
    
    return {
        "content": response.content,
        "trust_score": response.trust_score,
        "trust_score_display": f"{response.trust_score:.0f}/100",
        "badges": [{"name": b, "color": badge_colors.get(b, "gray")} for b in response.badges],
        "status_icon": status_icon,
        "status_text": status_text,
        "show_to_client": response.show_to_client,
        "warnings": response.warnings,
        "fact_check_summary": response.fact_check.summary if response.fact_check else "",
        "requires_action": response.requires_human_review and not response.is_approved,
    }
