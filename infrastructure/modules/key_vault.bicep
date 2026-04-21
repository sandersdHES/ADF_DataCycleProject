param keyVaultName string
param location string
param tenantId string

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

resource vault 'Microsoft.KeyVault/vaults@2025-05-01' = {
  name: keyVaultName
  location: location
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: tenantId
    networkAcls: {
      bypass: 'None'
      defaultAction: 'Allow'
      ipRules: []
      virtualNetworkRules: []
    }
    enabledForDeployment: false
    enabledForDiskEncryption: false
    enabledForTemplateDeployment: false
    enableSoftDelete: true
    softDeleteRetentionInDays: 90
    enableRbacAuthorization: true
    publicNetworkAccess: 'Enabled'
  }
}

// Secrets seeded from deploy-time parameters. Storage account key for `adls-access-key`
// is written separately by modules/storage.bicep via listKeys() — doing it there avoids
// circular references between KV and storage modules.

resource secretDatabricksToken 'Microsoft.KeyVault/vaults/secrets@2025-05-01' = {
  parent: vault
  name: 'Databricks-Access-Token'
  properties: {
    value: databricksToken
    attributes: {
      enabled: true
    }
  }
}

resource secretAdminSqlPassword 'Microsoft.KeyVault/vaults/secrets@2025-05-01' = {
  parent: vault
  name: 'Admin-SQL-Password'
  properties: {
    value: adminSqlPassword
    attributes: {
      enabled: true
    }
  }
}

resource secretAdminVmPassword 'Microsoft.KeyVault/vaults/secrets@2025-05-01' = {
  parent: vault
  name: 'Admin-VM-Password'
  properties: {
    value: adminVmPassword
    attributes: {
      enabled: true
    }
  }
}

resource secretStudentVmPassword 'Microsoft.KeyVault/vaults/secrets@2025-05-01' = {
  parent: vault
  name: 'Student-VM-Password'
  properties: {
    value: studentVmPassword
    attributes: {
      enabled: true
    }
  }
}

resource secretKnime 'Microsoft.KeyVault/vaults/secrets@2025-05-01' = {
  parent: vault
  name: 'knime'
  properties: {
    value: knimeSecret
    attributes: {
      enabled: true
    }
  }
}

resource secretKnimeAppId 'Microsoft.KeyVault/vaults/secrets@2025-05-01' = {
  parent: vault
  name: 'knimeappid'
  properties: {
    value: knimeAppId
    attributes: {
      enabled: true
    }
  }
}

resource secretKnimeAppSecret 'Microsoft.KeyVault/vaults/secrets@2025-05-01' = {
  parent: vault
  name: 'knimeappsecret'
  properties: {
    value: knimeAppSecret
    attributes: {
      enabled: true
    }
  }
}

resource secretSacPassword 'Microsoft.KeyVault/vaults/secrets@2025-05-01' = {
  parent: vault
  name: 'sacpassword'
  properties: {
    value: sacPassword
    attributes: {
      enabled: true
    }
  }
}

output keyVaultName string = vault.name
output keyVaultId string = vault.id
output keyVaultUri string = vault.properties.vaultUri
