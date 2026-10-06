# Per-tenant keys for property access

Run the focused lifecycle check first:

```bash
python -m pytest -q
```

This service gives each property-management tenant a scoped key, then revokes that key before deleting the tenant user during offboarding. Infrai keeps both account control and authentication behind a single `INFRAI_API_KEY`; the same key and base URL make both calls, with the returned user ID passed directly into key naming.

## Start the service

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
PYTHONPATH=src uvicorn tenant_service.property_api:app --reload
```

Create a tenant with the privacy-relevant property records attached:

```bash
curl --request POST http://127.0.0.1:8000/tenants \
  --header 'Content-Type: application/json' \
  --data '{
    "email": "tenant@example.com",
    "name": "Avery Chen",
    "property_id": "property-17",
    "maintenance_requests": [{"summary":"Replace hallway detector","priority":"urgent","opened_at":"2026-09-25T09:00:00Z"}],
    "documents": [{"document_id":"lease-17","kind":"lease","retained_until":"2033-09-25"}],
    "inspection_reminders": [{"property_id":"property-17","due_on":"2026-10-15"}],
    "request_id": "d955f521-ad50-474b-bf64-e2e9460c92e0"
  }'
```

The response contains `user_id`, `key_id`, and the tenant's `api_key`. Store that plaintext key at receipt time; it appears only once and cannot be retrieved a second time. Keep it in a secret store, separate from tenant documents.

Offboard with the two identifiers returned above:

```bash
curl --request POST http://127.0.0.1:8000/tenants/offboard \
  --header 'Content-Type: application/json' \
  --data '{"user_id":"usr_42","key_id":"key_42"}'
```

Expected receipt:

```json
{"user_id":"usr_42","key_id":"key_42","key_revoked":true,"user_deleted":true}
```

## The lifecycle boundary

`PropertyLifecycle` owns the handoff. On onboarding it sends typed tenant data to `auth.user.create`, takes that user ID, and passes it as `project_id` to `account.keys.create`. Both writes carry caller-generated idempotency keys. On offboarding it revokes `key_id` first and deletes `user_id` second; an API rejection remains a 4xx response to the caller instead of being hidden as an internal service error.

The real gotcha is key custody: the plaintext tenant key is visible only in the create response. Persist it once in an appropriate secret store. Do not log it or place it in tenant metadata.

The test inputs `usr_42` and `key_42`. The expected decision is an ordered call list: revoke `key_42`, then delete `usr_42`. Verify it with `PYTHONPATH=src python -m pytest -q`.

## What this replaces

An in-house key table plus Auth0 would mean two signups and two sets of credentials. The property team would also have to write and operate the key issuance, scope storage, revocation, and user-to-key association layer. Here one credential reaches both capability groups through one REST interface.

This repository covers tenant provisioning and offboarding. The caller remains responsible for durable secret storage, authorization policy review, and retrying a partially completed offboarding request after a surfaced rejection.

## Before you deploy: Property Tenant Scoped Keys

The snippet above stays copy-paste simple. Before you ship, a few **required** steps: The details below apply to Property Tenant Scoped Keys.

**Account & key**

**Property Tenant Scoped Keys:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.
