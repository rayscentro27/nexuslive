"""
Oracle Cloud check — reports ARM instance status via OCI CLI.
"""
import os


def _get_tenancy() -> str:
    tenancy = os.getenv("OCI_TENANCY", "")
    if not tenancy:
        oci_cfg = os.path.expanduser("~/.oci/config")
        if os.path.exists(oci_cfg):
            for line in open(oci_cfg):
                if line.strip().lower().startswith("tenancy="):
                    tenancy = line.strip().split("=", 1)[1].strip()
                    break
    return tenancy or "ocid1.tenancy.oc1..aaaaaaaaarpguhwhqq4ladn3asodgnwxnykjgffldwhik4ippigtlleyjdhq"


async def run(page, payload: dict) -> dict:
    """Check OCI ARM instance status via CLI (no browser needed)."""
    tenancy = payload.get("tenancy_ocid", _get_tenancy())
    region = payload.get("region", "us-phoenix-1")

    # Check via OCI CLI instead of browser (faster, lower memory)
    import subprocess
    result = subprocess.run(
        ["oci", "compute", "instance", "list",
         "--compartment-id", tenancy,
         "--query", "data[*].{name:\"display-name\",state:\"lifecycle-state\",shape:shape}",
         "--output", "json"],
        capture_output=True, text=True, timeout=60,
    )

    if result.returncode != 0:
        return {"status": "error", "message": result.stderr[:300]}

    import json
    try:
        instances = json.loads(result.stdout)
    except Exception:
        instances = []

    arm_instances = [i for i in instances if "A1" in i.get("shape", "")]
    running = [i for i in arm_instances if i.get("state") == "RUNNING"]

    lines = [f"Oracle ARM Instances ({region}):"]
    if not arm_instances:
        lines.append("  No ARM instances found — capacity still pending")
    else:
        for inst in arm_instances:
            lines.append(f"  {inst['name']}: {inst['state']} ({inst['shape']})")

    return {
        "status": "ok",
        "summary": "\n".join(lines),
        "running_count": len(running),
        "total_arm": len(arm_instances),
    }
