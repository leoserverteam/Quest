"""Tests for the public question-pool library."""
from tests.conftest import create_profile, create_user_session


def _create_pool(client, name="Пул", description=None):
    response = client.post("/api/pools", json={"name": name, "description": description})
    assert response.status_code == 200, response.text
    return response.json()["id"]


def _add_item(client, pool_id, title="Вопрос", qtype="text", options=None, required=False):
    payload = {"title": title, "type": qtype, "required": required}
    if options is not None:
        payload["options"] = options
    response = client.post(f"/api/pools/{pool_id}/items", json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def _publish(client, pool_id, **kwargs):
    payload = {"visibility": "public", **kwargs}
    response = client.put(f"/api/pools/{pool_id}/publication", json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def _use_user(client, token):
    client.cookies.set("quest_session", token)


def _anonymous(client):
    client.cookies.clear()


def _library_items(client, **params):
    response = client.get("/api/library/pools", params=params)
    assert response.status_code == 200, response.text
    return response.json()


def test_publication_modes_and_library_visibility(auth_client):
    client = auth_client
    pool_id = _create_pool(client, "Музыка")
    _add_item(
        client,
        pool_id,
        "Любимый жанр",
        "select",
        options=[{"value": "rock", "label": "Rock"}, {"value": "pop", "label": "Pop"}],
    )

    # A new pool is private by default and is not listed in the library.
    own = client.get("/api/pools").json()
    assert own[0]["visibility"] == "private"
    assert own[0]["share_slug"] is None
    assert _library_items(client)["total"] == 0

    published = _publish(client, pool_id, category="music", tags=["rock", "музыка"])
    slug = published["share_slug"]
    assert slug

    listing = _library_items(client)
    assert listing["total"] == 1
    item = listing["items"][0]
    assert item["name"] == "Музыка"
    assert item["category"] == "music"
    assert item["tags"] == ["rock", "музыка"]
    assert item["count"] == 1

    detail = client.get(f"/api/library/pools/{slug}")
    assert detail.status_code == 200
    assert detail.json()["items"][0]["options"][0]["label"] == "Rock"

    # Unlisted pools are reachable by link but hidden from the catalogue.
    _publish(client, pool_id, visibility="unlisted")
    assert _library_items(client)["total"] == 0
    assert client.get(f"/api/library/pools/{slug}").status_code == 200

    # Back to private: the public link stops working.
    _publish(client, pool_id, visibility="private")
    assert client.get(f"/api/library/pools/{slug}").status_code == 404


def test_publishing_requires_at_least_one_question(auth_client):
    client = auth_client
    pool_id = _create_pool(client, "Пустой")
    response = client.put(
        f"/api/pools/{pool_id}/publication", json={"visibility": "public"}
    )
    assert response.status_code == 400


def test_only_owner_can_publish(client):
    owner_id, owner_token = create_user_session("Owner")
    _use_user(client, owner_token)
    pool_id = _create_pool(client, "Owner pool")
    _add_item(client, pool_id)

    _, other_token = create_user_session("Other")
    _use_user(client, other_token)
    response = client.put(
        f"/api/pools/{pool_id}/publication", json={"visibility": "public"}
    )
    assert response.status_code == 404
    response = client.put(f"/api/pools/{pool_id}", json={"name": "Hijacked"})
    assert response.status_code == 404


def test_copy_creates_independent_pool_and_keeps_origin(client):
    owner_id, owner_token = create_user_session("Owner")
    _use_user(client, owner_token)
    pool_id = _create_pool(client, "Музыка")
    _add_item(
        client,
        pool_id,
        "Жанр",
        "select",
        options=[{"value": "rock", "label": "Rock"}, {"value": "pop", "label": "Pop"}],
    )
    published = _publish(client, pool_id, category="music", tags=["rock"])
    slug = published["share_slug"]

    _, other_token = create_user_session("Other")
    _use_user(client, other_token)
    detail = client.get(f"/api/library/pools/{slug}").json()
    assert detail["is_added"] is False

    response = client.post(f"/api/library/pools/{slug}/copy")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["created"] is True
    copy_id = body["pool"]["id"]
    assert copy_id != pool_id

    my_pools = client.get("/api/pools").json()
    copy = next(pool for pool in my_pools if pool["id"] == copy_id)
    assert copy["visibility"] == "private"
    assert copy["origin"]["pool_id"] == pool_id
    assert copy["origin"]["title"] == "Музыка"
    assert copy["origin"]["author_name"] == "Owner"
    assert copy["origin"]["available"] is True

    # Adding the same pool again returns the existing copy.
    again = client.post(f"/api/library/pools/{slug}/copy")
    assert again.status_code == 200
    assert again.json()["created"] is False
    assert again.json()["pool"]["id"] == copy_id
    assert len([p for p in client.get("/api/pools").json() if p["id"] == copy_id]) == 1
    assert client.get(f"/api/library/pools/{slug}").json()["adds_count"] == 1

    # The copy is fully independent from the original.
    copy_detail = client.get(f"/api/pools/{copy_id}").json()
    copy_item = copy_detail["items"][0]
    response = client.put(
        f"/api/pools/{copy_id}/items/{copy_item['id']}",
        json={
            "title": "Изменённый вопрос",
            "type": "select",
            "options": [{"value": "rock", "label": "Rock"}],
        },
    )
    assert response.status_code == 200

    _use_user(client, owner_token)
    original = client.get(f"/api/pools/{pool_id}").json()
    assert original["items"][0]["title"] == "Жанр"
    assert [option["value"] for option in original["items"][0]["options"]] == ["rock", "pop"]


def test_copy_works_after_original_is_deleted_and_answers_survive(client):
    owner_id, owner_token = create_user_session("Owner")
    _use_user(client, owner_token)
    pool_id = _create_pool(client, "Кино")
    _add_item(client, pool_id, "Любимый фильм")
    slug = _publish(client, pool_id)["share_slug"]

    _, other_token = create_user_session("Other")
    _use_user(client, other_token)
    copy_id = client.post(f"/api/library/pools/{slug}/copy").json()["pool"]["id"]

    _, edit_token = create_profile(client, slug="other-profile")
    headers = {"X-Edit-Token": edit_token}
    response = client.put(
        "/api/edit/me/pools", headers=headers, json={"pool_ids": [copy_id]}
    )
    assert response.status_code == 200, response.text

    edit_data = client.get("/api/edit/me", headers=headers).json()
    question = next(
        question
        for category in edit_data["categories"]
        if category.get("source") == "pool"
        for question in category["questions"]
    )
    question_id = question["id"]

    response = client.put(
        "/api/edit/me/answers",
        headers=headers,
        json={"answers": [{"question_id": question_id, "value": "Начало"}]},
    )
    assert response.status_code == 200, response.text

    # The original is deleted; the copy keeps working and keeps its answers.
    _use_user(client, owner_token)
    assert client.delete(f"/api/pools/{pool_id}").status_code == 200

    _use_user(client, other_token)
    copy_detail = client.get(f"/api/pools/{copy_id}")
    assert copy_detail.status_code == 200
    assert copy_detail.json()["origin"]["available"] is False
    assert client.get(f"/api/library/pools/{slug}").status_code == 404

    edit_data = client.get("/api/edit/me", headers=headers).json()
    assert edit_data["answers"][question_id]["value"] == "Начало"
    public = client.get("/api/profiles/other-profile/public")
    assert public.status_code == 200
    assert public.json()["answers"][question_id] == "Начало"


def test_unpublished_original_does_not_break_copy(client):
    owner_id, owner_token = create_user_session("Owner")
    _use_user(client, owner_token)
    pool_id = _create_pool(client, "Книги")
    _add_item(client, pool_id)
    slug = _publish(client, pool_id)["share_slug"]

    _, other_token = create_user_session("Other")
    _use_user(client, other_token)
    copy_id = client.post(f"/api/library/pools/{slug}/copy").json()["pool"]["id"]

    _use_user(client, owner_token)
    _publish(client, pool_id, visibility="private")

    _use_user(client, other_token)
    assert client.get(f"/api/pools/{copy_id}").status_code == 200
    assert client.get(f"/api/library/pools/{slug}").status_code == 404


def test_private_pool_cannot_be_copied_but_unlisted_can(client):
    owner_id, owner_token = create_user_session("Owner")
    _use_user(client, owner_token)
    pool_id = _create_pool(client, "Секретный")
    _add_item(client, pool_id)
    slug = _publish(client, pool_id)["share_slug"]

    _publish(client, pool_id, visibility="unlisted")

    _, other_token = create_user_session("Other")
    _use_user(client, other_token)
    copied = client.post(f"/api/library/pools/{slug}/copy")
    assert copied.status_code == 200
    # The secret link of an unlisted original is not exposed through a copy.
    copy_id = copied.json()["pool"]["id"]
    copy = next(p for p in client.get("/api/pools").json() if p["id"] == copy_id)
    assert copy["origin"]["available"] is False
    assert copy["origin"]["share_slug"] is None

    # A pool that was never published has no link at all.
    _use_user(client, owner_token)
    private_pool = _create_pool(client, "Приватный")
    _add_item(client, private_pool)
    assert client.post(f"/api/library/pools/{private_pool}/copy").status_code == 404


def test_copy_requires_authentication(auth_client):
    client = auth_client
    pool_id = _create_pool(client, "Публичный")
    _add_item(client, pool_id)
    slug = _publish(client, pool_id)["share_slug"]

    _anonymous(client)
    assert client.post(f"/api/library/pools/{slug}/copy").status_code == 401


def test_views_are_counted_once_per_viewer(auth_client):
    client = auth_client
    owner_token = client.cookies.get("quest_session")
    pool_id = _create_pool(client, "Просмотры")
    _add_item(client, pool_id)
    slug = _publish(client, pool_id)["share_slug"]

    _anonymous(client)
    first = client.get(f"/api/library/pools/{slug}").json()
    second = client.get(f"/api/library/pools/{slug}").json()
    assert first["views_count"] == 1
    assert second["views_count"] == 1

    # Preview requests do not count as views.
    preview = client.get(f"/api/library/pools/{slug}", params={"preview": 1}).json()
    assert preview["views_count"] == 1

    # The owner's own visits are ignored.
    _use_user(client, owner_token)
    owner_view = client.get(f"/api/library/pools/{slug}").json()
    assert owner_view["views_count"] == 1

    # A different authenticated user is a different viewer.
    _, other_token = create_user_session("Other")
    _use_user(client, other_token)
    third = client.get(f"/api/library/pools/{slug}").json()
    assert third["views_count"] == 2

    _use_user(client, other_token)
    assert client.get(f"/api/library/pools/{slug}").json()["views_count"] == 2


def test_library_search_filters_and_sort(client):
    owner_id, owner_token = create_user_session("Owner")
    _use_user(client, owner_token)

    gaming_id = _create_pool(client, "Gaming pool", "About games")
    _add_item(client, gaming_id)
    _publish(client, gaming_id, category="gaming", tags=["pvp", "coop"])

    music_id = _create_pool(client, "Music pool", "About music")
    _add_item(client, music_id)
    _publish(client, music_id, category="music", tags=["rock"])

    _anonymous(client)

    # SQLite (used by the test suite) lowercases only ASCII, so the search
    # checks use Latin text; PostgreSQL handles Cyrillic case-insensitively.
    assert _library_items(client, q="gaming")["total"] == 1
    assert _library_items(client, q="games")["total"] == 1
    assert _library_items(client, category="music")["total"] == 1
    assert _library_items(client, tag="pvp")["total"] == 1
    assert _library_items(client, tag="rock")["total"] == 1
    assert _library_items(client, tag="unknown")["total"] == 0

    recent = _library_items(client, sort="recent")
    assert recent["total"] == 2
    assert recent["sort"] == "recent"

    meta = client.get("/api/library/meta").json()
    assert {category["id"] for category in meta["categories"]} >= {"gaming", "music"}
    assert {tag["tag"] for tag in meta["tags"]} >= {"pvp", "rock"}


def test_old_pools_stay_private(auth_client):
    client = auth_client
    pool_id = _create_pool(client, "Старый пул")
    _add_item(client, pool_id)

    pool = client.get(f"/api/pools/{pool_id}").json()
    assert pool["visibility"] == "private"
    assert pool["share_slug"] is None
    assert pool["published_at"] is None

    _anonymous(client)
    assert _library_items(client)["total"] == 0


def test_publication_validates_input(auth_client):
    client = auth_client
    pool_id = _create_pool(client, "Валидация")
    _add_item(client, pool_id)

    response = client.put(
        f"/api/pools/{pool_id}/publication", json={"visibility": "everyone"}
    )
    assert response.status_code == 400

    response = client.put(
        f"/api/pools/{pool_id}/publication",
        json={"visibility": "public", "category": "unknown"},
    )
    assert response.status_code == 400

    response = client.put(
        f"/api/pools/{pool_id}/publication",
        json={"visibility": "public", "tags": ["x" * 30]},
    )
    assert response.status_code == 400


def test_library_list_marks_added_pools(client):
    owner_id, owner_token = create_user_session("Owner")
    _use_user(client, owner_token)
    pool_id = _create_pool(client, "Отметка")
    _add_item(client, pool_id)
    slug = _publish(client, pool_id)["share_slug"]

    _, other_token = create_user_session("Other")
    _use_user(client, other_token)
    assert _library_items(client)["items"][0]["is_added"] is False

    client.post(f"/api/library/pools/{slug}/copy")
    assert _library_items(client)["items"][0]["is_added"] is True
