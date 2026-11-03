import uuid

import pytest

from app.models.profile import Answer
from app.db.session import SessionLocal
from app.services.questions import (
    QuestionValidationError,
    normalize_options,
    normalize_question_type,
    questions_service,
)
from tests.conftest import create_profile


def test_open_to_chat_is_configured_as_single_choice():
    question = None
    for category in questions_service.get_categories():
        for item in category.get("questions", []):
            if item["id"] == "open_to_chat":
                question = item
                break
    assert question is not None
    assert question["type"] == "select"
    assert len(question["options"]) >= 5
    assert {option["value"] for option in question["options"]} == {
        "always",
        "shared_interests",
        "mood",
        "interesting_people",
        "observe_first",
        "not_looking",
    }


def test_question_type_and_options_validation():
    assert normalize_question_type("select") == "select"
    assert normalize_question_type("single_choice") == "select"
    assert normalize_question_type("multiple_choice") == "multiselect"

    with pytest.raises(QuestionValidationError):
        normalize_question_type("unknown")

    with pytest.raises(QuestionValidationError):
        normalize_options([])

    with pytest.raises(QuestionValidationError):
        normalize_options([{"value": "a", "label": ""}])

    with pytest.raises(QuestionValidationError):
        normalize_options([{"value": "a", "label": "A"}, {"value": "a", "label": "B"}])

    assert normalize_options([{"value": "a", "label": "A"}]) == [{"value": "a", "label": "A"}]


def _add_pool_item(client, pool_id, payload):
    response = client.post(f"/api/pools/{pool_id}/items", json=payload)
    return response


def _pool_questions(categories):
    return [
        question
        for category in categories
        if category.get("source") == "pool"
        for question in category.get("questions", [])
    ]


def test_single_and_multiple_choice_full_cycle(auth_client):
    client = auth_client
    profile_id, edit_token = create_profile(client)
    headers = {"X-Edit-Token": edit_token}

    pool_response = client.post("/api/pools", json={"name": "Гейминг"})
    assert pool_response.status_code == 200, pool_response.text
    pool_id = pool_response.json()["id"]

    # A choice question cannot be created without options.
    response = _add_pool_item(
        client,
        pool_id,
        {"title": "Во что играешь?", "type": "multiselect", "options": []},
    )
    assert response.status_code == 400

    # Duplicate option ids are rejected.
    response = _add_pool_item(
        client,
        pool_id,
        {
            "title": "Bad",
            "type": "select",
            "options": [{"value": "x", "label": "X"}, {"value": "x", "label": "X2"}],
        },
    )
    assert response.status_code == 400

    response = _add_pool_item(
        client,
        pool_id,
        {
            "title": "Какой стиль музыки тебе ближе?",
            "type": "select",
            "required": True,
            "options": [
                {"value": "rock", "label": "Rock"},
                {"value": "metal", "label": "Metal"},
                {"value": "electronic", "label": "Electronic"},
                {"value": "hiphop", "label": "Hip-hop"},
            ],
        },
    )
    assert response.status_code == 200, response.text
    select_item = response.json()

    response = _add_pool_item(
        client,
        pool_id,
        {
            "title": "Во что ты играешь?",
            "type": "multiselect",
            "options": [
                {"value": "rpg", "label": "RPG"},
                {"value": "strategy", "label": "Strategy"},
                {"value": "shooters", "label": "Shooters"},
                {"value": "survival", "label": "Survival"},
                {"value": "indie", "label": "Indie"},
            ],
        },
    )
    assert response.status_code == 200, response.text

    # Re-open the constructor and edit/reorder options.
    response = client.put(
        f"/api/pools/{pool_id}/items/{select_item['id']}",
        json={
            "title": "Какой стиль музыки тебе ближе?",
            "type": "select",
            "required": True,
            "options": [
                {"value": "hiphop", "label": "Hip-hop"},
                {"value": "rock", "label": "Rock"},
                {"value": "metal", "label": "Metal"},
                {"value": "electronic", "label": "Electronic"},
            ],
        },
    )
    assert response.status_code == 200, response.text
    assert [o["value"] for o in response.json()["options"]] == ["hiphop", "rock", "metal", "electronic"]

    pool_data = client.get(f"/api/pools/{pool_id}").json()
    assert len(pool_data["items"]) == 2

    # Attach the pool through the edit-token API used by the editor.
    response = client.put(f"/api/edit/me/pools", headers=headers, json={"pool_ids": [pool_id]})
    assert response.status_code == 200, response.text
    assert len(response.json()["attached"]) == 1

    # Repeated attachment must not duplicate anything.
    response = client.put(f"/api/edit/me/pools", headers=headers, json={"pool_ids": [pool_id]})
    assert response.status_code == 200, response.text
    assert len(response.json()["attached"]) == 1

    edit_data = client.get("/api/edit/me", headers=headers).json()
    pool_questions = _pool_questions(edit_data["categories"])
    assert len(pool_questions) == 2
    assert {q["type"] for q in pool_questions} == {"select", "multiselect"}
    select_question = next(q for q in pool_questions if q["type"] == "select")
    multi_question = next(q for q in pool_questions if q["type"] == "multiselect")
    select_id = select_question["id"]
    multi_id = multi_question["id"]

    # Save one answer of each kind plus the standard open_to_chat question.
    response = client.put(
        "/api/edit/me/answers",
        headers=headers,
        json={
            "answers": [
                {"question_id": select_id, "value": "metal"},
                {"question_id": multi_id, "value": ["rpg", "survival"]},
                {"question_id": "open_to_chat", "value": "shared_interests"},
            ]
        },
    )
    assert response.status_code == 200, response.text

    # Invalid option values are rejected.
    response = client.put(
        "/api/edit/me/answers",
        headers=headers,
        json={"answers": [{"question_id": select_id, "value": "invalid"}]},
    )
    assert response.status_code == 400

    public = client.get("/api/profiles/tester/public").json()
    assert public["answers"][select_id] == "metal"
    assert public["answers"][multi_id] == ["rpg", "survival"]
    assert public["answers"]["open_to_chat"] == "shared_interests"
    public_pool_questions = _pool_questions(public["categories"])
    assert len(public_pool_questions) == 2

    export = client.get("/api/profiles/tester/json")
    assert export.status_code == 200, export.text
    assert export.json()["design"]["preset"] == "dark"

    # Detaching the pool keeps saved answers in the database.
    response = client.put("/api/edit/me/pools", headers=headers, json={"pool_ids": []})
    assert response.status_code == 200, response.text
    db = SessionLocal()
    answer_ids = {
        row.question_id
        for row in db.query(Answer).filter(Answer.profile_id == uuid.UUID(profile_id)).all()
    }
    db.close()
    assert {select_id, multi_id, "open_to_chat"} <= answer_ids

    edit_data = client.get("/api/edit/me", headers=headers).json()
    assert _pool_questions(edit_data["categories"]) == []

    # Re-attaching the same pool produces the same stable question ids and
    # keeps the previous answers.
    response = client.put(f"/api/edit/me/pools", headers=headers, json={"pool_ids": [pool_id]})
    assert response.status_code == 200, response.text
    edit_data = client.get("/api/edit/me", headers=headers).json()
    pool_questions = _pool_questions(edit_data["categories"])
    assert {q["id"] for q in pool_questions} == {select_id, multi_id}
    assert edit_data["answers"][select_id]["value"] == "metal"
    assert edit_data["answers"][multi_id]["value"] == ["rpg", "survival"]


