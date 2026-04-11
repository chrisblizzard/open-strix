# Chainlink Setup for 5 Whys

Chainlink is a CLI issue tracker that gives 5 Whys analyses persistent, structured
storage. Trees become issues with parent-child relationships, action items become
trackable issues with labels, and chains survive across sessions.

This is optional. The 5 Whys skill works without chainlink — you can write trees as
markdown. But chainlink adds: persistence, search, blocking relationships, session
tracking, and falsification cascades.

## Installing Rust

Chainlink is written in Rust. You need cargo.

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
source "$HOME/.cargo/env"
```

Verify:
```bash
rustc --version
cargo --version
```

## Installing Chainlink

```bash
cargo install chainlink-tracker
```

This compiles from source and takes a few minutes. On resource-constrained machines
(< 2GB RAM), it may be slow or fail. If it fails with an OOM:

```bash
# Reduce parallel compilation
CARGO_BUILD_JOBS=1 cargo install chainlink-tracker
```

Verify:
```bash
chainlink --version
```

## Initializing a 5 Whys Database

Chainlink stores its database in a `.chainlink/` directory. It walks up from the
current directory to find the nearest one. This means **where you run `chainlink
init` determines which database you use.**

For 5 Whys, use a **dedicated directory** separate from any task-tracking database:

```bash
# Create a dedicated RCA directory
mkdir -p ~/rca
cd ~/rca
chainlink init
```

This creates `~/rca/.chainlink/issues.db` — your 5 Whys database. Task tracking,
backlog management, and other chainlink uses should have their own separate
`.chainlink/` directory elsewhere.

**Why separate databases?** RCA chains and task backlogs serve different purposes.
RCA chains are investigative — they branch, they have falsification relationships,
they close when you understand something. Task issues are operational — they close
when you've done something. Mixing them creates noise in both directions.

## Verifying the Setup

```bash
cd ~/rca
chainlink issue list
# Should show: (empty, no issues)
```

## PATH Setup

If `chainlink` isn't on your PATH after install:

```bash
export PATH="$HOME/.cargo/bin:$PATH"
```

Add this to your shell profile (`~/.bashrc`, `~/.zshrc`) for persistence.
