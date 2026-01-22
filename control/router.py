"""
Router for making routing decisions.
Determines model selection, RAG usage, and caching strategy.
"""
from typing import Dict, Any, Optional
from control.cost_model import CostModel
from control.policy_engine import PolicyEngine
import logging

logger = logging.getLogger(__name__)


class Router:
    """
    Makes routing decisions based on policies, cost, and request characteristics.
    """
    
    def __init__(
        self,
        policy_engine: PolicyEngine,
        cost_model: CostModel,
        cache_enabled: bool = True
    ):
        self.policy_engine = policy_engine
        self.cost_model = cost_model
        self.cache_enabled = cache_enabled
        self._cache = {}  # Simple in-memory cache
    
    def route(
        self,
        prompt: str,
        request_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make routing decision for a request.
        
        Returns:
            Dictionary with routing decision
        """
        routing_policy = self.policy_engine.get_routing_policy()
        
        decision = {
            "model": routing_policy.get("default_model", "gpt-4-turbo-preview"),
            "use_rag": False,
            "use_cache": False,
            "reasoning": []
        }
        
        # Check cache first
        if self.cache_enabled and routing_policy.get("cache_first", True):
            cache_key = self._generate_cache_key(prompt)
            if cache_key in self._cache:
                decision["use_cache"] = True
                decision["reasoning"].append("Cache hit found")
                return decision
        
        # Cost-aware routing
        if routing_policy.get("cost_aware_routing", True):
            cost_estimate = self.cost_model.estimate_cost(
                prompt=prompt,
                model=decision["model"]
            )
            
            # Check if cost exceeds threshold
            cost_policy = self.policy_engine.check_cost_policy(cost_estimate["estimated_cost"])
            
            if cost_policy["policy_check"] == "failed":
                # Downgrade to cheaper model
                cheaper_model = self.cost_model.suggest_cheaper_model(decision["model"])
                decision["model"] = cheaper_model
                decision["reasoning"].append(f"Cost-aware routing: downgraded to {cheaper_model}")
        
        # RAG decision
        rag_policy = self.policy_engine.policies.get("rag", {})
        if rag_policy.get("enabled", True):
            # Simple heuristic: use RAG for complex queries
            if self._is_complex_query(prompt):
                decision["use_rag"] = True
                decision["reasoning"].append("Complex query detected, RAG enabled")
        
        return decision
    
    def _generate_cache_key(self, prompt: str) -> str:
        """Generate cache key from prompt."""
        import hashlib
        return hashlib.sha256(prompt.encode()).hexdigest()
    
    def _is_complex_query(self, prompt: str) -> bool:
        """Determine if query is complex enough for RAG."""
        # Simple heuristics
        complexity_indicators = [
            len(prompt.split()) > 20,  # Long prompt
            '?' in prompt,  # Question
            any(word in prompt.lower() for word in ['explain', 'describe', 'what is', 'how does'])
        ]
        return sum(complexity_indicators) >= 2
