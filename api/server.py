"""
FastAPI server for LLM control plane.
Handles request lifecycle governance.
"""
import asyncio
import time
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import logging

from control.policy_engine import PolicyEngine
from control.risk_scorer import RiskScorer
from control.cost_model import CostModel
from control.router import Router
from decisions.enforcement import DecisionEnforcer
from pipelines.inference_adapter import InferenceAdapter
from pipelines.rag_adapter import RAGAdapter
from pipelines.evaluation_adapter import EvaluationAdapter
from config.settings import settings

logger = logging.getLogger(__name__)

app = FastAPI(
    title="LLM Control Plane",
    description="Production-grade runtime governance for LLM systems",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
policy_engine: Optional[PolicyEngine] = None
risk_scorer: Optional[RiskScorer] = None
cost_model: Optional[CostModel] = None
router: Optional[Router] = None
enforcer: Optional[DecisionEnforcer] = None
inference_adapter: Optional[InferenceAdapter] = None
rag_adapter: Optional[RAGAdapter] = None
evaluation_adapter: Optional[EvaluationAdapter] = None


class LLMRequest(BaseModel):
    """LLM request model."""
    prompt: str = Field(..., min_length=1)
    model: Optional[str] = None
    max_tokens: int = Field(100, ge=1, le=4096)
    temperature: float = Field(0.7, ge=0.0, le=2.0)
    use_rag: Optional[bool] = None
    request_id: Optional[str] = None


class LLMResponse(BaseModel):
    """LLM response model."""
    text: str
    request_id: str
    decision_trace: Dict[str, Any]
    cost: float
    latency_ms: float
    enforcement_action: str


@app.on_event("startup")
async def startup():
    """Initialize services."""
    global policy_engine, risk_scorer, cost_model, router, enforcer
    global inference_adapter, rag_adapter, evaluation_adapter
    
    # Initialize components
    policy_engine = PolicyEngine(settings.policies_path)
    risk_scorer = RiskScorer()
    cost_model = CostModel()
    router = Router(policy_engine, cost_model, settings.cache_enabled)
    enforcer = DecisionEnforcer(policy_engine)
    
    # Initialize adapters
    inference_adapter = InferenceAdapter(
        provider=settings.llm_provider,
        api_key=settings.openai_api_key if settings.llm_provider == "openai" else settings.anthropic_api_key
    )
    rag_adapter = RAGAdapter(settings.vector_db_url)
    evaluation_adapter = EvaluationAdapter()
    
    logger.info("Control plane initialized")


@app.post("/api/v1/llm/generate", response_model=LLMResponse)
async def generate(request: LLMRequest):
    """
    Generate LLM output with full control plane governance.
    
    Request lifecycle:
    1. Pre-generation checks (risk, safety, cost)
    2. Routing decision (model, RAG, cache)
    3. Generation
    4. Post-generation evaluation
    5. Policy enforcement
    """
    start_time = time.time()
    request_id = request.request_id or f"req_{int(time.time())}"
    
    decision_trace = {
        "request_id": request_id,
        "pre_generation": {},
        "routing": {},
        "generation": {},
        "post_generation": {},
        "enforcement": {}
    }
    
    try:
        # PRE-GENERATION CHECKS
        # 1. Risk scoring
        risk_results = risk_scorer.score_prompt(request.prompt)
        decision_trace["pre_generation"]["risk_scoring"] = risk_results
        
        # 2. Safety check
        safety_check = policy_engine.check_safety_policy(risk_results["risk_score"])
        decision_trace["pre_generation"]["safety_check"] = safety_check
        
        if safety_check["action"] == "block":
            raise HTTPException(
                status_code=403,
                detail=f"Request blocked: {safety_check['reason']}"
            )
        
        # 3. Cost estimation
        cost_estimate = cost_model.estimate_cost(
            prompt=request.prompt,
            model=request.model or "gpt-4-turbo-preview",
            estimated_output_tokens=request.max_tokens
        )
        decision_trace["pre_generation"]["cost_estimate"] = cost_estimate
        
        # 4. Cost policy check
        cost_check = policy_engine.check_cost_policy(cost_estimate["estimated_cost"])
        decision_trace["pre_generation"]["cost_check"] = cost_check
        
        if cost_check["action"] == "block":
            raise HTTPException(
                status_code=402,
                detail=f"Request blocked: {cost_check['reason']}"
            )
        
        # ROUTING DECISION
        routing_decision = router.route(request.prompt)
        decision_trace["routing"] = routing_decision
        
        # Determine final model
        final_model = request.model or routing_decision["model"]
        
        # GENERATION
        context = None
        if routing_decision["use_rag"]:
            rag_results = await rag_adapter.retrieve(request.prompt)
            context = rag_results.get("context", "")
            decision_trace["generation"]["rag"] = rag_results
        
        # Generate
        generation_start = time.time()
        gen_result = await inference_adapter.generate(
            prompt=request.prompt,
            model=final_model,
            max_tokens=request.max_tokens,
            temperature=request.temperature
        )
        generation_time = (time.time() - generation_start) * 1000
        
        decision_trace["generation"]["result"] = {
            "model": final_model,
            "tokens_used": gen_result.get("tokens_used", 0),
            "generation_time_ms": generation_time
        }
        
        output_text = gen_result["text"]
        
        # POST-GENERATION EVALUATION
        eval_results = await evaluation_adapter.evaluate(
            answer=output_text,
            context=context,
            hallucination_threshold=settings.hallucination_threshold,
            grounding_threshold=settings.grounding_threshold
        )
        decision_trace["post_generation"]["evaluation"] = eval_results
        
        # Record actual cost
        actual_cost = cost_estimate["estimated_cost"]  # Simplified
        cost_model.record_cost(actual_cost, final_model)
        
        # ENFORCEMENT
        total_latency = (time.time() - start_time) * 1000
        enforcement_decision = enforcer.enforce(
            output=output_text,
            evaluation_results=eval_results,
            cost=actual_cost,
            latency_ms=total_latency
        )
        decision_trace["enforcement"] = enforcement_decision
        
        return LLMResponse(
            text=enforcement_decision["output"],
            request_id=request_id,
            decision_trace=decision_trace,
            cost=actual_cost,
            latency_ms=total_latency,
            enforcement_action=enforcement_decision["action"]
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


@app.get("/health")
async def health():
    """Health check."""
    return {
        "status": "healthy",
        "components": {
            "policy_engine": policy_engine is not None,
            "risk_scorer": risk_scorer is not None,
            "cost_model": cost_model is not None,
            "router": router is not None
        }
    }


@app.get("/metrics")
async def metrics():
    """Get control plane metrics."""
    if not cost_model:
        return {}
    
    return {
        "total_cost": cost_model.total_cost,
        "request_count": cost_model.request_count,
        "avg_cost_per_request": cost_model.total_cost / max(cost_model.request_count, 1)
    }
