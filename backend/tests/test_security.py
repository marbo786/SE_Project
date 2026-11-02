from datetime import datetime, timedelta
from email import policy
from email.parser import BytesParser
import re
import pytest
import bcrypt
from app.models.user import User
from app.models.session import AuthSession, AuthChallenge
from app.core.config import get_settings
from app.core.security import token_digest


def csrf(client):
    return {"X-CSRF-Token": client.cookies.get("srs_csrf")}


def mail_token():
    from pathlib import Path
    files = list(Path(get_settings().MAIL_SINK_DIR).glob("*.eml"))
    message = BytesParser(policy=policy.default).parsebytes(files[-1].read_bytes())
    return re.search(r"#token=([\w-]+)", message.get_content()).group(1)


def test_cookie_session_csrf_origin_and_revocation(client, account, db_session):
    assert client.get("/auth/me").json()["email"] == "reviewer@example.com"
    assert client.post("/projects/", json={"name": "Denied"}).status_code == 403
    assert client.post("/projects/", headers={**csrf(client), "Origin": "https://attacker.example"}, json={"name": "Denied"}).status_code == 403
    assert client.post("/projects/", headers=csrf(client), json={"name": "Allowed"}).status_code == 200
    stored = db_session.query(AuthSession).one()
    assert stored.token_hash == token_digest(account["access_token"])
    assert stored.token_hash != account["access_token"]
    assert client.post("/auth/logout", headers=csrf(client)).status_code == 204
    assert client.get("/auth/me", headers={"Authorization": "Bearer " + account["access_token"]}).status_code == 401


def test_session_rotation_expiry_and_cookie_flags(client, account, db_session):
    response = client.post("/auth/login", json={"email": "REVIEWER@EXAMPLE.COM", "password": "testing-password-123"})
    assert response.status_code == 200
    cookie = response.headers.get_list("set-cookie")[0]
    assert "HttpOnly" in cookie and "SameSite=lax" in cookie
    assert client.get("/auth/me", headers={"Authorization": "Bearer " + account["access_token"]}).status_code == 401
    new = db_session.query(AuthSession).filter_by(token_hash=token_digest(response.json()["access_token"])).one()
    new.expires_at = datetime.utcnow() - timedelta(seconds=1)
    db_session.commit()
    assert client.get("/auth/me").status_code == 401


@pytest.mark.parametrize("token", ["bad", "x" * 300, "eyJhbGciOiJIUzI1NiJ9.invalid"])
def test_invalid_session_is_unauthorized(client, token):
    assert client.get("/auth/me", headers={"Authorization": "Bearer " + token}).status_code == 401


def test_old_bcrypt_password_upgraded_on_login(client, db_session):
    user = User(name="Legacy", email="legacy@example.com", hashed_password=bcrypt.hashpw(b"old-valid-password", bcrypt.gensalt()).decode())
    db_session.add(user); db_session.commit()
    assert client.post("/auth/login", json={"email": user.email, "password": "old-valid-password"}).status_code == 200
    db_session.refresh(user)
    assert user.hashed_password.startswith("$argon2")


def test_login_rate_limit_shared_in_database(client):
    for _ in range(10):
        assert client.post("/auth/login", json={"email": "unknown@example.com", "password": "invalid"}).status_code == 401
    denied = client.post("/auth/login", json={"email": "unknown@example.com", "password": "invalid"})
    assert denied.status_code == 429
    assert int(denied.headers["Retry-After"]) > 0


def test_reset_is_private_single_use_and_revokes_sessions(client, account, db_session):
    first = client.post("/auth/forgot-password", json={"email": "reviewer@example.com"})
    second = client.post("/auth/forgot-password", json={"email": "absent@example.com"})
    assert first.json() == second.json()
    token = mail_token()
    challenge = db_session.query(AuthChallenge).one()
    assert challenge.token_hash == token_digest(token)
    assert client.post("/auth/reset-password", json={"token": token, "password": "new-valid-password"}).status_code == 200
    assert client.get("/auth/me").status_code == 401
    assert client.post("/auth/reset-password", json={"token": token, "password": "new-valid-password"}).status_code == 400
    assert client.post("/auth/login", json={"email": "reviewer@example.com", "password": "testing-password-123"}).status_code == 401
    assert client.post("/auth/login", json={"email": "reviewer@example.com", "password": "new-valid-password"}).status_code == 200


def test_verification_is_single_use_and_purpose_bound(client, account, db_session):
    assert client.post("/auth/request-verification", headers=csrf(client)).status_code == 200
    token = mail_token()
    assert client.post("/auth/reset-password", json={"token": token, "password": "new-valid-password"}).status_code == 400
    assert client.post("/auth/verify-email", json={"token": token}).status_code == 200
    assert client.get("/auth/me").json()["email_verified"] is True
    assert client.post("/auth/verify-email", json={"token": token}).status_code == 400


def test_expired_recovery_token_rejected(client, account, db_session):
    client.post("/auth/forgot-password", json={"email": "reviewer@example.com"})
    token = mail_token()
    db_session.query(AuthChallenge).one().expires_at = datetime.utcnow() - timedelta(minutes=1)
    db_session.commit()
    assert client.post("/auth/reset-password", json={"token": token, "password": "new-valid-password"}).status_code == 400


def test_cross_origin_login_denied(client):
    assert client.post("/auth/login", headers={"Origin": "https://attacker.example"}, json={"email": "reviewer@example.com", "password": "testing-password-123"}).status_code == 403


@pytest.mark.parametrize("name,password", [("  ", "valid-password-123"), ("Name", "short"), ("Name", "x" * 129)])
def test_registration_policy(client, name, password):
    assert client.post("/auth/register", json={"name": name, "email": "test@example.com", "password": password}).status_code == 422


def test_csv_export_neutralizes_formulas(client, headers, db_session):
    import csv
    import io
    from app.models.traceability import TraceLink
    pid = client.post("/projects/", headers=headers, json={"name": "Export"}).json()["id"]
    db_session.add(TraceLink(project_id=pid, source_type="requirement", source_id="=1+1", target_type="usecase", target_id="\t+formula"))
    db_session.commit()
    response = client.get(f"/traceability/project/{pid}/export", headers=headers)
    assert response.status_code == 200
    rows = list(csv.reader(io.StringIO(response.text)))
    assert rows[1][1] == "'=1+1"
    assert rows[1][3].startswith("'")
