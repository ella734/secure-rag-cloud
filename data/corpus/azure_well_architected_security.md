# Azure Well-Architected Framework: Security Discipline

## 1. Zero Trust Principles
The Security pillar of the Azure Well-Architected Framework is grounded in three Zero Trust tenets:
1. **Verify Explicitly**: Always authenticate and authorize based on all available data points (identity, location, device health, service or workload).
2. **Use Least Privilege Access**: Limit user and service access with Just-In-Time (JIT) and Just-Enough-Access (JEA), risk-based adaptive policies, and data protection.
3. **Assume Breach**: Minimize blast radius by segmenting access by network, user, devices, and application awareness. Encrypt all sessions end-to-end and use analytics for threat detection.

## 2. Identity and Authentication with Microsoft Entra ID
- Centralize identity governance through Microsoft Entra ID (formerly Azure AD).
- Enforce Multi-Factor Authentication (MFA) and Conditional Access policies for all privileged identities.
- Eliminate static service principal secrets in favor of federated credentials or Managed Identities.
- Implement Privileged Identity Management (PIM) with approval workflows and time-bound role activations.

## 3. Data Protection and Encryption
- **Encryption at Rest**: All storage accounts, managed disks, and Azure SQL databases must enforce 256-bit AES encryption. For compliance, utilize Customer-Managed Keys (CMK) stored in Azure Key Vault Premium with HSM backing.
- **Encryption in Transit**: Enforce TLS 1.3 across all communication endpoints. Disable legacy protocols (TLS 1.0, TLS 1.1, SSL 3.0) and weak cipher suites.
- **Data Classification**: Apply sensitivity labels via Microsoft Purview to discover and protect confidential assets.

## 4. Network Security and Perimeter Defense
- **Perimeter Defense**: Deploy Azure DDoS Protection Standard at the virtual network level.
- **Web Application Firewall (WAF)**: Position Azure Application Gateway or Azure Front Door with WAF rules to inspect HTTP/S traffic against OWASP Top 10 web vulnerabilities.
- **Private Link**: Eliminate public IP exposure for PaaS backends (e.g. Azure OpenAI, Cosmos DB, Azure SQL) by enforcing Azure Private Link and Private Endpoints.
