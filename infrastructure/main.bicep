targetScope = 'subscription'

@description('Environment name, e.g. dev or prod.')
param environmentName string = 'dev'

@description('Azure region for all resources.')
param location string = 'switzerlandnorth'

@description('Target subscription ID (used for building resource IDs).')
param subscriptionId string

@description('Target tenant ID (used for the Key Vault).')
param tenantId string

@description('Project resource group name.')
param resourceGroupName string

@description('Databricks managed resource group name. Must not exist prior to first deploy.')
param databricksManagedRgName string

@description('Globally unique ADLS Gen2 storage account name (max 24 chars).')
param storageAccountName string

@description('Globally unique Key Vault name.')
param keyVaultName string

@description('Globally unique SQL server name.')
param sqlServerName string

@description('SQL database name.')
param sqlDatabaseName string = 'DataCycleDB'

@description('SQL administrator login name.')
param sqlAdminLogin string

@secure()
@description('SQL administrator password. Injected from GitHub Secrets in CI.')
param sqlAdminPassword string

@description('Databricks workspace name.')
param databricksWorkspaceName string

@description('ADF name.')
param adfName string

@description('Action Group name for alert routing.')
param actionGroupName string

@description('Databricks SKU.')
param databricksSkuName string = 'standard'

@description('On-prem VM IP (whitelisted on SQL firewall).')
param onPremVmIp string

@description('On-prem VM user (currently unused by Bicep, documented for downstream steps).')
param onPremVmUser string = 'Student'

@description('Client IP rules to add to the SQL firewall.')
param allowedClientIpRanges array = []

@description('Email receivers for the action group.')
param alertEmailReceivers array = []

@secure()
param databricksToken string

@secure()
param adminSqlPassword string

@secure()
param adminVmPassword string

@secure()
param studentVmPassword string

@secure()
param knimeSecret string

@secure()
param knimeAppId string

@secure()
param knimeAppSecret string

@secure()
param sacPassword string

@description('KNIME deployment + user values (non-sensitive).')
param knimeDeployDataPrep string
param knimeDeployModelSel string
param knimeDeployCons string
param knimeDeploySolar string
param knimeApiUser string

module resourceGroups 'modules/resource_groups.bicep' = {
  name: 'resource-groups-${environmentName}'
  params: {
    projectRgName: resourceGroupName
    location: location
  }
}

module keyVault 'modules/key_vault.bicep' = {
  name: 'key-vault-${environmentName}'
  scope: resourceGroup(resourceGroupName)
  dependsOn: [resourceGroups]
  params: {
    keyVaultName: keyVaultName
    location: location
    tenantId: tenantId
    databricksToken: databricksToken
    adminSqlPassword: adminSqlPassword
    adminVmPassword: adminVmPassword
    studentVmPassword: studentVmPassword
    knimeSecret: knimeSecret
    knimeAppId: knimeAppId
    knimeAppSecret: knimeAppSecret
    sacPassword: sacPassword
  }
}

module storage 'modules/storage.bicep' = {
  name: 'storage-${environmentName}'
  scope: resourceGroup(resourceGroupName)
  dependsOn: [resourceGroups, keyVault]
  params: {
    storageAccountName: storageAccountName
    location: location
    keyVaultName: keyVaultName
  }
}

module sql 'modules/sql.bicep' = {
  name: 'sql-${environmentName}'
  scope: resourceGroup(resourceGroupName)
  dependsOn: [resourceGroups]
  params: {
    sqlServerName: sqlServerName
    sqlDatabaseName: sqlDatabaseName
    sqlAdminLogin: sqlAdminLogin
    sqlAdminPassword: sqlAdminPassword
    location: location
    allowedClientIpRanges: allowedClientIpRanges
    onPremVmIp: onPremVmIp
  }
}

module databricksWorkspace 'modules/databricks_workspace.bicep' = {
  name: 'dbx-workspace-${environmentName}'
  scope: resourceGroup(resourceGroupName)
  dependsOn: [resourceGroups]
  params: {
    databricksWorkspaceName: databricksWorkspaceName
    location: location
    skuName: databricksSkuName
    subscriptionId: subscriptionId
    managedResourceGroupName: databricksManagedRgName
  }
}

module dataFactory 'modules/data_factory.bicep' = {
  name: 'adf-${environmentName}'
  scope: resourceGroup(resourceGroupName)
  dependsOn: [resourceGroups]
  params: {
    adfName: adfName
    location: location
  }
}

module monitoring 'modules/monitoring.bicep' = {
  name: 'monitoring-${environmentName}'
  scope: resourceGroup(resourceGroupName)
  dependsOn: [resourceGroups, dataFactory]
  params: {
    actionGroupName: actionGroupName
    adfName: adfName
    alertEmailReceivers: alertEmailReceivers
  }
}

module roleAssignments 'modules/role_assignments.bicep' = {
  name: 'role-assignments-${environmentName}'
  scope: resourceGroup(resourceGroupName)
  dependsOn: [dataFactory, storage, keyVault]
  params: {
    storageAccountName: storageAccountName
    keyVaultName: keyVaultName
    adfPrincipalId: dataFactory.outputs.adfPrincipalId
  }
}

output projectRgName string = resourceGroupName
output databricksManagedRgName string = databricksManagedRgName
output storageAccountName string = storage.outputs.storageAccountName
output keyVaultName string = keyVault.outputs.keyVaultName
output keyVaultUri string = keyVault.outputs.keyVaultUri
output keyVaultId string = keyVault.outputs.keyVaultId
output sqlServerFqdn string = sql.outputs.sqlServerFqdn
output sqlDatabaseName string = sql.outputs.sqlDatabaseName
output sqlServerName string = sqlServerName
output databricksWorkspaceUrl string = databricksWorkspace.outputs.workspaceUrl
output databricksWorkspaceName string = databricksWorkspaceName
output adfName string = dataFactory.outputs.adfName
output adfPrincipalId string = dataFactory.outputs.adfPrincipalId
output actionGroupId string = monitoring.outputs.actionGroupId

// KNIME deployment IDs are carried through as outputs for convenience when running
// downstream scripts that hit the KNIME REST endpoints. These are not secrets.
output knimeDeployDataPrep string = knimeDeployDataPrep
output knimeDeployModelSel string = knimeDeployModelSel
output knimeDeployCons string = knimeDeployCons
output knimeDeploySolar string = knimeDeploySolar
output knimeApiUser string = knimeApiUser
output onPremVmUser string = onPremVmUser
