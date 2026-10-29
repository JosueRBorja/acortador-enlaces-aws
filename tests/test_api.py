from datetime import datetime
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
from botocore.exceptions import ClientError
from fastapi.testclient import TestClient

from backend.app.main import create_app

ORIGINAL = "https://www.example.com/articulos/arquitectura-cloud?tema=aws&nivel=1"


def create_link(client):
    response = client.post("/shorten", json={"original_url": ORIGINAL})
    assert response.status_code == 201
    return response.json()


def test_create_persist_info_and_real_redirect(client, aws_table):
    data = create_link(client)
    assert UUID(data["short_code"]).version == 4
    assert data["short_url"] == f"https://api.example.com/{data['short_code']}"
    assert datetime.fromisoformat(data["created_at"]).utcoffset().total_seconds() == 0
    persisted = aws_table.get_item(Key={"short_code": data["short_code"]})["Item"]
    assert persisted["original_url"] == ORIGINAL
    assert persisted["created_at"] == data["created_at"]
    info = client.get(f"/urls/{data['short_code']}")
    assert info.status_code == 200
    assert info.json() == persisted
    redirect = client.get(f"/{data['short_code']}", follow_redirects=False)
    assert redirect.status_code == 307
    assert redirect.headers["location"] == ORIGINAL


@pytest.mark.parametrize("code", [str(uuid4()), "no-es-un-uuid"])
def test_missing_links_are_404(client, code):
    assert client.get(f"/{code}", follow_redirects=False).status_code == 404
    assert client.get(f"/urls/{code}").status_code == 404


@pytest.mark.parametrize(
    "url",
    [
        "no-es-url",
        "javascript:alert(1)",
        "ftp://example.com",
        "https://user:password@example.com",
        "",
    ],
)
def test_invalid_urls_are_rejected(client, url):
    assert client.post("/shorten", json={"original_url": url}).status_code == 422


def test_missing_field_and_unknown_fields(client):
    assert client.post("/shorten", json={}).status_code == 422
    assert (
        client.post("/shorten", json={"original_url": ORIGINAL, "short_code": "x"}).status_code
        == 422
    )


def test_uuid_is_unique(client):
    assert create_link(client)["short_code"] != create_link(client)["short_code"]


def test_persistence_after_application_restart(aws_table, settings):
    with TestClient(create_app(settings)) as first:
        data = create_link(first)
    with TestClient(create_app(settings)) as restarted:
        response = restarted.get(f"/{data['short_code']}", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == ORIGINAL


def test_exact_cors_origins(client):
    headers = {
        "Origin": "http://frontend.example.com",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type",
    }
    response = client.options("/shorten", headers=headers)
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == headers["Origin"]
    headers["Origin"] = "http://untrusted.example.com"
    denied = client.options("/shorten", headers=headers)
    assert denied.status_code == 400
    assert "access-control-allow-origin" not in denied.headers


def test_storage_failure_does_not_expose_aws_details(client):
    error = ClientError(
        {"Error": {"Code": "AccessDeniedException", "Message": "private"}}, "PutItem"
    )
    with patch("backend.app.repository.LinkRepository.insert", side_effect=error):
        response = client.post("/shorten", json={"original_url": ORIGINAL})
    assert response.status_code == 503
    assert "private" not in response.text
    assert "AccessDenied" not in response.text


def test_collision_retries_without_overwriting(client, aws_table):
    data = create_link(client)
    with patch("backend.app.service.uuid4", side_effect=[UUID(data["short_code"]), uuid4()]):
        other = create_link(client)
    assert other["short_code"] != data["short_code"]
    assert (
        aws_table.get_item(Key={"short_code": data["short_code"]})["Item"]["created_at"]
        == data["created_at"]
    )
