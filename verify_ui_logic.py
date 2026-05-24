
import sys
import os
import unittest
import json
import importlib
from unittest.mock import MagicMock, patch

# --- 1. Comprehensive Mocking of Project Modules ---
# We must mock everything that pages/15_midterm_plan.py imports

# Create a recursive mock that handles attributes automatically
core_mock = MagicMock()
sys.modules["core"] = core_mock
sys.modules["core.auth"] = MagicMock()
sys.modules["core.style_utils"] = MagicMock()
sys.modules["core.schemas"] = MagicMock()
sys.modules["core.schemas.midterm_plan_schema"] = MagicMock()
sys.modules["core.midterm_plan_engine"] = MagicMock()
sys.modules["core.midterm_plan_store"] = MagicMock()
sys.modules["core.docx_writer"] = MagicMock()
sys.modules["core.ppt_writer"] = MagicMock()

# Mock Streamlit
sys.modules["streamlit"] = MagicMock()
import streamlit as st

# Setup specific streamlit mocks
st.expander = MagicMock()
st.columns = MagicMock(return_value=[MagicMock(), MagicMock()]) # Fix for unpacking
st.markdown = MagicMock()
st.json = MagicMock()
st.error = MagicMock()
st.caption = MagicMock()
st.popover = MagicMock() # Need to mock popover context manager too
st.popover.return_value.__enter__.return_value = MagicMock()
st.session_state = {}

# Mock importlib.reload to avoid crashing on mocks
original_reload = importlib.reload
def mock_reload(module):
    if isinstance(module, MagicMock):
        return module
    return original_reload(module)
importlib.reload = mock_reload

# --- 2. Define Helper Classes for Schema Mocks ---
# These are needed because the UI code might do isinstance checks or attribute access
class MockMetadata:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

class MockSection:
    def __init__(self, **kwargs):
        self.generation_metadata = None
        self.section_id = 1
        self.section_title = "Test"
        self.narrative = "Text"
        self.data = {}
        for k, v in kwargs.items():
            setattr(self, k, v)

# Inject specific classes into the mocked modules
# This enables `from core.schemas.midterm_plan_schema import MidtermPlanSection` to work
# AND logic like `isinstance(obj, MidtermPlanSection)` to work if we use these classes.
sys.modules["core.schemas.midterm_plan_schema"].MidtermPlanSection = MockSection
sys.modules["core.schemas.midterm_plan_schema"].GenerationMetadata = MockMetadata
sys.modules["core.midterm_plan_engine"].MidtermPlanSection = MockSection

class TestUIComponents(unittest.TestCase):
    def setUp(self):
        st.expander.reset_mock()
        st.markdown.reset_mock()
        st.json.reset_mock()

    def test_render_audit_log(self):
        """
        Dynamically execute pages/15_midterm_plan.py and test render_audit_log.
        """
        file_path = "pages/15_midterm_plan.py"
        
        with open(file_path, "r", encoding="utf-8") as f:
            code = f.read()

        # Execute in captured namespace
        global_vars = {
            "__name__": "__test__",
            "st": st,
            # We also inject the mocks directly into globals if the script uses `import core.x` and expects `core` to be there
        }
        
        try:
            exec(code, global_vars)
        except Exception as e:
            self.fail(f"Failed to execute UI file: {e}")

        if "render_audit_log" not in global_vars:
            self.fail("render_audit_log function not found in UI file.")
        
        render_audit_log = global_vars["render_audit_log"]

        # Create Mock Data
        metadata = MockMetadata(
            model_name="gpt-4o",
            usage={"total_tokens": 1234},
            prompt_snapshot='[{"role":"user","content":"test"}]',
            generated_at="2026-01-01T12:00:00",
            finish_reason="stop",
            system_fingerprint="fp_123"
        )
        section = MockSection(generation_metadata=metadata, section_id=1, section_title="Test Section")

        # Run the function
        try:
            render_audit_log(section)
        except Exception as e:
            self.fail(f"render_audit_log raised an exception: {e}")

        # Verify
        st.expander.assert_called_with("🔍 生成監査ログ (Decision Audit)", expanded=False)
        # Check if json was called (it displays metadata and usage)
        self.assertTrue(st.json.called or st.markdown.called, "Should display content via json or markdown")
        
        print("\n✅ UI Component Test Passed: render_audit_log executed safely.")

if __name__ == "__main__":
    unittest.main()
