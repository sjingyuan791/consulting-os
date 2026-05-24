from typing import Dict

class LLMRouter:
    # Model definitions - using actual OpenAI model names
    MODEL_MAP = {
        "light": "gpt-4o-mini",      # Fast, cost-effective
        "analysis": "gpt-4o",        # Balanced performance
        "premium": "o1"              # Advanced reasoning
    }

    @staticmethod
    def route(task_type: str) -> str:
        """
        Returns the appropriate model name based on the task type.
        """
        # Light Tasks
        if task_type in ["summary", "chat", "review"]:
            return LLMRouter.MODEL_MAP["light"]
        
        # Analysis Tasks
        elif task_type in ["diagnosis", "strategy", "chapter"]:
            return LLMRouter.MODEL_MAP["analysis"]
        
        # Premium Tasks
        elif task_type in ["final_plan", "bank_doc"]:
            return LLMRouter.MODEL_MAP["premium"]
        
        # Default fallback
        else:
            return LLMRouter.MODEL_MAP["analysis"]
