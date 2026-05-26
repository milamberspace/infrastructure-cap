"""Integration tests for /api/api and /api/list endpoints."""

from __future__ import annotations

import json
import re


async def test_api_is_public_and_valid_openapi(app):
    client = app.test_client()
    response = await client.get("/api/api")
    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith("application/json")
    assert "Cache-Control" in response.headers
    assert "max-age=300" in response.headers["Cache-Control"]

    body = await response.get_json()
    assert re.match(r"^3\.", body["openapi"]), body["openapi"]
    # /api/list and /api/api must appear in the served document.
    assert "/api/list" in body["paths"]
    assert "/api/api" in body["paths"]


async def test_api_document_advertises_pydantic_schemas(app):
    """The /api document must surface our Pydantic models so external
    integrators can see request and response shapes. See SPEC section 9.9."""
    client = app.test_client()
    response = await client.get("/api/api")
    body = await response.get_json()

    components = body.get("components", {}).get("schemas", {})
    # The full ResponseOption discriminated union must be reachable from
    # /api/list via ListResponse -> Question -> response_option.
    assert "Question" in components, components.keys()
    assert "VoteOption" in components
    assert "LazyConsensusOption" in components
    assert "FreeTextOption" in components

    list_responses = body["paths"]["/api/list"]["get"]["responses"]
    # 200 references ListResponse (inlined or via $ref both acceptable).
    schema_200 = list_responses["200"]["content"]["application/json"]["schema"]
    assert schema_200.get("title") == "ListResponse" or "ListResponse" in str(schema_200)
    # 401 references our error model.
    schema_401 = list_responses["401"]["content"]["application/json"]["schema"]
    assert schema_401.get("title") == "AuthenticationRequired" or "AuthenticationRequired" in str(
        schema_401
    )


async def test_list_unauthenticated_returns_401_json(app):
    client = app.test_client()
    response = await client.get("/api/list", headers={"Accept": "application/json"})
    assert response.status_code == 401
    body = await response.get_json()
    assert body["error"] == "authentication_required"
    assert "login_url" in body


async def test_list_unauthenticated_html_redirects_to_oauth(app):
    client = app.test_client()
    response = await client.get("/api/list", headers={"Accept": "text/html"})
    assert response.status_code in (301, 302, 303, 307, 308)
    assert "/api/auth" in response.headers.get("Location", "")


async def test_list_returns_seeded_questions_for_authenticated_user(
    app, stub_session, seed_questions
):
    seed_questions(app, count=2)
    client = app.test_client()
    response = await client.get("/api/list", headers={"Accept": "application/json"})
    assert response.status_code == 200
    body = await response.get_json()
    assert body["user"] == "alice"
    assert len(body["pending"]) == 2
    first = body["pending"][0]
    assert first["project_id"] == "seapony"
    assert first["status"] == "open"
    # viewer_is_binding flips true because the seeded user is on 'seapony'.
    assert first["viewer_is_binding"] is True
    # time_remaining_seconds is server-stamped and positive (closes_at in
    # the future per the fixture).
    assert first["time_remaining_seconds"] > 0


async def test_list_filters_private_question_caller_cannot_see(app, stub_session, seed_questions):
    # Public question on seapony (visible) + private question on a project
    # the user is not on (invisible).
    seed_questions(app, count=1, project_id="seapony", is_private=0)
    seed_questions(app, count=1, project_id="infra", is_private=1, request_id="req_secret")

    client = app.test_client()
    response = await client.get("/api/list", headers={"Accept": "application/json"})
    body = await response.get_json()
    project_ids = {q["project_id"] for q in body["pending"]}
    assert project_ids == {"seapony"}


async def test_list_omits_resolved_and_removed_questions(app, stub_session, seed_questions):
    seed_questions(app, count=1, status="open")
    seed_questions(
        app,
        count=1,
        status="resolved",
        outcome="approved",
        request_id="resolved_req",
    )
    seed_questions(
        app,
        count=1,
        status="removed",
        outcome="withdrawn",
        request_id="removed_req",
    )

    client = app.test_client()
    response = await client.get("/api/list", headers={"Accept": "application/json"})
    body = await response.get_json()
    statuses = {q["status"] for q in body["pending"]}
    assert statuses == {"open"}


