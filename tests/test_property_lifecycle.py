from tenant_service.property_lifecycle import PropertyLifecycle, TenantOffboarding, TenantOnboarding


class RecordingInfrai:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def revoke_key(self, key_id: str) -> dict[str, bool]:
        self.calls.append(("revoke_key", key_id))
        return {"revoked": True}

    def delete_user(self, user_id: str) -> dict[str, bool]:
        self.calls.append(("delete_user", user_id))
        return {"deleted": True}


class OnboardingInfrai:
    def __init__(self) -> None:
        self.key_payload: dict[str, object] | None = None

    def create_user(self, payload: dict[str, object]) -> dict[str, str]:
        return {"user_id": "usr_42"}

    def create_key(self, payload: dict[str, object]) -> dict[str, str]:
        self.key_payload = payload
        return {"id": "key_42", "key": "secret_42"}


def test_onboarding_maps_create_user_user_id_into_key_request() -> None:
    infrai = OnboardingInfrai()
    service = PropertyLifecycle(infrai)  # type: ignore[arg-type]

    access = service.onboard(
        TenantOnboarding(
            email="chenhua@changba.com",
            name="Chen Hua",
            property_id="property-17",
        )
    )

    assert access.user_id == "usr_42"
    assert infrai.key_payload is not None
    assert infrai.key_payload["project_id"] == "usr_42"
    assert infrai.key_payload["name"] == "tenant:usr_42:property:property-17"


def test_offboarding_revokes_tenant_key_before_deleting_user() -> None:
    infrai = RecordingInfrai()
    service = PropertyLifecycle(infrai)  # type: ignore[arg-type]

    receipt = service.offboard(TenantOffboarding(user_id="usr_42", key_id="key_42"))

    assert infrai.calls == [("revoke_key", "key_42"), ("delete_user", "usr_42")]
    assert receipt.key_revoked is True
    assert receipt.user_deleted is True
    assert receipt.user_id == "usr_42"
    assert receipt.key_id == "key_42"
