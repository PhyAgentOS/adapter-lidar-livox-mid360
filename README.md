[English](README.md) | [简体中文](README_zh.md)

# Livox Mid-360 acquisition

Publishes Forge PointCloudBuffer and Imu from Livox streams, preserving per-point time, line index, reflectivity and sampling context.

## Runtime

- Node `0.3.0`, Forge 2, Dora CLI/Python bindings 1.0.1, Forge Msgs/Common 2.1.0; exact build dependencies are in `uv.lock`.
- Ubuntu 24.04 x86_64, Python 3.12 ABI, external ROS 2 Jazzy and required algorithm/message overlays.
- Source the ROS/overlay setup before launch. `livox_mid360 --check-runtime` validates imports and generated wire types without opening hardware.
- The `directory_tar_gz` artifact contains the complete `livox_mid360/` runtime; execute `livox_mid360/livox_mid360`. Do not move its executable away from its libraries.
- Forge 1 artifacts remain immutable. Upgrade the binary, Dora and message peers together; changing only the external CLI does not migrate a frozen Node.

## Behavior

The default mode subscribes to an external driver. managed_driver optionally owns a separate driver process and session-only network configuration. Managed clock verification requires FORGE_SENSOR_CLOCK diagnostics; an ordinary driver must use external management with explicitly verified clock mapping. No guessed PTP accuracy is reported.

Optional capabilities remain disabled when unconfigured. The Node owns only its own child processes; it does not modify vendor projects or control unrelated applications. Snapshots are observations, not a control API; consumers must verify freshness.

## Development and packaging

```bash
uv sync --frozen --group dev --group build
uv run --frozen pytest -q
uv run --frozen ruff check .
source /opt/ros/jazzy/setup.bash
# Source required algorithm/message overlays for this deployment.
BUILD_PYTHON=.venv/bin/python bash scripts/build_pyinstaller.sh
```

Interfaces: [docs/interfaces.md](docs/interfaces.md). Configuration examples are in `config/`; deployment-specific paths and topics must be supplied by the caller. See `THIRD_PARTY_NOTICES.md` for sources and redistribution notices.

## Versioned releases

Contribute through a personal fork and a PR to `main`. After merging, create a new annotated `vX.Y.Z` tag matching `pyproject.toml` and dispatch **Build versioned release** with that tag. The workflow validates source identity, the Forge/Dora line, locked dependencies, tests and lint, then builds on Ubuntu 24.04 with ROS 2 Jazzy and checks the real frozen entrypoint. It attaches the runtime archive, SHA256 and source metadata to a Draft Release. Review and publish that draft before separately registering the Node in the resource platform.

Archive names use `<entrypoint>-v<version>-ubuntu24.04-x86_64-ros2-jazzy.tar.gz`. Existing releases/assets are never overwritten; changed bytes require a new version. ROS and algorithm backends remain external. Build-time Livox validation compiles only digest-checked official wire definitions and never starts a sensor driver. CI/import tests and simulation do not establish physical hardware acceptance.
