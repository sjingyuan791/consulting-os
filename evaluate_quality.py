import asyncio
import argparse
import json
import logging
import os
import sys
from datetime import datetime
from uuid import uuid4

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from core.midterm_plan_engine import (
    create_midterm_plan_engine, 
    SECTION_DEFINITIONS, 
    MidtermPlanDocument, 
    ChapterStatus, 
    MidtermPlanSection
)
from core.schemas.midterm_plan_schema import QualityCheckResult

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def run_evaluation(client_id: str, use_mock: bool = True):
    """
    Run a full generation cycle and quality check.
    """
    logger.info(f"Starting evaluation for client: {client_id} (Mock={use_mock})")

    # 1. Setup Engine
    pipeline_data = {} # In a real scenario, we'd load this from DB or a fixture
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

    # 2. Touch the document (Empty)
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
                narrative=""
            ) for d in SECTION_DEFINITIONS
        ]
    )

    # 3. Generate All Sections (or subset)
    logger.info("Generating full plan...")
    # In a real eval, we might want to just generate, but `generate_full_plan` is convenient.
    # However, generating 13 sections takes time/money. 
    # For dev speed, we might want to mock the generation or just do 1-2 sections if testing logic.
    # But for "Quality Eval", we need the content.
    
    # Check if we can use a pre-generated mock content for speed if use_mock is True
    if use_mock:
        logger.info("Using MOCK generation (filling dummy text)...")
        for s in doc.sections:
            s.narrative = f"MOCK CONTENT for Section {s.section_id}. This is a placeholder for evaluation logic testing."
            s.chapter_state.status = ChapterStatus.AI_GENERATED
            # Add some dummy data for Section 12/13 to test data checks
            if s.section_id == 12:
                s.data = {"strategic_kpis": [{"name": "Sales", "targets": {"Y3": 150}}]}
            if s.section_id == 13:
                s.narrative += "\nSales targets are aggressive."
    else:
        logger.info("Using REAL generation (Calling LLM)...")
        doc = await engine.generate_full_plan(doc)

    # 4. Run Quality Check
    logger.info("Running Quality Check...")
    try:
        qa_result = await engine.run_quality_check(doc)
        
        # 5. Output Results
        print("\n" + "="*50)
        print(f" EVALUATION REPORT")
        print("="*50)
        print(f"Overall Score: {qa_result.overall_score}/100")
        print(f"Grade:         {qa_result.grade}")
        print("-" * 30)
        print(f"Summary:       {qa_result.executive_summary}")
        print("-" * 30)
        print("Axis Scores:")
        for axis in qa_result.axis_scores:
            print(f"  - {axis.axis_name}: {axis.score}/20")
            print(f"    Assessment: {axis.assessment}")
        
        print("-" * 30)
        if qa_result.critical_issues:
            print(f"CRITICAL ISSUES ({len(qa_result.critical_issues)}):")
            for issue in qa_result.critical_issues:
                print(f"  [§{issue.target_section}] {issue.description}")
        else:
            print("No critical issues found.")

        # Save to file
        report_path = f"eval_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(qa_result.model_dump(), ensure_ascii=False, indent=2))
        logger.info(f"Report saved to {report_path}")

    except Exception as e:
        logger.error(f"Evaluation failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Midterm Plan Quality Evaluation")
    parser.add_argument("--client_id", type=str, default="eval_test_client", help="Client ID")
    parser.add_argument("--real", action="store_true", help="Use real LLM generation (costs money)")
    args = parser.parse_args()

    asyncio.run(run_evaluation(args.client_id, use_mock=not args.real))
