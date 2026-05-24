import pytest
from unittest.mock import MagicMock, patch
from core.midterm_plan_engine import MidtermPlanEngine
from core.schemas.midterm_plan_schema import MidtermPlanSection, FeedbackItem, ChapterStatus

def test_feedback_schema():
    """Verify FeedbackItem schema and integration with MidtermPlanSection"""
    fb = FeedbackItem(content="More details needed")
    assert fb.content == "More details needed"
    assert fb.resolved is False
    assert fb.id is not None
    assert fb.timestamp is not None

    section = MidtermPlanSection(
        section_id=1,
        section_title="Test Section",
        narrative="Initial content",
        feedback_history=[fb]
    )
    assert len(section.feedback_history) == 1
    assert section.feedback_history[0].content == "More details needed"

import asyncio

def test_feedback_injection_in_prompt():
    """Verify feedback is injected into the prompt"""
    async def _run_test():
        # Mock dependencies
        engine = MidtermPlanEngine()
        
        # Mock current content with unresolved feedback
        fb = FeedbackItem(content="Fix the tone to be more formal.")
        current_section = MidtermPlanSection(
            section_id=1,
            section_title="Corporate Philosophy",
            narrative="Draft content",
            feedback_history=[fb]
        )
        
        # Mock OpenAI client
        with patch("core.midterm_plan_engine.openai_client") as mock_openai:
            # Configuration for mock response
            mock_response = MagicMock()
            mock_response.choices[0].message.content = '{"narrative": "Updated content based on feedback", "data": {}}'
            mock_response.usage.prompt_tokens = 10
            mock_response.usage.completion_tokens = 10
            mock_response.usage.total_tokens = 20
            mock_openai.chat.completions.create.return_value = mock_response
            
            # Run generation
            await engine.generate_single_chapter(
                chapter_id=1,
                locked_chapters=[],
                user_input="",
                current_content=current_section
            )
            
            # Verify prompt content
            call_args = mock_openai.chat.completions.create.call_args
            messages = call_args.kwargs['messages']
            user_msg = messages[1]['content']
            
            assert "Fix the tone to be more formal" in user_msg
            assert "過去のフィードバック" in user_msg

    asyncio.run(_run_test())

def test_feedback_preservation():
    """Verify feedback history is preserved in the new section object"""
    async def _run_test():
        engine = MidtermPlanEngine()
        
        fb = FeedbackItem(content="Keep this feedback.")
        current_section = MidtermPlanSection(
            section_id=1,
            section_title="Test",
            narrative="Old",
            feedback_history=[fb]
        )
        
        with patch("core.midterm_plan_engine.openai_client") as mock_openai:
            mock_response = MagicMock()
            mock_response.choices[0].message.content = '{"narrative": "New", "data": {}}'
            mock_openai.chat.completions.create.return_value = mock_response
            
            new_section = await engine.generate_single_chapter(
                chapter_id=1,
                locked_chapters=[],
                user_input="",
                current_content=current_section
            )
            
            # Verify feedback is preserved
            assert len(new_section.feedback_history) == 1
            assert new_section.feedback_history[0].content == "Keep this feedback."

    asyncio.run(_run_test())
