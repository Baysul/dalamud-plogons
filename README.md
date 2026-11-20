# dalamud-plogons

Custom Dalamud plugin repository following the [Dalamud Custom Repositories](https://dalamud.dev/plugin-publishing/custom-repositories) format.

## Repository URL

Add this URL in FFXIV under `/xlsettings` → **Experimental** → **Custom Plugin Repositories**:

```
https://raw.githubusercontent.com/Baysul/dalamud-plogons/main/pluginmaster.json
```

## Included Plugins

| Plugin | Internal Name | Source | Description |
|---|---|---|---|
| **XIVPerf** | `XIVPerf` | [Baysul/cuddly-train](https://github.com/Baysul/cuddly-train) | Targeted native engine patches for crowded cities (`/xivperf`). |

## Updating

`pluginmaster.json` is generated from the latest GitHub Releases of the repositories listed in `plugins.json`:

- Runs automatically every 6 hours and on edits to `plugins.json`.
- Can be triggered immediately via **Actions → Update Dalamud Plugin Repository → Run workflow** after publishing a new plugin release.
