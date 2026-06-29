"""
Plugin SDK Service - Custom plugins, extension system, and API access
"""
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
import uuid
import os
import json
import zipfile
import shutil

from shared.database.mongodb import get_mongodb
from shared.database.redis import get_redis
from shared.infrastructure.logging import get_logger

logger = get_logger(__name__)

app = FastAPI(
    title="Plugin SDK Service",
    description="Custom plugins, extension system, and API access for AI Companion",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models
class PluginType(str):
    """Plugin types"""
    INTEGRATION = "integration"
    EXTENSION = "extension"
    THEME = "theme"
    BEHAVIOR = "behavior"


class PluginStatus(str):
    """Plugin status"""
    DEVELOPMENT = "development"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    DEPRECATED = "deprecated"


class Plugin(BaseModel):
    """Plugin model"""
    plugin_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., description="Plugin name")
    version: str = Field(..., description="Plugin version (semver)")
    author: str = Field(..., description="Plugin author")
    description: str = Field(..., description="Plugin description")
    type: PluginType = Field(..., description="Plugin type")
    status: PluginStatus = Field(default=PluginStatus.DEVELOPMENT, description="Plugin status")
    api_endpoints: List[str] = Field(default_factory=list, description="API endpoints provided by plugin")
    permissions: List[str] = Field(default_factory=list, description="Required permissions")
    dependencies: List[str] = Field(default_factory=list, description="Plugin dependencies")
    config_schema: Optional[Dict[str, Any]] = Field(default=None, description="Configuration schema")
    icon_url: Optional[str] = Field(default=None, description="Plugin icon URL")
    screenshots: List[str] = Field(default_factory=list, description="Plugin screenshot URLs")
    downloads: int = Field(default=0, description="Download count")
    rating: float = Field(default=0.0, description="Average rating (0-5)")
    reviews_count: int = Field(default=0, description="Number of reviews")
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class PluginInstallation(BaseModel):
    """Plugin installation model"""
    installation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = Field(..., description="User ID")
    plugin_id: str = Field(..., description="Plugin ID")
    config: Dict[str, Any] = Field(default_factory=dict, description="Plugin configuration")
    installed_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    enabled: bool = Field(default=True, description="Whether plugin is enabled")


class PluginAPIRequest(BaseModel):
    """Plugin API request model"""
    plugin_id: str = Field(..., description="Plugin ID")
    endpoint: str = Field(..., description="API endpoint")
    method: str = Field(default="GET", description="HTTP method")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Request parameters")


class PluginAPIResponse(BaseModel):
    """Plugin API response model"""
    plugin_id: str = Field(..., description="Plugin ID")
    endpoint: str = Field(..., description="API endpoint")
    response: Dict[str, Any] = Field(..., description="API response")
    status_code: int = Field(..., description="HTTP status code")


class PluginReview(BaseModel):
    """Plugin review model"""
    review_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    plugin_id: str = Field(..., description="Plugin ID")
    user_id: str = Field(..., description="User ID")
    rating: int = Field(..., ge=1, le=5, description="Rating (1-5)")
    comment: str = Field(..., description="Review comment")
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# Plugin registry
class PluginRegistry:
    """Manages plugin registry and distribution"""
    
    def __init__(self):
        self.plugin_storage_path = "./plugins"
        self._ensure_storage_directory()
    
    def _ensure_storage_directory(self):
        """Ensure plugin storage directory exists"""
        if not os.path.exists(self.plugin_storage_path):
            os.makedirs(self.plugin_storage_path)
    
    async def register_plugin(self, plugin: Plugin) -> str:
        """Register a new plugin"""
        db = await get_mongodb()
        plugins = db["plugins"]
        
        # Check if plugin with same name and version exists
        existing = await plugins.find_one({
            "name": plugin.name,
            "version": plugin.version
        })
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Plugin {plugin.name} v{plugin.version} already exists"
            )
        
        # Store plugin in database
        await plugins.insert_one(plugin.dict())
        
        logger.info(f"Registered plugin {plugin.name} v{plugin.version}")
        
        return plugin.plugin_id
    
    async def get_plugin(self, plugin_id: str) -> Optional[Plugin]:
        """Get a plugin by ID"""
        db = await get_mongodb()
        plugins = db["plugins"]
        
        plugin_doc = await plugins.find_one({"plugin_id": plugin_id})
        
        if not plugin_doc:
            return None
        
        plugin_doc.pop("_id", None)
        return Plugin(**plugin_doc)
    
    async def list_plugins(
        self,
        type: Optional[PluginType] = None,
        status: Optional[PluginStatus] = None,
        limit: int = 50
    ) -> List[Plugin]:
        """List plugins with optional filters"""
        db = await get_mongodb()
        plugins = db["plugins"]
        
        query = {}
        if type:
            query["type"] = type
        if status:
            query["status"] = status
        
        cursor = plugins.find(query).sort("created_at", -1).limit(limit)
        
        result = []
        async for plugin_doc in cursor:
            plugin_doc.pop("_id", None)
            result.append(Plugin(**plugin_doc))
        
        return result
    
    async def update_plugin(self, plugin_id: str, updates: Dict[str, Any]) -> bool:
        """Update a plugin"""
        db = await get_mongodb()
        plugins = db["plugins"]
        
        updates["updated_at"] = datetime.utcnow().isoformat()
        
        result = await plugins.update_one(
            {"plugin_id": plugin_id},
            {"$set": updates}
        )
        
        return result.modified_count > 0
    
    async def delete_plugin(self, plugin_id: str) -> bool:
        """Delete a plugin"""
        db = await get_mongodb()
        plugins = db["plugins"]
        
        result = await plugins.delete_one({"plugin_id": plugin_id})
        
        if result.deleted_count > 0:
            # Remove plugin files
            plugin_path = os.path.join(self.plugin_storage_path, plugin_id)
            if os.path.exists(plugin_path):
                shutil.rmtree(plugin_path)
        
        return result.deleted_count > 0


