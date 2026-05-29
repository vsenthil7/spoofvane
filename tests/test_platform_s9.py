"""Sprint 9 — platform G7, G8, G10, G11, G12 (review §8 group G)."""
import pytest
from src.common.rate_limiter import TokenBucketRateLimiter
from src.common.idempotency import IdempotencyStore
from src.common.byok import ByokEnvelope, LocalKms, PROVIDERS
from src.common.data_residency import DataResidencyGuard, ResidencyViolation, REGIONS
from src.deepfake.chain_of_custody import ChainOfCustody


def test_rate_limiter_blocks_over_capacity():
    rl = TokenBucketRateLimiter(capacity=3, refill_per_sec=0)
    assert [rl.allow("t") for _ in range(5)] == [True, True, True, False, False]


def test_rate_limiter_per_tenant_isolated():
    rl = TokenBucketRateLimiter(capacity=1, refill_per_sec=0)
    assert rl.allow("a") and rl.allow("b")  # separate buckets
    assert not rl.allow("a")


def test_idempotency_executes_once():
    store = IdempotencyStore(); n = []
    fn = lambda: (n.append(1), "r")[1]
    r1, replayed1 = store.execute("t", "k", fn)
    r2, replayed2 = store.execute("t", "k", fn)
    assert r1 == r2 == "r"
    assert replayed1 is False and replayed2 is True
    assert len(n) == 1


def test_idempotency_key_scoped_per_tenant():
    store = IdempotencyStore()
    store.execute("a", "k", lambda: "A")
    r, replayed = store.execute("b", "k", lambda: "B")
    assert r == "B" and replayed is False


def test_byok_envelope_roundtrip():
    for name in PROVIDERS:
        b = ByokEnvelope(PROVIDERS[name]())
        ct = b.encrypt(b"top secret payload", "tenant-1")
        assert b.decrypt(ct) == b"top secret payload"


def test_byok_wrong_tenant_cannot_decrypt():
    b = ByokEnvelope(LocalKms())
    ct = b.encrypt(b"secret", "tenant-1")
    # decrypting with a ciphertext rebound to another tenant yields garbage
    ct.tenant_id = "tenant-2"
    assert b.decrypt(ct) != b"secret"


def test_data_residency_blocks_cross_region():
    g = DataResidencyGuard(); g.set_region("t", "EU")
    with pytest.raises(ResidencyViolation):
        g.route("t", "US", "store_evidence")


def test_data_residency_allows_same_region_with_proof():
    g = DataResidencyGuard(); g.set_region("t", "IN")
    proof = g.route("t", "IN", "store_evidence")
    assert proof.crossed_boundary is False
    assert "ap-south-1" in proof.endpoint


def test_all_four_regions_supported():
    assert REGIONS == {"EU", "US", "APAC", "IN"}


def test_chain_of_custody_verifies_and_detects_tamper():
    coc = ChainOfCustody("df_1")
    coc.record("acquired", "analyst1", b"video-bytes")
    coc.record("analysed", "analyst2", b"video-bytes")
    coc.record("exported", "legal", b"video-bytes")
    assert coc.verify() is True
    pack = coc.export_pack()
    assert pack["event_count"] == 3 and pack["chain_valid"] is True
    coc.events[1].handler = "attacker"
    assert coc.verify() is False
