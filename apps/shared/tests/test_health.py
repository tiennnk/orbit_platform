import pytest
from django.db import DatabaseError


@pytest.mark.django_db
def test_health_ok_without_auth(anon_client):
    response = anon_client.get("/health/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_health_reports_database_failure(anon_client, monkeypatch):
    def broken_cursor():
        raise DatabaseError("down")

    monkeypatch.setattr("apps.shared.health.connection.cursor", broken_cursor)

    response = anon_client.get("/health/")

    assert response.status_code == 503
    assert response.json()["database"] == "unreachable"
