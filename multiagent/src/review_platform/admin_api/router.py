"""Gom router con cua Console API duoi mot tien to duy nhat."""
from fastapi import APIRouter

from review_platform.admin_api import auth_routes, dashboard_routes


router = APIRouter(prefix="/api/console/v1", tags=["console"])
router.include_router(auth_routes.router)
router.include_router(dashboard_routes.router)
