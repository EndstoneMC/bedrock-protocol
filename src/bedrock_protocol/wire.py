"""Connection-owned native batching, compression and encryption.

Wait for caller backpressure before encode(). A successful encode advances the
cipher; send every returned batch in order. A decode failure is terminal.
"""

from ._native.wire import BatchCodec, Compression, PacketBatch, PacketDecodeError

__all__ = ["BatchCodec", "Compression", "PacketBatch", "PacketDecodeError"]
