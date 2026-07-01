"""
Asset Service - 3D asset management
Handles character models, animations, textures, and other 3D assets with metadata and versioning
"""
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
import uuid
import os

from shared.database.postgres import get_postgres
from shared.database.mongodb import get_mongodb
from shared.infrastructure.logging import get_logger

logger = get_logger(__name__)

app = FastAPI(
    title="Asset Service",
    description="3D asset management for AI Companion",
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
class AssetMetadata(BaseModel):
    """Asset metadata model"""
    asset_id: str = Field(..., description="Asset ID")
    name: str = Field(..., description="Asset name")
    asset_type: str = Field(..., description="Asset type: character, animation, texture, material, mesh, audio")
    format: str = Field(..., description="File format: fbx, glb, png, jpg, wav, etc.")
    file_size: int = Field(..., description="File size in bytes")
    version: str = Field(default="1.0.0", description="Asset version")
    description: Optional[str] = Field(default=None, description="Asset description")
    tags: List[str] = Field(default_factory=list, description="Asset tags")
    category: Optional[str] = Field(default=None, description="Asset category")
    author: Optional[str] = Field(default=None, description="Asset author")
    license: Optional[str] = Field(default=None, description="Asset license")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")
    is_public: bool = Field(default=False, description="Whether asset is public")
    download_url: Optional[str] = Field(default=None, description="Download URL")


class AssetVersion(BaseModel):
    """Asset version model"""
    version_id: str = Field(..., description="Version ID")
    asset_id: str = Field(..., description="Asset ID")
    version: str = Field(..., description="Version number")
    file_url: str = Field(..., description="File URL")
    file_size: int = Field(..., description="File size in bytes")
    changelog: Optional[str] = Field(default=None, description="Version changelog")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    is_current: bool = Field(default=False, description="Whether this is the current version")


class AssetBundle(BaseModel):
    """Asset bundle model"""
    bundle_id: str = Field(..., description="Bundle ID")
    name: str = Field(..., description="Bundle name")
    description: Optional[str] = Field(default=None, description="Bundle description")
    assets: List[str] = Field(..., description="Asset IDs in bundle")
    bundle_type: str = Field(default="character", description="Bundle type: character, scene, environment")
    target_platform: str = Field(default="all", description="Target platform: all, mobile, desktop")
    is_active: bool = Field(default=True, description="Whether bundle is active")


class AssetUpload(BaseModel):
    """Asset upload model"""
    name: str = Field(..., description="Asset name")
    asset_type: str = Field(..., description="Asset type")
    format: str = Field(..., description="File format")
    description: Optional[str] = Field(default=None, description="Asset description")
    tags: Optional[List[str]] = Field(default=None, description="Asset tags")
    category: Optional[str] = Field(default=None, description="Asset category")
    author: Optional[str] = Field(default=None, description="Asset author")
    license: Optional[str] = Field(default=None, description="Asset license")
    is_public: bool = Field(default=False, description="Whether asset is public")


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting Asset Service")
    
    # Create tables in PostgreSQL
    postgres = await get_postgres()
    
    await postgres.execute("""
        CREATE TABLE IF NOT EXISTS assets (
            asset_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(255) NOT NULL,
            asset_type VARCHAR(50) NOT NULL,
            format VARCHAR(20) NOT NULL,
            file_size BIGINT NOT NULL,
            version VARCHAR(20) DEFAULT '1.0.0',
            description TEXT,
            tags TEXT[] DEFAULT '{}',
            category VARCHAR(100),
            author VARCHAR(255),
            license VARCHAR(100),
            metadata JSONB DEFAULT '{}',
            is_public BOOLEAN DEFAULT false,
            download_url VARCHAR(500),
            current_version_id UUID,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    await postgres.execute("""
        CREATE TABLE IF NOT EXISTS asset_versions (
            version_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            asset_id UUID NOT NULL REFERENCES assets(asset_id) ON DELETE CASCADE,
            version VARCHAR(20) NOT NULL,
            file_url VARCHAR(500) NOT NULL,
            file_size BIGINT NOT NULL,
            changelog TEXT,
            is_current BOOLEAN DEFAULT false,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(asset_id, version)
        )
    """)
    
    await postgres.execute("""
        CREATE TABLE IF NOT EXISTS asset_bundles (
            bundle_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(255) NOT NULL,
            description TEXT,
            assets UUID[] NOT NULL,
            bundle_type VARCHAR(50) DEFAULT 'character',
            target_platform VARCHAR(50) DEFAULT 'all',
            is_active BOOLEAN DEFAULT true,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create indexes
    await postgres.execute("CREATE INDEX IF NOT EXISTS idx_assets_type ON assets(asset_type)")
    await postgres.execute("CREATE INDEX IF NOT EXISTS idx_assets_category ON assets(category)")
    await postgres.execute("CREATE INDEX IF NOT EXISTS idx_assets_tags ON assets USING GIN(tags)")
    await postgres.execute("CREATE INDEX IF NOT EXISTS idx_assets_public ON assets(is_public)")
    await postgres.execute("CREATE INDEX IF NOT EXISTS idx_asset_versions_asset ON asset_versions(asset_id)")
    await postgres.execute("CREATE INDEX IF NOT EXISTS idx_asset_bundles_type ON asset_bundles(bundle_type)")
    
    logger.info("Asset Service started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Asset Service")


# API endpoints
@app.post("/api/v1/assets", status_code=status.HTTP_201_CREATED)
async def create_asset(asset: AssetUpload, file_size: int, download_url: str):
    """
    Create a new asset entry
    """
    try:
        postgres = await get_postgres()
        
        asset_id = await postgres.fetchval("""
            INSERT INTO assets (
                name, asset_type, format, file_size, description, tags,
                category, author, license, is_public, download_url
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            RETURNING asset_id
        """, asset.name, asset.asset_type, asset.format, file_size,
            asset.description, asset.tags or [], asset.category,
            asset.author, asset.license, asset.is_public, download_url)
        
        # Create initial version
        version_id = await postgres.fetchval("""
            INSERT INTO asset_versions (asset_id, version, file_url, file_size, is_current)
            VALUES ($1, '1.0.0', $2, $3, true)
            RETURNING version_id
        """, asset_id, download_url, file_size)
        
        # Update asset with current version
        await postgres.execute(
            "UPDATE assets SET current_version_id = $1 WHERE asset_id = $2",
            version_id, asset_id
        )
        
        logger.info(f"Created asset {asset_id}")
        
        return {
            "asset_id": str(asset_id),
            "name": asset.name,
            "version": "1.0.0",
            "status": "created"
        }
        
    except Exception as e:
        logger.error(f"Failed to create asset: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create asset: {str(e)}"
        )


@app.get("/api/v1/assets/{asset_id}")
async def get_asset(asset_id: str):
    """
    Get asset by ID
    """
    try:
        postgres = await get_postgres()
        
        asset = await postgres.fetchrow(
            "SELECT * FROM assets WHERE asset_id = $1",
            asset_id
        )
        
        if not asset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Asset not found"
            )
        
        # Get current version
        current_version = await postgres.fetchrow(
            "SELECT * FROM asset_versions WHERE version_id = $1",
            asset["current_version_id"]
        )
        
        return {
            "asset_id": str(asset["asset_id"]),
            "name": asset["name"],
            "asset_type": asset["asset_type"],
            "format": asset["format"],
            "file_size": asset["file_size"],
            "version": asset["version"],
            "description": asset["description"],
            "tags": asset["tags"],
            "category": asset["category"],
            "author": asset["author"],
            "license": asset["license"],
            "metadata": asset["metadata"],
            "is_public": asset["is_public"],
            "download_url": asset["download_url"],
            "current_version": {
                "version_id": str(current_version["version_id"]) if current_version else None,
                "version": current_version["version"] if current_version else None,
                "file_url": current_version["file_url"] if current_version else None,
                "created_at": current_version["created_at"] if current_version else None
            },
            "created_at": asset["created_at"],
            "updated_at": asset["updated_at"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get asset: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get asset: {str(e)}"
        )


@app.get("/api/v1/assets")
async def list_assets(
    asset_type: Optional[str] = None,
    category: Optional[str] = None,
    tags: Optional[List[str]] = None,
    is_public: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0
):
    """
    List assets with filtering
    """
    try:
        postgres = await get_postgres()
        
        query = "SELECT * FROM assets WHERE 1=1"
        params = []
        param_count = 1
        
        if asset_type:
            query += f" AND asset_type = ${param_count}"
            params.append(asset_type)
            param_count += 1
        
        if category:
            query += f" AND category = ${param_count}"
            params.append(category)
            param_count += 1
        
        if tags:
            for tag in tags:
                query += f" AND ${param_count} = ANY(tags)"
                params.append(tag)
                param_count += 1
        
        if is_public is not None:
            query += f" AND is_public = ${param_count}"
            params.append(is_public)
            param_count += 1
        
        query += " ORDER BY created_at DESC LIMIT ${param_count} OFFSET ${param_count + 1}"
        params.extend([limit, offset])
        
        assets = await postgres.fetch(query, *params)
        
        results = []
        for asset in assets:
            results.append({
                "asset_id": str(asset["asset_id"]),
                "name": asset["name"],
                "asset_type": asset["asset_type"],
                "format": asset["format"],
                "version": asset["version"],
                "category": asset["category"],
                "tags": asset["tags"],
                "is_public": asset["is_public"],
                "download_url": asset["download_url"],
                "created_at": asset["created_at"]
            })
        
        return {
            "assets": results,
            "count": len(results)
        }
        
    except Exception as e:
        logger.error(f"Failed to list assets: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list assets: {str(e)}"
        )


@app.post("/api/v1/assets/{asset_id}/versions", status_code=status.HTTP_201_CREATED)
async def create_asset_version(
    asset_id: str,
    version: str,
    file_url: str,
    file_size: int,
    changelog: Optional[str] = None
):
    """
    Create a new version of an asset
    """
    try:
        postgres = await get_postgres()
        
        # Check if asset exists
        asset = await postgres.fetchrow(
            "SELECT asset_id FROM assets WHERE asset_id = $1",
            asset_id
        )
        
        if not asset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Asset not found"
            )
        
        # Check if version already exists
        existing = await postgres.fetchrow(
            "SELECT version_id FROM asset_versions WHERE asset_id = $1 AND version = $2",
            asset_id, version
        )
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Version already exists"
            )
        
        # Create new version
        version_id = await postgres.fetchval("""
            INSERT INTO asset_versions (asset_id, version, file_url, file_size, changelog)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING version_id
        """, asset_id, version, file_url, file_size, changelog)
        
        # Update all versions to not current
        await postgres.execute(
            "UPDATE asset_versions SET is_current = false WHERE asset_id = $1",
            asset_id
        )
        
        # Set new version as current
        await postgres.execute(
            "UPDATE asset_versions SET is_current = true WHERE version_id = $1",
            version_id
        )
        
        # Update asset with new version
        await postgres.execute("""
            UPDATE assets
            SET version = $2, current_version_id = $3, file_size = $4, download_url = $5, updated_at = CURRENT_TIMESTAMP
            WHERE asset_id = $1
        """, asset_id, version, version_id, file_size, file_url)
        
        logger.info(f"Created version {version} for asset {asset_id}")
        
        return {
            "version_id": str(version_id),
            "asset_id": asset_id,
            "version": version,
            "status": "created"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create asset version: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create asset version: {str(e)}"
        )


@app.get("/api/v1/assets/{asset_id}/versions")
async def get_asset_versions(asset_id: str):
    """
    Get all versions of an asset
    """
    try:
        postgres = await get_postgres()
        
        versions = await postgres.fetch(
            "SELECT * FROM asset_versions WHERE asset_id = $1 ORDER BY created_at DESC",
            asset_id
        )
        
        results = []
        for version in versions:
            results.append({
                "version_id": str(version["version_id"]),
                "version": version["version"],
                "file_url": version["file_url"],
                "file_size": version["file_size"],
                "changelog": version["changelog"],
                "is_current": version["is_current"],
                "created_at": version["created_at"]
            })
        
        return {
            "asset_id": asset_id,
            "versions": results,
            "count": len(results)
        }
        
    except Exception as e:
        logger.error(f"Failed to get asset versions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get asset versions: {str(e)}"
        )


@app.post("/api/v1/assets/bundles", status_code=status.HTTP_201_CREATED)
async def create_asset_bundle(bundle: AssetBundle):
    """
    Create an asset bundle
    """
    try:
        postgres = await get_postgres()
        
        bundle_id = await postgres.fetchval("""
            INSERT INTO asset_bundles (name, description, assets, bundle_type, target_platform, is_active)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING bundle_id
        """, bundle.name, bundle.description, bundle.assets,
            bundle.bundle_type, bundle.target_platform, bundle.is_active)
        
        logger.info(f"Created asset bundle {bundle_id}")
        
        return {
            "bundle_id": str(bundle_id),
            "name": bundle.name,
            "status": "created"
        }
        
    except Exception as e:
        logger.error(f"Failed to create asset bundle: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create asset bundle: {str(e)}"
        )


@app.get("/api/v1/assets/bundles/{bundle_id}")
async def get_asset_bundle(bundle_id: str):
    """
    Get asset bundle by ID
    """
    try:
        postgres = await get_postgres()
        
        bundle = await postgres.fetchrow(
            "SELECT * FROM asset_bundles WHERE bundle_id = $1",
            bundle_id
        )
        
        if not bundle:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Asset bundle not found"
            )
        
        # Get assets in bundle
        assets = await postgres.fetch(
            "SELECT asset_id, name, asset_type, download_url FROM assets WHERE asset_id = ANY($1)",
            bundle["assets"]
        )
        
        asset_details = []
        for asset in assets:
            asset_details.append({
                "asset_id": str(asset["asset_id"]),
                "name": asset["name"],
                "asset_type": asset["asset_type"],
                "download_url": asset["download_url"]
            })
        
        return {
            "bundle_id": str(bundle["bundle_id"]),
            "name": bundle["name"],
            "description": bundle["description"],
            "assets": asset_details,
            "bundle_type": bundle["bundle_type"],
            "target_platform": bundle["target_platform"],
            "is_active": bundle["is_active"],
            "created_at": bundle["created_at"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get asset bundle: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get asset bundle: {str(e)}"
        )


@app.put("/api/v1/assets/{asset_id}")
async def update_asset(
    asset_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    tags: Optional[List[str]] = None,
    category: Optional[str] = None,
    is_public: Optional[bool] = None
):
    """
    Update asset metadata
    """
    try:
        postgres = await get_postgres()
        
        # Build update query dynamically
        update_fields = []
        update_values = []
        param_count = 1
        
        if name is not None:
            update_fields.append(f"name = ${param_count}")
            update_values.append(name)
            param_count += 1
        
        if description is not None:
            update_fields.append(f"description = ${param_count}")
            update_values.append(description)
            param_count += 1
        
        if tags is not None:
            update_fields.append(f"tags = ${param_count}")
            update_values.append(tags)
            param_count += 1
        
        if category is not None:
            update_fields.append(f"category = ${param_count}")
            update_values.append(category)
            param_count += 1
        
        if is_public is not None:
            update_fields.append(f"is_public = ${param_count}")
            update_values.append(is_public)
            param_count += 1
        
        if update_fields:
            update_fields.append("updated_at = CURRENT_TIMESTAMP")
            query = f"""
                UPDATE assets
                SET {', '.join(update_fields)}
                WHERE asset_id = ${param_count}
            """
            update_values.append(asset_id)
            
            result = await postgres.execute(query, *update_values)
            
            if result == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Asset not found"
                )
        
        logger.info(f"Updated asset {asset_id}")
        
        return {
            "asset_id": asset_id,
            "status": "updated"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update asset: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update asset: {str(e)}"
        )


@app.delete("/api/v1/assets/{asset_id}")
async def delete_asset(asset_id: str):
    """
    Delete an asset
    """
    try:
        postgres = await get_postgres()
        
        result = await postgres.execute(
            "DELETE FROM assets WHERE asset_id = $1",
            asset_id
        )
        
        if result == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Asset not found"
            )
        
        logger.info(f"Deleted asset {asset_id}")
        
        return {
            "asset_id": asset_id,
            "status": "deleted"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete asset: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete asset: {str(e)}"
        )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "asset-service",
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8013)
