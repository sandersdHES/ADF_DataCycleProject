param natGateways_nat_gateway_name string = 'nat-gateway'
param virtualNetworks_workers_vnet_name string = 'workers-vnet'
param networkSecurityGroups_workers_sg_name string = 'workers-sg'
param publicIPAddresses_nat_gw_public_ip_name string = 'nat-gw-public-ip'
param storageAccounts_dbstorager3vovthg4dggs_name string = 'dbstorager3vovthg4dggs'
param userAssignedIdentities_dbmanagedidentity_name string = 'dbmanagedidentity'

resource userAssignedIdentities_dbmanagedidentity_name_resource 'Microsoft.ManagedIdentity/userAssignedIdentities@2025-01-31-preview' = {
  name: userAssignedIdentities_dbmanagedidentity_name
  location: 'switzerlandnorth'
  tags: {
    application: 'databricks'
    'databricks-environment': 'true'
  }
}

resource networkSecurityGroups_workers_sg_name_resource 'Microsoft.Network/networkSecurityGroups@2025-05-01' = {
  name: networkSecurityGroups_workers_sg_name
  location: 'switzerlandnorth'
  tags: {
    application: 'databricks'
    'databricks-environment': 'true'
  }
  properties: {
    securityRules: [
      {
        name: 'databricks-worker-to-worker'
        id: networkSecurityGroups_workers_sg_name_databricks_worker_to_worker.id
        type: 'Microsoft.Network/networkSecurityGroups/securityRules'
        properties: {
          description: 'Required for worker nodes communication within a cluster.'
          protocol: '*'
          sourcePortRange: '*'
          destinationPortRange: '*'
          sourceAddressPrefix: 'VirtualNetwork'
          destinationAddressPrefix: 'VirtualNetwork'
          access: 'Allow'
          priority: 200
          direction: 'Inbound'
          sourcePortRanges: []
          destinationPortRanges: []
          sourceAddressPrefixes: []
          destinationAddressPrefixes: []
        }
      }
    ]
  }
}

resource storageAccounts_dbstorager3vovthg4dggs_name_resource 'Microsoft.Storage/storageAccounts@2025-06-01' = {
  name: storageAccounts_dbstorager3vovthg4dggs_name
  location: 'switzerlandnorth'
  tags: {
    application: 'databricks'
    'databricks-environment': 'true'
  }
  sku: {
    name: 'Standard_ZRS'
    tier: 'Standard'
  }
  kind: 'StorageV2'
  properties: {
    allowCrossTenantReplication: false
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    isHnsEnabled: true
    networkAcls: {
      ipv6Rules: []
      bypass: 'AzureServices'
      virtualNetworkRules: []
      ipRules: []
      defaultAction: 'Allow'
    }
    supportsHttpsTrafficOnly: true
    encryption: {
      services: {
        file: {
          keyType: 'Account'
          enabled: true
        }
        blob: {
          keyType: 'Account'
          enabled: true
        }
      }
      keySource: 'Microsoft.Storage'
    }
    accessTier: 'Hot'
  }
}

resource natGateways_nat_gateway_name_resource 'Microsoft.Network/natGateways@2025-05-01' = {
  name: natGateways_nat_gateway_name
  location: 'switzerlandnorth'
  tags: {
    application: 'databricks'
    'databricks-environment': 'true'
  }
  sku: {
    name: 'Standard'
    tier: 'Regional'
  }
  properties: {
    idleTimeoutInMinutes: 20
    publicIpAddresses: [
      {
        id: publicIPAddresses_nat_gw_public_ip_name_resource.id
      }
    ]
  }
}

resource networkSecurityGroups_workers_sg_name_databricks_worker_to_worker 'Microsoft.Network/networkSecurityGroups/securityRules@2025-05-01' = {
  name: '${networkSecurityGroups_workers_sg_name}/databricks-worker-to-worker'
  properties: {
    description: 'Required for worker nodes communication within a cluster.'
    protocol: '*'
    sourcePortRange: '*'
    destinationPortRange: '*'
    sourceAddressPrefix: 'VirtualNetwork'
    destinationAddressPrefix: 'VirtualNetwork'
    access: 'Allow'
    priority: 200
    direction: 'Inbound'
    sourcePortRanges: []
    destinationPortRanges: []
    sourceAddressPrefixes: []
    destinationAddressPrefixes: []
  }
  dependsOn: [
    networkSecurityGroups_workers_sg_name_resource
  ]
}

