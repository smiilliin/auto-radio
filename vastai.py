import dotenv
import os
import time
import subprocess
import json
from urllib.parse import urlparse

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
        "--image",
        "vastai/pytorch:@vastai-automatic-tag",
        "--onstart-cmd",
        "'entrypoint.sh'",
        "--disk",
        "20",
        "--ssh",
        "--direct",
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

        if result["actual_status"] == "running":
            url = subprocess.check_output(
                ["vastai", "ssh-url", str(instance_id)],
                text=True,
            ).strip()

            parsed = urlparse(url)

            HOST = f"{parsed.username}@{parsed.hostname}"
            PORT = parsed.port

            ssh_command = [
                "ssh",
                "-i",
                os.path.expanduser("~/.ssh/id_ed25519"),
                "-o",
                "StrictHostKeyChecking=no",
                "-o",
                "UserKnownHostsFile=/dev/null",
                "-p",
                str(PORT),
                HOST,
            ]

            scp_command = [
                "scp",
                "-i",
                os.path.expanduser("~/.ssh/id_ed25519"),
                "-o",
                "StrictHostKeyChecking=no",
                "-o",
                "UserKnownHostsFile=/dev/null",
                "-P",
                str(PORT),
            ]

            try:
                subprocess.run(
                    ssh_command + ["echo hello"],
                    check=True,
                )
            except:
                pass
            else:
                print(f"Instance is running. SSH command: {ssh_command}")
                break

        time.sleep(10)

    subprocess.run(
        ssh_command
        + [
            f"""
                cd /workspace
                if [ ! -d auto-radio ]; then
                    git clone https://github.com/smiilliin/auto-radio.git
                fi
                cd auto-radio
                git pull
                cd /workspace/
                if [ ! -d smiilliin.github.io ]; then
                    git clone --depth 1 'https://x-access-token:{GITHUB_TOKEN}@github.com/smiilliin/smiilliin.github.io.git'
                fi
                cd smiilliin.github.io
                git pull

                if [ ! -d auto-radio/jlpt_n4 ]; then
                    mkdir -p auto-radio/jlpt_n4
                fi

                cp -r /workspace/smiilliin.github.io/auto-radio/jlpt_n4 /workspace/auto-radio/
            """,
        ],
        check=True,
    )
    subprocess.run(
        scp_command
        + [
            ".env",
            f"{HOST}:/workspace/auto-radio/.env",
        ],
        check=True,
    )

    subprocess.run(
        ssh_command
        + [
            f"""
                cd /workspace/auto-radio
                git pull

                if [ ! -d .venv ]; then
                    uv python install 3.13
                    uv venv --python 3.13
                fi

                uv sync
                source .venv/bin/activate
                
                python main.py
            """,
        ],
        check=True,
    )
    subprocess.run(
        ssh_command
        + [
            f"""
                cd /workspace/smiilliin.github.io
                
                git remote set-url origin 'https://x-access-token:{GITHUB_TOKEN}@github.com/smiilliin/smiilliin.github.io.git'

                git pull                

                git config user.name "github-actions[bot]"
                git config user.email "github-actions[bot]@users.noreply.github.com"

                cp -r /workspace/auto-radio/jlpt_n4 /workspace/smiilliin.github.io/auto-radio/
                git add auto-radio
                git commit -m "chore(auto-radio): update radio outputs"
                git push origin main
            """,
        ],
        check=True,
    )
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
