# Dockerized Flow vs. Realistic Production Scenario

## RabbitMQ (Message Broker)

**Dockerized flow:**
RabbitMQ runs as a single Docker container on the dev machine. Producer and consumer connect to it via `localhost:5672`.

**Production scenario:**
RabbitMQ would run as a clustered deployment (e.g., RabbitMQ cluster on Kubernetes or EC2) with HA mirrored queues. Producer and consumer connect to a load-balanced endpoint.

---

## Python Producer (Flask API)

**Dockerized flow:**
Flask app runs in a Docker container on the dev machine, exposed on port `25001`. It publishes events to RabbitMQ on `localhost:5672`.

**Production scenario:**
The producer would be deployed as a service behind a load balancer (e.g., ALB on ECS / ingress on Kubernetes). Multiple replicas would run for high availability.

---

## Go Consumer

**Dockerized flow:**
Go binary runs in a Docker container on the dev machine. It polls RabbitMQ every minute and logs received messages.

**Production scenario:**
The consumer would be deployed as a Kubernetes Deployment or ECS service with multiple replicas sharing the queue (competing consumers pattern). It would run as a daemon on each node, or as a sidecar.

---

## Logs

**Dockerized flow:**
Each container writes logs to a mounted volume under `logs/<service>/<service>.log` on the host machine. Alloy (also running in Docker) mounts this same `logs/` directory as read-only and tails all `.log` files inside it.

**Production scenario:**
Each application would write logs to a local file or stdout. Alloy would be deployed as a DaemonSet (Kubernetes) or installed as an agent on each EC2 machine, tailing log files from the host filesystem. In containerized platforms, Alloy can also read from the container runtime's stdout/stderr stream directly.

---

## Grafana Alloy (Log Collector)

**Dockerized flow:**
Alloy runs as a Docker container on the dev machine. It mounts the `logs/` folder and reads from it. It forwards parsed log entries to Loki over the Docker network.

**Production scenario:**
Alloy would be deployed on each EC2 machine or as a DaemonSet on each Kubernetes node. It would scrape logs from local disk (e.g., `/var/log/applications/*.log`) or from the container runtime socket, and forward them to a central Loki instance running in a shared observability cluster.

---

## Loki (Log Storage)

**Dockerized flow:**
Loki runs as a single Docker container on the dev machine, accepting log pushes from Alloy at `http://loki:3100`.

**Production scenario:**
Loki would be deployed in a microservices mode (ingester, querier, distributor, compactor) for horizontal scalability. It would run on dedicated infrastructure (e.g., a separate EKS cluster) with object storage backend (S3, GCS) for long-term retention.

---

## Grafana (Dashboard)

**Dockerized flow:**
Grafana runs as a Docker container with an anonymous admin login and a pre-provisioned Loki datasource pointing to `http://loki:3100`.

**Production scenario:**
Grafana would be deployed with authenticated access (OAuth, LDAP), multiple data sources (Loki, Prometheus, Tempo), alerting rules, and team-based folder permissions. It would run behind a reverse proxy with TLS termination.
