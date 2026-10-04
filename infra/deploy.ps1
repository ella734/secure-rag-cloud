<#
.SYNOPSIS
    Deploys SecureRAG Cloud infrastructure and container to Microsoft Azure.
.DESCRIPTION
    Provisions Log Analytics, Application Insights, ACR, and Container Apps via Bicep.
#>

param (
    [string]$ResourceGroupName = "rg-secure-rag-cloud",
    [string]$Location = "westeurope"
)

Write-Host "🚀 Deploying SecureRAG Cloud to Azure..." -ForegroundColor Cyan

# Check Azure CLI
if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
    Write-Error "Azure CLI (az) is required but not installed or not in PATH."
    exit 1
}

# Create Resource Group
Write-Host "Creating Resource Group '$ResourceGroupName' in '$Location'..."
az group create --name $ResourceGroupName --location $Location --output table

# Deploy Bicep template
Write-Host "Provisioning Cloud Resources with Bicep..."
$deployment = az deployment group create `
    --resource-group $ResourceGroupName `
    --template-file ./infra/main.bicep `
    --query "properties.outputs" `
    --output json | ConvertFrom-Json

$fqdn = $deployment.containerAppFqdn.value
$acr = $deployment.acrLoginServer.value

Write-Host "✅ Provisioning complete!" -ForegroundColor Green
Write-Host "Container Registry: $acr"
Write-Host "Application URL: https://$fqdn"
Write-Host "API Documentation: https://$fqdn/docs"