# Plugin installation manager
class PluginInstallationManager:
    """Manages plugin installation and configuration"""
    
    async def install_plugin(
        self,
        user_id: str,
        plugin_id: str,
        config: Optional[Dict[str, Any]] = None
    ) -> PluginInstallation:
        """Install a plugin for a user"""
        db = await get_mongodb()
        installations = db["plugin_installations"]
        
        # Check if plugin exists
        registry = PluginRegistry()
        plugin = await registry.get_plugin(plugin_id)
        
        if not plugin:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Plugin {plugin_id} not found"
            )
        
        # Check if already installed
        existing = await installations.find_one({
            "user_id": user_id,
            "plugin_id": plugin_id
        })
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Plugin {plugin_id} already installed for user {user_id}"
            )
        
        # Create installation record
        installation = PluginInstallation(
            user_id=user_id,
            plugin_id=plugin_id,
            config=config or {}
        )
        
        await installations.insert_one(installation.dict())
        
        # Increment download count
        await registry.update_plugin(plugin_id, {
            "downloads": plugin.downloads + 1
        })
        
        logger.info(f"Installed plugin {plugin_id} for user {user_id}")
        
        return installation
    
    async def uninstall_plugin(self, user_id: str, plugin_id: str) -> bool:
        """Uninstall a plugin for a user"""
        db = await get_mongodb()
        installations = db["plugin_installations"]
        
        result = await installations.delete_one({
            "user_id": user_id,
            "plugin_id": plugin_id
        })
        
        return result.deleted_count > 0
    
    async def get_user_plugins(self, user_id: str) -> List[PluginInstallation]:
        """Get installed plugins for a user"""
        db = await get_mongodb()
        installations = db["plugin_installations"]
        
        cursor = installations.find({"user_id": user_id})
        
        result = []
        async for installation_doc in cursor:
            installation_doc.pop("_id", None)
            result.append(PluginInstallation(**installation_doc))
        
        return result
    
    async def enable_plugin(self, user_id: str, plugin_id: str) -> bool:
        """Enable a plugin for a user"""
        db = await get_mongodb()
        installations = db["plugin_installations"]
        
        result = await installations.update_one(
            {"user_id": user_id, "plugin_id": plugin_id},
            {"$set": {"enabled": True}}
        )
        
        return result.modified_count > 0
    
    async def disable_plugin(self, user_id: str, plugin_id: str) -> bool:
        """Disable a plugin for a user"""
        db = await get_mongodb()
        installations = db["plugin_installations"]
        
        result = await installations.update_one(
            {"user_id": user_id, "plugin_id": plugin_id},
            {"$set": {"enabled": False}}
        )
        
        return result.modified_count > 0


