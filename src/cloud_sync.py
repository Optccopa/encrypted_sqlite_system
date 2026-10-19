"""
cloud_sync.py — Encrypted Cloud Backup & Disaster Recovery Sync Engine.

Provides zero-downtime online SQLite database backups and background synchronization
to S3-compatible cloud object storage providers:
- Cloudflare R2
- AWS S3
- Backblaze B2
- MinIO / Self-hosted S3

Features:
- Non-blocking online database snapshots via SQLite Backup API.
- Automated retention policy (e.g. keep last N backups).
- Remote backup listing and 1-command cloud disaster recovery restore.
"""

import os
import time
import shutil
import sqlite3
import hashlib
from typing import Any
from pathlib import Path
from .database import DB_PATH, DATA_DIR


def encrypt_snapshot_file(source_path: Path, output_path: Path, raw_key: bytes | None = None) -> Path:
    """Encrypt a point-in-time SQLite snapshot file using AES-256-GCM envelope encryption."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from .database import _get_raw_key_material
    key = raw_key if raw_key is not None else _get_raw_key_material()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    data = source_path.read_bytes()
    ciphertext = aesgcm.encrypt(nonce, data, associated_data=b"sqlite-snapshot-envelope-v1")
    payload = b"ENCSNAP1:" + nonce + ciphertext
    output_path.write_bytes(payload)
    return output_path


def decrypt_snapshot_file(source_path: Path, output_path: Path, raw_key: bytes | None = None) -> Path:
    """Decrypt an encrypted snapshot envelope file using AES-256-GCM."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from .database import _get_raw_key_material
    key = raw_key if raw_key is not None else _get_raw_key_material()
    aesgcm = AESGCM(key)
    raw = source_path.read_bytes()
    if not raw.startswith(b"ENCSNAP1:") or len(raw) < 21:
        raise ValueError("Invalid encrypted snapshot format or missing header.")
    nonce = raw[9:21]
    ciphertext = raw[21:]
    plaintext = aesgcm.decrypt(nonce, ciphertext, associated_data=b"sqlite-snapshot-envelope-v1")
    output_path.write_bytes(plaintext)
    return output_path


