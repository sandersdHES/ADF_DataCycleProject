param databricksWorkspaceName string
param location string
param skuName string = 'standard'
param subscriptionId string
param managedResourceGroupName string

// The managed RG is populated by Databricks on first deploy — do not pre-create it.
// `managedResourceGroupId` only needs to be a valid ARM resource ID path.
var managedRgId = '/subscriptions/${subscriptionId}/resourceGroups/${managedResourceGroupName}'

resource workspace 'Microsoft.Databricks/workspaces@2026-01-01' = {
  name: databricksWorkspaceName
  location: location
  sku: {
    name: skuName
  }
  properties: {
    computeMode: 'Hybrid'
    managedResourceGroupId: managedRgId
    parameters: {
      enableNoPublicIp: {
        value: true
      }
      prepareEncryption: {
        value: false
      }
      requireInfrastructureEncryption: {
        value: false
      }
      storageAccountSkuName: {
        value: 'Standard_ZRS'
      }
    }
  }
}

output workspaceId string = workspace.id
output workspaceUrl string = 'https://${workspace.properties.workspaceUrl}'
output workspaceName string = workspace.name
