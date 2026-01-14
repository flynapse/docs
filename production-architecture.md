# Flynapse Production Architecture (Client AWS)

## Goals and constraints
- Run all data and runtime services inside the client AWS account and VPC.
- Prefer container deployments for operational simplicity and parity with UAT.
- Keep the existing self-managed observability stack (Prometheus, Loki, Tempo, Grafana, OTel).
- Cognito hosted in our AWS account, federated to client Microsoft Entra ID (Outlook-based SSO).
- Use external LLM provider (Azure OpenAI) controlled by us; outbound egress only from client AWS.
- Cost-optimized baseline with tolerance for brief downtime; HA is an optional upgrade.
- Plan for 400 users now, up to 150 concurrent peak, and 3x growth in 5 years.

## Current services (from docker-compose)
| Service | UAT role | Production mapping | Initial ECS tasks | EBS allocation |
| --- | --- | --- | --- | --- |
| api | Backend API | ECS service (EC2) | 2 | none |
| dashboard | Frontend UI | ECS service (EC2) | 1 | none |
| dynamodb-local | Local dev store | DynamoDB (managed) | n/a | n/a |
| redis | Cache | ElastiCache Redis | n/a | n/a |
| weaviate | Vector DB | ECS service (EC2) | 1 (scale to 2-3) | gp3 500 GB per node (dedicated) |
| otel-collector | Telemetry | ECS service (EC2) | 1 | none |
| prometheus | Metrics | ECS service (EC2) | 1 | gp3 500 GB per observability instance (shared) |
| loki | Logs | ECS service (EC2) | 1 | gp3 500 GB per observability instance (shared) |
| tempo | Traces | ECS service (EC2) | 1 | gp3 500 GB per observability instance (shared) |
| grafana | Dashboards | ECS service (EC2) | 1 | gp3 500 GB per observability instance (shared) |

Note: Observability services share a gp3 500 GB EBS volume per observability EC2 instance; cost baseline uses 1 instance (total 500 GB).

## Target architecture overview
```
Users -> Client DNS -> ALB (public) -> ECS services (EC2, private subnets)
  - dashboard (container)
  - api (container)

API -> DynamoDB (managed)
API -> ElastiCache Redis (managed)
API -> Weaviate (private)
API -> S3 (outputs, artifacts)
API -> Azure OpenAI (egress via NAT, allowlist IPs)

OTel -> OTel Collector -> Prometheus/Loki/Tempo -> Grafana
```

## Networking
- Reuse client VPC and subdomain; create a new ALB for this stack.
- If the client VPC/ALB already exist, import them into Terraform instead of creating new.
- Public subnets: ALB only, optionally WAF in front of ALB.
- Private subnets (multi-AZ): ECS tasks, Weaviate nodes, observability stack.
- ALB spans two public subnets (AWS requirement); ECS tasks can run in a single AZ for cost.
- NAT gateway for outbound calls (Azure OpenAI); use fixed egress IPs for allowlisting.
- Security groups to restrict east-west traffic:
  - Only API tasks can reach DynamoDB, Redis, Weaviate.
  - Observability ports are private-only.
- VPC endpoints for ECR, S3, CloudWatch to reduce NAT use.

## Compute and orchestration
- ECS on EC2 for all services (stateless and stateful).
- Use multiple capacity providers (ASGs) to isolate workloads by resource profile.
- Single-AZ placement is acceptable for cost; expand to multi-AZ when availability needs increase.
- Autoscaling:
  - API: scale on CPU/memory and ALB request count.
  - Dashboard: scale on CPU/memory and ALB request count.
  - Weaviate: scale by node count when vector workload grows.

## ECS capacity grouping (EC2)
- Single ECS cluster with multiple capacity providers (ASGs) is recommended.
- App pool (stateless): API 2 tasks, dashboard 1 task, OTel Collector 1 task (no EBS).
- Observability pool: 1 EC2 instance, 1 task each for Prometheus/Loki/Tempo/Grafana with shared gp3 500 GB.
- Weaviate pool: 1 node, one task per instance, gp3 500 GB per node (dedicated).
- Minimum isolation: keep Weaviate on its own pool; app + OTel can share.

## Data stores and persistence
- DynamoDB:
  - Use on-demand or auto-scaled provisioned capacity.
  - Enable PITR and backups.
- ElastiCache Redis:
  - Single-node cluster for cost; expect brief downtime during maintenance.
  - Upgrade path: replication group with Multi-AZ auto-failover.
  - Use auth token and in-transit encryption.
- Weaviate:
  - Start with 1 node for cost; add nodes for HA as usage grows.
  - Store data on gp3 500 GB EBS per node; schedule snapshots to S3.
  - Expose only internally (private subnets, SG-restricted).
