param adfName string
param location string

resource adf 'Microsoft.DataFactory/factories@2018-06-01' = {
  name: adfName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {}
}

output adfName string = adf.name
output adfId string = adf.id
output adfPrincipalId string = adf.identity.principalId
