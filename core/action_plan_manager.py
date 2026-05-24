"""
Action Plan Manager for Consulting OS.
Provides structured action plan creation, tracking, and monitoring.

アクションプラン管理モジュール:
- アクションプラン作成・テンプレート
- 進捗追跡
- マイルストーン管理
- 責任者・期限管理
"""
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime, date, timedelta


class ActionPriority(str, Enum):
    """アクション優先度"""
    CRITICAL = "critical"   # 最優先
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ActionStatus(str, Enum):
    """アクション状態"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DELAYED = "delayed"
    CANCELLED = "cancelled"


class ActionCategory(str, Enum):
    """アクションカテゴリ"""
    FINANCE = "finance"           # 財務改善
    SALES = "sales"               # 営業強化
    OPERATIONS = "operations"     # 業務改善
    ORGANIZATION = "organization" # 組織・人事
    DX = "dx"                     # デジタル化
    STRATEGY = "strategy"         # 戦略


class ActionItem(BaseModel):
    """アクションアイテム"""
    action_id: str
    title: str
    description: str = Field(default="")
    
    # 分類
    category: ActionCategory
    priority: ActionPriority = Field(default=ActionPriority.MEDIUM)
    
    # 担当・期限
    owner: str = Field(default="")
    department: str = Field(default="")
    due_date: Optional[date] = None
    
    # 状態
    status: ActionStatus = Field(default=ActionStatus.NOT_STARTED)
    progress_percent: int = Field(default=0, ge=0, le=100)
    
    # 効果
    expected_impact: str = Field(default="", description="期待される効果")
    kpi_target: Optional[str] = None
    
    # 依存関係
    depends_on: List[str] = Field(default=[], description="依存するアクションID")
    
    # 備考
    notes: str = Field(default="")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat()[:10])
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat()[:10])


class Milestone(BaseModel):
    """マイルストーン"""
    milestone_id: str
    title: str
    target_date: date
    status: ActionStatus = Field(default=ActionStatus.NOT_STARTED)
    action_ids: List[str] = Field(default=[], description="関連アクションID")
    deliverables: List[str] = Field(default=[], description="成果物")


class ActionPlan(BaseModel):
    """アクションプラン"""
    plan_id: str
    plan_name: str
    company_name: Optional[str] = None
    
    # 期間
    start_date: date
    end_date: date
    
    # 目的
    objectives: List[str] = Field(default=[])
    
    # アクション
    actions: List[ActionItem] = Field(default=[])
    
    # マイルストーン
    milestones: List[Milestone] = Field(default=[])
    
    # メタデータ
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat()[:10])
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat()[:10])


class ActionPlanSummary(BaseModel):
    """アクションプランサマリー"""
    total_actions: int = Field(default=0)
    by_status: Dict[str, int] = Field(default={})
    by_priority: Dict[str, int] = Field(default={})
    by_category: Dict[str, int] = Field(default={})
    
    completion_rate: float = Field(default=0.0)
    on_track_rate: float = Field(default=0.0)
    
    overdue_actions: List[str] = Field(default=[])
    upcoming_deadlines: List[Dict[str, Any]] = Field(default=[])
    
    recommendations: List[str] = Field(default=[])


class ActionPlanManager:
    """アクションプラン管理エンジン"""
    
    # カテゴリ別テンプレートアクション
    TEMPLATE_ACTIONS = {
        ActionCategory.FINANCE: [
            ("予算管理体制の構築", "月次予実管理の導入と定例レビュー"),
            ("資金繰り表の作成", "3ヶ月ローリング資金繰り予測"),
            ("原価管理の強化", "商品別・プロジェクト別原価分析")
        ],
        ActionCategory.SALES: [
            ("営業KPI設定", "訪問件数・提案数・成約率の可視化"),
            ("顧客管理強化", "CRM導入またはExcel管理の改善"),
            ("営業プロセス標準化", "営業マニュアル・トークスクリプト作成")
        ],
        ActionCategory.OPERATIONS: [
            ("業務フロー可視化", "主要業務のフローチャート作成"),
            ("ムダ・ボトルネック特定", "業務効率化ポイントの洗い出し"),
            ("標準化・マニュアル化", "作業標準書の整備")
        ],
        ActionCategory.ORGANIZATION: [
            ("組織図の明確化", "役割・責任範囲の明文化"),
            ("評価制度の見直し", "目標管理制度の導入"),
            ("1on1面談の導入", "上司部下の定期コミュニケーション")
        ],
        ActionCategory.DX: [
            ("現状IT棚卸し", "利用中システム・ツールの一覧化"),
            ("業務のデジタル化", "紙・Excel業務のシステム化"),
            ("データ活用基盤構築", "経営データの一元管理")
        ],
        ActionCategory.STRATEGY: [
            ("経営理念・ビジョン策定", "中長期の方向性明確化"),
            ("事業計画策定", "3カ年中期経営計画の作成"),
            ("定例経営会議の設置", "月次経営レビューの仕組み化")
        ]
    }
    
    def create_plan(
        self,
        plan_name: str,
        duration_months: int = 6,
        objectives: List[str] = [],
        company_name: Optional[str] = None
    ) -> ActionPlan:
        """新規アクションプランを作成"""
        
        today = date.today()
        end_date = today + timedelta(days=duration_months * 30)
        
        return ActionPlan(
            plan_id=f"AP-{today.strftime('%Y%m%d')}-001",
            plan_name=plan_name,
            company_name=company_name,
            start_date=today,
            end_date=end_date,
            objectives=objectives,
            actions=[],
            milestones=[]
        )
    
    def add_action(
        self,
        plan: ActionPlan,
        title: str,
        category: ActionCategory,
        owner: str = "",
        due_date: Optional[date] = None,
        priority: ActionPriority = ActionPriority.MEDIUM,
        expected_impact: str = ""
    ) -> ActionPlan:
        """アクションを追加"""
        
        action_id = f"A-{len(plan.actions) + 1:03d}"
        
        action = ActionItem(
            action_id=action_id,
            title=title,
            category=category,
            owner=owner,
            due_date=due_date,
            priority=priority,
            expected_impact=expected_impact
        )
        
        plan.actions.append(action)
        plan.updated_at = datetime.now().isoformat()[:10]
        
        return plan
    
    def generate_template_plan(
        self,
        categories: List[ActionCategory],
        duration_months: int = 6,
        company_name: Optional[str] = None
    ) -> ActionPlan:
        """テンプレートからアクションプランを生成"""
        
        plan = self.create_plan(
            plan_name="経営改善アクションプラン",
            duration_months=duration_months,
            company_name=company_name
        )
        
        today = date.today()
        action_num = 1
        
        for category in categories:
            templates = self.TEMPLATE_ACTIONS.get(category, [])
            
            for i, (title, description) in enumerate(templates):
                # 期限を分散（1ヶ月ごと）
                due = today + timedelta(days=30 * (i + 1))
                
                action = ActionItem(
                    action_id=f"A-{action_num:03d}",
                    title=title,
                    description=description,
                    category=category,
                    priority=ActionPriority.HIGH if i == 0 else ActionPriority.MEDIUM,
                    due_date=due
                )
                plan.actions.append(action)
                action_num += 1
        
        # マイルストーン追加
        milestones = [
            Milestone(
                milestone_id="M-001",
                title="Phase 1 完了（基盤構築）",
                target_date=today + timedelta(days=90),
                deliverables=["業務フロー図", "改善ポイント一覧"]
            ),
            Milestone(
                milestone_id="M-002",
                title="Phase 2 完了（施策実行）",
                target_date=today + timedelta(days=180),
                deliverables=["改善施策完了報告", "効果測定結果"]
            )
        ]
        plan.milestones = milestones
        
        return plan
    
    def get_summary(self, plan: ActionPlan) -> ActionPlanSummary:
        """アクションプランサマリーを取得"""
        
        today = date.today()
        
        # カウント集計
        by_status = {}
        by_priority = {}
        by_category = {}
        
        overdue = []
        upcoming = []
        completed = 0
        on_track = 0
        
        for action in plan.actions:
            # ステータス別
            status = action.status.value
            by_status[status] = by_status.get(status, 0) + 1
            
            # 優先度別
            priority = action.priority.value
            by_priority[priority] = by_priority.get(priority, 0) + 1
            
            # カテゴリ別
            category = action.category.value
            by_category[category] = by_category.get(category, 0) + 1
            
            # 完了
            if action.status == ActionStatus.COMPLETED:
                completed += 1
            
            # 遅延チェック
            if action.due_date:
                if action.due_date < today and action.status not in [ActionStatus.COMPLETED, ActionStatus.CANCELLED]:
                    overdue.append(action.title)
                elif action.due_date <= today + timedelta(days=7) and action.status != ActionStatus.COMPLETED:
                    upcoming.append({
                        "title": action.title,
                        "due_date": action.due_date.isoformat(),
                        "owner": action.owner
                    })
                elif action.status != ActionStatus.DELAYED:
                    on_track += 1
        
        total = len(plan.actions)
        completion_rate = completed / total if total > 0 else 0
        on_track_rate = on_track / total if total > 0 else 0
        
        # 推奨事項
        recommendations = []
        if overdue:
            recommendations.append(f"【緊急】{len(overdue)}件の遅延アクションがあります")
        if by_priority.get("critical", 0) > 0:
            recommendations.append("クリティカル優先度のアクションに注力してください")
        if completion_rate < 0.3 and total > 5:
            recommendations.append("進捗が遅れています。リソース配分を見直してください")
        
        return ActionPlanSummary(
            total_actions=total,
            by_status=by_status,
            by_priority=by_priority,
            by_category=by_category,
            completion_rate=completion_rate,
            on_track_rate=on_track_rate,
            overdue_actions=overdue,
            upcoming_deadlines=upcoming[:5],
            recommendations=recommendations
        )
    
    def update_action_status(
        self,
        plan: ActionPlan,
        action_id: str,
        status: ActionStatus,
        progress_percent: Optional[int] = None,
        notes: Optional[str] = None
    ) -> ActionPlan:
        """アクションステータスを更新"""
        
        for action in plan.actions:
            if action.action_id == action_id:
                action.status = status
                if progress_percent is not None:
                    action.progress_percent = progress_percent
                if notes:
                    action.notes = notes
                action.updated_at = datetime.now().isoformat()[:10]
                break
        
        plan.updated_at = datetime.now().isoformat()[:10]
        return plan


# ==========================================
# ファサード関数
# ==========================================

def create_action_plan(
    plan_name: str,
    categories: List[str] = ["finance", "sales", "operations"],
    duration_months: int = 6,
    company_name: Optional[str] = None
) -> ActionPlan:
    """
    アクションプランを作成。
    
    Args:
        plan_name: プラン名
        categories: カテゴリ ["finance", "sales", "operations", "organization", "dx", "strategy"]
        duration_months: 期間（月）
        company_name: 企業名
    
    Example:
        >>> plan = create_action_plan(
        ...     "収益改善プラン",
        ...     ["finance", "sales"],
        ...     6,
        ...     "株式会社ABC"
        ... )
        >>> print(len(plan.actions))
    """
    manager = ActionPlanManager()
    
    category_enums = []
    for cat in categories:
        try:
            category_enums.append(ActionCategory(cat.lower()))
        except ValueError:
            pass
    
    return manager.generate_template_plan(
        categories=category_enums,
        duration_months=duration_months,
        company_name=company_name
    )


def get_plan_summary(plan: ActionPlan) -> ActionPlanSummary:
    """アクションプランサマリーを取得"""
    manager = ActionPlanManager()
    return manager.get_summary(plan)


def export_plan_to_dict(plan: ActionPlan) -> Dict[str, Any]:
    """アクションプランを辞書形式でエクスポート"""
    return plan.model_dump()
