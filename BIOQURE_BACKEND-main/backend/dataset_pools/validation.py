"""FASTA payload checks for pool uploads (portable; object storage migration can reuse)."""

from __future__ import annotations

_MAX_SNIFF = 65536


def validate_fasta_bytes(data: bytes, *, max_bytes: int) -> None:
    """
    Reject empty, oversized, obviously binary, or non-FASTA-ish payloads.
    Does not fully validate biological correctness.
    """
    if not data:
        raise ValueError("Empty file")
    if len(data) > max_bytes:
        raise ValueError(f"File exceeds maximum size ({max_bytes // (1024 * 1024)} MiB)")
    if b"\x00" in data[:4096]:
        raise ValueError("Binary content is not allowed")
    # Tolerant decode for public FASTA (may include odd whitespace); binary still caught via NUL.
    head = data[:_MAX_SNIFF].decode("utf-8", errors="replace")
    lines = [ln.strip() for ln in head.splitlines() if ln.strip()]
    if not lines:
        raise ValueError("No content")
    first = lines[0]
    if first.startswith(">"):
        body = "".join(lines[1:])[:5000]
    else:
        body = "".join(lines)[:5000]
    # Allow common IUPAC ambiguity symbols seen in public assemblies.
    allowed = set("ACGTNacgtnRYSWKMBVDHryswkmbvdh \t\r\n-")
    if body and not all(c in allowed for c in body):
        raise ValueError("FASTA sequence region contains unsupported characters")
