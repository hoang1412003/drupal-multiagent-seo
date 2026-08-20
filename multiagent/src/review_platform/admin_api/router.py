"""Gom router con cua Console API duoi mot tien to duy nhat."""
from fastapi import APIRouter

from review_platform.admin_api import (
    audit_routes,
    auth_routes,
    connection_routes,
    dashboard_routes,
    filter_routes,
    job_routes,
    readonly_routes,
    review_routes,
)


router = APIRouter(prefix="/api/console/v1", tags=["console"])
router.include_router(audit_routes.router)
router.include_router(auth_routes.router)
router.include_router(connection_routes.router)
router.include_router(dashboard_routes.router)
router.include_router(filter_routes.router)
router.include_router(job_routes.router)
router.include_router(readonly_routes.router)
router.include_router(review_routes.router)