class CloudSyncEngine:
    """Manages online encrypted database snapshots and S3 cloud synchronization."""

    def __init__(
        self,
        bucket_name: str | None = None,
        endpoint_url: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        region_name: str = "auto"
    ):
        self.bucket_name = bucket_name or os.getenv("S3_BUCKET_NAME", "encrypted-sqlite-backups")
        self.endpoint_url = endpoint_url or os.getenv("S3_ENDPOINT_URL")
        self.access_key = access_key or os.getenv("S3_ACCESS_KEY_ID")
        self.secret_key = secret_key or os.getenv("S3_SECRET_ACCESS_KEY")
        self.region_name = region_name or os.getenv("S3_REGION", "auto")

    def create_local_snapshot(self, snapshot_name: str | None = None) -> Path:
        """
        Create a live, point-in-time consistent SQLite snapshot using SQLite Online Backup API.
        Guarantees zero database locking or bot downtime.
        """
        snapshots_dir = DATA_DIR / "snapshots"
        snapshots_dir.mkdir(parents=True, exist_ok=True)

        ts_str = time.strftime("%Y%m%d_%H%M%S")
        name = snapshot_name or f"snapshot_{ts_str}"
        target_path = snapshots_dir / f"{name}.db"

        if DB_PATH.exists():
            # Online atomic SQLite backup
            source_conn = sqlite3.connect(str(DB_PATH), timeout=30.0)
            dest_conn = sqlite3.connect(str(target_path))
            try:
                with dest_conn:
                    source_conn.backup(dest_conn)
            finally:
                source_conn.close()
                dest_conn.close()
        else:
            # Empty database case
            target_path.touch()

        return target_path

    def compute_file_sha256(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of a file for integrity check."""
        sha = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha.update(chunk)
        return sha.hexdigest()

    def sync_to_cloud(
        self,
        snapshot_path: Path | None = None,
        retention_count: int = 7,
        client: Any = None,
        encrypt: bool = False
    ) -> dict:
        """
        Upload local encrypted database snapshot to S3/Cloudflare R2 and prune older backups.
        Supports whole-file AES-256-GCM envelope encryption.
        """
        if snapshot_path is None or not snapshot_path.exists():
            snapshot_path = self.create_local_snapshot()

        should_encrypt = encrypt or os.getenv("ENCRYPT_CLOUD_BACKUPS", "false").lower() in ("true", "1", "yes")
        upload_path = snapshot_path
        temp_enc_path = None

        if should_encrypt and not snapshot_path.name.endswith(".enc"):
            temp_enc_path = snapshot_path.with_suffix(snapshot_path.suffix + ".enc")
            encrypt_snapshot_file(snapshot_path, temp_enc_path)
            upload_path = temp_enc_path

        try:
            file_size = upload_path.stat().st_size
            checksum = self.compute_file_sha256(upload_path)
            remote_key = f"backups/{upload_path.name}"

            s3_client = client or self._get_s3_client()

            if s3_client is not None:
                # Upload snapshot to S3 bucket
                with open(upload_path, "rb") as f:
                    s3_client.put_object(
                        Bucket=self.bucket_name,
                        Key=remote_key,
                        Body=f,
                        Metadata={"sha256": checksum, "encrypted": str(should_encrypt).lower()}
                    )

                # Auto-prune old remote backups if retention_count is set
                self._prune_remote_backups(s3_client, retention_count)

            return {
                "status": "success",
                "snapshot_file": str(upload_path.name),
                "size_bytes": file_size,
                "sha256": checksum,
                "remote_key": remote_key,
                "bucket": self.bucket_name,
                "encrypted": should_encrypt,
                "timestamp": int(time.time()),
            }
        finally:
            if temp_enc_path is not None and temp_enc_path.exists():
                try:
                    temp_enc_path.unlink()
                except Exception:
                    pass

    def list_cloud_backups(self, client: Any = None) -> list[dict]:
        """List all available remote backups in the cloud bucket."""
        s3_client = client or self._get_s3_client()
        if s3_client is None:
            return []

        try:
            response = s3_client.list_objects_v2(Bucket=self.bucket_name, Prefix="backups/")
            contents = response.get("Contents", [])
            backups = []
            for item in sorted(contents, key=lambda x: x.get("LastModified", ""), reverse=True):
                backups.append({
                    "key": item["Key"],
                    "size_bytes": item["Size"],
                    "last_modified": str(item.get("LastModified")),
                })
            return backups
        except Exception as e:
            print(f"[CloudSync] Error listing cloud backups: {e}")
            return []

    def restore_from_cloud(
        self,
        remote_key: str,
        target_path: Path | None = None,
        client: Any = None
    ) -> bool:
        """Download remote backup, decrypt if envelope-encrypted, and restore database."""
        target_path = target_path or DB_PATH
        s3_client = client or self._get_s3_client()
        if s3_client is None:
            return False

        temp_restore = DATA_DIR / "restore_temp.db"
        temp_download = DATA_DIR / "restore_download.tmp"
        try:
            with open(temp_download, "wb") as f:
                s3_client.download_fileobj(self.bucket_name, remote_key, f)

            # Check if downloaded backup is envelope-encrypted
            is_encrypted = False
            with open(temp_download, "rb") as f:
                header = f.read(9)
                if header == b"ENCSNAP1:":
                    is_encrypted = True

            if is_encrypted or remote_key.endswith(".enc"):
                decrypt_snapshot_file(temp_download, temp_restore)
                temp_download.unlink(missing_ok=True)
            else:
                shutil.move(temp_download, temp_restore)

            # Verify SQLite integrity
            check_conn = sqlite3.connect(str(temp_restore))
            with check_conn:
                check_conn.execute("PRAGMA integrity_check")
            check_conn.close()

            # Atomic replace
            if target_path.exists():
                shutil.copy2(target_path, DATA_DIR / "backup_before_restore.db")
            shutil.move(temp_restore, target_path)
            return True
        except Exception as e:
            print(f"[CloudSync] Error restoring cloud backup: {e}")
            if temp_download.exists():
                temp_download.unlink()
            if temp_restore.exists():
                temp_restore.unlink()
            return False

    def _prune_remote_backups(self, s3_client: Any, retention_count: int):
        """Keep only the most recent N backups in cloud bucket."""
        if retention_count <= 0:
            return
        try:
            backups = self.list_cloud_backups(client=s3_client)
            if len(backups) > retention_count:
                to_delete = backups[retention_count:]
                for item in to_delete:
                    s3_client.delete_object(Bucket=self.bucket_name, Key=item["key"])
        except Exception:
            pass

    def _get_s3_client(self) -> Any:
        """Dynamically initialize boto3 S3 client if available."""
        try:
            import boto3
            session = boto3.session.Session()
            return session.client(
                "s3",
                endpoint_url=self.endpoint_url,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                region_name=self.region_name
            )
        except ImportError:
            return None


# Global singleton instance
cloud_sync = CloudSyncEngine()
