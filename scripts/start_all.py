#!/usr/bin/env python3
import argparse
import os
import signal
import subprocess
import sys
import time

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CONTAINERS = [
    "rabbitmq",
    "python-producer",
    "go-consumer",
    "loki",
    "tempo",
    "mimir",
    "alloy",
    "grafana",
]

NETWORK_NAME = "grafana-net"
TRAFFIC_PID_FILE = os.path.join(PROJECT_DIR, ".traffic_pid")


def run(cmd, check=True, **kwargs):
    print(f"  $ {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, **kwargs)
    if check and result.returncode != 0:
        print(f"  FAILED (exit code {result.returncode})", file=sys.stderr)
        if result.stdout.strip():
            print(f"  stdout: {result.stdout.strip()}", file=sys.stderr)
        if result.stderr.strip():
            print(f"  stderr: {result.stderr.strip()}", file=sys.stderr)
        print(file=sys.stderr)
        sys.exit(1)
    return result


def ensure_network():
    result = run(["docker", "network", "ls", "--filter", f"name={NETWORK_NAME}", "--format", "{{.Name}}"])
    if NETWORK_NAME not in result.stdout.strip().split():
        print(f"  Creating network '{NETWORK_NAME}' ...")
        run(["docker", "network", "create", NETWORK_NAME])
    else:
        print(f"  Network '{NETWORK_NAME}' already exists")


def ensure_log_dirs(logs_home):
    # Only services that natively write log files to disk
    for sub in ["rabbitmq", "producer", "consumer", "grafana"]:
        path = os.path.join(logs_home, sub)
        os.makedirs(path, exist_ok=True)
        print(f"  Ensuring {path}")


def image_exists(name):
    result = run(["docker", "image", "inspect", name], check=False)
    return result.returncode == 0


def build_images():
    if image_exists("python-producer"):
        print("  python-producer image exists, skipping build")
    else:
        print("  Building python-producer ...")
        run(["docker", "build", "-t", "python-producer", os.path.join(PROJECT_DIR, "python-producer")])
    if image_exists("go-consumer"):
        print("  go-consumer image exists, skipping build")
    else:
        print("  Building go-consumer ...")
        run(["docker", "build", "-t", "go-consumer", os.path.join(PROJECT_DIR, "go-consumer")])


def container_exists(name):
    result = run(["docker", "ps", "-a", "--filter", f"name=^{name}$", "--format", "{{.Names}}"], check=False)
    return name in result.stdout.strip().split()


def container_running(name):
    result = run(["docker", "ps", "--filter", f"name=^{name}$", "--format", "{{.Names}}"], check=False)
    return name in result.stdout.strip().split()


def wait_for_healthy(name, timeout=60):
    for i in range(timeout // 2):
        result = run(
            ["docker", "inspect", "--format={{.State.Health.Status}}", name],
            check=False,
        )
        status = result.stdout.strip()
        if status == "healthy":
            print(f"  {name} is healthy")
            return True
        time.sleep(2)
    print(f"  WARNING: {name} not healthy after {timeout}s, continuing anyway", file=sys.stderr)
    return False


def stop_container(name):
    if container_running(name):
        print(f"  Stopping {name} ...")
        run(["docker", "stop", name], check=False)
    if container_exists(name):
        print(f"  Removing {name} ...")
        run(["docker", "rm", name], check=False)


def start_services(logs_home):
    print("=" * 60)
    print(f"Starting all services (logs_home={logs_home})")
    print("=" * 60)

    ensure_network()
    ensure_log_dirs(logs_home)
    build_images()

    grafana_dir = os.path.join(PROJECT_DIR, "grafana")
    logs_home_abs = os.path.abspath(logs_home)

    # ── 1. rabbitmq ──────────────────────────────────────────────────────
    print("\n[1/8] Starting rabbitmq ...")
    if container_running("rabbitmq"):
        print("  Already running")
    else:
        if container_exists("rabbitmq"):
            run(["docker", "rm", "rabbitmq"])
        run([
            "docker", "run", "-d",
            "--name", "rabbitmq",
            "--network", NETWORK_NAME,
            "-e", "RABBITMQ_LOGS=/var/log/rabbitmq/rabbitmq.log",
            "-v", f"{logs_home_abs}/rabbitmq:/var/log/rabbitmq",
            "rabbitmq:4-management",
        ])
        wait_for_healthy("rabbitmq")

    # ── 2. python-producer ───────────────────────────────────────────────
    print("\n[2/8] Starting python-producer ...")
    if container_running("python-producer"):
        print("  Already running")
    else:
        if container_exists("python-producer"):
            run(["docker", "rm", "python-producer"])
        run([
            "docker", "run", "-d",
            "--name", "python-producer",
            "--network", NETWORK_NAME,
            "-p", "25001:25001",
            "-e", "RABBITMQ_HOST=rabbitmq",
            "-e", "OTEL_EXPORTER_OTLP_ENDPOINT=http://alloy:14317",
            "-e", "OTEL_SERVICE_NAME=python-producer",
            "-v", f"{logs_home_abs}/producer:/app/logs",
            "python-producer",
        ])

    # ── 3. go-consumer ───────────────────────────────────────────────────
    print("\n[3/8] Starting go-consumer ...")
    if container_running("go-consumer"):
        print("  Already running")
    else:
        if container_exists("go-consumer"):
            run(["docker", "rm", "go-consumer"])
        run([
            "docker", "run", "-d",
            "--name", "go-consumer",
            "--network", NETWORK_NAME,
            "-e", "RABBITMQ_HOST=rabbitmq",
            "-e", "OTEL_EXPORTER_OTLP_ENDPOINT=http://alloy:14317",
            "-e", "OTEL_SERVICE_NAME=go-consumer",
            "-v", f"{logs_home_abs}/consumer:/app/logs",
            "go-consumer",
        ])

    # ── 4. loki ──────────────────────────────────────────────────────────
    print("\n[4/8] Starting loki ...")
    if container_running("loki"):
        print("  Already running")
    else:
        if container_exists("loki"):
            run(["docker", "rm", "loki"])
        run([
            "docker", "run", "-d",
            "--name", "loki",
            "--network", NETWORK_NAME,
            "grafana/loki:latest",
        ])
        time.sleep(3)

    # ── 5. tempo ─────────────────────────────────────────────────────────
    print("\n[5/8] Starting tempo ...")
    if container_running("tempo"):
        print("  Already running")
    else:
        if container_exists("tempo"):
            run(["docker", "rm", "tempo"])
        run([
            "docker", "run", "-d",
            "--name", "tempo",
            "--network", NETWORK_NAME,
            "-v", f"{grafana_dir}/tempo/tempo.yml:/etc/tempo/tempo.yml:ro",
            "grafana/tempo:latest",
            "-config.file=/etc/tempo/tempo.yml",
        ])
        time.sleep(3)

    # ── 6. mimir ─────────────────────────────────────────────────────────
    print("\n[6/8] Starting mimir ...")
    if container_running("mimir"):
        print("  Already running")
    else:
        if container_exists("mimir"):
            run(["docker", "rm", "mimir"])
        run([
            "docker", "run", "-d",
            "--name", "mimir",
            "--network", NETWORK_NAME,
            "-v", f"{grafana_dir}/mimir/mimir.yml:/etc/mimir/mimir.yml:ro",
            "grafana/mimir:latest",
            "--config.file=/etc/mimir/mimir.yml",
        ])
        time.sleep(3)

    # ── 7. alloy ─────────────────────────────────────────────────────────
    print("\n[7/8] Starting alloy ...")
    if container_running("alloy"):
        print("  Already running")
    else:
        if container_exists("alloy"):
            run(["docker", "rm", "alloy"])
        run([
            "docker", "run", "-d",
            "--name", "alloy",
            "--network", NETWORK_NAME,
            "-v", f"{grafana_dir}/alloy/config.alloy:/etc/alloy/config.alloy:ro",
            "-v", f"{logs_home_abs}:/logs:ro",
            "grafana/alloy:latest",
            "run", "/etc/alloy/config.alloy",
            "--server.http.listen-addr=0.0.0.0:12345",
        ])
        time.sleep(3)

    # ── 8. grafana ───────────────────────────────────────────────────────
    print("\n[8/8] Starting grafana ...")
    if container_running("grafana"):
        print("  Already running")
    else:
        if container_exists("grafana"):
            run(["docker", "rm", "grafana"])
        run([
            "docker", "run", "-d",
            "--name", "grafana",
            "--network", NETWORK_NAME,
            "-p", "3000:3000",
            "-v", f"{grafana_dir}/datasources:/etc/grafana/provisioning/datasources",
            "-v", f"{grafana_dir}/dashboards:/etc/grafana/provisioning/dashboards",
            "-v", f"{grafana_dir}/alerting:/etc/grafana/provisioning/alerting",
            "-v", f"{logs_home_abs}/grafana:/var/log/grafana",
            "-e", "GF_AUTH_ANONYMOUS_ENABLED=true",
            "-e", "GF_AUTH_ANONYMOUS_ORG_ROLE=Admin",
            "-e", "GF_LOG_MODE=console file",
            "-e", "GF_LOG_DIR=/var/log/grafana",
            "grafana/grafana:latest",
        ])

    print("\n" + "=" * 60)
    print("All services started. Show status with --status")
    print("=" * 60)


def stop_services():
    print("Stopping all services ...")
    for name in reversed(CONTAINERS):
        stop_container(name)
    print("Done")


def show_status():
    print(f"{'Container':<20} {'Status':<12}")
    print("-" * 32)
    for name in CONTAINERS:
        running = container_running(name)
        exists = container_exists(name)
        if running:
            status = "running"
        elif exists:
            status = "stopped"
        else:
            status = "not found"
        print(f"{name:<20} {status:<12}")
    print()
    net_result = run(
        ["docker", "network", "ls", "--filter", f"name={NETWORK_NAME}", "--format", "{{.Name}}"]
    )
    if NETWORK_NAME in net_result.stdout.strip():
        print(f"Network '{NETWORK_NAME}': exists")
    else:
        print(f"Network '{NETWORK_NAME}': not found")


def clean_services(logs_home):
    stop_services()
    print(f"Removing network '{NETWORK_NAME}' ...")
    run(["docker", "network", "rm", NETWORK_NAME])
    if logs_home and os.path.isdir(logs_home):
        print(f"Removing logs directory {logs_home} ...")
        import shutil
        shutil.rmtree(logs_home, ignore_errors=True)
    print("Clean complete")


def start_traffic():
    script = os.path.join(PROJECT_DIR, "test", "continuous_traffic.py")
    logfile = os.path.join(PROJECT_DIR, "traffic.log")
    open(logfile, "a").close()
    proc = subprocess.Popen(
        [sys.executable, script],
        stdout=open(logfile, "a"),
        stderr=subprocess.STDOUT,
    )
    with open(TRAFFIC_PID_FILE, "w") as f:
        f.write(str(proc.pid))
    print(f"Traffic generator started (pid {proc.pid}), logging to {logfile}")


def stop_traffic():
    if os.path.exists(TRAFFIC_PID_FILE):
        with open(TRAFFIC_PID_FILE) as f:
            pid = int(f.read().strip())
        try:
            os.kill(pid, signal.SIGTERM)
            print(f"Traffic generator (pid {pid}) stopped")
        except ProcessLookupError:
            print("Traffic generator was not running")
        os.remove(TRAFFIC_PID_FILE)
    else:
        subprocess.run(["pkill", "-f", "continuous_traffic.py"], capture_output=True, check=False)


def main():
    default_logs = "/home/ubuntu/logs"

    parser = argparse.ArgumentParser(description="Start/stop all services using docker run commands")
    parser.add_argument("--logs-home", default=default_logs,
                        help=f"Logs directory (default: {default_logs})")
    parser.add_argument("--stop", action="store_true", help="Stop all services")
    parser.add_argument("--status", action="store_true", help="Show container status")
    parser.add_argument("--clean", action="store_true", help="Stop, remove containers, network, and logs")
    parser.add_argument("--no-traffic", action="store_true", help="Start services without traffic generator")
    parser.add_argument("--stop-traffic", action="store_true", help="Stop the background traffic generator")
    args = parser.parse_args()

    logs_home = os.path.abspath(args.logs_home) if args.logs_home else None

    if args.clean:
        if args.logs_home == "/home/ubuntu/logs":
            print("WARNING: --clean with default logs-home is dangerous.", file=sys.stderr)
            print("Refusing to clean. Specify a custom --logs-home or remove the dir manually.", file=sys.stderr)
            sys.exit(1)
        stop_traffic()
        clean_services(logs_home)
    elif args.stop:
        stop_traffic()
        stop_services()
    elif args.status:
        show_status()
    elif args.stop_traffic:
        stop_traffic()
    elif args.no_traffic:
        start_services(logs_home)
    else:
        start_services(logs_home)
        start_traffic()


if __name__ == "__main__":
    main()
