"""
Policy engine for declarative policy enforcement.
Loads policies from YAML and enforces them at runtime.
"""
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)


class PolicyEngine:
    """
    Declarative policy engine that enforces policies at runtime.
    """
    
    def __init__(self, policies_path: str):
        self.policies_path = Path(policies_path)
        self.policies: Dict[str, Any] = {}
        self._load_policies()
    
    def _load_policies(self):
        """Load policies from YAML file."""
        try:
            if not self.policies_path.exists():
                logger.warning(f"Policies file not found: {self.policies_path}, using defaults")
                self.policies = self._get_default_policies()
                return
            
            with open(self.policies_path, 'r') as f:
                data = yaml.safe_load(f)
                self.policies = data.get('policies', {})
            
            logger.info("Policies loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load policies: {str(e)}")
            self.policies = self._get_default_policies()
    
    def _get_default_policies(self) -> Dict[str, Any]:
        """Get default policies if file not found."""
        return {
            "cost": {
                "max_cost_per_request": 0.10,
                "budget_ceiling": 1000.00
            },
            "safety": {
                "hard_rejection_enabled": True,
                "risk_threshold": 0.8
            },
            "quality": {
                "min_grounding_score": 0.6,
                "max_hallucination_probability": 0.7
            }
        }
    
    def check_cost_policy(self, estimated_cost: float) -> Dict[str, Any]:
        """
        Check if request violates cost policies.
        
        Returns:
            Dictionary with policy_check result and action
        """
        cost_policy = self.policies.get("cost", {})
        max_cost = cost_policy.get("max_cost_per_request", 0.10)
        
        result = {
            "policy_check": "passed",
            "action": "allow",
            "reason": "",
            "estimated_cost": estimated_cost,
            "threshold": max_cost
        }
        
        if estimated_cost > max_cost:
            result["policy_check"] = "failed"
            result["action"] = cost_policy.get("enforcement_action", "block")
            result["reason"] = f"Estimated cost {estimated_cost:.4f} exceeds threshold {max_cost:.4f}"
        
        return result
    
    def check_safety_policy(self, risk_score: float) -> Dict[str, Any]:
        """
        Check if request violates safety policies.
        
        Returns:
            Dictionary with policy_check result and action
        """
        safety_policy = self.policies.get("safety", {})
        risk_threshold = safety_policy.get("risk_threshold", 0.8)
        hard_rejection = safety_policy.get("hard_rejection_enabled", True)
        
        result = {
            "policy_check": "passed",
            "action": "allow",
            "reason": "",
            "risk_score": risk_score,
            "threshold": risk_threshold
        }
        
        if risk_score >= risk_threshold:
            result["policy_check"] = "failed"
            if hard_rejection:
                result["action"] = "block"
            else:
                result["action"] = "retry"
            result["reason"] = f"Risk score {risk_score:.2f} exceeds threshold {risk_threshold:.2f}"
        
        return result
    
    def check_quality_policy(
        self,
        hallucination_score: float,
        grounding_score: float
    ) -> Dict[str, Any]:
        """
        Check if output violates quality policies.
        
        Returns:
            Dictionary with policy_check result and action
        """
        quality_policy = self.policies.get("quality", {})
        max_hallucination = quality_policy.get("max_hallucination_probability", 0.7)
        min_grounding = quality_policy.get("min_grounding_score", 0.6)
        
        result = {
            "policy_check": "passed",
            "action": "return",
            "reason": "",
            "hallucination_score": hallucination_score,
            "grounding_score": grounding_score
        }
        
        violations = []
        
        if hallucination_score > max_hallucination:
            violations.append(f"Hallucination score {hallucination_score:.2f} exceeds {max_hallucination:.2f}")
        
        if grounding_score < min_grounding:
            violations.append(f"Grounding score {grounding_score:.2f} below {min_grounding:.2f}")
        
        if violations:
            result["policy_check"] = "failed"
            result["action"] = quality_policy.get("enforcement_action", "retry")
            result["reason"] = "; ".join(violations)
        
        return result
    
    def check_latency_policy(self, latency_ms: float) -> Dict[str, Any]:
        """Check if request violates latency policies."""
        latency_policy = self.policies.get("latency", {})
        max_latency = latency_policy.get("max_latency_ms", 5000)
        
        result = {
            "policy_check": "passed",
            "action": "return",
            "latency_ms": latency_ms,
            "threshold": max_latency
        }
        
        if latency_ms > max_latency:
            result["policy_check"] = "failed"
            result["action"] = "downgrade"
            result["reason"] = f"Latency {latency_ms:.0f}ms exceeds threshold {max_latency:.0f}ms"
        
        return result
    
    def get_routing_policy(self) -> Dict[str, Any]:
        """Get routing policy configuration."""
        return self.policies.get("routing", {})
    
    def get_retry_policy(self) -> Dict[str, Any]:
        """Get retry policy configuration."""
        return self.policies.get("retry", {})
    
    def get_enforcement_actions(self) -> List[str]:
        """Get available enforcement actions."""
        enforcement = self.policies.get("enforcement", {})
        return enforcement.get("actions", ["return", "retry", "downgrade", "block"])
