"""Dove vivono i file caricati (i PDF delle bollette): in una cartella locale oppure su un servizio compatibile con S3
(AWS S3, MinIO, Cloudflare R2, Backblaze B2, Wasabi...). Stessa interfaccia, scelta con STORAGE_DRIVER.

L'app non espone mai l'indirizzo del bucket: i file passano da qui, così valgono gli stessi controlli di accesso dell'API."""
from __future__ import annotations

import io
from pathlib import Path
from typing import Protocol


class Storage(Protocol):
    def put(self, name: str, data: bytes) -> None: ...
    def get(self, name: str) -> bytes: ...
    def exists(self, name: str) -> bool: ...
    def delete(self, name: str) -> None: ...


class LocalStorage:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, name: str) -> Path:
        path = (self.root / name).resolve()
        if self.root.resolve() not in path.parents:
            raise ValueError(f"Nome file non valido: {name}")
        return path

    def put(self, name: str, data: bytes) -> None:
        self._path(name).write_bytes(data)

    def get(self, name: str) -> bytes:
        return self._path(name).read_bytes()

    def exists(self, name: str) -> bool:
        return self._path(name).is_file()

    def delete(self, name: str) -> None:
        self._path(name).unlink(missing_ok=True)

    def __repr__(self) -> str:
        return f"cartella {self.root}"


class S3Storage:
    def __init__(self, bucket: str, prefix: str = "", endpoint_url: str | None = None, region: str | None = None,
                 access_key_id: str | None = None, secret_access_key: str | None = None, addressing: str = "auto"):
        import boto3
        from botocore.config import Config

        if not bucket:
            raise ValueError("STORAGE_DRIVER=s3 richiede S3_BUCKET.")
        self.bucket, self.prefix = bucket, prefix.strip("/")
        self.endpoint_url = endpoint_url
        # MinIO e simili vogliono l'indirizzo «a percorso» (host/bucket/chiave); AWS, di norma, quello «virtuale»
        style = addressing if addressing in ("path", "virtual") else ("path" if endpoint_url else "auto")
        self.client = boto3.client(
            "s3", endpoint_url=endpoint_url, region_name=region or ("us-east-1" if endpoint_url else None),
            aws_access_key_id=access_key_id, aws_secret_access_key=secret_access_key,
            config=Config(s3={"addressing_style": style}, retries={"max_attempts": 3}),
        )

    def _key(self, name: str) -> str:
        if "/" in name or name in ("", ".", ".."):
            raise ValueError(f"Nome file non valido: {name}")
        return f"{self.prefix}/{name}" if self.prefix else name

    def put(self, name: str, data: bytes) -> None:
        self.client.put_object(Bucket=self.bucket, Key=self._key(name), Body=data, ContentType="application/pdf")

    def get(self, name: str) -> bytes:
        try:
            return self.client.get_object(Bucket=self.bucket, Key=self._key(name))["Body"].read()
        except self.client.exceptions.NoSuchKey:
            raise FileNotFoundError(name) from None

    def exists(self, name: str) -> bool:
        from botocore.exceptions import ClientError

        try:
            self.client.head_object(Bucket=self.bucket, Key=self._key(name))
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] in ("404", "NoSuchKey", "NotFound"):
                return False
            raise

    def delete(self, name: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=self._key(name))  # S3 non protesta se la chiave non esiste

    def check(self) -> None:
        """All'avvio: fallisce subito (e chiaramente) se bucket o credenziali non vanno, invece che al primo upload."""
        self.client.head_bucket(Bucket=self.bucket)

    def __repr__(self) -> str:
        return f"bucket s3://{self.bucket}/{self.prefix}" + (f" ({self.endpoint_url})" if self.endpoint_url else "")


def from_config(cfg) -> Storage:
    driver = cfg["STORAGE_DRIVER"]
    if driver == "local":
        return LocalStorage(cfg["STORAGE_PATH"])
    if driver == "s3":
        return S3Storage(cfg["S3_BUCKET"], cfg["S3_PREFIX"], cfg["S3_ENDPOINT_URL"], cfg["S3_REGION"],
                         cfg["S3_ACCESS_KEY_ID"], cfg["S3_SECRET_ACCESS_KEY"], cfg["S3_ADDRESSING"])
    raise ValueError(f"STORAGE_DRIVER non valido: «{driver}» (valori ammessi: local, s3).")


def as_file(data: bytes) -> io.BytesIO:
    return io.BytesIO(data)