# Plugin API manager
class PluginAPIManager:
    """Manages plugin API calls"""
    
    async def call_plugin_api(
        self,
        user_id: str,
        request: PluginAPIRequest
    ) -> PluginAPIResponse:
        """Call a plugin API endpoint"""
        # Check if plugin is installed and enabled
        installation_manager = PluginInstallationManager()
        installations = await installation_manager.get_user_plugins(user_id)
        
        user_installation = None
        for installation in installations:
            if installation.plugin_id == request.plugin_id and installation.enabled:
                user_installation = installation
                break
        
        if not user_installation:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Plugin {request.plugin_id} not installed or disabled for user {user_id}"
            )
        
        # Get plugin configuration
        config = user_installation.config
        
        # Call plugin API (placeholder)
        # In production, this would actually call the plugin's API
        response = await self._execute_plugin_call(request, config)
        
        return PluginAPIResponse(
            plugin_id=request.plugin_id,
            endpoint=request.endpoint,
            response=response,
            status_code=200
        )
    
    async def _execute_plugin_call(
        self,
        request: PluginAPIRequest,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute plugin API call"""
        # Placeholder implementation
        # In production, this would:
        # 1. Load the plugin code
        # 2. Execute the requested endpoint
        # 3. Return the response
        
        plugin_id = request.plugin_id
        
        # Example: Spotify plugin
        if "spotify" in plugin_id.lower():
            return await self._call_spotify_api(request, config)
        
        # Example: Notion plugin
        elif "notion" in plugin_id.lower():
            return await self._call_notion_api(request, config)
        
        # Default response
        return {
            "status": "success",
            "message": f"Called {request.endpoint} on plugin {plugin_id}",
            "parameters": request.parameters
        }
    
    async def _call_spotify_api(
        self,
        request: PluginAPIRequest,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Call Spotify API (placeholder)"""
        # In production, this would use the Spotify API
        return {
            "status": "success",
            "action": request.endpoint,
            "result": f"Spotify {request.endpoint} executed"
        }
    
    async def _call_notion_api(
        self,
        request: PluginAPIRequest,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Call Notion API (placeholder)"""
        # In production, this would use the Notion API
        return {
            "status": "success",
            "action": request.endpoint,
            "result": f"Notion {request.endpoint} executed"
        }


# Plugin review manager
class PluginReviewManager:
    """Manages plugin reviews and ratings"""
    
    async def add_review(self, review: PluginReview) -> str:
        """Add a review for a plugin"""
        db = await get_mongodb()
        reviews = db["plugin_reviews"]
        
        # Store review
        await reviews.insert_one(review.dict())
        
        # Update plugin rating
        registry = PluginRegistry()
        plugin = await registry.get_plugin(review.plugin_id)
        
        if plugin:
            # Calculate new average rating
            all_reviews = await self.get_plugin_reviews(review.plugin_id)
            total_rating = sum(r.rating for r in all_reviews)
            new_rating = total_rating / len(all_reviews)
            
            await registry.update_plugin(review.plugin_id, {
                "rating": new_rating,
                "reviews_count": plugin.reviews_count + 1
            })
        
        logger.info(f"Added review for plugin {review.plugin_id}")
        
        return review.review_id
    
    async def get_plugin_reviews(self, plugin_id: str) -> List[PluginReview]:
        """Get reviews for a plugin"""
        db = await get_mongodb()
        reviews = db["plugin_reviews"]
        
        cursor = reviews.find({"plugin_id": plugin_id}).sort("created_at", -1)
        
        result = []
        async for review_doc in cursor:
            review_doc.pop("_id", None)
            result.append(PluginReview(**review_doc))
        
        return result


# Global instances
plugin_registry = PluginRegistry()
plugin_installation_manager = PluginInstallationManager()
plugin_api_manager = PluginAPIManager()
plugin_review_manager = PluginReviewManager()


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting Plugin SDK Service")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Plugin SDK Service")


# API endpoints
@app.post("/api/v1/plugins/register", status_code=status.HTTP_201_CREATED)
async def register_plugin(plugin: Plugin):
    """
    Register a new plugin
    """
    try:
        plugin_id = await plugin_registry.register_plugin(plugin)
        
        return {
            "plugin_id": plugin_id,
            "status": "registered"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to register plugin: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register plugin: {str(e)}"
        )


@app.get("/api/v1/plugins/{plugin_id}")
async def get_plugin(plugin_id: str):
    """
    Get a plugin by ID
    """
    try:
        plugin = await plugin_registry.get_plugin(plugin_id)
        
        if not plugin:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Plugin {plugin_id} not found"
            )
        
        return plugin.dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get plugin: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get plugin: {str(e)}"
        )


@app.get("/api/v1/plugins")
async def list_plugins(
    type: Optional[PluginType] = None,
    status: Optional[PluginStatus] = None,
    limit: int = 50
):
    """
    List plugins with optional filters
    """
    try:
        plugins = await plugin_registry.list_plugins(type, status, limit)
        
        return {
            "plugins": [plugin.dict() for plugin in plugins],
            "count": len(plugins)
        }
        
    except Exception as e:
        logger.error(f"Failed to list plugins: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list plugins: {str(e)}"
        )


@app.put("/api/v1/plugins/{plugin_id}")
async def update_plugin(plugin_id: str, updates: Dict[str, Any]):
    """
    Update a plugin
    """
    try:
        success = await plugin_registry.update_plugin(plugin_id, updates)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Plugin {plugin_id} not found"
            )
        
        return {
            "plugin_id": plugin_id,
            "status": "updated"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update plugin: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update plugin: {str(e)}"
        )


@app.delete("/api/v1/plugins/{plugin_id}")
async def delete_plugin(plugin_id: str):
    """
    Delete a plugin
    """
    try:
        success = await plugin_registry.delete_plugin(plugin_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Plugin {plugin_id} not found"
            )
        
        return {
            "plugin_id": plugin_id,
            "status": "deleted"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete plugin: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete plugin: {str(e)}"
        )


@app.post("/api/v1/plugins/install", status_code=status.HTTP_201_CREATED)
async def install_plugin(user_id: str, plugin_id: str, config: Optional[Dict[str, Any]] = None):
    """
    Install a plugin for a user
    """
    try:
        installation = await plugin_installation_manager.install_plugin(
            user_id,
            plugin_id,
            config
        )
        
        return installation.dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to install plugin: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to install plugin: {str(e)}"
        )


@app.delete("/api/v1/plugins/installations/{user_id}/{plugin_id}")
async def uninstall_plugin(user_id: str, plugin_id: str):
    """
    Uninstall a plugin for a user
    """
    try:
        success = await plugin_installation_manager.uninstall_plugin(user_id, plugin_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Plugin {plugin_id} not installed for user {user_id}"
            )
        
        return {
            "user_id": user_id,
            "plugin_id": plugin_id,
            "status": "uninstalled"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to uninstall plugin: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to uninstall plugin: {str(e)}"
        )


@app.get("/api/v1/plugins/installations/{user_id}")
async def get_user_plugins(user_id: str):
    """
    Get installed plugins for a user
    """
    try:
        installations = await plugin_installation_manager.get_user_plugins(user_id)
        
        return {
            "user_id": user_id,
            "installations": [installation.dict() for installation in installations],
            "count": len(installations)
        }
        
    except Exception as e:
        logger.error(f"Failed to get user plugins: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user plugins: {str(e)}"
        )


@app.put("/api/v1/plugins/installations/{user_id}/{plugin_id}/enable")
async def enable_plugin(user_id: str, plugin_id: str):
    """
    Enable a plugin for a user
    """
    try:
        success = await plugin_installation_manager.enable_plugin(user_id, plugin_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Plugin {plugin_id} not installed for user {user_id}"
            )
        
        return {
            "user_id": user_id,
            "plugin_id": plugin_id,
            "status": "enabled"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to enable plugin: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to enable plugin: {str(e)}"
        )


@app.put("/api/v1/plugins/installations/{user_id}/{plugin_id}/disable")
async def disable_plugin(user_id: str, plugin_id: str):
    """
    Disable a plugin for a user
    """
    try:
        success = await plugin_installation_manager.disable_plugin(user_id, plugin_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Plugin {plugin_id} not installed for user {user_id}"
            )
        
        return {
            "user_id": user_id,
            "plugin_id": plugin_id,
            "status": "disabled"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to disable plugin: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to disable plugin: {str(e)}"
        )


@app.post("/api/v1/plugins/api/call")
async def call_plugin_api(user_id: str, request: PluginAPIRequest):
    """
    Call a plugin API endpoint
    """
    try:
        response = await plugin_api_manager.call_plugin_api(user_id, request)
        
        return response.dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to call plugin API: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to call plugin API: {str(e)}"
        )


@app.post("/api/v1/plugins/reviews", status_code=status.HTTP_201_CREATED)
async def add_plugin_review(review: PluginReview):
    """
    Add a review for a plugin
    """
    try:
        review_id = await plugin_review_manager.add_review(review)
        
        return {
            "review_id": review_id,
            "status": "added"
        }
        
    except Exception as e:
        logger.error(f"Failed to add review: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add review: {str(e)}"
        )


@app.get("/api/v1/plugins/{plugin_id}/reviews")
async def get_plugin_reviews(plugin_id: str):
    """
    Get reviews for a plugin
    """
    try:
        reviews = await plugin_review_manager.get_plugin_reviews(plugin_id)
        
        return {
            "plugin_id": plugin_id,
            "reviews": [review.dict() for review in reviews],
            "count": len(reviews)
        }
        
    except Exception as e:
        logger.error(f"Failed to get plugin reviews: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get plugin reviews: {str(e)}"
        )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "plugin-service",
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8013)
