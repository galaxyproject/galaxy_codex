# Changelog

## [Unreleased] — Local git cloning for tool extraction

### Changed

- **`sources/bin/extract_galaxy_tools.py`** — Replaced GitHub API (PyGithub) with local git cloning:
  - `get_tool_repositories()` now clones `planemo-monitor` locally instead of reading files via GitHub API
  - `clone_repositories()` clones/pulls each tool repo into a local cache directory
  - `parse_tools_from_local()` parses tools from the local filesystem instead of via `ContentFile` objects
  - `get_tool_metadata_from_local()` uses `galaxy.util.xml_macros` for proper XML macro expansion
  - Removed `--api` flag (no GitHub token required), added `--repo-dir`, `--repo-url`, `--workers`
  - Parallel parsing support via `ThreadPoolExecutor`
  - Handles non-GitHub URLs (GitLab, self-hosted, etc.)
- **`sources/bin/extract_all_tools.sh`** — Removed `--api $GITHUB_API_KEY` from all invocations
- **`.github/workflows/fetch_filter_resources.yaml`** — Removed unused `GITHUB_API_KEY` env var
- **`.github/workflows/run_tests.yaml`** — Removed unused `GITHUB_API_KEY` env var

### Added

- **74 new tools** discovered that the old GitHub API approach missed:

| Repository | Tools gained | Reason previously missed |
|---|---|---|
| `gregvonkuster/galaxy_tools` | 41 | Rate limiting / API failures during `get_contents()` |
| `galaxy-team/galaxy-tools` (gitlab.pasteur.fr) | 18 | Non-`https://github.com/` URL rejected by old `get_github_repo()` |
| `galaxyproject/tools-iuc` | 10 | New tools added since last production run |
| `bgruening/galaxytools` | 3 | Nested `.shed.yml` not found by old parser |
| `galaxyecology/tools-ecology` | 1 | Tool added since last production run |
| `galaxyproteomics/tools-galaxyp` | 1 | Tool added since last production run |

- **36 conda packages** now correctly resolved via XML macro expansion (old code relied on `etree.fromstring()` which cannot resolve macros)
- `--workers N` flag for parallel tool parsing
- `--repo-url` flag for specifying individual repos to process
- `--repo-dir` flag for customizing the local clone cache location
- `--clone-depth` flag for controlling git clone depth (default: 1 for CI-efficient shallow clones; pass 0 for full history)
- Repository URL deduplication in `clone_repositories()` prevents cloning the same repo twice

### Removed

- `--api` / `GITHUB_API_KEY` requirement — tool extraction no longer needs a GitHub token
- `get_github_repo()`, `get_string_content()`, `get_suite_ID_fallback()`, `get_tools()` — replaced by local-cloning equivalents

### Fixed

- Non-GitHub repository URLs (e.g., GitLab, self-hosted) are now supported
- XML macro expansion via `galaxy.util.xml_macros` finds requirements and cross-references that simple XML parsing missed
- Nested tool directory structures handled more reliably
- No more GitHub API rate limiting issues during extraction
- Duplicate repository URLs are now skipped (was wasting ~12 GB and clone time)
