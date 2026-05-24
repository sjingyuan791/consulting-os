from core.plan_blueprint import PlanBlueprint
from core.llm_client import generate_chapter_content
from core.models import StrategyContext, DiagnosisReport, StrategyResponse
import json
import concurrent.futures
import os
import pandas as pd

class ChapterGenerator:
    def __init__(self, context: StrategyContext, full_package: dict = None):
        self.context = context
        self.blueprint = PlanBlueprint.get_standard_blueprint()
        self.full_package = full_package or {}

    def _get_context_str(self, required_keys: list) -> str:
        # Filter context to save tokens (Task 3)
        ctx_dict = self.context.model_dump()
        
        # If no keys specified, maybe send everything or minimal? 
        # Default behavior: send full if empty? Or minimal.
        # Let's assume defaults in blueprint might be empty which usually means "general". 
        # But specifically requested filtering:
        if not required_keys:
             # Default fallback: Company info + Hypotheses
             required_keys = ['company_summary', 'hypotheses', 'issue_definition']
        
        filtered = {k: ctx_dict.get(k) for k in required_keys if k in ctx_dict}
        return json.dumps(filtered, ensure_ascii=False)

    def _resolve_data_source(self, source_path: str):
        """Helper to resolve dot notation path in full_package"""
        if not source_path:
            return None
        
        parts = source_path.split('.')
        current = self.full_package
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                # Try getattr if it's a model
                current = getattr(current, part, None)
            
            if current is None:
                return None
        return current

    def _render_deterministic(self, instruction_type: str, data_source: str, header: str) -> str:
        """Renders content deterministically without LLM."""
        data = self._resolve_data_source(data_source)
        if not data:
            return f"*(Data for {header} needs to be generated)*"

        content = ""
        
        if instruction_type == "financial_table":
            # Expecting list of records or metrics
            if isinstance(data, list):
                try:
                    df = pd.DataFrame(data)
                    # Simple markdown table
                    content = df.to_markdown(index=False)
                except (TypeError, ValueError):
                    content = str(data)
            # Handle Simulation Result specifically
            elif isinstance(data, dict):
                 # SimulationResultSchema
                 content = f"""
| Metric | Value |
| :--- | :--- |
| Base Case Revenue | {data.get('base_case_revenue', 0):,.0f} |
| Projected Revenue | {data.get('projected_revenue', 0):,.0f} |
| Projected Profit | {data.get('projected_profit', 0):,.0f} |
| ROI | {data.get('roi', 0):.1f}% |
"""
            else:
                content = str(data)

        elif instruction_type == "strategy_card":
            # selected_strategy
            if isinstance(data, dict):
                content = f"""
**Selected Strategy**: {data.get('chosen_option_id', 'N/A')}

**Reasons**:
{chr(10).join(['- ' + r for r in data.get('reasons', [])])}

**Exit Criteria**:
{chr(10).join(['- ' + e for e in data.get('exit_criteria', [])])}
"""
        elif instruction_type == "roadmap_list":
            # execution_roadmap
            if isinstance(data, dict):
                content = f"**Strategy Name**: {data.get('strategy_name', '')}\n\n"
                initiatives = data.get('initiatives', [])
                for init in initiatives:
                    content += f"### {init.get('title')}\n"
                    content += f"- **Owner**: {init.get('owner')}\n"
                    content += f"- **Timeline**: Month {init.get('start_month')} - {init.get('start_month') + init.get('duration_months')}\n"
                    content += f"- **KPI**: {init.get('kpi_metric')} (Target: {init.get('target_value')})\n\n"

        elif instruction_type == "list":
             # Generic list
             if isinstance(data, dict):
                 # specialized for external_intelligence
                 opps = data.get('opportunities', [])
                 threats = data.get('threats', [])
                 content += "**Opportunities**\n" + "\n".join([f"- {o}" for o in opps]) + "\n\n"
                 content += "**Threats**\n" + "\n".join([f"- {t}" for t in threats])
             elif isinstance(data, list):
                 content = "\n".join([f"- {item}" for item in data])
             else:
                 content = str(data)
                 
        else:
            content = f"*(Unknown instruction type: {instruction_type})*"

        return f"### {header}\n\n{content}"

    def generate_full_plan_content(self, progress_callback=None) -> dict:
        """
        Generates content for all chapters using Hybrid Execution.
        """
        full_content = {}
        
        # Split tasks into Deterministic and LLM
        llm_tasks = []
        deterministic_content = {} # (chapter, section) -> content
        
        for chapter in self.blueprint:
            for section in chapter.sections:
                if section.instruction_type == "narrative":
                    llm_tasks.append({
                        'chapter': chapter.title,
                        'section': section.title,
                        'prompt': section.content_prompt,
                        'required_context': section.required_context
                    })
                else:
                    # Deterministic Render
                    content = self._render_deterministic(
                        section.instruction_type, 
                        section.data_source, 
                        section.content_prompt
                    )
                    deterministic_content[(chapter.title, section.title)] = content
        
        total_tasks = len(llm_tasks)
        completed = 0
        
        llm_results_map = {} # (chapter, section) -> content

        if total_tasks > 0:
            # Determine max workers
            max_workers = min(8, os.cpu_count() or 4)
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_task = {}
                for t in llm_tasks:
                    context_str = self._get_context_str(t['required_context'])
                    future = executor.submit(generate_chapter_content, t['section'], t['prompt'], context_str)
                    future_to_task[future] = t
                
                for future in concurrent.futures.as_completed(future_to_task):
                    task = future_to_task[future]
                    try:
                        content = future.result()
                        llm_results_map[(task['chapter'], task['section'])] = content
                    except Exception as e:
                        print(f"Error in section {task['section']}: {e}")
                        llm_results_map[(task['chapter'], task['section'])] = f"[Generation Failed: {e}]"
    
                    completed += 1
                    if progress_callback:
                        progress_callback(completed / total_tasks, f"Generated {task['section']}")

        # Reconstruct hierarchical dict
        for chapter in self.blueprint:
            chapter_title = chapter.title
            full_content[chapter_title] = {}
            for section in chapter.sections:
                section_title = section.title
                
                if (chapter_title, section_title) in deterministic_content:
                    content = deterministic_content[(chapter_title, section_title)]
                else:
                    content = llm_results_map.get((chapter_title, section_title), "")
                
                full_content[chapter_title][section_title] = content
            
        return full_content
