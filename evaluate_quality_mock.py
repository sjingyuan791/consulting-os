import asyncio
import argparse
import json
import logging
import os
import sys
from uuid import uuid4
from datetime import datetime
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from core.midterm_plan_engine import (
    create_midterm_plan_engine, 
    SECTION_DEFINITIONS, 
    MidtermPlanDocument, 
    ChapterStatus, 
    MidtermPlanSection
)
from core.schemas.midterm_plan_schema import QualityCheckResult, QAAxisScore, QAIssueItem
from core.executive_decision_board import build_decision_board

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def run_evaluation_fully_mocked(client_id: str):
    """
    Run evaluation with BOTH generation and checking mocked.
    This tests the script scaffolding and report generation logic.
    """
    logger.info(f"Starting FULLY MOCKED evaluation for client: {client_id}")

    # 1. Setup Engine
    pipeline_data = {}
    guardrails = {
        "mission_objective": "To be the leading automated consulting firm.",
        "time_horizon_years": 3,
        "investment_limit": 100
    }
    
    engine = create_midterm_plan_engine(
        pipeline_data=pipeline_data,
        guardrails=guardrails,
        client_id=client_id
    )

    pm_decision_board = build_decision_board({str(i): "done" for i in range(1, 15)})

    # 2. Mock Document
    doc = MidtermPlanDocument(
        document_id=str(uuid4()),
        client_id=client_id,
        plan_period="3年",
        sections=[
            MidtermPlanSection(
                section_id=d["id"],
                section_title=d["title"],
                section_title_en=d["title_en"],
                references=d["references"],
                narrative="MOCK CONTENT"
            ) for d in SECTION_DEFINITIONS
        ]
    )
    
    # 3. Mock the Quality Check Result
    mock_qa_result = QualityCheckResult(
        overall_score=85,
        grade="A",
        executive_summary="This is a MOCK evaluation result. The plan is generally sound but lacks specific financial data.",
        axis_scores=[
            QAAxisScore(axis_name="論理的一貫性", score=18, assessment="Strong logic flow.", issues=[], recommendations=[]),
            QAAxisScore(axis_name="数値整合性", score=15, assessment="Some gaps in KPI vs Financials.", issues=["KPI targets not fully reflected"], recommendations=["Update Section 13"]),
            QAAxisScore(axis_name="SWOT整合性", score=19, assessment="Excellent alignment.", issues=[], recommendations=[]),
            QAAxisScore(axis_name="実現可能性", score=16, assessment="Reasonable given resources.", issues=[], recommendations=[]),
            QAAxisScore(axis_name="欠落・矛盾", score=17, assessment="No major contradictions.", issues=[], recommendations=[])
        ],
        critical_issues=[],
        warnings=[
            QAIssueItem(
                severity="warning",
                target_section=13,
                target_section_title="数値計画",
                description="Revenue growth seems optimistic compared to market trends.",
                suggestion="Revisit growth assumptions."
            )
        ],
        strengths=["Clear vision", "Strong SWOT analysis"],
        cross_reference_summary="Good linkage between Section 6 and 8."
    )

    # Patch the engine's run_quality_check method
    with patch.object(engine, 'run_quality_check', return_value=mock_qa_result):
        logger.info("Running Quality Check (Mocked)...")
        qa_result = await engine.run_quality_check(doc)
        
        # 5. Output Results
        print("\n" + "="*50)
        print(f" EVALUATION REPORT (MOCKED)")
        print("="*50)
        print(f"Overall Score: {qa_result.overall_score}/100")
        print(f"Grade:         {qa_result.grade}")
        print("-" * 30)
        print(f"Summary:       {qa_result.executive_summary}")
        print("-" * 30)
        print("PM Decision Audit:")
        print(f"  Readiness:   {pm_decision_board.readiness_score}/100")
        print(f"  Status:      {pm_decision_board.status}")
        print(f"  Next Issue:  {pm_decision_board.next_decision}")
        print(f"  Next Action: {pm_decision_board.next_action}")
        print("-" * 30)
        print("Axis Scores:")
        for axis in qa_result.axis_scores:
            print(f"  - {axis.axis_name}: {axis.score}/20")
            print(f"    Assessment: {axis.assessment}")
        
        print("-" * 30)
        if qa_result.critical_issues:
            print(f"CRITICAL ISSUES ({len(qa_result.critical_issues)}):")
        else:
            print("No critical issues found.")

        # Save to file
        report_path = f"eval_report_MOCK_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        payload = qa_result.model_dump()
        payload["pm_decision_audit"] = {
            "readiness_score": pm_decision_board.readiness_score,
            "status": pm_decision_board.status,
            "next_decision": pm_decision_board.next_decision,
            "next_action": pm_decision_board.next_action,
            "blocking_questions": pm_decision_board.blocking_questions,
            "quality_gates": pm_decision_board.quality_gates,
            "differentiation_signals": pm_decision_board.differentiation_signals,
        }
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False, indent=2))
        logger.info(f"Report saved to {report_path}")

if __name__ == "__main__":
    asyncio.run(run_evaluation_fully_mocked("mock_client_001"))
