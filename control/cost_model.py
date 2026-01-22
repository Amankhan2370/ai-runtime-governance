"""
Cost model for token-level cost estimation and tracking.
Implements per-request cost tracking and budget management.
"""
from typing import Dict, Any, Optional
import tiktoken
import logging

logger = logging.getLogger(__name__)


class CostModel:
    """
    Cost estimation and tracking for LLM requests.
    """
    
    # Model pricing (per 1K tokens, as of 2024)
    MODEL_PRICING = {
        "gpt-4-turbo-preview": {
            "input": 0.01,  # $0.01 per 1K tokens
            "output": 0.03  # $0.03 per 1K tokens
        },
        "gpt-4": {
            "input": 0.03,
            "output": 0.06
        },
        "gpt-3.5-turbo": {
            "input": 0.0015,
            "output": 0.002
        },
        "claude-3-opus": {
            "input": 0.015,
            "output": 0.075
        },
        "claude-3-sonnet": {
            "input": 0.003,
            "output": 0.015
        }
    }
    
    def __init__(self):
        self.total_cost = 0.0
        self.request_count = 0
        self._encodings = {}
    
    def estimate_cost(
        self,
        prompt: str,
        model: str = "gpt-4-turbo-preview",
        estimated_output_tokens: int = 100
    ) -> Dict[str, Any]:
        """
        Estimate cost for a request.
        
        Returns:
            Dictionary with cost breakdown
        """
        # Get token counts
        input_tokens = self._count_tokens(prompt, model)
        
        # Get pricing
        pricing = self.MODEL_PRICING.get(model, self.MODEL_PRICING["gpt-3.5-turbo"])
        
        # Calculate costs
        input_cost = (input_tokens / 1000) * pricing["input"]
        output_cost = (estimated_output_tokens / 1000) * pricing["output"]
        total_cost = input_cost + output_cost
        
        return {
            "estimated_cost": total_cost,
            "input_tokens": input_tokens,
            "output_tokens": estimated_output_tokens,
            "input_cost": input_cost,
            "output_cost": output_cost,
            "model": model,
            "breakdown": {
                "input": f"${input_cost:.6f}",
                "output": f"${output_cost:.6f}",
                "total": f"${total_cost:.6f}"
            }
        }
    
    def record_cost(self, actual_cost: float, model: str):
        """Record actual cost for tracking."""
        self.total_cost += actual_cost
        self.request_count += 1
        logger.info(f"Cost recorded: ${actual_cost:.6f} (Total: ${self.total_cost:.6f})")
    
    def get_budget_status(self, budget_ceiling: float) -> Dict[str, Any]:
        """Get current budget status."""
        remaining = budget_ceiling - self.total_cost
        percentage_used = (self.total_cost / budget_ceiling * 100) if budget_ceiling > 0 else 0
        
        return {
            "total_cost": self.total_cost,
            "budget_ceiling": budget_ceiling,
            "remaining": remaining,
            "percentage_used": percentage_used,
            "status": "within_budget" if remaining > 0 else "exceeded"
        }
    
    def _count_tokens(self, text: str, model: str) -> int:
        """Count tokens in text."""
        try:
            # Use tiktoken for OpenAI models
            if "gpt" in model.lower():
                encoding_name = "cl100k_base"  # For GPT-4 and GPT-3.5
                if encoding_name not in self._encodings:
                    self._encodings[encoding_name] = tiktoken.get_encoding(encoding_name)
                encoding = self._encodings[encoding_name]
                return len(encoding.encode(text))
            else:
                # Fallback: approximate 4 characters per token
                return len(text) // 4
        except Exception as e:
            logger.warning(f"Token counting failed: {str(e)}, using approximation")
            return len(text) // 4
    
    def suggest_cheaper_model(self, current_model: str) -> Optional[str]:
        """Suggest a cheaper alternative model."""
        model_hierarchy = [
            "gpt-4-turbo-preview",
            "gpt-4",
            "gpt-3.5-turbo"
        ]
        
        try:
            current_index = model_hierarchy.index(current_model)
            if current_index < len(model_hierarchy) - 1:
                return model_hierarchy[current_index + 1]
        except ValueError:
            pass
        
        return "gpt-3.5-turbo"  # Default fallback
