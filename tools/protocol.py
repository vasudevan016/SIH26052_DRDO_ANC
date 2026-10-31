"""Bounded, resynchronizing parser for the board's dual-microphone PCM packets."""
import struct
import zlib

HEADER = struct.Struct("<4sBBHIII")
FRAMES = 32
PAYLOAD_BYTES = FRAMES*2*2
PACKET_BYTES = HEADER.size+PAYLOAD_BYTES


class Parser:
    def __init__(self):
        self.buffer = bytearray()
        self.crc_errors = 0

    def feed(self, chunk):
        if len(chunk) > 65536:
            raise ValueError("Feed chunks of at most 65536 bytes.")
        self.buffer.extend(chunk)
        result = []
        while len(self.buffer) >= HEADER.size:
            start = self.buffer.find(b"MANC")
            if start < 0:
                del self.buffer[:-3]
                break
            if start:
                del self.buffer[:start]
            if len(self.buffer) < HEADER.size:
                break
            _, version, channels, frames, sequence, drops, crc = HEADER.unpack_from(self.buffer)
            if (version, channels, frames) != (1, 2, FRAMES):
                del self.buffer[0]
                continue
            if len(self.buffer) < PACKET_BYTES:
                break
            payload = bytes(self.buffer[HEADER.size:PACKET_BYTES])
            if zlib.crc32(payload) != crc:
                self.crc_errors += 1
                del self.buffer[0]
                continue
            del self.buffer[:PACKET_BYTES]
            result.append((sequence, drops, payload))
        return result
