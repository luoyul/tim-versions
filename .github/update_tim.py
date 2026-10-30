import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

CONFIG_URL = "https://jsonschema.qpic.cn/99c2de7e3c0daa2e1eb6fa548bbf0c88/d80bde56620e0c005f06232ef2582bfc/versions"
PACKAGE = "com.tencent.tim"
REPOSITORY = os.environ.get("GITHUB_REPOSITORY", "luoyul/tim-versions")
ROOT = Path(os.environ.get("GITHUB_WORKSPACE", Path.cwd()))
CATALOG_PATH = ROOT / "catalog" / "tim.json"
CHECKSUM_PATH = ROOT / "checksums" / "TIM-SHA256SUMS.txt"


def run(*args, check=True, capture=False):
    return subprocess.run(args, check=check, text=True, capture_output=capture)


def fetch_json(url):
    request = urllib.request.Request(url, headers={"User-Agent": "tim-versions-updater", "Cache-Control": "no-cache", "Pragma": "no-cache"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def aapt_path():
    sdk_root = Path(os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT") or "/opt/android-sdk")
    candidates = sorted(sdk_root.joinpath("build-tools").glob("*/aapt2"))
    if not candidates:
        raise RuntimeError("aapt2 was not found")
    return str(candidates[-1])


def read_badging(apk):
    output = run(aapt_path(), "dump", "badging", str(apk), capture=True).stdout
    match = re.search(r"package: name='([^']+)' versionCode='([^']+)' versionName='([^']+)'", output)
    if not match:
        raise RuntimeError("Unable to read APK package metadata")
    return match.group(1), match.group(2), match.group(3)


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    config = fetch_json(CONFIG_URL + "?t=" + uuid.uuid4().hex)
    android_versions = []
    for entry in config.get("version_history", []):
        if any(log.get("platform") == "android" for log in entry.get("logs", [])):
            android_versions.append(str(entry.get("version_code")))
    version_name = android_versions[0] if android_versions else ""
    download_url = (config.get("download_link") or {}).get("android")
    if not version_name or not download_url:
        raise RuntimeError("Official TIM config does not contain an Android version and download URL")

    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8-sig"))
    versions = catalog.setdefault("versions", [])

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_apk = Path(temp_dir) / f"TIM-{version_name}.apk"
        cache_busted_url = download_url + ("&" if "?" in download_url else "?") + "t=" + uuid.uuid4().hex
        request = urllib.request.Request(cache_busted_url, headers={"User-Agent": "tim-versions-updater", "Cache-Control": "no-cache"})
        with urllib.request.urlopen(request, timeout=120) as response, temp_apk.open("wb") as output:
            shutil.copyfileobj(response, output, length=1024 * 1024)

        package_name, version_code, actual_name = read_badging(temp_apk)
        if package_name != PACKAGE or actual_name != version_name:
            raise RuntimeError(f"APK metadata mismatch: {package_name} {actual_name} {version_code}")

        release_tag = f"tim-{version_name}-{version_code}"
        file_name = f"TIM-{version_name}-{version_code}.apk"
        if any(str(item.get("versionName")) == version_name and str(item.get("versionCode")) == version_code for item in versions):
            print(f"Already catalogued: {release_tag}")
            return

        digest = sha256(temp_apk)
        size = temp_apk.stat().st_size
        notes = f"Version: {version_name}\nVersion code: {version_code}\nPackage: {PACKAGE}\nSHA-256: {digest}\nSize: {size} bytes"
        asset = temp_apk.with_name(file_name)
        temp_apk.rename(asset)
        release = subprocess.run(["gh", "release", "view", release_tag, "--repo", REPOSITORY], capture_output=True, text=True)
        if release.returncode == 0:
            run("gh", "release", "upload", release_tag, str(asset), "--repo", REPOSITORY, "--clobber")
            run("gh", "release", "edit", release_tag, "--repo", REPOSITORY, "--title", f"TIM {version_name} ({version_code})", "--notes", notes)
        else:
            run("gh", "release", "create", release_tag, str(asset), "--repo", REPOSITORY, "--title", f"TIM {version_name} ({version_code})", "--notes", notes)

    record = {
        "product": "tim",
        "packageName": PACKAGE,
        "versionName": version_name,
        "versionCode": int(version_code),
        "fileName": file_name,
        "size": size,
        "sha256": digest,
        "sourcePage": CONFIG_URL,
        "downloadedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "releaseTag": release_tag,
        "releaseUrl": f"https://github.com/{REPOSITORY}/releases/tag/{release_tag}",
    }
    versions[:] = [item for item in versions if item.get("releaseTag") != release_tag]
    versions.append(record)
    versions.sort(key=lambda item: (tuple(int(part) for part in str(item.get("versionName", "0")).split(".")), int(item.get("versionCode", 0))), reverse=True)
    CATALOG_PATH.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = []
    if CHECKSUM_PATH.exists():
        lines = [line for line in CHECKSUM_PATH.read_text(encoding="utf-8-sig").splitlines() if file_name not in line]
    lines.append(f"{digest}  {file_name}")
    CHECKSUM_PATH.write_text("\n".join(lines) + "\n", encoding="ascii")
    print(f"Published {release_tag}: {digest}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
