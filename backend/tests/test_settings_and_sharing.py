"""Self-service settings (theme, notification email, clinic email) and the
new email-share / Ask AI endpoints, with Resend and Claude mocked out."""
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient

from app.services.extraction.base import AskAIResult, AskAISource
from tests.conftest import create_user, signup_clinic
from tests.test_notes_editing import _ready_encounter


async def test_update_my_theme_preference(client: AsyncClient):
    admin = await signup_clinic(client)
    provider = await create_user(client, admin["headers"], role="PROVIDER")

    resp = await client.patch(
        "/api/v1/users/me", headers=provider["headers"], json={"theme_preference": "jade"}
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["theme_preference"] == "jade"

    me_resp = await client.get("/api/v1/auth/me", headers=provider["headers"])
    assert me_resp.json()["theme_preference"] == "jade"


async def test_theme_preference_rejects_unknown_value(client: AsyncClient):
    admin = await signup_clinic(client)
    resp = await client.patch(
        "/api/v1/users/me", headers=admin["headers"], json={"theme_preference": "sunset"}
    )
    assert resp.status_code == 422


async def test_update_my_notification_email(client: AsyncClient):
    admin = await signup_clinic(client)
    provider = await create_user(client, admin["headers"], role="PROVIDER")

    resp = await client.patch(
        "/api/v1/users/me",
        headers=provider["headers"],
        json={"notification_email": "personal@example.com"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["notification_email"] == "personal@example.com"


async def test_clinic_email_settings_admin_only(client: AsyncClient):
    admin = await signup_clinic(client)
    provider = await create_user(client, admin["headers"], role="PROVIDER")

    forbidden = await client.patch(
        "/api/v1/clinics/me",
        headers=provider["headers"],
        json={"contact_email": "clinic@example.com"},
    )
    assert forbidden.status_code == 403

    ok = await client.patch(
        "/api/v1/clinics/me",
        headers=admin["headers"],
        json={"contact_email": "clinic@example.com", "staff_email": "staff@example.com"},
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["contact_email"] == "clinic@example.com"
    assert ok.json()["staff_email"] == "staff@example.com"


async def test_share_note_via_email(client: AsyncClient):
    admin = await signup_clinic(client)
    provider = await create_user(client, admin["headers"], role="PROVIDER")
    encounter_id = await _ready_encounter(client, admin["headers"], provider)

    with patch("app.api.notes.send_share_email") as mock_send:
        mock_send.return_value = "email_abc123"
        resp = await client.post(
            f"/api/v1/encounters/{encounter_id}/share",
            headers=provider["headers"],
            json={"content_type": "note", "recipients": ["staff@example.com"]},
        )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "sent"
    assert body["recipients"] == ["staff@example.com"]
    mock_send.assert_called_once()
    assert mock_send.call_args.kwargs["to"] == ["staff@example.com"]

    audit_resp = await client.get(
        "/api/v1/audit-log", headers=admin["headers"], params={"resource_type": "Encounter"}
    )
    assert "NOTE_SHARED" in [a["action"] for a in audit_resp.json()]


async def test_share_transcript_include_self_uses_notification_email(client: AsyncClient):
    admin = await signup_clinic(client)
    provider = await create_user(client, admin["headers"], role="PROVIDER")
    await client.patch(
        "/api/v1/users/me",
        headers=provider["headers"],
        json={"notification_email": "myinbox@example.com"},
    )
    encounter_id = await _ready_encounter(client, admin["headers"], provider)

    with patch("app.api.notes.send_share_email") as mock_send:
        mock_send.return_value = "email_xyz"
        resp = await client.post(
            f"/api/v1/encounters/{encounter_id}/share",
            headers=provider["headers"],
            json={"content_type": "transcript", "recipients": [], "include_self": True},
        )
    assert resp.status_code == 200, resp.text
    assert resp.json()["recipients"] == ["myinbox@example.com"]


async def test_share_without_any_recipient_fails(client: AsyncClient):
    admin = await signup_clinic(client)
    provider = await create_user(client, admin["headers"], role="PROVIDER")
    encounter_id = await _ready_encounter(client, admin["headers"], provider)

    resp = await client.post(
        f"/api/v1/encounters/{encounter_id}/share",
        headers=provider["headers"],
        json={"content_type": "note", "recipients": []},
    )
    assert resp.status_code == 400


async def test_share_surfaces_clean_error_when_email_not_configured(client: AsyncClient):
    admin = await signup_clinic(client)
    provider = await create_user(client, admin["headers"], role="PROVIDER")
    encounter_id = await _ready_encounter(client, admin["headers"], provider)

    from app.services.email_service import EmailNotConfiguredError

    with patch("app.api.notes.send_share_email", side_effect=EmailNotConfiguredError("no key")):
        resp = await client.post(
            f"/api/v1/encounters/{encounter_id}/share",
            headers=provider["headers"],
            json={"content_type": "note", "recipients": ["staff@example.com"]},
        )
    assert resp.status_code == 400


async def test_ask_ai_rework_returns_revision_and_can_be_applied(client: AsyncClient):
    admin = await signup_clinic(client)
    provider = await create_user(client, admin["headers"], role="PROVIDER")
    encounter_id = await _ready_encounter(client, admin["headers"], provider)

    fake_result = AskAIResult(result_type="revision", revised_content="A much shorter note.")
    with patch("app.api.notes.AnthropicExtractionProvider") as mock_cls:
        mock_cls.return_value.ask_ai = AsyncMock(return_value=fake_result)
        resp = await client.post(
            f"/api/v1/encounters/{encounter_id}/note/ask-ai",
            headers=provider["headers"],
            json={"instruction": "make this shorter"},
        )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["result_type"] == "revision"
    assert body["revised_content"] == "A much shorter note."

    # The doctor applies it via the existing whole-content edit path.
    apply_resp = await client.patch(
        f"/api/v1/encounters/{encounter_id}/note",
        headers=provider["headers"],
        json={"rendered_content": body["revised_content"]},
    )
    assert apply_resp.status_code == 200
    assert apply_resp.json()["rendered_content"] == "A much shorter note."


async def test_ask_ai_lookup_returns_answer_with_sources(client: AsyncClient):
    admin = await signup_clinic(client)
    provider = await create_user(client, admin["headers"], role="PROVIDER")
    encounter_id = await _ready_encounter(client, admin["headers"], provider)

    fake_result = AskAIResult(
        result_type="answer",
        answer="Current guidance recommends X.",
        sources=[AskAISource(title="Guideline body", url="https://example.org/guideline")],
    )
    with patch("app.api.notes.AnthropicExtractionProvider") as mock_cls:
        mock_cls.return_value.ask_ai = AsyncMock(return_value=fake_result)
        resp = await client.post(
            f"/api/v1/encounters/{encounter_id}/note/ask-ai",
            headers=provider["headers"],
            json={"instruction": "what's the current guidance on X"},
        )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["result_type"] == "answer"
    assert body["answer"] == "Current guidance recommends X."
    assert body["sources"][0]["url"] == "https://example.org/guideline"


async def test_ask_ai_blocked_on_signed_note(client: AsyncClient):
    admin = await signup_clinic(client)
    provider = await create_user(client, admin["headers"], role="PROVIDER")
    encounter_id = await _ready_encounter(client, admin["headers"], provider)

    sign_resp = await client.post(
        f"/api/v1/encounters/{encounter_id}/note/sign", headers=provider["headers"]
    )
    assert sign_resp.status_code == 200

    resp = await client.post(
        f"/api/v1/encounters/{encounter_id}/note/ask-ai",
        headers=provider["headers"],
        json={"instruction": "make this shorter"},
    )
    assert resp.status_code == 409
