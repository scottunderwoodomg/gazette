import os
import subprocess
import modal

app = modal.App("gazette")

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install_from_requirements("gazette/requirements.txt")
    .add_local_dir(
        "gazette",
        remote_path="/root/gazette",
        copy=True,
        ignore=["cache", "**/__pycache__"],
    )
    .add_local_dir("images", remote_path="/root/images", copy=True)
)

cache = modal.Volume.from_name("gazette-cache", create_if_missing=True)
CACHE_DIR = "/root/gazette/cache"

@app.function(
    image=image,
    schedule=modal.Cron("0 7 * * *", timezone="America/New_York"),
    secrets=[modal.Secret.from_name("gazette")],
    volumes={CACHE_DIR: cache},   # volume appears exactly where the app expects it
    timeout=30 * 60,
)
def run_daily():
    os.makedirs(CACHE_DIR, exist_ok=True)   # no-op normally; harmless safety net
    subprocess.run(
        ["python", "gazette/run.py"],
        cwd="/root",                         # so "gazette/cache" and "./gazette/cache" resolve here
        check=True,
    )
    cache.commit()
