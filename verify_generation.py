import asyncio
import os
import sys
import traceback

# Force use of Service Key for this backend test to bypass RLS constraints
from dotenv import load_dotenv
load_dotenv()
service_key = os.environ.get("SUPABASE_SERVICE_KEY")
if service_key:
    os.environ["SUPABASE_KEY"] = service_key

# Add current dir to path
sys.path.append(os.getcwd())

# Redirect output to file
class LoggerWriter:
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.log = open(filename, "w", encoding="utf-8")
    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
    def flush(self):
        self.terminal.flush()
        self.log.flush()

sys.stdout = LoggerWriter("verify_log.txt")
sys.stderr = sys.stdout

from core.midterm_plan_engine import create_midterm_plan_engine, MidtermPlanDocument, SECTION_DEFINITIONS
from core.strategic_guardrails_service import get_latest_guardrails
from core.repos.dataset_repo import DatasetRepo
from core.midterm_plan_store import save_midterm_plan

CLIENT_ID = "00000000-0000-0000-0000-000000000001"

async def main():
    print(f"🚀 Starting Midterm Plan Generation Verification for Client: {CLIENT_ID}")
    
    # 1. Fetch Data (Guardrails & Datasets)
    print("--- 1. Loading Context Data ---")
    guardrails_obj = get_latest_guardrails(CLIENT_ID)
    if not guardrails_obj:
        print("❌ Guardrails not found for test client.")
        return
    guardrails = guardrails_obj.model_dump()
    print(f"✅ Guardrails loaded: {guardrails.get('mission_objective', '')[:30]}...")

    dataset_repo = DatasetRepo()
    pipeline_data = {}
    
    # Financial
    v_fin = dataset_repo.get_current_dataset_version(CLIENT_ID, "financial")
    if v_fin:
        pipeline_data["financial"] = v_fin.get("normalized_json", {})
        print("✅ Financial data loaded.")
    else:
        print("⚠️ No Financial data.")

    # Internal
    v_int = dataset_repo.get_current_dataset_version(CLIENT_ID, "internal")
    if v_int:
        pipeline_data["internal"] = v_int.get("normalized_json", {})
        print("✅ Internal data loaded.")

    # External
    v_ext = dataset_repo.get_current_dataset_version(CLIENT_ID, "external")
    if v_ext:
        pipeline_data["external"] = v_ext.get("normalized_json", {})
        print("✅ External data loaded.")

    # 2. Initialize Engine
    print("\n--- 2. Initializing AI Engine ---")
    try:
        # Debug: Check types/values in guardrails
        print("DEBUG: Checking guardrails data...")
        for k, v in guardrails.items():
            print(f"  {k}: {type(v)} = {str(v)[:50]}...")
            if v is None:
                print(f"⚠️ Warning: guardrails['{k}'] is None")
        
        print("\nDEBUG: Attempting init with REAL data...")
        engine = create_midterm_plan_engine(
            pipeline_data=pipeline_data,
            guardrails=guardrails,
            client_id=CLIENT_ID
        )
        # engine = create_midterm_plan_engine(
        #     pipeline_data=pipeline_data,
        #     guardrails={},
        #     client_id=CLIENT_ID
        # )
        # print("✅ Engine initialized with EMPTY guardrails.")
        
        # IF successful, try passing real guardrails manually to debug
        # engine.guardrails = guardrails
        # print("✅ Assigned real guardrails after init.")

        print("✅ Engine initialized.")
    except Exception as e:
        print(f"❌ Failed to initialize engine: {e}")
        # import traceback
        traceback.print_exc()
        return

    # 3. Validation Check
    if engine.validation_errors:
        print(f"⚠️ Validation Errors: {engine.validation_errors}")
    else:
        print("✅ Data validation passed.")

    # 4. Run Generation (Partial Test - maybe just 1 chapter to save time/tokens? 
    # Or full if user wants "Batch Generation" verified. Let's try full but be aware of time.)
    # For a smoke test, generating all might take long. 
    # Let's try generating just the first section: "1. 経営理念・ミッション"
    # But the instruction was to verify "Batch Generation". The engine has `generate_full_plan`.
    # Let's try `generate_full_plan` but maybe mock the heavy LLM calls? 
    # No, we want    # 3. Executing Batch Generation (Full Plan)
    # Reverted to full mode after RAG fix verification
    print("\n--- 3. Executing Batch Generation (Full Plan) ---")
    print("This may take some time (calling AI)...")
    
    try:
        doc = await engine.generate_full_plan()
        print(f"Generated {len(doc.sections)} sections.")
        
        # Check content
        empty_sections = [s.section_id for s in doc.sections if not s.narrative]
        if empty_sections:
            print(f"⚠️ Warning: Sections {empty_sections} are empty.")
        else:
            print("✅ All sections have content.")

        # 5. Save
        print("\n--- 4. Saving to Database ---")
        success = save_midterm_plan(CLIENT_ID, doc)
        if success:
            print("✅ Saved successfully.")
        else:
            print("❌ Failed to save.")

    except Exception as e:
        import traceback
        print(f"❌ Generation failed: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
