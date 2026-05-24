"""
Stage 3: Hypothesis Verification Planner
Generates validation activities for root cause hypotheses.
Produces data requirements, interview questions, and validation methods.
"""
from typing import Dict, Any, Optional, List
from core.pipeline.base_engine import AIEngine, EngineConfig
from core.schemas.pipeline_stages import (
    Stage3Output, DataRequirement, InterviewQuestion,
    ValidationMethod, HypothesisVerification
)
import json


class VerificationPlannerEngine(AIEngine[Dict[str, Any], Stage3Output]):
    """
    Hypothesis Verification Planner - Stage 3 of the consulting pipeline.
    
    Designs validation activities to confirm or refute root cause hypotheses
    before proceeding to strategy design.
    """
    
    STAGE_NUMBER = 3
    STAGE_NAME = "Hypothesis Verification Planner"
    
    # Templates for common verification approaches
    VERIFICATION_TEMPLATES = {
        "operational": {
            "data_types": ["プロセスKPI", "作業時間データ", "品質データ", "コストデータ"],
            "interview_targets": ["現場マネージャー", "作業者", "品質管理担当"],
            "methods": ["プロセス分析", "時間観測", "品質チェック"]
        },
        "market": {
            "data_types": ["市場調査データ", "競合分析", "顧客アンケート", "販売データ"],
            "interview_targets": ["営業担当", "マーケティング担当", "顧客"],
            "methods": ["市場調査", "競合ベンチマーク", "顧客インタビュー"]
        },
        "organizational": {
            "data_types": ["組織図", "人事データ", "スキルマップ", "研修記録"],
            "interview_targets": ["人事部門", "部門長", "従業員"],
            "methods": ["組織診断", "スキル評価", "エンゲージメント調査"]
        },
        "financial": {
            "data_types": ["詳細財務データ", "部門別PL", "コスト構造分析"],
            "interview_targets": ["経理部門", "CFO", "事業部長"],
            "methods": ["財務分析", "コスト分解", "収益性分析"]
        }
    }
    
    async def process(
        self,
        input_data: Dict[str, Any],
        previous_output: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Stage3Output:
        """
        Generate verification plan for root cause hypotheses.
        """
        # Extract root causes from Stage 2
        stage2_output = previous_output or {}
        primary_cause = stage2_output.get("primary_root_cause", {})
        secondary_causes = stage2_output.get("secondary_causes", [])
        
        all_causes = [primary_cause] + secondary_causes
        
        # Generate verification plans
        hypotheses_to_verify = []
        all_data_requirements = []
        all_interview_questions = []
        all_validation_methods = []
        
        for i, cause in enumerate(all_causes):
            if not cause:
                continue
                
            category = cause.get("category", "operational")
            templates = self.VERIFICATION_TEMPLATES.get(category, self.VERIFICATION_TEMPLATES["operational"])
            
            # Create hypothesis verification plan
            hyp_verification = self._create_hypothesis_verification(cause, i + 1)
            hypotheses_to_verify.append(hyp_verification)
            
            # Generate data requirements
            data_reqs = self._generate_data_requirements(cause, templates, i + 1)
            all_data_requirements.extend(data_reqs)
            
            # Generate interview questions
            questions = self._generate_interview_questions(cause, templates, i + 1)
            all_interview_questions.extend(questions)
            
            # Generate validation methods
            methods = self._generate_validation_methods(cause, templates, i + 1)
            all_validation_methods.extend(methods)
        
        # Estimate timeline
        timeline = self._estimate_timeline(all_data_requirements, all_interview_questions)
        
        return Stage3Output(
            hypotheses_to_verify=hypotheses_to_verify,
            required_additional_data=all_data_requirements,
            interview_questions=all_interview_questions,
            validation_methods=all_validation_methods,
            verification_timeline=timeline,
            resource_requirements={
                "estimated_person_days": len(all_causes) * 5,
                "required_roles": ["アナリスト", "インタビュアー", "プロジェクトマネージャー"]
            },
            confidence_score=0.80
        )
    
    def _create_hypothesis_verification(
        self,
        cause: Dict,
        index: int
    ) -> HypothesisVerification:
        """Create verification plan for a single hypothesis."""
        cause_id = cause.get("id", f"cause_{index}")
        description = cause.get("description", "")
        
        return HypothesisVerification(
            hypothesis_id=cause_id,
            hypothesis_description=description,
            verification_approach=f"定量・定性データの収集と分析による{description[:20]}の検証",
            required_data=[f"data_req_{cause_id}_1", f"data_req_{cause_id}_2"],
            validation_methods=[f"method_{cause_id}_1"],
            success_criteria=f"仮説を支持するエビデンスが3件以上、または棄却するエビデンスが2件以上",
            estimated_confidence_if_verified=0.85
        )
    
    def _generate_data_requirements(
        self,
        cause: Dict,
        templates: Dict,
        index: int
    ) -> List[DataRequirement]:
        """Generate data requirements for hypothesis verification."""
        requirements = []
        cause_id = cause.get("id", f"cause_{index}")
        
        for i, data_type in enumerate(templates["data_types"][:3]):
            priority = "critical" if i == 0 else "important" if i == 1 else "nice_to_have"
            
            requirements.append(DataRequirement(
                id=f"data_req_{cause_id}_{i+1}",
                data_type=data_type,
                description=f"{cause.get('description', '')[:30]}の検証に必要な{data_type}",
                source="社内データ" if "社内" in data_type or "プロセス" in data_type else "外部調査",
                priority=priority,
                acquisition_method="データ抽出" if "データ" in data_type else "調査実施",
                estimated_effort="1-2日" if priority == "critical" else "3-5日"
            ))
        
        return requirements
    
    def _generate_interview_questions(
        self,
        cause: Dict,
        templates: Dict,
        index: int
    ) -> List[InterviewQuestion]:
        """Generate interview questions for hypothesis verification."""
        questions = []
        cause_id = cause.get("id", f"cause_{index}")
        description = cause.get("description", "問題")
        
        question_templates = [
            ("現状認識", "{}について、現場ではどのような課題を感じていますか？"),
            ("原因探索", "{}の主な原因は何だと考えますか？"),
            ("影響範囲", "{}は他のどの業務や指標に影響していますか？"),
            ("改善案", "{}を改善するためにどのような施策が考えられますか？"),
            ("障壁", "{}の改善を妨げている要因は何ですか？")
        ]
        
        for i, target in enumerate(templates["interview_targets"][:2]):
            for j, (q_type, q_template) in enumerate(question_templates[:3]):
                questions.append(InterviewQuestion(
                    id=f"q_{cause_id}_{i}_{j}",
                    target_role=target,
                    question=q_template.format(description[:30]),
                    hypothesis_link=cause_id,
                    expected_insight=f"{q_type}に関する定性的情報",
                    follow_up_questions=[
                        "具体的な事例を教えてください",
                        "それはいつ頃から発生していますか？"
                    ]
                ))
        
        return questions
    
    def _generate_validation_methods(
        self,
        cause: Dict,
        templates: Dict,
        index: int
    ) -> List[ValidationMethod]:
        """Generate validation methods for hypothesis verification."""
        methods = []
        cause_id = cause.get("id", f"cause_{index}")
        
        # Quantitative method
        methods.append(ValidationMethod(
            id=f"method_{cause_id}_quant",
            hypothesis_id=cause_id,
            method_type="quantitative",
            description="定量データ分析による仮説検証",
            success_criteria="統計的有意性（p < 0.05）または20%以上の差異",
            data_requirements=[f"data_req_{cause_id}_1"],
            estimated_duration="3-5日"
        ))
        
        # Qualitative method
        methods.append(ValidationMethod(
            id=f"method_{cause_id}_qual",
            hypothesis_id=cause_id,
            method_type="qualitative",
            description="インタビューによる定性検証",
            success_criteria="3名以上の関係者からの一致した見解",
            data_requirements=[],
            estimated_duration="5-7日"
        ))
        
        # Mixed method
        methods.append(ValidationMethod(
            id=f"method_{cause_id}_mixed",
            hypothesis_id=cause_id,
            method_type="mixed",
            description="定量・定性の三角検証",
            success_criteria="両方の分析結果が一致する場合に仮説を採択",
            data_requirements=[f"data_req_{cause_id}_1", f"data_req_{cause_id}_2"],
            estimated_duration="7-10日"
        ))
        
        return methods
    
    def _estimate_timeline(
        self,
        data_requirements: List[DataRequirement],
        interview_questions: List[InterviewQuestion]
    ) -> str:
        """Estimate overall verification timeline."""
        critical_count = len([d for d in data_requirements if d.priority == "critical"])
        interview_targets = len(set(q.target_role for q in interview_questions))
        
        base_days = 5
        data_days = critical_count * 2
        interview_days = interview_targets * 3
        
        total_days = base_days + data_days + interview_days
        weeks = (total_days + 4) // 5  # Convert to weeks
        
        return f"推定所要期間: {weeks}週間（{total_days}営業日）"
    
    def build_prompt(
        self,
        input_data: Dict[str, Any],
        previous_output: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build prompt for AI-enhanced verification planning."""
        return f"""根本原因仮説の検証計画を策定してください。

## 根本原因仮説
{json.dumps(previous_output, ensure_ascii=False, indent=2) if previous_output else '{}'}

以下を生成してください：
1. 必要な追加データ（優先度付き）
2. インタビュー質問（対象者別）
3. 検証方法（定量・定性）
4. 成功基準
5. スケジュール"""


# Factory function
def create_verification_planner(config: Optional[EngineConfig] = None) -> VerificationPlannerEngine:
    """Create and return a Verification Planner Engine instance."""
    return VerificationPlannerEngine(config)
