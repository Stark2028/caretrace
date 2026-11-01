# Deployment and operations

The public workspace is intended for low-traffic research demonstrations using invented or public simulated dialogue. Infrastructure hardening does not make the extraction model clinically production-ready.

## Shared AWS EC2

The supplied `deploy/compose.shared.yaml` joins the existing `saga-agent_default` network. It publishes no host port and serves the source extractor only. The existing Caddy proxy terminates HTTPS for `caretrace.65.0.103.235.sslip.io`. No new EC2 instance, managed database, paid model endpoint, or GPU host is required. Existing EC2/network charges continue.

Before deployment, inspect available memory, disk, Docker health, and all existing routes. The initial capacity check showed approximately 751 MiB available memory and 13 GiB disk free on the shared 2 GiB host. These are observations, not reserved capacity. CareTrace is capped at 256 MiB and half a CPU, with 64 PIDs, a read-only root, no Linux capabilities, and rotating logs. It has no application database or model weights to back up.

```bash
git clone https://github.com/Stark2028/caretrace.git /opt/caretrace
cd /opt/caretrace
# Check out a reviewed immutable commit before building.
git checkout <reviewed-commit>
docker compose -p caretrace -f deploy/compose.shared.yaml build
docker compose -p caretrace -f deploy/compose.shared.yaml up -d
docker inspect caretrace-api --format '{{.State.Health.Status}}'
```

Do not run these clone commands over an existing checkout. The shared network must already exist. Only trusted services may join it: the API trusts forwarded client addresses from this internal network so its per-client limiter works behind Caddy.

## Add the route

Back up `/opt/saga/deploy/aws/Caddyfile`, then append the site block in `deploy/Caddyfile.fragment` while preserving every existing site. Validate the complete configuration, including the existing `SAGA_DOMAIN` variable, before reloading. Compare the host and container Caddyfile hashes first: replacing a single-file bind mount atomically can leave the running container on the old inode. If hashes differ, remount the full intended file by recreating only the proxy service using its existing Compose configuration.

For a matching mounted file:

```bash
docker exec saga-agent-proxy-1 caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
docker exec saga-agent-proxy-1 caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile
```

Check HTTPS, readiness, static assets, one invented extraction request, and all pre-existing application routes. The hostname is tied to the instance's public IP; a changed IP requires DNS/configuration changes. TLS issuance and renewal require reachable ports 80/443.

## Monitor

```bash
docker inspect caretrace-api --format '{{.State.Health.Status}}'
docker stats --no-stream caretrace-api
docker logs --tail 100 caretrace-api
curl --fail https://caretrace.65.0.103.235.sslip.io/health/ready
```

Readiness must report `source-v1`. Health checks assess process/engine availability, not extraction correctness. Review memory, swap, disk, container restarts, and 429/5xx rates on the entire shared host. The current release has no automated alerting or uptime SLA. Do not enable transcript/request-body logging.

## Upgrade and rollback

Record the running commit with `git rev-parse HEAD` and retain the prior image by tagging its image ID before building. Fetch and check out a reviewed commit, rebuild, restart only CareTrace, then repeat the smoke checks. Repository updates do not automatically deploy to EC2.

For rollback, check out the previous reviewed commit, rebuild, and restart CareTrace; or restore the retained image. Restore the backed-up Caddyfile only if routing changed, validate it, and reload the proxy. To stop the app, use `docker compose -p caretrace -f deploy/compose.shared.yaml stop`; remove only its site block if retiring the route. Do not remove the shared network or other applications.

## Larger-model mode

The local 7B experiment used a laptop NVIDIA GPU with some CPU offload. It is not suitable for this 2 GiB shared host. Keep it local, or separately provision and validate adequate hardware before changing the public engine. The standard image intentionally omits ML dependencies and weights. See [SECURITY.md](../SECURITY.md) for data handling, endpoint restrictions, and rate-limiter limits.
