"""
Packs plaintext level JSON into a real level_shipping bundle -- see README.md
for the format and how --hash gets used.

Usage: python main.py <cv> [src_dir] [out_dir] [--hash <hash>]
"""
import gzip
import hashlib
import json
import sys
import tarfile
import tempfile
from base64 import b64encode, urlsafe_b64encode
from pathlib import Path

from compiledtext import encode, decode


def build_bundle(cv: str, src_dir: Path, out_dir: Path, override_hash: str | None = None) -> None:
    files = sorted(src_dir.glob("*.json"))
    if not files:
        sys.exit(f"no *.json files found in {src_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest_list = []
    with tempfile.TemporaryDirectory() as work_str:
        work = Path(work_str)
        for path in files:
            plain = path.read_bytes()
            member = encode(plain)
            if decode(member) != plain:
                sys.exit(f"self-check failed encoding {path.name} -- refusing to publish a broken bundle")

            member_b64 = b64encode(member)
            (work / path.name).write_bytes(member_b64)
            manifest_list.append({"Name": path.name, "Hash": hashlib.md5(member_b64).hexdigest()})
            print(f"  encoded {path.name} ({len(plain)} -> {len(member_b64)} bytes)")

        tar_path = work / "bundle.tar"
        with tarfile.open(tar_path, "w", format=tarfile.USTAR_FORMAT) as tar:
            for path in files:
                tar.add(work / path.name, arcname=path.name)
        tar_bytes = tar_path.read_bytes()

    # double gzip + e-charset base64, matching the real bundle wrapper
    wrapped = urlsafe_b64encode(gzip.compress(tar_bytes)).decode("ascii").replace("=", ",")
    wrapped = urlsafe_b64encode(gzip.compress(wrapped.encode("ascii"))).decode("ascii").replace("=", ",")
    bundle_text = wrapped

    bundle_hash = override_hash if override_hash else hashlib.sha256(bundle_text.encode("ascii")).hexdigest()

    # manifest's outer layer uses the e-field charset, not plain base64url like the bundle above
    manifest_json = json.dumps({"File": {"List": manifest_list}}, separators=(",", ":"))
    manifest_blob = b64encode(encode(manifest_json.encode("utf-8"))).decode("ascii")
    manifest_blob = manifest_blob.replace("+", "-").replace("/", "_").replace("=", ",")

    (out_dir / f"{bundle_hash}.txt").write_text(bundle_text, encoding="ascii")
    (out_dir / f"{bundle_hash}_md5.txt").write_text(manifest_blob, encoding="ascii")

    print(f"\nbundle hash: {bundle_hash}")
    print(f"wrote: {out_dir / (bundle_hash + '.txt')}")
    print(f"wrote: {out_dir / (bundle_hash + '_md5.txt')}")
    print(f"\nserved at hotupdate/ad/level_shipping/{cv}/{bundle_hash}(.txt|_md5.txt)")


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("cv", help="client version tag, e.g. 4.2.1")
    ap.add_argument("src_dir", nargs="?", help="default: raw/<cv>/")
    ap.add_argument("out_dir", nargs="?", help="default: dist/hotupdate/ad/level_shipping/<cv>/")
    ap.add_argument("--hash", help="publish under this filename instead of one computed here")
    args = ap.parse_args()

    root = Path(__file__).resolve().parent
    src = Path(args.src_dir) if args.src_dir else root / "raw" / args.cv
    out = Path(args.out_dir) if args.out_dir else root / "dist" / "hotupdate" / "ad" / "level_shipping" / args.cv

    build_bundle(args.cv, src, out, override_hash=args.hash)
