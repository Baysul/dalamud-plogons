#!/usr/bin/env python3
"""Generate Dalamud custom plugin repository index (pluginmaster.json) from GitHub Releases.

Follows https://dalamud.dev/plugin-publishing/custom-repositories:
  - Reads plugins.json
  - Fetches each plugin's latest non-draft GitHub Release (and optional pre-release for testing)
  - Downloads the DalamudPackager-generated manifest JSON asset from the release
  - Populates Store Entry keys (DownloadLinkInstall, DownloadLinkUpdate, DownloadLinkTesting,
    DownloadCount, LastUpdate, IsHide, IsTestingExclusive, TestingAssemblyVersion)
  - Writes pluginmaster.json
"""
import datetime
import json
import os
import sys
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGINS_PATH = os.path.join(ROOT, "plugins.json")
OUT_PATH = os.path.join(ROOT, "pluginmaster.json")


def http_get_json(url: str) -> object:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "dalamud-plogons-updater/1.0",
    }
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token and url.startswith("https://api.github.com/"):
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def find_asset(release: dict, name: str) -> dict | None:
    for asset in release.get("assets", []):
        if asset.get("name") == name:
            return asset
    return None


def iso_to_epoch_str(ts: str) -> str:
    dt = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return str(int(dt.timestamp()))


def build_entry(cfg: dict) -> dict:
    repo = cfg["repo"]
    manifest_name = cfg.get("manifest_asset", f"{cfg['internal_name']}.json")
    zip_name = cfg.get("zip_asset", "latest.zip")

    releases = http_get_json(f"https://api.github.com/repos/{repo}/releases?per_page=30")
    if not isinstance(releases, list):
        raise RuntimeError(f"Unexpected releases payload for {repo}")

    stable = None
    testing = None
    total_downloads = 0
    for rel in releases:
        if rel.get("draft"):
            continue
        z = find_asset(rel, zip_name)
        if z:
            total_downloads += int(z.get("download_count", 0))
        if rel.get("prerelease"):
            if testing is None and z and find_asset(rel, manifest_name):
                testing = rel
        else:
            if stable is None and z and find_asset(rel, manifest_name):
                stable = rel

    primary = stable or testing
    if primary is None:
        raise RuntimeError(f"No published release with {manifest_name} and {zip_name} found in {repo}")

    manifest_asset = find_asset(primary, manifest_name)
    zip_asset = find_asset(primary, zip_name)
    assert manifest_asset is not None and zip_asset is not None

    entry = http_get_json(manifest_asset["browser_download_url"])
    if not isinstance(entry, dict):
        raise RuntimeError(f"Invalid manifest JSON in {repo}")

    zip_url = zip_asset["browser_download_url"]
    published = primary.get("published_at") or primary.get("created_at")

    entry.setdefault("RepoUrl", f"https://github.com/{repo}")
    entry["IsHide"] = bool(cfg.get("is_hide", False))
    entry["IsTestingExclusive"] = bool(cfg.get("is_testing_exclusive", stable is None))
    entry["DownloadCount"] = total_downloads
    entry["DownloadLinkInstall"] = zip_url
    entry["DownloadLinkUpdate"] = zip_url
    entry["DownloadLinkTesting"] = zip_url
    entry["TestingAssemblyVersion"] = None
    entry["LastUpdate"] = iso_to_epoch_str(published)

    if cfg.get("icon_url"):
        entry["IconUrl"] = cfg["icon_url"]
    if cfg.get("image_urls"):
        entry["ImageUrls"] = cfg["image_urls"]

    if testing is not None and stable is not None:
        t_manifest = http_get_json(find_asset(testing, manifest_name)["browser_download_url"])
        t_zip = find_asset(testing, zip_name)
        if isinstance(t_manifest, dict) and t_zip:
            t_ver = t_manifest.get("AssemblyVersion")
            if t_ver and t_ver != entry.get("AssemblyVersion"):
                entry["TestingAssemblyVersion"] = t_ver
                entry["DownloadLinkTesting"] = t_zip["browser_download_url"]
                if t_manifest.get("DalamudApiLevel"):
                    entry["TestingDalamudApiLevel"] = t_manifest["DalamudApiLevel"]
                if t_manifest.get("Changelog"):
                    entry["TestingChangelog"] = t_manifest["Changelog"]

    return entry


def main() -> int:
    with open(PLUGINS_PATH, "r", encoding="utf-8") as f:
        plugins = json.load(f)

    entries = []
    for cfg in plugins:
        entry = build_entry(cfg)
        entries.append(entry)
        print(
            f"Updated {entry.get('InternalName')} v{entry.get('AssemblyVersion')} "
            f"(API {entry.get('DalamudApiLevel')}) -> {entry.get('DownloadLinkInstall')}"
        )

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2)
        f.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
