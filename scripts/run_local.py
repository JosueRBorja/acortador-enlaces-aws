"""Demo local con DynamoDB emulado. Los datos se pierden al detener el proceso."""

import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import urlsplit

import boto3
import uvicorn
from moto import mock_aws

# Permite ejecutar `python scripts/run_local.py` desde cualquier carpeta.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.config import Settings  # noqa: E402
from backend.app.main import create_app  # noqa: E402


class LocalFrontend(SimpleHTTPRequestHandler):
    def do_GET(self) -> None:
        # La demo siempre llama a localhost aunque config.js ya apunte a EC2.
        if urlsplit(self.path).path == "/config.js":
            body = b'window.APP_CONFIG = Object.freeze({API_BASE_URL:"http://127.0.0.1:8000"});'
            self.send_response(200)
            self.send_header("Content-Type", "application/javascript; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()


def main() -> None:
    settings = Settings(
        _env_file=None,
        aws_region="us-east-1",
        dynamodb_table="nexo-local-demo",
        public_base_url="http://127.0.0.1:8000",
        cors_origins=["http://127.0.0.1:5500", "http://localhost:5500"],
    )
    handler = partial(LocalFrontend, directory=str(ROOT / "frontend"))
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name=settings.aws_region)
        dynamodb.create_table(
            TableName=settings.dynamodb_table,
            KeySchema=[{"AttributeName": "short_code", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "short_code", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        try:
            with ThreadingHTTPServer(("127.0.0.1", 5500), handler) as frontend:
                worker = Thread(target=frontend.serve_forever, daemon=True)
                worker.start()
                print("DEMO LOCAL: DynamoDB simulado; datos temporales. No usa tu cuenta AWS.")
                print("Interfaz: http://127.0.0.1:5500")
                print("API: http://127.0.0.1:8000/docs")
                print("Detener: Ctrl+C")
                try:
                    uvicorn.run(create_app(settings), host="127.0.0.1", port=8000, access_log=False)
                finally:
                    frontend.shutdown()
                    worker.join(timeout=5)
        finally:
            dynamodb.meta.client.close()


if __name__ == "__main__":
    main()