- Outputs and artifacts:
  - Store generated outputs in S3 instead of local volume mounts.
  - Enable versioning and SSE-KMS.

## Auth and identity
- Cognito hosted in our AWS account for operational control.
- Federation to client Microsoft Entra ID via SAML or OIDC.
- Use email domain and group claims to map access roles.
- Dashboard and API use Cognito tokens as they do now, with updated pool IDs.

## Observability (self-managed)
- Keep current stack: OTel Collector -> Prometheus, Loki, Tempo -> Grafana.
- Storage:
  - Cost baseline uses 1 observability EC2 instance with a shared gp3 500 GB volume.
  - Suggested per-service budgets on the shared volume: Prometheus 250 GB, Loki 100 GB, Tempo 100 GB, Grafana 50 GB.
  - Loki/Tempo use S3 for long-term storage; Prometheus snapshots to S3.
- Access:
  - Internal ALB or private access only.
  - Separate admin accounts and MFA for Grafana.
- Alerting:
  - Prometheus Alertmanager + Grafana alerts, routed to email/Slack/MS Teams.

## CI/CD with approval gates
- Build in our AWS account, then replicate/push images to client ECR using GitHub Actions with OIDC.
- Sign images during build; verify signatures during deploy.
- Manual approval step before production deploy.
- Deploy via ECS rolling updates (or CodeDeploy blue/green for zero-downtime).
- Add smoke tests after deploy and automatic rollback on failure.

## IaC delta (changes/additions only)
- Update networking to reference an existing VPC/subnets (data sources or import) and wire them into the new ALB/ECS resources.
- Add ALB (public) + target groups + listeners + security groups for API and dashboard.
- Add ECS cluster, launch templates, ASGs, and capacity providers (app/observability/weaviate pools).
- Add ECS task definitions and services for API, dashboard, OTel, Prometheus, Loki, Tempo, Grafana, Weaviate.
- Add IAM task/execution roles, instance profiles, and CloudWatch log groups for ECS.
- Add EBS data volumes via launch templates: shared gp3 500 GB for observability pool; dedicated gp3 500 GB per Weaviate node.
- Enable NAT gateway (currently commented in `iac/networking.tf`) or equivalent egress for Azure OpenAI.
- Add regional WAF for ALB (replace CloudFront/Amplify WAF patterns).
- Add ECR cross-account replication or repo policies for image delivery; add image signing configuration and verification step in deploy pipeline.

## Security and compliance
- Store all secrets in the client AWS account using Secrets Manager or SSM Parameter Store.
- IAM task roles for AWS service access (no static keys in containers).
- TLS everywhere:
  - ACM on ALB
  - In-transit encryption for Redis and internal service calls where feasible.
- WAF in front of ALB with rate limits and OWASP rules.

## Sizing baseline (ECS on EC2)
- App pool (API + dashboard + OTel Collector):
  - Instance family: `m6i` or `m7i` (balanced CPU/memory).
  - Starting size: 2 x `m6i.large` (2 vCPU, 8 GB) with 50 GB gp3 root volumes.
  - Initial tasks: API 2 tasks, dashboard 1 task, OTel 1 task.
- Observability pool (Prometheus/Loki/Tempo/Grafana):
  - Instance family: `m6i.xlarge` or `r6i.xlarge` (more memory for caching).
  - Starting size: 1 x `m6i.xlarge` with gp3 500 GB.
  - Initial tasks: 1 task each for Prometheus, Loki, Tempo, Grafana.
- Weaviate pool (dedicated, one task per instance):
  - Instance family: `r6i.xlarge` (4 vCPU, 32 GB) to start.
  - Initial nodes: 1 node with gp3 500 GB.
- Revisit after a load test that targets 100-150 concurrent users and realistic traffic mix.

## Availability and disaster recovery
- Single-AZ is acceptable for ECS/Redis/Weaviate/Observability at the cost-optimized tier.
- DynamoDB is managed across AZs by AWS.
- Daily snapshots for Weaviate EBS and Prometheus; S3 versioning for artifacts.
- Define RTO/RPO targets and document restore procedures.

## Migration and rollout
- Stage in our AWS to validate IaC and sizing.
- Replicate to client AWS with identical VPC/ALB patterns.
- Seed DynamoDB tables, move Redis data if needed, and migrate Weaviate data via snapshots.
- Run load tests and verify performance before production cutover.

## Next steps
- Run a load test at 100-150 concurrent users and adjust capacity providers.
- Finalize WAF rules and outbound IP allowlists for Azure OpenAI.
- Confirm RTO/RPO and backup retention for Weaviate and observability data.
