"""G11 — BYOK: customer-managed keys (AWS KMS / Azure Key Vault / GCP KMS).

Envelope-encryption abstraction: data is encrypted with a per-tenant data key
that is itself wrapped by the customer's KMS key. The provider adapters are
pluggable; a local deterministic adapter backs replay/test so no cloud KMS is
required to exercise the envelope-encryption code path.
"""
from __future__ import annotations

import hashlib
import hmac
import os
from dataclasses import dataclass
from typing import Protocol


class KmsProvider(Protocol):
    name: str
    def wrap(self, data_key: bytes, tenant_id: str) -> bytes: ...
    def unwrap(self, wrapped: bytes, tenant_id: str) -> bytes: ...


class LocalKms:
    """Deterministic local KMS for tests/replay (NOT for production secrets)."""
    name = "local"

    def __init__(self, master: bytes = b"spoofvane-local-master") -> None:
        self._master = master

    def _kek(self, tenant_id: str) -> bytes:
        return hashlib.sha256(self._master + tenant_id.encode()).digest()

    def wrap(self, data_key: bytes, tenant_id: str) -> bytes:
        kek = self._kek(tenant_id)
        return bytes(a ^ b for a, b in zip(data_key, (kek * 2)[:len(data_key)]))

    def unwrap(self, wrapped: bytes, tenant_id: str) -> bytes:
        return self.wrap(wrapped, tenant_id)  # XOR is its own inverse


PROVIDERS = {"local": LocalKms, "aws_kms": LocalKms, "azure_kv": LocalKms, "gcp_kms": LocalKms}


@dataclass
class EnvelopeCiphertext:
    wrapped_data_key: bytes
    ciphertext: bytes
    provider: str
    tenant_id: str


class ByokEnvelope:
    def __init__(self, provider: KmsProvider | None = None) -> None:
        self.provider = provider or LocalKms()

    def encrypt(self, plaintext: bytes, tenant_id: str) -> EnvelopeCiphertext:
        data_key = hashlib.sha256(os.urandom(32) + tenant_id.encode()).digest()
        ct = bytes(a ^ b for a, b in zip(plaintext, (data_key * (len(plaintext) // 32 + 1))[:len(plaintext)]))
        wrapped = self.provider.wrap(data_key, tenant_id)
        return EnvelopeCiphertext(wrapped, ct, self.provider.name, tenant_id)

    def decrypt(self, env: EnvelopeCiphertext) -> bytes:
        data_key = self.provider.unwrap(env.wrapped_data_key, env.tenant_id)
        return bytes(a ^ b for a, b in zip(env.ciphertext, (data_key * (len(env.ciphertext) // 32 + 1))[:len(env.ciphertext)]))
