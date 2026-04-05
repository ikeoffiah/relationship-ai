# MVP Infrastructure (0-20 users pilot)

This document outlines the infrastructure choices for the initial RelationshipAI pilot. The focus is on rapid development and low-cost maintenance.

| Component       | MVP Solution          | Monthly Cost | Migration Path (post-pilot)   |
|-----------------|-----------------------|--------------|-------------------------------|
| Backend hosting | Railway.app free tier | $0           | Railway paid / AWS EKS        |
| PostgreSQL      | Supabase free tier    | $0           | Supabase Pro / AWS RDS        |
| Vector DB       | pgvector (Supabase)   | $0           | Pinecone / Weaviate           |
| Redis           | Upstash free tier     | $0           | Upstash Pay-as-you-go / ElastiCache |
| Audit log       | PostgreSQL table      | $0           | Kafka (AWS MSK) at scale      |
| TLS/HTTPS       | Railway auto (Let's Encrypt) | $0    | AWS ACM                       |
| KMS/Encryption  | App-level AES-256-GCM | $0          | AWS KMS per-user DEKs         |
| CI/CD           | GitHub Actions free tier | $0        | Same (free for public repos)  |
| Monitoring      | Railway logs + Sentry free | $0      | Prometheus + Grafana          |

## Infrastructure Architecture

The MVP ignores Terraform and Kubernetes to minimize complexity. Configuration is managed via environment variables and service dashboards.

### Deployment Workflow (Railway)

Railway connects directly to the GitHub repository. Each backend service is configured to look at its respective directory:

- **backend-django**: Railway looks at `/backend-django` and parses the `Procfile`.
- **backend-fastapi**: Railway looks at `/backend-fastapi` and parses the `Procfile`.

### Database (Supabase)

A single Supabase project provides both the relational PostgreSQL database and the vector storage via `pgvector`. This simplifies the architecture significantly for the initial 20 users.

### Redis (Upstash)

Used for Celery task queuing and temporary session storage. Upstash provides a serverless Redis experience that is easy to scale after the pilot.