def test_cannot_attach_another_users_pool(client):
    from tests.conftest import create_user_session

    owner_id, owner_token = create_user_session("Owner")
    client.cookies.set("quest_session", owner_token)
    pool_response = client.post("/api/pools", json={"name": "Private pool"})
    assert pool_response.status_code == 200
    pool_id = pool_response.json()["id"]

    # A second user creates a profile and tries to attach the first user's pool.
    other_id, other_token = create_user_session("Other")
    client.cookies.set("quest_session", other_token)
    _, edit_token = create_profile(client, slug="other-profile")
    response = client.put(
        "/api/edit/me/pools",
        headers={"X-Edit-Token": edit_token},
        json={"pool_ids": [pool_id]},
    )
    assert response.status_code == 403


def test_answer_for_unknown_question_is_rejected(auth_client):
    client = auth_client
    _, edit_token = create_profile(client)
    response = client.put(
        "/api/edit/me/answers",
        headers={"X-Edit-Token": edit_token},
        json={"answers": [{"question_id": "does-not-exist", "value": "x"}]},
    )
    assert response.status_code == 400


def test_choice_type_aliases_are_normalized(auth_client):
    client = auth_client
    pool_response = client.post("/api/pools", json={"name": "Aliases"})
    pool_id = pool_response.json()["id"]

    response = client.post(
        f"/api/pools/{pool_id}/items",
        json={
            "title": "Single",
            "type": "single_choice",
            "options": [{"value": "a", "label": "A"}],
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["type"] == "select"

    response = client.post(
        f"/api/pools/{pool_id}/items",
        json={
            "title": "Multiple",
            "type": "multiple_choice",
            "options": [{"value": "a", "label": "A"}, {"value": "b", "label": "B"}],
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["type"] == "multiselect"


def test_attached_pool_is_snapshotted(auth_client):
    client = auth_client
    _, edit_token = create_profile(client)
    headers = {"X-Edit-Token": edit_token}

    pool_id = client.post("/api/pools", json={"name": "Snapshot"}).json()["id"]
    item = client.post(
        f"/api/pools/{pool_id}/items",
        json={
            "title": "Original title",
            "type": "select",
            "options": [{"value": "a", "label": "A"}],
        },
    ).json()

    response = client.put("/api/edit/me/pools", headers=headers, json={"pool_ids": [pool_id]})
    assert response.status_code == 200, response.text

    # Editing the source pool must not change an already attached questionnaire.
    response = client.put(
        f"/api/pools/{pool_id}/items/{item['id']}",
        json={
            "title": "Changed title",
            "type": "select",
            "options": [{"value": "a", "label": "A"}, {"value": "b", "label": "B"}],
        },
    )
    assert response.status_code == 200, response.text

    categories = client.get("/api/edit/me", headers=headers).json()["categories"]
    pool_questions = _pool_questions(categories)
    assert len(pool_questions) == 1
    assert pool_questions[0]["title"] == "Original title"
    assert [o["value"] for o in pool_questions[0]["options"]] == ["a"]

    # Re-attaching (after detach) takes a fresh snapshot.
    client.put("/api/edit/me/pools", headers=headers, json={"pool_ids": []})
    client.put("/api/edit/me/pools", headers=headers, json={"pool_ids": [pool_id]})
    categories = client.get("/api/edit/me", headers=headers).json()["categories"]
    pool_questions = _pool_questions(categories)
    assert pool_questions[0]["title"] == "Changed title"
    assert [o["value"] for o in pool_questions[0]["options"]] == ["a", "b"]


