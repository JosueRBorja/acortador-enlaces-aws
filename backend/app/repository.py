from typing import Any

import boto3
from botocore.config import Config

from backend.app.config import Settings


class LinkRepository:
    """Acceso a DynamoDB. Boto3 resuelve las credenciales mediante su cadena estándar."""

    def __init__(self, settings: Settings):
        self.resource = boto3.resource(
            "dynamodb",
            region_name=settings.aws_region,
            config=Config(
                connect_timeout=3,
                read_timeout=5,
                retries={"mode": "standard", "total_max_attempts": 3},
            ),
        )
        self.table = self.resource.Table(settings.dynamodb_table)

    def insert(self, item: dict[str, str]) -> None:
        # Evita sobrescribir otro enlace incluso ante una improbable colisión de UUID.
        self.table.put_item(Item=item, ConditionExpression="attribute_not_exists(short_code)")

    def get(self, short_code: str) -> dict[str, Any] | None:
        result = self.table.get_item(Key={"short_code": short_code}, ConsistentRead=True)
        return result.get("Item")

    def close(self) -> None:
        self.resource.meta.client.close()
