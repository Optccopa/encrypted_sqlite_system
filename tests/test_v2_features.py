"""
test_v2_features.py — Tests for advanced cryptographic hardening, bug fixes,
concurrency checks, and disaster recovery envelope encryption.
"""

import os
import time
import pytest
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305, AESGCM

from src.database import (
    kv_set, kv_get, kv_delete, init_db, get_db_connection,
    derive_key_from_passphrase, set_cipher_passphrase, set_cipher_key,
    pack_and_encrypt, decrypt_and_unpack, _PREFIX_CHACHA,
    rebuild_bloom_filter, bloom, ConcurrentModificationError,
    set_indexed_fields, kv_find_by_index, DATA_DIR, DB_PATH
)
from src.secure_json import save_json, load_json
from src.transaction import Transaction
from src.write_behind import WriteBehindEngine
from src.cloud_sync import encrypt_snapshot_file, decrypt_snapshot_file, CloudSyncEngine


def test_passphrase_derivation():
    """Verify PBKDF2-HMAC-SHA256 passphrase key derivation."""
    key1, salt1 = derive_key_from_passphrase("SuperSecretPassphrase123!")
    key2, _ = derive_key_from_passphrase("SuperSecretPassphrase123!", salt=salt1)
    key3, _ = derive_key_from_passphrase("DifferentPassphrase", salt=salt1)

    assert len(key1) == 32
    assert key1 == key2
    assert key1 != key3

    # Set cipher passphrase
    set_cipher_passphrase("MyUniqueAppPassphrase999!")
    kv_set("passphrase_test.json", {"status": "authenticated", "code": 42})
    res = kv_get("passphrase_test.json")
    assert res == {"status": "authenticated", "code": 42}


def test_chacha20_poly1305_aead():
    """Verify ChaCha20-Poly1305 cipher integration and prefix tagging."""
    key_bytes = ChaCha20Poly1305.generate_key()
    cipher = ChaCha20Poly1305(key_bytes)

    payload = {"algorithm": "ChaCha20-Poly1305", "secure": True}
    encrypted = pack_and_encrypt(payload, cipher=cipher)

    assert encrypted.startswith(_PREFIX_CHACHA)

    decrypted = decrypt_and_unpack(encrypted, cipher=cipher)
    assert decrypted == payload


def test_zombie_disk_file_cleanup():
    """Verify that deleting a document removes the fallback disk file to prevent resurrection."""
    key = "zombie_test_doc.json"
    data = {"resurrected": False, "count": 1}

    save_json(key, data)
    assert (DATA_DIR / key).exists()

    # Call kv_delete
    kv_delete(key)

    # Disk file must be gone
    assert not (DATA_DIR / key).exists()

    # load_json should return default fallback, not resurrect
    recovered = load_json(key, default={"empty": True})
    assert recovered == {"empty": True}


def test_write_behind_blind_indexes_and_version():
    """Verify write-behind updates blind indexes, increments version, and honors TTL."""
    conn = get_db_connection()
    set_indexed_fields(["customer_id"])

    engine = WriteBehindEngine(flush_interval=0.05, max_batch_size=10)
    try:
        engine.queue_write("wb_order_1.json", {"customer_id": "cust_888", "amount": 199.95})
        engine.flush()

        # Check version and blind index in SQLite
        cur = conn.execute("SELECT version FROM kv_store WHERE key = 'wb_order_1.json'")
        row = cur.fetchone()
        assert row is not None
        assert row["version"] >= 1

        matches = kv_find_by_index("customer_id", "cust_888")
        assert "wb_order_1.json" in matches
        assert matches["wb_order_1.json"]["amount"] == 199.95
    finally:
        engine.close()
        set_indexed_fields([])


def test_bloom_filter_rebuild():
    """Verify that rebuild_bloom_filter repopulates from SQLite and clear() works."""
    init_db()
    kv_set("bloom_doc_1.json", {"a": 1})
    kv_set("bloom_doc_2.json", {"b": 2})

    assert bloom.contains("bloom_doc_1.json")
    assert bloom.contains("bloom_doc_2.json")

    bloom.clear()
    assert not bloom.contains("bloom_doc_1.json")

    rebuild_bloom_filter()
    assert bloom.contains("bloom_doc_1.json")
    assert bloom.contains("bloom_doc_2.json")


def test_transaction_optimistic_locking_conflict():
    """Verify that Transaction detects concurrent modifications and rolls back."""
    key = "bank_account.json"
    kv_set(key, {"balance": 100})

    tx = Transaction()
    val = tx.get(key)
    assert val == {"balance": 100}

    # Simulate another thread/process modifying the document while tx is open
    kv_set(key, {"balance": 150})

    # tx tries to write based on stale read
    tx.set(key, {"balance": val["balance"] + 20})

    # commit must raise ConcurrentModificationError
    with pytest.raises(ConcurrentModificationError):
        tx.commit()

    # Balance must remain the concurrent writer's 150
    assert kv_get(key) == {"balance": 150}


def test_cloud_snapshot_envelope_encryption(tmp_path):
    """Verify whole-snapshot AES-256-GCM envelope encryption and decryption."""
    dummy_db = tmp_path / "test_snapshot.db"
    dummy_db.write_bytes(b"SQLite format 3\x00DummyDatabasePayloadForTestingEnvelopeEncryption123456")

    enc_path = tmp_path / "test_snapshot.db.enc"
    dec_path = tmp_path / "test_snapshot_decrypted.db"

    encrypt_snapshot_file(dummy_db, enc_path)
    assert enc_path.exists()
    assert enc_path.read_bytes().startswith(b"ENCSNAP1:")

    decrypt_snapshot_file(enc_path, dec_path)
    assert dec_path.exists()
    assert dec_path.read_bytes() == dummy_db.read_bytes()
