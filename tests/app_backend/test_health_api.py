from fastapi.testclient import TestClient

from app.backend.main import create_app
from app.backend.models.settings import AppSettings
from app.backend.services.download_manager import DownloadManager


def test_health_endpoint():
    app = create_app(
        manager=DownloadManager(settings=AppSettings(), providers=[]),
    )
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_providers_endpoint():
    app = create_app(
        manager=DownloadManager(settings=AppSettings(), providers=[]),
    )
    client = TestClient(app)
    response = client.get("/api/providers")
    assert response.status_code == 200
    assert response.json() == []

