# ============================================================
# S3 / MinIO Storage Backend — S3-Compatible Object Storage
# ============================================================

from __future__ import annotations

import asyncio
import io
from typing import Any

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from backend.app.core.config import get_settings
from backend.app.core.exceptions import StorageError
from backend.app.core.logging import logger
from backend.app.storage.base import StorageBackend


class S3Storage(StorageBackend):
    """S3-compatible object storage backend supporting AWS S3 and MinIO."""

    def __init__(self):
        settings = get_settings()
        self.endpoint_url = settings.s3_endpoint
        self.region = settings.s3_region
        self.access_key = settings.s3_access_key
        self.secret_key = settings.s3_secret_key
        self.bucket = settings.s3_bucket
        self.use_ssl = settings.s3_secure

        self.client = boto3.client(
            "s3",
            endpoint_url=self.endpoint_url,
            region_name=self.region,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            use_ssl=self.use_ssl,
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        )

        # Initialize bucket idempotently
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self) -> None:
        """Create the target bucket if it does not already exist."""
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except ClientError as e:
            error_code = str(e.response.get("Error", {}).get("Code", ""))
            if error_code in ("404", "NoSuchBucket"):
                try:
                    if self.region and self.region != "us-east-1":
                        self.client.create_bucket(
                            Bucket=self.bucket,
                            CreateBucketConfiguration={"LocationConstraint": self.region},
                        )
                    else:
                        self.client.create_bucket(Bucket=self.bucket)
                    logger.info("Created S3/MinIO bucket '{bucket}'", bucket=self.bucket)
                except Exception as create_exc:
                    logger.warning("Could not auto-create bucket '{bucket}': {err}", bucket=self.bucket, err=str(create_exc))
            else:
                logger.warning("S3 head_bucket check warning: {err}", err=str(e))
        except Exception as exc:
            logger.warning("S3 client initialization warning (storage may be offline during build): {err}", err=str(exc))

    def _clean_key(self, path: str) -> str:
        """Sanitize and normalize an object key to prevent traversal."""
        clean = path.replace("\\", "/").strip().lstrip("/")
        parts = clean.split("/")
        if ".." in parts:
            raise StorageError("Path traversal detected in object key")
        return "/".join(p for p in parts if p)

    async def store(self, content: bytes, path: str) -> str:
        """Store content in S3/MinIO under the cleaned object key."""
        key = self._clean_key(path)

        def _put():
            self.client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=content,
            )

        try:
            await asyncio.to_thread(_put)
            return key
        except Exception as exc:
            raise StorageError(f"Failed to store object in S3: {exc}") from exc

    async def retrieve(self, path: str) -> bytes:
        """Retrieve object content from S3/MinIO."""
        key = self._clean_key(path)

        def _get() -> bytes:
            resp = self.client.get_object(Bucket=self.bucket, Key=key)
            return resp["Body"].read()

        try:
            return await asyncio.to_thread(_get)
        except ClientError as ce:
            error_code = str(ce.response.get("Error", {}).get("Code", ""))
            if error_code in ("404", "NoSuchKey"):
                raise StorageError(f"Object not found in S3: {key}") from ce
            raise StorageError(f"S3 retrieve error: {ce}") from ce
        except Exception as exc:
            raise StorageError(f"Failed to retrieve object from S3: {exc}") from exc

    async def delete(self, path: str) -> bool:
        """Delete an object from S3/MinIO."""
        key = self._clean_key(path)

        def _del():
            self.client.delete_object(Bucket=self.bucket, Key=key)

        try:
            await asyncio.to_thread(_del)
            return True
        except Exception:
            return False

    async def get_url(self, path: str) -> str:
        """Return the canonical S3 URI or presigned URL."""
        key = self._clean_key(path)
        return f"s3://{self.bucket}/{key}"

    async def object_exists(self, path: str) -> bool:
        """Check if an object exists in S3."""
        key = self._clean_key(path)

        def _head():
            try:
                self.client.head_object(Bucket=self.bucket, Key=key)
                return True
            except ClientError:
                return False

        return await asyncio.to_thread(_head)

    async def head_object(self, path: str) -> dict | None:
        """Retrieve S3 object metadata."""
        key = self._clean_key(path)

        def _head():
            try:
                resp = self.client.head_object(Bucket=self.bucket, Key=key)
                return {
                    "size_bytes": resp.get("ContentLength", 0),
                    "content_type": resp.get("ContentType"),
                    "etag": resp.get("ETag", "").strip('"'),
                    "modified_at": resp.get("LastModified"),
                }
            except ClientError:
                return None

        return await asyncio.to_thread(_head)

    async def copy_object(self, source_path: str, dest_path: str) -> str:
        """Copy object from source key to destination key within the bucket."""
        src_key = self._clean_key(source_path)
        dst_key = self._clean_key(dest_path)

        def _copy():
            copy_source = {"Bucket": self.bucket, "Key": src_key}
            self.client.copy_object(
                Bucket=self.bucket,
                Key=dst_key,
                CopySource=copy_source,
            )

        try:
            await asyncio.to_thread(_copy)
            return dst_key
        except Exception as exc:
            raise StorageError(f"Failed to copy S3 object: {exc}") from exc

    async def generate_download_reference(self, path: str, expires_in_seconds: int = 3600) -> str:
        """Generate a secure, time-limited presigned download URL."""
        key = self._clean_key(path)

        def _presign():
            return self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=expires_in_seconds,
            )

        try:
            return await asyncio.to_thread(_presign)
        except Exception as exc:
            raise StorageError(f"Failed to generate presigned download URL: {exc}") from exc
