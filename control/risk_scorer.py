"""
Risk scoring for pre-generation safety checks.
Implements prompt risk scoring, ambiguity detection, and safety classification.
"""
import re
from typing import Dict, Any, List
from sentence_transformers import SentenceTransformer
import logging

logger = logging.getLogger(__name__)


class RiskScorer:
    """
    Scores prompts for risk, ambiguity, and safety concerns.
    """
    
    def __init__(self):
        try:
            self.similarity_model = SentenceTransformer('all-MiniLM-L6-v2')
        except Exception as e:
            logger.warning(f"Failed to load similarity model: {str(e)}")
            self.similarity_model = None
        
        # Risk patterns
        self.injection_patterns = [
            r'ignore\s+(previous|above|all)\s+instructions?',
            r'forget\s+(everything|all|previous)',
            r'you\s+are\s+now',
            r'act\s+as\s+if',
            r'pretend\s+to\s+be',
            r'system\s*:',
            r'<\|.*?\|>',
        ]
        
        self.safety_keywords = [
            'harmful', 'dangerous', 'illegal', 'violence',
            'hate', 'discrimination', 'explicit'
        ]
    
    def score_prompt(self, prompt: str) -> Dict[str, Any]:
        """
        Comprehensive risk scoring for a prompt.
        
        Returns:
            Dictionary with risk scores and classifications
        """
        results = {
            "risk_score": 0.0,
            "safety_classification": "safe",
            "checks": {},
            "warnings": []
        }
        
        # Check 1: Prompt Injection Detection
        injection_score = self._detect_prompt_injection(prompt)
        results["checks"]["prompt_injection"] = {
            "score": injection_score,
            "detected": injection_score > 0.5
        }
        results["risk_score"] += injection_score * 0.4
        
        # Check 2: Safety Classification
        safety_score = self._classify_safety(prompt)
        results["checks"]["safety"] = {
            "score": safety_score,
            "classification": "unsafe" if safety_score > 0.7 else "safe"
        }
        results["risk_score"] += safety_score * 0.4
        results["safety_classification"] = results["checks"]["safety"]["classification"]
        
        # Check 3: Ambiguity Detection
        ambiguity_score = self._detect_ambiguity(prompt)
        results["checks"]["ambiguity"] = {
            "score": ambiguity_score,
            "high_ambiguity": ambiguity_score > 0.6
        }
        results["risk_score"] += ambiguity_score * 0.2
        
        # Normalize risk score
        results["risk_score"] = min(results["risk_score"], 1.0)
        
        # Generate warnings
        if injection_score > 0.5:
            results["warnings"].append("Potential prompt injection detected")
        if safety_score > 0.7:
            results["warnings"].append("Unsafe content detected")
        if ambiguity_score > 0.6:
            results["warnings"].append("High ambiguity in prompt")
        
        return results
    
    def _detect_prompt_injection(self, prompt: str) -> float:
        """
        Detect prompt injection attempts.
        Returns score between 0 and 1.
        """
        prompt_lower = prompt.lower()
        matches = 0
        
        for pattern in self.injection_patterns:
            if re.search(pattern, prompt_lower, re.IGNORECASE):
                matches += 1
        
        # Score based on number of matches
        if matches == 0:
            return 0.0
        elif matches == 1:
            return 0.5
        elif matches >= 2:
            return 1.0
        
        return 0.0
    
    def _classify_safety(self, prompt: str) -> float:
        """
        Classify prompt for safety concerns.
        Returns score between 0 and 1.
        """
        prompt_lower = prompt.lower()
        matches = sum(1 for keyword in self.safety_keywords if keyword in prompt_lower)
        
        # Score based on keyword matches
        if matches == 0:
            return 0.0
        elif matches == 1:
            return 0.5
        elif matches >= 2:
            return 0.9
        
        return 0.0
    
    def _detect_ambiguity(self, prompt: str) -> float:
        """
        Detect ambiguity in prompt.
        Returns score between 0 and 1.
        """
        # Simple heuristics for ambiguity
        ambiguity_indicators = [
            len(prompt.split()) < 5,  # Very short
            prompt.count('?') > 2,  # Multiple questions
            prompt.count('or') > 2,  # Multiple alternatives
            'maybe' in prompt.lower(),
            'possibly' in prompt.lower(),
            'unclear' in prompt.lower()
        ]
        
        score = sum(ambiguity_indicators) / len(ambiguity_indicators)
        return min(score, 1.0)
