"""
Minimal, dependency-free Snappy block-format encoder.

Prometheus Remote Write and Loki's protobuf push both require the request body
to be Snappy-compressed (block format, not framed) -- but they do NOT require the
data to actually be *compressed*. Snappy's block format allows a run of raw
"literal" bytes, so we emit a valid Snappy block that stores the payload
verbatim (zero compression). Every conformant Snappy reader accepts it, and we
avoid the C `python-snappy` dependency.

Format (https://github.com/google/snappy/blob/main/format_description.txt):
  * preamble: uncompressed length as a little-endian base-128 varint
  * one or more elements; a literal element is a tag byte whose low 2 bits are
    00, then the raw bytes. For a literal of length L:
      - if L-1 < 60: tag = (L-1) << 2
      - else:        tag = (59 + n) << 2, followed by n little-endian bytes of
                     (L-1), where n is how many bytes (1..4) L-1 needs.

Only encoding is implemented (we produce payloads; we never read them).
"""
from __future__ import annotations

#: Snappy literals cannot exceed 2**32 bytes; chunk anything larger.
_MAX_LITERAL = 0xFFFFFFFF + 1


def _varint(n: int) -> bytes:
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def _literal(chunk: bytes) -> bytes:
    length_minus_1 = len(chunk) - 1
    out = bytearray()
    if length_minus_1 < 60:
        out.append(length_minus_1 << 2)
    else:
        n = (length_minus_1.bit_length() + 7) // 8      # bytes needed (1..4)
        out.append((59 + n) << 2)
        for i in range(n):
            out.append((length_minus_1 >> (8 * i)) & 0xFF)
    return bytes(out) + chunk


def compress(data: bytes) -> bytes:
    """Return a valid Snappy block that stores `data` uncompressed (all literals)."""
    out = bytearray(_varint(len(data)))
    if not data:
        return bytes(out)
    for i in range(0, len(data), _MAX_LITERAL):
        out += _literal(data[i:i + _MAX_LITERAL])
    return bytes(out)
