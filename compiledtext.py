"""
PopCap "CompiledText" container: magic -> Rijndael-256/192-CBC -> header
(magic + size) -> zlib. Key/IV are fixed and global; pyvz2rijndael derives
the IV from the key, so callers here only ever pass the key. Matches
Server/src/crypto/CompiledText.php in the main server byte for byte.
"""
import hashlib
import struct
import zlib

from pyvz2rijndael import RijndaelCBC

BLOCK = 24
MAGIC = bytes([0x10, 0x00])
HEADER_MAGIC = bytes([0xD4, 0xFE, 0xAD, 0xDE])  # 0xDEADFED4, little-endian

LEVEL_KEY = hashlib.md5(b"com_popcap_pvz2_magento_product_2013_05_05").hexdigest()


def encode(plaintext: bytes, key: str = LEVEL_KEY) -> bytes:
    compressed = zlib.compress(plaintext)
    header = HEADER_MAGIC + struct.pack("<I", len(plaintext))
    cipher = RijndaelCBC(key=key, block_size=BLOCK).encrypt(header + compressed)
    return MAGIC + cipher


def decode(blob: bytes, key: str = LEVEL_KEY) -> bytes:
    if blob[:2] != MAGIC:
        raise ValueError("not a CompiledText blob (bad magic)")
    plain = RijndaelCBC(key=key, block_size=BLOCK).decrypt(blob[2:])
    if plain[:4] != HEADER_MAGIC:
        raise ValueError("not a CompiledText blob (bad header magic)")
    (size,) = struct.unpack("<I", plain[4:8])
    return zlib.decompress(plain[8:])[:size]
