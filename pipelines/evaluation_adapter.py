"""
Evaluation adapter for post-generation quality checks.
"""
from typing import Dict, Any, Optional
from sentence_transformers import SentenceTransformer
import logging

logger = logging.getLogger(__name__)


class EvaluationAdapter:
    """
    Adapter for evaluation pipeline.
    """
    
    def __init__(self):
        try:
            self.similarity_model = SentenceTransformer('all-MiniLM-L6-v2')
        except Exception as e:
            logger.warning(f"Failed to load similarity model: {str(e)}")
            self.similarity_model = None
    
    async def evaluate(
        self,
        answer: str,
        context: Optional[str] = None,
        hallucination_threshold: float = 0.7,
        grounding_threshold: float = 0.6
    ) -> Dict[str, Any]:
        """
        Evaluate output quality.
        
        Returns:
            Dictionary with evaluation scores
        """
        results = {
            "hallucination_score": 0.0,
            "grounding_score": 0.0,
            "is_hallucination": False,
            "is_grounded": False
        }
        
        if context and self.similarity_model:
            # Calculate grounding score
            try:
                answer_emb = self.similarity_model.encode([answer], convert_to_numpy=True)[0]
                context_emb = self.similarity_model.encode([context], convert_to_numpy=True)[0]
                
                import numpy as np
                similarity = np.dot(answer_emb, context_emb) / (
                    np.linalg.norm(answer_emb) * np.linalg.norm(context_emb)
                )
                
                results["grounding_score"] = float(max(0.0, similarity))
                results["is_grounded"] = results["grounding_score"] >= grounding_threshold
                
                # Hallucination is inverse of grounding
                results["hallucination_score"] = 1.0 - results["grounding_score"]
                results["is_hallucination"] = results["hallucination_score"] >= hallucination_threshold
            except Exception as e:
                logger.error(f"Evaluation failed: {str(e)}")
        
        return results
