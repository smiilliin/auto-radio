import dotenv
import os
import time
import subprocess
import json

dotenv.load_dotenv()

GITHUB_TOKEN = os.getenv("GH_TOKEN")

query = " ".join(
    [
        "reliability>0.99",
        "verified=True",
        "dlperf>12",
        "inet_up>500",
        "cuda_vers>=13",
        "reliability>0.995",
        "duration>7",
        "disk_bw>1500",
    ]
)

result = subprocess.check_output(
    [
        "vastai",
        "search",
        "offers",
        query,
        "--raw",
    ]
)

offers = json.loads(result)

offer = min(offers, key=lambda x: x["dph_total"])
offer_id = offer["id"]

result = subprocess.check_output(
    [
        "vastai",
        "create",
        "instance",
        str(offer_id),
        "--template_hash",
        os.getenv("TEMPLATE_HASH"),
        # "--image",
        # "ghcr.io/smiilliin/auto-radio:latest",
        "--disk",
        "20",
        # "--ssh",
        # "--direct",
        "--raw",
    ]
)

instance = json.loads(result)
instance_id = instance["new_contract"]

try:
    subprocess.run(["vastai", "start", "instance", str(instance_id)], check=True)
    while True:
        result = subprocess.check_output(
            ["vastai", "show", "instance", str(instance_id), "--raw"]
        )

        result = json.loads(result)

        status = result["actual_status"]

        if status == "running":
            break

        if status in ("dead", "stopped", "error"):
            raise RuntimeError(f"Instance failed: {status}")

        time.sleep(10)

    while True:
        info = json.loads(
            subprocess.check_output(
                ["vastai", "show", "instance", str(instance_id), "--raw"]
            )
        )

        status = info["actual_status"]

        print(status)

        if status == "exited":
            print("Job finished.")
            break

        if status in ("dead", "stopped", "error"):
            raise RuntimeError(f"Container failed: {status}")

        time.sleep(10)

except Exception as e:
    print(f"ERROR: {e}")
    raise
finally:
    subprocess.run(
        ["vastai", "destroy", "instance", str(instance_id)],
        input="y\n",
        text=True,
        check=True,
    )
