"""Network test configuration — Pi addresses, credentials, and host settings."""

HOST_IP = "192.168.178.20"
HOST_PORT = 8765

WORKERS = [
    {
        "name": "Player 1",
        "ip": "192.168.178.22",
        "ssh_user": "droid",
        "ssh_pass": "droid",
        "api_port": 9100,
    },
    {
        "name": "Player 2",
        "ip": "192.168.178.23",
        "ssh_user": "droid",
        "ssh_pass": "droid",
        "api_port": 9100,
    },
    {
        "name": "Player 3",
        "ip": "192.168.178.24",
        "ssh_user": "droid",
        "ssh_pass": "droid",
        "api_port": 9100,
    },
]

# Remote path where the worker script is deployed
REMOTE_WORKER_DIR = "/home/droid/dnd_worker"
REMOTE_WORKER_SCRIPT = f"{REMOTE_WORKER_DIR}/worker.py"
