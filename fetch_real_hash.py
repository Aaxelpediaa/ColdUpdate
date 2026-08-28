"""
Asks the real game server which level_shipping hash it hands a client for
a given version -- that hash is the only filename a replacement bundle can
be published under. Builds the request itself; no capture needed, since
the request body is just {"cv": "<cv>", "t": "0"}.

Usage: python fetch_real_hash.py [cv]
Requires pycryptodome (`pip install pycryptodome`).
"""
import hashlib
import json
import re
import sys
import urllib.request
from base64 import b64decode, b64encode

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

REAL_URL = "http://cloudpvz2android.ditwan.cn/index.php"
MSG_ID = "V1270"
FALLBACK_KEY = "1geh6fvq4r20M02s"
EV = "3"


def _key_iv(msg_id: str) -> tuple[bytes, bytes]:
    h1 = hashlib.md5((FALLBACK_KEY + msg_id).encode()).hexdigest()
    h2 = hashlib.md5(h1.encode()).hexdigest()
    return h1.encode(), h2[:16].encode()


def e_encrypt(plaintext: bytes, msg_id: str = MSG_ID) -> str:
    key, iv = _key_iv(msg_id)
    ct = AES.new(key, AES.MODE_CBC, iv).encrypt(pad(plaintext, AES.block_size))
    return b64encode(ct).decode().translate(str.maketrans({"+": "-", "/": "_", "=": ","}))


def e_decrypt(e_field: str, msg_id: str = MSG_ID) -> bytes | None:
    s = e_field.translate(str.maketrans({",": "=", "-": "+", "_": "/"}))
    s += "=" * (-len(s) % 4)
    ct = b64decode(s)
    if not ct:
        return None
    key, iv = _key_iv(msg_id)
    try:
        return unpad(AES.new(key, AES.MODE_CBC, iv).decrypt(ct), AES.block_size)
    except (ValueError, KeyError):
        return None


def send(e: str, ev: str = EV) -> str:
    boundary = "_{{}}_"
    parts = {"req": MSG_ID, "e": e, "ev": ev}
    body = "".join(
        f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'
        for name, value in parts.items()
    ) + f"--{boundary}--\r\n"

    req = urllib.request.Request(
        REAL_URL,
        data=body.encode(),
        headers={
            "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 14)",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Accept-Encoding": "gzip",
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        raw = resp.read()
        if resp.headers.get("Content-Encoding") == "gzip":
            import gzip
            raw = gzip.decompress(raw)
        return raw.decode()


def main() -> None:
    cv = sys.argv[1] if len(sys.argv) > 1 else "4.2.0"
    e = e_encrypt(json.dumps({"cv": cv, "t": "0"}).encode())

    resp = json.loads(send(e))
    if "e" not in resp:
        sys.exit(f"no \"e\" in the response -- server said: {resp}")

    plaintext = e_decrypt(resp["e"])
    if plaintext is None:
        sys.exit("could not decrypt the response")

    inner = json.loads(plaintext)
    lp = (inner.get("d") or {}).get("lp")

    if not lp:
        print(f"decrypted: {plaintext.decode()}")
        print(f"\nno bundle currently served (lp is empty) for {cv}.")
        return

    m = re.match(r"^hotupdate/ad/level_shipping/([^/]+)/([0-9a-f]+)$", lp)
    if not m:
        sys.exit(f"decrypted, but lp doesn't look like a level_shipping path: {lp}")

    print(f"cv:   {m.group(1)}")
    print(f"hash: {m.group(2)}")
    print(f"\nnext: python main.py {m.group(1)} raw/{m.group(1)} --hash {m.group(2)}")


if __name__ == "__main__":
    main()
