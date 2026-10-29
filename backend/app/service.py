from datetime import UTC, datetime
from uuid import UUID, uuid4

from botocore.exceptions import ClientError

from backend.app.repository import LinkRepository


class LinkService:
    def __init__(self, repository: LinkRepository):
        self.repository = repository

    def create(self, original_url: str) -> dict[str, str]:
        for _ in range(3):
            item = {
                "short_code": str(uuid4()),
                "original_url": original_url,
                "created_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            }
            try:
                self.repository.insert(item)
                return item
            except ClientError as exc:
                if exc.response["Error"]["Code"] != "ConditionalCheckFailedException":
                    raise
        raise RuntimeError("No se pudo generar un identificador único.")

    def find(self, short_code: str) -> dict[str, str] | None:
        try:
            canonical_code = str(UUID(short_code))
        except ValueError:
            return None
        return self.repository.get(canonical_code)
