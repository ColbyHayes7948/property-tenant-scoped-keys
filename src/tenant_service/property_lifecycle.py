from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .infrai_client import InfraiClient


class MaintenanceRequest(BaseModel):
    summary: str = Field(min_length=1)
    priority: Literal["routine", "urgent"]
    opened_at: datetime


class TenantDocument(BaseModel):
    document_id: str = Field(min_length=1)
    kind: Literal["lease", "consent", "inspection"]
    retained_until: date


class InspectionReminder(BaseModel):
    property_id: str = Field(min_length=1)
    due_on: date


class TenantOnboarding(BaseModel):
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    name: str = Field(min_length=1)
    property_id: str = Field(min_length=1)
    maintenance_requests: list[MaintenanceRequest] = Field(default_factory=list)
    documents: list[TenantDocument] = Field(default_factory=list)
    inspection_reminders: list[InspectionReminder] = Field(default_factory=list)
    request_id: UUID = Field(default_factory=uuid4)


class TenantAccess(BaseModel):
    user_id: str
    key_id: str
    api_key: str


class TenantOffboarding(BaseModel):
    user_id: str = Field(min_length=1)
    key_id: str = Field(min_length=1)


class OffboardingReceipt(BaseModel):
    user_id: str
    key_id: str
    key_revoked: bool
    user_deleted: bool


class PropertyLifecycle:
    def __init__(self, infrai: InfraiClient) -> None:
        self.infrai = infrai

    def onboard(self, request: TenantOnboarding) -> TenantAccess:
        handoff = self.infrai.create_user(
            {
                "email": request.email,
                "name": request.name,
                "metadata": {
                    "property_id": request.property_id,
                    "maintenance_requests": [item.model_dump(mode="json") for item in request.maintenance_requests],
                    "documents": [item.model_dump(mode="json") for item in request.documents],
                    "inspection_reminders": [item.model_dump(mode="json") for item in request.inspection_reminders],
                },
                "idempotency_key": f"tenant-user-{request.request_id}",
            }
        )
        user_id = str(handoff["user_id"])
        key = self.infrai.create_key(
            {
                "project_id": user_id,
                "name": f"tenant:{user_id}:property:{request.property_id}",
                "scopes": ["auth.user.create", "auth.user.delete"],
                "idempotency_key": f"tenant-key-{request.request_id}",
            }
        )
        return TenantAccess(
            user_id=user_id,
            key_id=str(key["id"]),
            api_key=str(key["key"]),
        )

    def offboard(self, request: TenantOffboarding) -> OffboardingReceipt:
        self.infrai.revoke_key(request.key_id)
        self.infrai.delete_user(request.user_id)
        return OffboardingReceipt(
            user_id=request.user_id,
            key_id=request.key_id,
            key_revoked=True,
            user_deleted=True,
        )