resource publicIPAddresses_nat_gw_public_ip_name_resource 'Microsoft.Network/publicIPAddresses@2025-05-01' = {
  name: publicIPAddresses_nat_gw_public_ip_name
  location: 'switzerlandnorth'
  tags: {
    application: 'databricks'
    'databricks-environment': 'true'
  }
  sku: {
    name: 'Standard'
    tier: 'Regional'
  }
  properties: {
    natGateway: {
      id: natGateways_nat_gateway_name_resource.id
    }
    ipAddress: '20.203.195.68'
    publicIPAddressVersion: 'IPv4'
    publicIPAllocationMethod: 'Static'
    idleTimeoutInMinutes: 20
    ipTags: []
    ddosSettings: {
      protectionMode: 'VirtualNetworkInherited'
    }
  }
}

resource storageAccounts_dbstorager3vovthg4dggs_name_default 'Microsoft.Storage/storageAccounts/blobServices@2025-06-01' = {
  parent: storageAccounts_dbstorager3vovthg4dggs_name_resource
  name: 'default'
  sku: {
    name: 'Standard_ZRS'
    tier: 'Standard'
  }
  properties: {
    cors: {
      corsRules: []
    }
    deleteRetentionPolicy: {
      allowPermanentDelete: false
      enabled: false
    }
  }
}

resource Microsoft_Storage_storageAccounts_fileServices_storageAccounts_dbstorager3vovthg4dggs_name_default 'Microsoft.Storage/storageAccounts/fileServices@2025-06-01' = {
  parent: storageAccounts_dbstorager3vovthg4dggs_name_resource
  name: 'default'
  sku: {
    name: 'Standard_ZRS'
    tier: 'Standard'
  }
  properties: {
    protocolSettings: {
      smb: {}
    }
    cors: {
      corsRules: []
    }
    shareDeleteRetentionPolicy: {
      enabled: true
      days: 7
    }
  }
}

resource Microsoft_Storage_storageAccounts_queueServices_storageAccounts_dbstorager3vovthg4dggs_name_default 'Microsoft.Storage/storageAccounts/queueServices@2025-06-01' = {
  parent: storageAccounts_dbstorager3vovthg4dggs_name_resource
  name: 'default'
  properties: {
    cors: {
      corsRules: []
    }
  }
}

resource Microsoft_Storage_storageAccounts_tableServices_storageAccounts_dbstorager3vovthg4dggs_name_default 'Microsoft.Storage/storageAccounts/tableServices@2025-06-01' = {
  parent: storageAccounts_dbstorager3vovthg4dggs_name_resource
  name: 'default'
  properties: {
    cors: {
      corsRules: []
    }
  }
}

resource virtualNetworks_workers_vnet_name_resource 'Microsoft.Network/virtualNetworks@2025-05-01' = {
  name: virtualNetworks_workers_vnet_name
  location: 'switzerlandnorth'
  tags: {
    application: 'databricks'
    'databricks-environment': 'true'
  }
  properties: {
    addressSpace: {
      addressPrefixes: [
        '10.139.0.0/16'
      ]
    }
    privateEndpointVNetPolicies: 'Disabled'
    subnets: [
      {
        name: 'public-subnet'
        id: virtualNetworks_workers_vnet_name_public_subnet.id
        properties: {
          addressPrefix: '10.139.0.0/18'
          networkSecurityGroup: {
            id: networkSecurityGroups_workers_sg_name_resource.id
          }
          natGateway: {
            id: natGateways_nat_gateway_name_resource.id
          }
          delegations: []
          privateEndpointNetworkPolicies: 'Disabled'
          privateLinkServiceNetworkPolicies: 'Enabled'
          defaultOutboundAccess: false
        }
        type: 'Microsoft.Network/virtualNetworks/subnets'
      }
      {
        name: 'private-subnet'
        id: virtualNetworks_workers_vnet_name_private_subnet.id
        properties: {
          addressPrefix: '10.139.64.0/18'
          networkSecurityGroup: {
            id: networkSecurityGroups_workers_sg_name_resource.id
          }
          natGateway: {
            id: natGateways_nat_gateway_name_resource.id
          }
          delegations: []
          privateEndpointNetworkPolicies: 'Disabled'
          privateLinkServiceNetworkPolicies: 'Enabled'
          defaultOutboundAccess: false
        }
        type: 'Microsoft.Network/virtualNetworks/subnets'
      }
    ]
    virtualNetworkPeerings: []
    enableDdosProtection: false
  }
}

