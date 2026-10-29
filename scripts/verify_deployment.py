"""Pruebas HTTP contra EC2 real; crea un elemento y no sigue redirecciones."""

import argparse
from datetime import datetime
from uuid import UUID, uuid4

import httpx


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", required=True)
    parser.add_argument("--origin", required=True, help="WebsiteUrl exacto de S3")
    parser.add_argument("--existing-code", help="UUID creado antes de reiniciar el backend")
    args = parser.parse_args()
    with httpx.Client(
        base_url=args.api_url.rstrip("/"), timeout=30, follow_redirects=False
    ) as client:
        if args.existing_code:
            info = client.get(f"/urls/{args.existing_code}")
            info.raise_for_status()
            redirect = client.get(f"/{args.existing_code}")
            assert redirect.status_code == 307, redirect.text
            assert redirect.headers["location"] == info.json()["original_url"]
            print("OK: el enlace previamente creado conserva su destino.")
            return
        origin = args.origin.rstrip("/")
        preflight = client.options(
            "/shorten",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        assert preflight.status_code == 200, preflight.text
        assert preflight.headers.get("access-control-allow-origin") == origin
        response = client.post(
            "/shorten",
            json={"original_url": "https://www.example.com/"},
            headers={"Origin": origin},
        )
        assert response.status_code == 201, response.text
        assert response.headers.get("access-control-allow-origin") == origin
        data = response.json()
        code = data["short_code"]
        assert UUID(code).version == 4
        assert data["short_url"] == f"{args.api_url.rstrip('/')}/{code}"
        assert datetime.fromisoformat(data["created_at"]).tzinfo is not None
        info = client.get(f"/urls/{code}")
        assert info.status_code == 200, info.text
        assert info.json()["original_url"] == data["original_url"]
        assert info.json()["created_at"] == data["created_at"]
        redirect = client.get(f"/{code}")
        assert redirect.status_code == 307, redirect.text
        assert redirect.headers["location"] == data["original_url"]
        missing = str(uuid4())
        assert client.get(f"/{missing}").status_code == 404
        assert client.get(f"/urls/{missing}").status_code == 404
        assert client.post("/shorten", json={"original_url": "invalida"}).status_code == 422
        print("OK: CORS, creación, UUID, consulta, redirección 307, 404 y validación.")
        print(f"UUID creado: {code}")
        print("Verifica el registro en DynamoDB y reinicia systemd en EC2.")
        print(f"Repite este comando agregando --existing-code {code}")


if __name__ == "__main__":
    main()
