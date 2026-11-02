"""Run against disposable development/CI services, never a production URL."""
import io
import os
import time
import uuid
import httpx
from docx import Document


def main():
    base = os.environ.get("SMOKE_API_URL", "http://localhost:5173/api")
    with httpx.Client(base_url=base, timeout=30) as client:
        for attempt in range(60):
            try:
                if client.get("/ready").status_code == 200:
                    break
            except httpx.TransportError:
                pass
            time.sleep(1)
        else:
            raise RuntimeError("API did not become ready through the frontend proxy")
        response = client.post("/auth/register", json={"name": "Smoke reviewer", "email": f"smoke-{uuid.uuid4().hex}@example.com", "password": "smoke-only-password-123"})
        response.raise_for_status()
        assert client.get("/auth/me").status_code == 200
        headers = {"X-CSRF-Token": client.cookies.get("srs_csrf")}
        response = client.post("/projects/", json={"name": "Smoke specification"}, headers=headers)
        response.raise_for_status()
        pid = response.json()["id"]
        document = Document()
        document.add_paragraph("FR-1 The system shall save the submitted record.")
        buffer = io.BytesIO(); document.save(buffer)
        response = client.post(f"/projects/{pid}/upload-srs", headers=headers, files={"file": ("smoke.docx", buffer.getvalue())})
        response.raise_for_status()
        assert client.post("/auth/logout", headers=headers).status_code == 204
        assert client.get("/auth/me").status_code == 401
        print("HTTP smoke passed: proxy readiness, signup, cookie auth, CSRF, project creation, upload and logout")


if __name__ == "__main__":
    main()