resource storageAccounts_dbstorager3vovthg4dggs_name_default_ephemeral 'Microsoft.Storage/storageAccounts/blobServices/containers@2025-06-01' = {
  parent: storageAccounts_dbstorager3vovthg4dggs_name_default
  name: 'ephemeral'
  properties: {
    immutableStorageWithVersioning: {
      enabled: false
    }
    defaultEncryptionScope: '$account-encryption-key'
    denyEncryptionScopeOverride: false
    publicAccess: 'None'
  }
  dependsOn: [
    storageAccounts_dbstorager3vovthg4dggs_name_resource
  ]
}

resource storageAccounts_dbstorager3vovthg4dggs_name_default_jobs 'Microsoft.Storage/storageAccounts/blobServices/containers@2025-06-01' = {
  parent: storageAccounts_dbstorager3vovthg4dggs_name_default
  name: 'jobs'
  properties: {
    immutableStorageWithVersioning: {
      enabled: false
    }
    defaultEncryptionScope: '$account-encryption-key'
    denyEncryptionScopeOverride: false
    publicAccess: 'None'
  }
  dependsOn: [
    storageAccounts_dbstorager3vovthg4dggs_name_resource
  ]
}

resource storageAccounts_dbstorager3vovthg4dggs_name_default_logs 'Microsoft.Storage/storageAccounts/blobServices/containers@2025-06-01' = {
  parent: storageAccounts_dbstorager3vovthg4dggs_name_default
  name: 'logs'
  properties: {
    immutableStorageWithVersioning: {
      enabled: false
    }
    defaultEncryptionScope: '$account-encryption-key'
    denyEncryptionScopeOverride: false
    publicAccess: 'None'
  }
  dependsOn: [
    storageAccounts_dbstorager3vovthg4dggs_name_resource
  ]
}

resource storageAccounts_dbstorager3vovthg4dggs_name_default_meta 'Microsoft.Storage/storageAccounts/blobServices/containers@2025-06-01' = {
  parent: storageAccounts_dbstorager3vovthg4dggs_name_default
  name: 'meta'
  properties: {
    immutableStorageWithVersioning: {
      enabled: false
    }
    defaultEncryptionScope: '$account-encryption-key'
    denyEncryptionScopeOverride: false
    publicAccess: 'None'
  }
  dependsOn: [
    storageAccounts_dbstorager3vovthg4dggs_name_resource
  ]
}

resource storageAccounts_dbstorager3vovthg4dggs_name_default_root 'Microsoft.Storage/storageAccounts/blobServices/containers@2025-06-01' = {
  parent: storageAccounts_dbstorager3vovthg4dggs_name_default
  name: 'root'
  properties: {
    immutableStorageWithVersioning: {
      enabled: false
    }
    defaultEncryptionScope: '$account-encryption-key'
    denyEncryptionScopeOverride: false
    publicAccess: 'None'
  }
  dependsOn: [
    storageAccounts_dbstorager3vovthg4dggs_name_resource
  ]
}

resource virtualNetworks_workers_vnet_name_private_subnet 'Microsoft.Network/virtualNetworks/subnets@2025-05-01' = {
  name: '${virtualNetworks_workers_vnet_name}/private-subnet'
  properties: {
    addressPrefix: '10.139.64.0/18'
    networkSecurityGroup: {
      id: networkSecurityGroups_workers_sg_name_resource.id
    }
    natGateway: {
      id: natGateways_nat_gateway_name_resource.id
    }
    delegations: []
    privateEndpointNetworkPolicies: 'Disabled'
    privateLinkServiceNetworkPolicies: 'Enabled'
    defaultOutboundAccess: false
  }
  dependsOn: [
    virtualNetworks_workers_vnet_name_resource
  ]
}

resource virtualNetworks_workers_vnet_name_public_subnet 'Microsoft.Network/virtualNetworks/subnets@2025-05-01' = {
  name: '${virtualNetworks_workers_vnet_name}/public-subnet'
  properties: {
    addressPrefix: '10.139.0.0/18'
    networkSecurityGroup: {
      id: networkSecurityGroups_workers_sg_name_resource.id
    }
    natGateway: {
      id: natGateways_nat_gateway_name_resource.id
    }
    delegations: []
    privateEndpointNetworkPolicies: 'Disabled'
    privateLinkServiceNetworkPolicies: 'Enabled'
    defaultOutboundAccess: false
  }
  dependsOn: [
    virtualNetworks_workers_vnet_name_resource
  ]
}
