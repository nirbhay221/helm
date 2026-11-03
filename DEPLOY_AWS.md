# Deploying Helm on AWS

The dashboard is a FastAPI app containerized by the `Dockerfile`. It runs in demo
mode with no secrets, so it deploys safely as-is. Two AWS paths; App Runner is the
simplest.

## Option A: App Runner from the GitHub repo (recommended)

1. Push this repo to GitHub.
2. AWS console, App Runner, Create service.
3. Source: Source code repository, connect GitHub, pick this repo and branch.
4. Deployment: Automatic (redeploys on push).
5. Build: App Runner detects the `Dockerfile` (confirm "Use a configuration file"
   to read `apprunner.yaml`, or set build to Dockerfile manually).
6. Service settings: port `8080`, CPU 1 vCPU, memory 2 GB (OR-Tools wants headroom).
7. Health check: HTTP path `/healthz`.
8. Environment variables: `DEMO_MODE=1` is enough for the public demo. To go live,
   add `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET`, `DEMO_MODE=0`, and the
   `HELM_LLM_*` keys (set these as secrets, never in the repo).
9. Create. App Runner builds the image and gives an HTTPS URL.

## Option B: build an image, push to ECR, run on App Runner or ECS

```bash
aws ecr create-repository --repository-name helm
# authenticate docker to ECR (replace ACCOUNT and REGION)
aws ecr get-login-password --region REGION | docker login --username AWS \
  --password-stdin ACCOUNT.dkr.ecr.REGION.amazonaws.com
docker build -t helm .
docker tag helm:latest ACCOUNT.dkr.ecr.REGION.amazonaws.com/helm:latest
docker push ACCOUNT.dkr.ecr.REGION.amazonaws.com/helm:latest
```

Then create an App Runner service from that ECR image (port 8080, health check
`/healthz`), or an ECS Fargate service behind an ALB.

## Notes

- OR-Tools is a large binary dependency; give the container at least 2 GB of
  memory or it can be OOM-killed during a solve.
- The app warms its data cache at startup, so the first request after a deploy is
  already fast; the health check at `/healthz` is cheap and does not trigger the
  build.
- Secrets live only in the service's environment, never in the image or the repo
  (`.env` is gitignored and excluded by `.dockerignore`).