async def test_list_returns_empty_array_not_null(app, stub_session):
    client = app.test_client()
    response = await client.get("/api/list", headers={"Accept": "application/json"})
    body = await response.get_json()
    assert body["pending"] == []
    assert isinstance(body["pending"], list)
    assert body["recent"] == []
    assert isinstance(body["recent"], list)


async def test_list_recent_includes_resolved_and_removed_within_window(
    app, stub_session, seed_questions
):
    """SPEC §9.1: `recent` surfaces non-open questions updated in the last 14 days."""
    from datetime import UTC, datetime, timedelta

    def _iso(dt):
        return dt.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")

    now = datetime.now(UTC)
    fresh = _iso(now - timedelta(days=2))
    stale = _iso(now - timedelta(days=20))

    [open_id] = seed_questions(app, count=1, status="open", request_id="open_req")
    [resolved_id] = seed_questions(
        app,
        count=1,
        status="resolved",
        outcome="approved",
        request_id="resolved_req",
        updated_at=fresh,
    )
    [removed_id] = seed_questions(
        app,
        count=1,
        status="removed",
        outcome="withdrawn",
        request_id="removed_req",
        updated_at=fresh,
    )
    [ancient_id] = seed_questions(
        app,
        count=1,
        status="resolved",
        outcome="approved",
        request_id="ancient_req",
        updated_at=stale,
    )

    client = app.test_client()
    response = await client.get("/api/list", headers={"Accept": "application/json"})
    assert response.status_code == 200
    body = await response.get_json()

    # `pending` still contains only open questions.
    pending_ids = {q["question_id"] for q in body["pending"]}
    assert pending_ids == {open_id}

    # `recent` carries the open + the two fresh-but-closed questions, but
    # not the 20-day-old one.
    recent_ids = {q["question_id"] for q in body["recent"]}
    assert open_id in recent_ids
    assert resolved_id in recent_ids
    assert removed_id in recent_ids
    assert ancient_id not in recent_ids

    # Status markers are carried per row so the UI can render an
    # "open vs closed" indicator without a per-id round trip.
    by_id = {q["question_id"]: q for q in body["recent"]}
    assert by_id[open_id]["status"] == "open"
    assert by_id[resolved_id]["status"] == "resolved"
    assert by_id[resolved_id]["outcome"] == "approved"
    assert by_id[removed_id]["status"] == "removed"
    assert by_id[removed_id]["outcome"] == "withdrawn"


async def test_list_recent_respects_private_acl(app, as_user, seed_questions):
    """Private questions outside the caller's reach must not bleed into `recent`."""
    from datetime import UTC, datetime, timedelta

    from cap_backend.auth import AuthenticatedUser

    def _iso(dt):
        return dt.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")

    fresh = _iso(datetime.now(UTC) - timedelta(days=1))

    as_user(AuthenticatedUser(uid="outsider", committees=("other",)))
    [hidden_id] = seed_questions(
        app,
        count=1,
        project_id="seapony",
        is_private=1,
        status="resolved",
        outcome="approved",
        request_id="hidden_req",
        updated_at=fresh,
    )
    [visible_id] = seed_questions(
        app,
        count=1,
        project_id="other",
        is_private=0,
        status="resolved",
        outcome="approved",
        request_id="visible_req",
        updated_at=fresh,
    )

    client = app.test_client()
    response = await client.get("/api/list", headers={"Accept": "application/json"})
    assert response.status_code == 200
    body = await response.get_json()
    recent_ids = {q["question_id"] for q in body["recent"]}
    assert hidden_id not in recent_ids
    assert visible_id in recent_ids


async def test_api_response_is_cached_across_requests(app):
    client = app.test_client()
    r1 = await client.get("/api/api")
    r2 = await client.get("/api/api")
    assert r1.status_code == r2.status_code == 200
    assert await r1.get_data() == await r2.get_data()


async def test_api_response_includes_service_version(app):
    client = app.test_client()
    response = await client.get("/api/api")
    body = json.loads(await response.get_data())
    assert "version" in body["info"]
