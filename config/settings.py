"""
Configuration settings for LLM control plane.
All sensitive values must be provided via environment variables.
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings."""
    
    # LLM Provider
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    llm_provider: str = "openai"
    
    # Control Plane
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    log_level: str = "INFO"
    policies_path: str = "config/policies.yaml"
    
    # Cost Configuration
    cost_tracking_enabled: bool = True
    max_cost_per_request: float = 0.10
    budget_ceiling: float = 1000.00
    auto_downgrade_enabled: bool = True
    
    # Safety Configuration
    safety_classification_enabled: bool = True
    hard_rejection_enabled: bool = True
    retry_with_strict_constraints: bool = True
    
    # Routing Configuration
    cache_enabled: bool = True
    cache_ttl: int = 3600
    routing_strategy: str = "cost_aware"
    
    # RAG Configuration
    rag_enabled: bool = True
    vector_db_url: Optional[str] = None
    rag_threshold: float = 0.7
    
    # Evaluation Configuration
    evaluation_enabled: bool = True
    hallucination_threshold: float = 0.7
    grounding_threshold: float = 0.6
    
    # Observability
    metrics_enabled: bool = True
    prometheus_port: int = 9090
    decision_logging: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
