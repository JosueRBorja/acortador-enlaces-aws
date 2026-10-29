import boto3
import pytest
from fastapi.testclient import TestClient
from moto import mock_aws

from backend.app.config import Settings
from backend.app.main import create_app


@pytest.fixture
def aws_table(monkeypatch):
    # Credenciales ficticias, válidas únicamente dentro del emulador Moto.
    for key in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN"):
        monkeypatch.setenv(key, "testing")
    with mock_aws():
        table = boto3.resource("dynamodb", region_name="us-east-1").create_table(
            TableName="test-links",
            KeySchema=[{"AttributeName": "short_code", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "short_code", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        yield table


@pytest.fixture
def settings():
    return Settings(
        _env_file=None,
        dynamodb_table="test-links",
        public_base_url="https://api.example.com",
        cors_origins=["http://frontend.example.com"],
    )


@pytest.fixture
def client(aws_table, settings):
    with TestClient(create_app(settings)) as client:
        yield client
