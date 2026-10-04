# Azure Container Apps: Security and Hardening Guidelines

## 1. Architecture Overview
Azure Container Apps (ACA) is a fully managed serverless container environment built on Kubernetes (AKS), KEDA, and Envoy. It enables microservices and containerized workloads to scale dynamically based on HTTP traffic, event triggers, or CPU/memory metrics without requiring manual cluster management.

## 2. Identity and Access Management
- **Managed Identities**: Workloads running in Container Apps must use Azure Managed Identities (System-Assigned or User-Assigned) to authenticate against other Azure services, eliminating hardcoded credentials or API keys.
- **Role-Based Access Control (RBAC)**: Assign least-privilege roles at the resource scope. For instance, granting `AcrPull` on Azure Container Registry (ACR) and `Key Vault Secrets User` on Azure Key Vault.

## 3. Network Isolation and Ingress Security
- **Virtual Network (VNet) Integration**: Production Container Apps environments must be deployed into a dedicated custom VNet with designated subnets.
- **Internal vs External Ingress**: Workloads not directly exposed to public traffic should use internal ingress accessible solely through private IP addresses or Azure Private Endpoints.
- **Transport Layer Security (TLS)**: Ingress terminates TLS 1.2 or TLS 1.3 automatically with managed certificates, enforcing HTTPS redirection for all client communication.

## 4. Container Hardening Standards
- **Non-Root Execution**: Container images must run under an unprivileged user (UID >= 1000) rather than `root`.
- **Minimal Base Images**: Production images must derive from minimal distroless or Alpine/Debian-slim base images to minimize the CVE attack surface.
- **Read-Only Filesystem**: Container root filesystems should be mounted as read-only wherever possible, redirecting temporary writes to ephemeral `/tmp` volumes.
- **Vulnerability Scanning**: Continuous automated scanning must be enforced via Microsoft Defender for Containers integrated with Azure Container Registry.

## 5. Secrets and Configuration Management
- Secrets must never be stored inside Docker images or source repositories.
- Use native Container Apps secrets references linked directly to Azure Key Vault secrets via Managed Identity. Secret rotations propagate automatically without container restarts when configured with versionless Key Vault URIs.
