"""Model routing system for intelligent model selection"""
import logging
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

from app.schemas import ModelProvider, ChatRequest
from app.services.base_provider import BaseLLMProvider
from app.core.exceptions import RoutingError

logger = logging.getLogger(__name__)


class RoutingStrategy(str, Enum):
    """Routing strategies"""
    COST_OPTIMIZED = "cost_optimized"
    QUALITY_OPTIMIZED = "quality_optimized"
    SPEED_OPTIMIZED = "speed_optimized"
    BALANCED = "balanced"


class ModelRouter:
    """Intelligent model routing system"""
    
    def __init__(self):
        self.providers: Dict[ModelProvider, BaseLLMProvider] = {}
        self.routing_strategy = RoutingStrategy.COST_OPTIMIZED
        self.model_cache: Dict[str, Dict[str, Any]] = {}
    
    def register_provider(self, provider: BaseLLMProvider):
        """Register a provider"""
        self.providers[provider.provider_type] = provider
        logger.info(f"Registered provider: {provider.provider_type}")
    
    def set_routing_strategy(self, strategy: RoutingStrategy):
        """Set routing strategy"""
        self.routing_strategy = strategy
        logger.info(f"Routing strategy set to: {strategy}")
    
    async def select_model(
        self,
        request: ChatRequest,
        user_tier: str = "free"
    ) -> Tuple[BaseLLMProvider, str]:
        """Select the best model for the request"""
        
        # If model is explicitly specified, use it
        if request.model and not request.enable_routing:
            provider = self._get_provider_for_model(request.model)
            if provider:
                return provider, request.model
            else:
                raise RoutingError(f"Model {request.model} not available")
        
        # Get available models
        available_models = await self._get_available_models()
        
        # Filter by user tier
        available_models = self._filter_by_tier(available_models, user_tier)
        
        if not available_models:
            raise RoutingError("No models available for user tier")
        
        # Filter by capabilities
        available_models = self._filter_by_capabilities(available_models, request)
        
        if not available_models:
            raise RoutingError("No models with required capabilities")
        
        # Filter by context length
        available_models = self._filter_by_context(available_models, request)
        
        if not available_models:
            raise RoutingError("No models with sufficient context length")
        
        # Select model based on routing strategy
        selected_model = self._select_by_strategy(available_models, request)
        
        # Get provider for selected model
        provider = self._get_provider_for_model(selected_model["id"])
        
        if not provider:
            raise RoutingError(f"Provider not found for model {selected_model['id']}")
        
        logger.info(f"Selected model: {selected_model['id']} (provider: {provider.provider_type})")
        return provider, selected_model["id"]
    
    def _get_provider_for_model(self, model_name: str) -> Optional[BaseLLMProvider]:
        """Get provider for a given model"""
        # Check each provider for the model
        for provider in self.providers.values():
            try:
                # Try to get model info to verify availability
                # In production, this would be cached
                return provider
            except Exception:
                continue
        return None
    
    async def _get_available_models(self) -> List[Dict[str, Any]]:
        """Get all available models from all providers"""
        all_models = []
        
        for provider in self.providers.values():
            try:
                models = await provider.list_models()
                all_models.extend(models)
            except Exception as e:
                logger.error(f"Failed to get models from {provider.provider_type}: {e}")
        
        return all_models
    
    def _filter_by_tier(
        self,
        models: List[Dict[str, Any]],
        user_tier: str
    ) -> List[Dict[str, Any]]:
        """Filter models by user subscription tier"""
        if user_tier == "enterprise":
            # All models available
            return models
        elif user_tier == "premium":
            # Exclude top-tier models
            return [m for m in models if m.get("priority", 0) < 15]
        else:
            # Free tier - only basic models
            return [m for m in models if m.get("priority", 0) < 10]
    
    def _filter_by_capabilities(
        self,
        models: List[Dict[str, Any]],
        request: ChatRequest
    ) -> List[Dict[str, Any]]:
        """Filter models by required capabilities"""
        filtered = models
        
        # Filter by function calling
        if request.functions:
            filtered = [m for m in filtered if m.get("supports_function_calling", False)]
        
        # Filter by streaming
        if request.stream:
            filtered = [m for m in filtered if m.get("supports_streaming", True)]
        
        return filtered
    
    def _filter_by_context(
        self,
        models: List[Dict[str, Any]],
        request: ChatRequest
    ) -> List[Dict[str, Any]]:
        """Filter models by context length requirements"""
        # Estimate required context length
        required_tokens = sum(len(msg.content.split()) * 1.3 for msg in request.messages)
        required_tokens += request.max_tokens
        
        filtered = [
            m for m in models
            if m.get("max_context_length", 0) >= required_tokens
        ]
        
        return filtered
    
    def _select_by_strategy(
        self,
        models: List[Dict[str, Any]],
        request: ChatRequest
    ) -> Dict[str, Any]:
        """Select model based on routing strategy"""
        
        if self.routing_strategy == RoutingStrategy.COST_OPTIMIZED:
            return self._select_by_cost(models)
        elif self.routing_strategy == RoutingStrategy.QUALITY_OPTIMIZED:
            return self._select_by_quality(models)
        elif self.routing_strategy == RoutingStrategy.SPEED_OPTIMIZED:
            return self._select_by_speed(models)
        else:  # BALANCED
            return self._select_balanced(models)
    
    def _select_by_cost(self, models: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Select model with lowest cost"""
        # Calculate total cost estimate
        for model in models:
            input_cost = model.get("input_cost_per_1k", 0.0)
            output_cost = model.get("output_cost_per_1k", 0.0)
            model["total_cost"] = input_cost + output_cost
        
        # Sort by cost
        models.sort(key=lambda m: m.get("total_cost", float("inf")))
        
        return models[0]
    
    def _select_by_quality(self, models: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Select model with highest quality"""
        # Sort by quality score (descending)
        models.sort(key=lambda m: m.get("quality_score", 0.0), reverse=True)
        
        return models[0]
    
    def _select_by_speed(self, models: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Select model with fastest response (heuristic)"""
        # Use priority as speed indicator (lower priority = faster)
        models.sort(key=lambda m: m.get("priority", 999))
        
        return models[0]
    
    def _select_balanced(self, models: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Select model with balanced cost/quality"""
        # Calculate balanced score
        for model in models:
            quality = model.get("quality_score", 0.0)
            cost = model.get("input_cost_per_1k", 0.0) + model.get("output_cost_per_1k", 0.0)
            
            # Balance score = quality / cost (higher is better)
            if cost > 0:
                model["balance_score"] = quality / cost
            else:
                model["balance_score"] = quality
        
        # Sort by balance score
        models.sort(key=lambda m: m.get("balance_score", 0.0), reverse=True)
        
        return models[0]
    
    async def get_provider(self, provider_type: ModelProvider) -> Optional[BaseLLMProvider]:
        """Get provider by type"""
        return self.providers.get(provider_type)
    
    async def health_check(self) -> Dict[str, bool]:
        """Check health of all providers"""
        health_status = {}
        
        for provider_type, provider in self.providers.items():
            try:
                health = await provider.health_check()
                health_status[provider_type.value] = health
            except Exception as e:
                logger.error(f"Health check failed for {provider_type}: {e}")
                health_status[provider_type.value] = False
        
        return health_status


# Global router instance
model_router = ModelRouter()
