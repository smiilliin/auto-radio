import dotenv
import os
import time
import subprocess

dotenv.load_dotenv()

GITHUB_TOKEN = os.getenv("GH_TOKEN")
INSTANCE_ID = os.getenv("INSTANCE_ID")
PORT = os.getenv("PORT")
IP = os.getenv("IP")


try:
    subprocess.run(["vastai", "start", "instance", str(INSTANCE_ID)], check=True)
    while True:
        result = subprocess.check_output(
            ["vastai", "show", "instance", str(INSTANCE_ID)]
        )
        if "running" in result.decode():
            break
        time.sleep(10)

    subprocess.run(
        [
            "ssh",
            "-p",
            str(PORT),
            f"root@{IP}",
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
        ["scp", "-P", str(PORT), ".env", f"root@{IP}:/workspace/auto-radio/.env"],
        check=True,
    )

    subprocess.run(
        [
            "ssh",
            "-p",
            str(PORT),
            f"root@{IP}",
            f"""
                cd /workspace/auto-radio
                if [ ! -d .venv ]; then
                    uv python install 3.13
                    uv venv --python 3.13
                    uv pip install -r requirements.txt
                fi
                git pull
                source .venv/bin/activate
                python main.py
            """,
        ],
        check=True,
    )
    subprocess.run(
        [
            "ssh",
            "-p",
            str(PORT),
            f"root@{IP}",
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
    subprocess.run(["vastai", "stop", "instance", str(INSTANCE_ID)])
