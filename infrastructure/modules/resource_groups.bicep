targetScope = 'subscription'

param projectRgName string
param location string

// The Databricks managed RG is intentionally NOT created here. The Databricks workspace
// creates and manages it automatically when `managedResourceGroupId` is specified on
// the workspace resource. Pre-creating it risks deployment conflicts with the
// Databricks control plane.

resource projectRg 'Microsoft.Resources/resourceGroups@2024-11-01' = {
  name: projectRgName
  location: location
  tags: {
    application: 'datacycle'
  }
}

output projectRgName string = projectRg.name
