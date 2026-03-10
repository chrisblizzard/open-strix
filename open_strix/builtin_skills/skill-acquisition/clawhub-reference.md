# ClawHub CLI Reference

ClawHub is the public skill registry for agent skills. Browse, search, install, publish, and manage skills.

Source: [github.com/openclaw/clawhub](https://github.com/openclaw/clawhub)
Website: [clawhub.ai](https://clawhub.ai)

## Install

```bash
npm i -g clawhub
```

Or run without installing: `npx clawhub <command>`

## Global Flags

| Flag | Description |
|------|-------------|
| `--workdir <dir>` | Working directory (default: cwd) |
| `--dir <dir>` | Install dir under workdir (default: `skills`) |
| `--site <url>` | Base URL for browser login (default: `https://clawhub.ai`) |
| `--registry <url>` | API base URL (default: discovered, else `https://clawhub.ai`) |
| `--no-input` | Disable interactive prompts |

Env equivalents: `CLAWHUB_SITE`, `CLAWHUB_REGISTRY`, `CLAWHUB_WORKDIR`

HTTP proxy supported: `HTTPS_PROXY`, `HTTP_PROXY`, `NO_PROXY`

## Commands

### Authentication

```bash
clawhub login                    # Browser-based GitHub OAuth
clawhub login --token clh_...   # Headless / CI
clawhub whoami                   # Verify stored token
```

Config location (macOS): `~/Library/Application Support/clawhub/config.json`
Override: `CLAWHUB_CONFIG_PATH`

### Discovery

```bash
# Vector search (natural language works)
clawhub search <query>

# Browse listings
clawhub explore                              # newest 25
clawhub explore --limit 50                   # more results
clawhub explore --sort newest                # default
clawhub explore --sort downloads             # most downloaded
clawhub explore --sort rating                # highest rated
clawhub explore --sort installs              # most installed
clawhub explore --sort installsAllTime       # all-time installs
clawhub explore --sort trending              # trending now
clawhub explore --json                       # machine-readable

# Output format: <slug>  v<version>  <age>  <summary>
```

### Inspection

```bash
clawhub inspect <slug>                       # metadata + description
clawhub inspect <slug> --version <version>   # specific version
clawhub inspect <slug> --tag <tag>           # tagged version (e.g. latest)
clawhub inspect <slug> --versions            # version history
clawhub inspect <slug> --versions --limit 50 # more versions
clawhub inspect <slug> --files               # list files in version
clawhub inspect <slug> --file SKILL.md       # raw file content (200KB limit)
clawhub inspect <slug> --json                # machine-readable
```

### Installation

```bash
# Install latest version
clawhub install <slug>

# Install to specific location
clawhub install <slug> --workdir ~/my-project --dir skills

# What it does:
#   1. Resolves latest version via /api/v1/skills/<slug>
#   2. Downloads zip via /api/v1/download
#   3. Extracts into <workdir>/<dir>/<slug>/
#   4. Writes lockfile: <workdir>/.clawhub/lock.json
#   5. Writes origin: <skill>/.clawhub/origin.json
```

### Management

```bash
clawhub list                     # Show installed skills (reads lock.json)
clawhub update <slug>            # Update specific skill
clawhub update --all             # Update all installed skills
clawhub update --force           # Overwrite local modifications
clawhub uninstall <slug>         # Remove (interactive confirmation)
clawhub uninstall <slug> --yes   # Remove (no confirmation)
```

Update behavior:
- Computes fingerprint from local files
- If fingerprint matches known version: updates silently
- If fingerprint differs (local edits): refuses by default, `--force` overwrites

### Social

```bash
clawhub star <slug>              # Star a skill
clawhub star <slug> --yes        # Skip confirmation
clawhub unstar <slug>            # Remove star
```

### Publishing

```bash
clawhub publish <path> \
  --slug my-skill \
  --name "My Skill" \
  --version 1.0.0 \
  --tags latest \
  --changelog "Initial release"

# Requirements:
#   - Must be logged in
#   - SKILL.md required with name + description in frontmatter
#   - Only text-based files (no binaries)
#   - Max bundle: 50MB
#   - Published under MIT-0 (free use, no attribution)
```

### Sync (Auto-Publish)

```bash
clawhub sync                     # Scan + publish interactively
clawhub sync --dry-run           # Preview only
clawhub sync --all               # Non-interactive
clawhub sync --root <dir>        # Extra scan roots
clawhub sync --bump minor        # Version bump (default: patch)
clawhub sync --changelog "text"  # Non-interactive changelog
clawhub sync --tags a,b,c        # Tags (default: latest)
clawhub sync --concurrency 4     # Parallel uploads
```

Auto-scans:
- Explicit `--root` directories
- Clawdbot workspace skills dirs (if configured)
- `~/.clawdbot/skills` (shared)

### Deletion / Moderation

```bash
clawhub delete <slug>            # Soft-delete (owner/mod/admin)
clawhub undelete <slug>          # Restore (owner/mod/admin)
clawhub hide <slug>              # Alias for delete
clawhub unhide <slug>            # Alias for undelete
```

### Ownership Transfer

```bash
clawhub transfer request <slug> <handle> [--message "..."]
clawhub transfer list [--outgoing]
clawhub transfer accept <slug>
clawhub transfer reject <slug>
clawhub transfer cancel <slug>
```

### Admin Commands

```bash
clawhub ban-user <handle> [--reason "..."] [--fuzzy]
clawhub set-role <handle> <role> [--fuzzy]
```

## API Endpoints

Key REST endpoints (base: `https://clawhub.ai`):

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/search?q=...` | GET | Vector search |
| `/api/v1/skills?limit=N` | GET | List skills |
| `/api/v1/skills/<slug>` | GET | Skill metadata |
| `/api/v1/skills` | POST | Publish (multipart) |
| `/api/v1/download` | GET | Download skill zip |
| `/api/v1/stars/<slug>` | POST/DELETE | Star/unstar |
| `/api/v1/whoami` | GET | Verify auth |

## Telemetry

Minimal install telemetry during `clawhub sync` (for install counts).
Disable: `export CLAWHUB_DISABLE_TELEMETRY=1`
