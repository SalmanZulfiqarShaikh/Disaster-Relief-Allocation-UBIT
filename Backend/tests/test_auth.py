
import pytest
from fastapi.testclient import TestClient

from core import auth, config

PASSWORD = "correct-horse-battery-staple"
EMAIL = "coordinator@example.com"

PROTECTED = [
    ("get", "/api/cases"),
    ("get", "/api/cases/1"),
    ("get", "/api/cases/1/dispatches"),
    ("get", "/api/volunteers"),
    ("get", "/api/admin/status"),
    ("get", "/events"),
    ("post", "/api/proposals/1/approve"),
    ("post", "/api/cases/1/reopen"),
    ("post", "/api/cases/1/responderlink"),
    ("post", "/api/admin/killswitch"),
]

PUBLIC = [
    ("get", "/api/hello"),
    ("get", "/api/zones"),
    ("get", "/api/auth/me"),
]


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(config, "MOCK_MODE", True)
    monkeypatch.setattr(config, "ADMIN_EMAIL", EMAIL)
    monkeypatch.setattr(config, "ADMIN_PASSWORD_HASH", auth.hash_password(PASSWORD))
    monkeypatch.setattr(config, "SESSION_SECRET", "test-secret-not-a-real-one")
    monkeypatch.setattr(config, "SESSION_TTL_HOURS", 12)

    import main
    from routes import zones

    class ZoneStore:
        @staticmethod
        def select(table, **filters):
            return [
                {"id": "johar", "name": "Gulistan-e-Jauhar", "lat": 24.92,
                 "lng": 67.13, "volunteer_group": "a", "risk_level": "elevated"},
            ]

    monkeypatch.setattr(zones, "store", ZoneStore)

    return TestClient(main.app, raise_server_exceptions=False)


def sign_in(client) -> None:
    response = client.post("/api/auth/login", json={"email": EMAIL, "password": PASSWORD})
    assert response.status_code == 200


@pytest.mark.parametrize("method,path", PROTECTED)
def test_signed_out_is_refused(client, method, path):
    response = client.request(method.upper(), path, json={} if method == "post" else None)
    assert response.status_code == 401, f"{path} answered a stranger"


@pytest.mark.parametrize("method,path", PUBLIC)
def test_public_endpoints_stay_public(client, method, path):
    response = client.request(method.upper(), path)
    assert response.status_code == 200, f"{path} needs a login but should not"


def test_the_webhook_is_not_behind_the_login(client):
    response = client.post("/webhook/whatsapp", json={"object": "whatsapp_business_account"})
    assert response.status_code != 401


def test_a_responder_link_needs_no_login(client):
    assert client.get("/api/r/some-token").status_code != 401


def test_correct_credentials_are_accepted(client):
    response = client.post("/api/auth/login", json={"email": EMAIL, "password": PASSWORD})
    assert response.status_code == 200
    assert response.json()["email"] == EMAIL


def test_the_session_cookie_is_httponly(client):
    response = client.post("/api/auth/login", json={"email": EMAIL, "password": PASSWORD})
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie
    assert "samesite=lax" in cookie


def test_a_wrong_password_is_refused(client):
    assert client.post(
        "/api/auth/login", json={"email": EMAIL, "password": "wrong"}
    ).status_code == 401


def test_a_wrong_email_is_refused(client):
    assert client.post(
        "/api/auth/login", json={"email": "someone@else.com", "password": PASSWORD}
    ).status_code == 401


def test_the_two_failures_are_indistinguishable(client):
    wrong_password = client.post(
        "/api/auth/login", json={"email": EMAIL, "password": "wrong"}
    )
    wrong_email = client.post(
        "/api/auth/login", json={"email": "someone@else.com", "password": PASSWORD}
    )
    assert wrong_password.json()["detail"] == wrong_email.json()["detail"]


def test_login_is_refused_when_the_server_has_no_credentials(client, monkeypatch):
    monkeypatch.setattr(config, "ADMIN_PASSWORD_HASH", "")
    assert client.post(
        "/api/auth/login", json={"email": EMAIL, "password": PASSWORD}
    ).status_code == 401


def test_a_signed_in_caller_gets_past_the_guard(client):
    sign_in(client)
    assert client.get("/api/cases").status_code != 401


def test_me_reports_the_signed_in_user(client):
    sign_in(client)
    body = client.get("/api/auth/me").json()
    assert body["authenticated"] is True
    assert body["email"] == EMAIL


def test_me_is_honest_when_signed_out(client):
    body = client.get("/api/auth/me").json()
    assert body["authenticated"] is False
    assert body["email"] is None


def test_logout_clears_the_cookie(client):
    sign_in(client)
    client.post("/api/auth/logout")
    assert client.get("/api/cases").status_code == 401


def test_a_tampered_cookie_is_refused(client):
    client.cookies.set(auth.SESSION_COOKIE, f"{EMAIL}|99999999999|notarealsignature")
    assert client.get("/api/cases").status_code == 401


def test_a_forged_email_is_refused(client):
    token, _ = auth.issue_session(EMAIL)
    _email, expires, signature = token.rsplit("|", 2)
    client.cookies.set(auth.SESSION_COOKIE, f"attacker@example.com|{expires}|{signature}")
    assert client.get("/api/cases").status_code == 401


def test_an_expired_session_is_refused(client, monkeypatch):
    sign_in(client)
    assert client.get("/api/cases").status_code != 401

    import time as real_time

    later = real_time.time() + (config.SESSION_TTL_HOURS + 1) * 3600
    monkeypatch.setattr(auth.time, "time", lambda: later)

    assert client.get("/api/cases").status_code == 401


def test_rotating_the_secret_ends_every_session(client, monkeypatch):
    sign_in(client)
    monkeypatch.setattr(config, "SESSION_SECRET", "a-different-secret")
    assert client.get("/api/cases").status_code == 401


def test_changing_the_admin_email_ends_the_old_session(client, monkeypatch):
    sign_in(client)
    monkeypatch.setattr(config, "ADMIN_EMAIL", "someone@else.com")
    assert client.get("/api/cases").status_code == 401


def test_a_hash_does_not_contain_the_password(client):
    assert PASSWORD not in auth.hash_password(PASSWORD)


def test_two_hashes_of_one_password_differ(client):
    assert auth.hash_password(PASSWORD) != auth.hash_password(PASSWORD)


def test_verify_accepts_the_right_password(client):
    assert auth.verify_password(PASSWORD, auth.hash_password(PASSWORD))


def test_verify_rejects_the_wrong_one(client):
    assert not auth.verify_password("nearly-right", auth.hash_password(PASSWORD))


@pytest.mark.parametrize("stored", ["", "garbage", "pbkdf2_sha256$notanumber$a$b", "md5$1$a$b"])
def test_a_malformed_hash_fails_closed(client, stored):
    assert not auth.verify_password(PASSWORD, stored)


def test_is_configured_needs_all_three(client, monkeypatch):
    assert auth.is_configured()
    for field in ("ADMIN_EMAIL", "ADMIN_PASSWORD_HASH", "SESSION_SECRET"):
        monkeypatch.setattr(config, field, "")
        assert not auth.is_configured()
        monkeypatch.undo()
        monkeypatch.setattr(config, "MOCK_MODE", True)
        monkeypatch.setattr(config, "ADMIN_EMAIL", EMAIL)
        monkeypatch.setattr(config, "ADMIN_PASSWORD_HASH", auth.hash_password(PASSWORD))
        monkeypatch.setattr(config, "SESSION_SECRET", "test-secret-not-a-real-one")
