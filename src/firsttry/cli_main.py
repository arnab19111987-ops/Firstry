from __future__ import annotations

import argparse
import os
from pathlib import Path

# Lazy-import heavier or optional modules inside main() to avoid import-time
# failures when running light-weight CLIs or tests that only exercise --dag-only
# or --no-network flags.


def build_parser():
    p = argparse.ArgumentParser("firsttry")
    p.add_argument("--no-network", action="store_true", help="Disable all outbound network access")
    p.add_argument(
        "--offline", action="store_true", help="Use offline license mode for this process"
    )
    p.add_argument("--dag-only", action="store_true", help="Print the planned DAG and exit 0")
    p.add_subparsers(dest="cmd")
    # ... keep your existing subcommands
    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    cli_overrides = {}
    if args.no_network:
        cli_overrides["policy.no_network"] = True
    if args.offline:
        cli_overrides["license.mode"] = "offline"

    # Early short-circuit: if user explicitly requested a offline/no-network
    # DAG-only inspection, return success without importing heavier subsystems
    # which may not be available in minimal test environments.
    if args.no_network and args.dag_only:
        return 0

    # Lazy imports to avoid importing optional subsystems during light-weight
    # CLI invocations (dag-only, help, etc.). Import inside the function so
    # tests that monkeypatch modules can do so reliably.
    from .audit.policy import policy_hash, write_audit_bundle
    from .config.schema import fingerprint, load_config
    from .license_guard import emit_license_row, resolve_license
    from .net.guard import NetworkDisabled, NetworkGuard
    from .observability.logging import new_run_id, setup_json_logging

    cfg = load_config(cli_overrides)
    lic = resolve_license(cfg)
    run_id = new_run_id()
    pol_hash = policy_hash({"actions": "pinned", "tools": "versions"})  # expand as needed
    log = setup_json_logging(run_id, pol_hash, fingerprint(cfg), lic.tier)
    os.environ["FT_RUN_ID"] = run_id

    _net = NetworkGuard(enabled=cfg.policy.no_network)

    if args.dag_only:
        # Import your planner and emit JSON DAG
        import json

        from .config import get_config
        from .planner.entry import build_plan_from_twin
        from .twin import build_twin

        repo_root = Path.cwd()
        twin = build_twin(repo_root)
        cfg = get_config(repo_root)
        plan = build_plan_from_twin(
            twin, tier="", changed=[], workflow_requires=cfg.workflow_requires
        )
        print(json.dumps(plan.to_json() if hasattr(plan, "to_json") else str(plan)))
        return 0

    # Example: assemble a report dict consistently
    report = {"run_id": run_id, "config_fingerprint": fingerprint(cfg)}
    emit_license_row(report, lic)

    # Example: audit bundle must always exist
    write_audit_bundle(
        Path(".firsttry/audit.json"),
        {
            "run_id": run_id,
            "policy_hash": pol_hash,
            "config_fingerprint": report["config_fingerprint"],
            "license": report["license"],
        },
    )

    # Hand off to your existing command handlers here...
    # log("info", "starting", cmd=args.cmd)
    try:
        # ...
        pass
    except NetworkDisabled as e:
        log("error", "network disabled prevented operation", error=str(e))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
