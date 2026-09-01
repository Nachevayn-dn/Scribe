"""Template CRUD + doctor preference CRUD, and their effect on extraction."""
from httpx import AsyncClient

from tests.conftest import create_user, signup_clinic


async def test_list_templates_includes_global_seeds(client: AsyncClient):
    admin = await signup_clinic(client)
    resp = await client.get("/api/v1/templates", headers=admin["headers"])
    assert resp.status_code == 200
    names = {t["name"] for t in resp.json()}
    assert {"Clinical Summary", "Referral Letter"}.issubset(names)


async def test_assistant_cannot_create_template(client: AsyncClient):
    admin = await signup_clinic(client)
    assistant = await create_user(client, admin["headers"], role="ASSISTANT")
    resp = await client.post(
        "/api/v1/templates",
        headers=assistant["headers"],
        json={"name": "My Template", "template_type": "CUSTOM", "structure": ["Notes"]},
    )
    assert resp.status_code == 403


async def test_provider_can_create_and_edit_own_custom_template(client: AsyncClient):
    admin = await signup_clinic(client)
    provider = await create_user(client, admin["headers"], role="PROVIDER")

    create_resp = await client.post(
        "/api/v1/templates",
        headers=provider["headers"],
        json={"name": "Dr. Smith's Format", "template_type": "CUSTOM", "structure": ["Notes"]},
    )
    assert create_resp.status_code == 201, create_resp.text
    template_id = create_resp.json()["id"]

    update_resp = await client.patch(
        f"/api/v1/templates/{template_id}",
        headers=provider["headers"],
        json={"structure": ["Notes", "Follow-up"]},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["structure"] == ["Notes", "Follow-up"]

    delete_resp = await client.delete(
        f"/api/v1/templates/{template_id}", headers=provider["headers"]
    )
    assert delete_resp.status_code == 204


async def test_provider_cannot_edit_another_providers_template(client: AsyncClient):
    admin = await signup_clinic(client)
    provider_a = await create_user(client, admin["headers"], role="PROVIDER")
    provider_b = await create_user(client, admin["headers"], role="PROVIDER")

    create_resp = await client.post(
        "/api/v1/templates",
        headers=provider_a["headers"],
        json={"name": "A's Template", "template_type": "CUSTOM", "structure": []},
    )
    template_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/templates/{template_id}",
        headers=provider_b["headers"],
        json={"name": "Hijacked"},
    )
    assert resp.status_code == 403


async def test_system_templates_are_immutable(client: AsyncClient):
    admin = await signup_clinic(client)
    resp = await client.get("/api/v1/templates", headers=admin["headers"])
    global_template = next(t for t in resp.json() if t["name"] == "Clinical Summary")

    update_resp = await client.patch(
        f"/api/v1/templates/{global_template['id']}",
        headers=admin["headers"],
        json={"name": "Hacked"},
    )
    assert update_resp.status_code == 403


async def test_preference_crud_and_scoping(client: AsyncClient):
    admin = await signup_clinic(client)
    provider = await create_user(client, admin["headers"], role="PROVIDER")
    assistant = await create_user(client, admin["headers"], role="ASSISTANT")

    # Assistants can't manage preferences at all.
    forbidden = await client.get("/api/v1/preferences", headers=assistant["headers"])
    assert forbidden.status_code == 403

    create_resp = await client.post(
        "/api/v1/preferences",
        headers=provider["headers"],
        json={"trigger_phrase": "tooth pain", "instruction": "always suggest a CBCT scan"},
    )
    assert create_resp.status_code == 201, create_resp.text
    pref = create_resp.json()
    assert pref["provider_id"] == provider["id"]

    # Provider sees only their own.
    list_resp = await client.get("/api/v1/preferences", headers=provider["headers"])
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    # Admin can see it too via provider_id filter.
    admin_list = await client.get(
        "/api/v1/preferences",
        headers=admin["headers"],
        params={"provider_id": provider["id"]},
    )
    assert admin_list.status_code == 200
    assert len(admin_list.json()) == 1

    update_resp = await client.patch(
        f"/api/v1/preferences/{pref['id']}",
        headers=provider["headers"],
        json={"is_active": False},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["is_active"] is False

    delete_resp = await client.delete(
        f"/api/v1/preferences/{pref['id']}", headers=provider["headers"]
    )
    assert delete_resp.status_code == 204


async def test_provider_cannot_set_preferences_for_another_provider(client: AsyncClient):
    admin = await signup_clinic(client)
    provider_a = await create_user(client, admin["headers"], role="PROVIDER")
    provider_b = await create_user(client, admin["headers"], role="PROVIDER")

    resp = await client.post(
        "/api/v1/preferences",
        headers=provider_a["headers"],
        json={
            "provider_id": provider_b["id"],
            "trigger_phrase": "x",
            "instruction": "y",
        },
    )
    assert resp.status_code == 403
