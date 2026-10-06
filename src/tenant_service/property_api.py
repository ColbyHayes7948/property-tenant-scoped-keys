from fastapi import FastAPI, HTTPException

from .infrai_client import InfraiClient, InfraiError
from .property_lifecycle import (
    OffboardingReceipt,
    PropertyLifecycle,
    TenantAccess,
    TenantOffboarding,
    TenantOnboarding,
)

app = FastAPI(title="Property tenant access")


def lifecycle() -> PropertyLifecycle:
    return PropertyLifecycle(InfraiClient())


@app.post("/tenants", response_model=TenantAccess, status_code=201)
def onboard_tenant(request: TenantOnboarding) -> TenantAccess:
    try:
        return lifecycle().onboard(request)
    except InfraiError as error:
        raise HTTPException(status_code=error.status_code, detail=error.detail) from error


@app.post("/tenants/offboard", response_model=OffboardingReceipt)
def offboard_tenant(request: TenantOffboarding) -> OffboardingReceipt:
    try:
        return lifecycle().offboard(request)
    except InfraiError as error:
        raise HTTPException(status_code=error.status_code, detail=error.detail) from error
