# Get started with GuardKit

Use GuardKit interactively in your coding agent first. Add standalone AutoBuild when you have a plan and a configured execution environment. Operating the [Software Factory](../software-factory/index.md) is a separate setup.

**Verified 17 October 2026** against GuardKit `23d99208` and guardkitfactory `40615a7e`. Installation steps were checked against source; this documentation refresh did not perform a clean installation or run a model-backed build.

## Install the current source workflow

You need Git, Python **3.12 or newer** and a supported coding agent. The current AutoBuild harness dependency supports Python 3.12 through 3.x. Use a virtual environment for the Python packages.

For the implementation described here, check out matching GuardKit and harness sources as siblings. This avoids assuming an older package release includes the current dcode integration:

```bash
# Shell: run in a directory where you keep source repositories.
git clone https://github.com/guardkit/guardkitfactory.git
git clone https://github.com/guardkit/guardkit.git
# Pin the source snapshot described by this guide.
git -C guardkitfactory checkout 40615a7e0ff6952b5a5492ada0d3a66dc10c8533
cd guardkit
git checkout 23d99208598706f81f43a21628f5dcfb89d92a55
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e ../guardkitfactory
./installer/scripts/install.sh
```

The installer installs the Python package with its `autobuild` extra, command definitions and the `guardkit` shell wrapper. It configures Claude Code integration. Follow its PATH instructions and keep this Python environment available when you run GuardKit. The Python package's entry point is **`guardkit-py`**; the installer adds **`guardkit`** as a wrapper. A bare `pip install guardkit-py` should not be described as an equivalent complete interactive installation. [Package definition](https://github.com/guardkit/guardkit/blob/23d99208598706f81f43a21628f5dcfb89d92a55/pyproject.toml) · [Installer](https://github.com/guardkit/guardkit/blob/23d99208598706f81f43a21628f5dcfb89d92a55/installer/scripts/install.sh)

To add Pi integration, use `./installer/scripts/install.sh --pi`. Its commands use `/skill:task-create`, `/skill:task-work` and other `/skill:` names. See [harness support](../harness/index.md#installed-support).

Verify the actual environment:

```bash
guardkit-py --help
guardkit-py doctor
guardkit autobuild --help
```

If `guardkit` is missing but `guardkit-py` works, resolve the installer's PATH setup. Fix dependency-installation failures before attempting AutoBuild; installed command files alone do not prove the runtime is ready.

## Initialize the project you want to change

Leave the GuardKit source directory and enter your application repository:

```bash
cd /path/to/your-project
guardkit init default
```

Choose a fitting template in place of `default`, for example `fastapi-python`, `react-typescript`, `nextjs-fullstack` or `python-library`. `guardkit-py init --help` describes the installed command; [the template source](https://github.com/guardkit/guardkit/tree/23d99208598706f81f43a21628f5dcfb89d92a55/installer/core/templates) lists the audited inventory. Initialization adds project context and task directories; inspect the changes before committing.

For an existing installation whose commands are stale:

```bash
guardkit init --update
```

This refreshes already installed command files from the installed package, preserving and reporting files you edited locally. It does not fetch a newer package. Update the package/source first; use `--force` only to discard local command edits. [Initialization implementation](https://github.com/guardkit/guardkit/blob/23d99208598706f81f43a21628f5dcfb89d92a55/guardkit/cli/init.py)

## Run one task in the coding agent

Open Claude Code **in the application repository**. These are agent commands, not shell commands:

```text
/task-create "Reject an empty display name with a useful validation message"
/task-work TASK-<the-id-created-above>
```

Answer required checkpoints. Review the resulting diff and actual test output. Green work normally remains `IN_REVIEW`; then use `/task-complete TASK-<id>` after review. The optional `/task-work ... --complete` enables the current completion phase; it is not the default.

For a feature, use `/feature-spec` to curate behaviour and `/feature-plan` to decompose work. Generated IDs are examples, not commands to copy literally.

## Choose the next execution path

| You want to… | Continue with… |
| --- | --- |
| Work through tasks with an interactive coding agent | [GuardKit in a coding harness](../harness/index.md) |
| Run a planned feature under your own shell session | [AutoBuild architecture and standalone commands](../deep-dives/autobuild-architecture.md#standalone-entry-points) |
| Submit work to services that manage stages and decisions | [Software Factory](../software-factory/index.md) |

AutoBuild requires an explicitly configured model endpoint and a matching harness installation. Its current normal Player is local dcode; the legacy Claude-named CLI default is not a ready-to-use configuration for that path. Quality gates report evidence for checks that actually ran. They do not guarantee that generated code is correct or production-ready.
