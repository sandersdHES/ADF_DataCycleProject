param actionGroupName string
param adfName string
param alertEmailReceivers array

resource adf 'Microsoft.DataFactory/factories@2018-06-01' existing = {
  name: adfName
}

resource actionGroup 'microsoft.insights/actionGroups@2024-10-01-preview' = {
  name: actionGroupName
  location: 'Global'
  properties: {
    groupShortName: take(actionGroupName, 12)
    enabled: true
    emailReceivers: [for receiver in alertEmailReceivers: {
      name: receiver.name
      emailAddress: receiver.email
      useCommonAlertSchema: false
    }]
    smsReceivers: []
    webhookReceivers: []
    eventHubReceivers: []
    itsmReceivers: []
    azureAppPushReceivers: []
    automationRunbookReceivers: []
    voiceReceivers: []
    logicAppReceivers: []
    azureFunctionReceivers: []
    armRoleReceivers: []
  }
}

resource ingestFailedAlert 'Microsoft.Insights/metricalerts@2018-03-01' = {
  name: 'ar-pl-ingest-bronze-failed'
  location: 'global'
  properties: {
    severity: 0
    enabled: true
    scopes: [
      adf.id
    ]
    evaluationFrequency: 'PT1H'
    windowSize: 'PT1H'
    criteria: {
      allOf: [
        {
          threshold: json('0')
          name: 'PipelineFailedRuns-PL_Ingest_Bronze'
          metricNamespace: 'Microsoft.DataFactory/factories'
          metricName: 'PipelineFailedRuns'
          dimensions: [
            {
              name: 'FailureType'
              operator: 'Include'
              values: [
                'UserError'
                'SystemError'
                'BadGateway'
              ]
            }
            {
              name: 'Name'
              operator: 'Include'
              values: [
                'PL_Ingest_Bronze'
              ]
            }
          ]
          operator: 'GreaterThan'
          timeAggregation: 'Total'
          criterionType: 'StaticThresholdCriterion'
        }
      ]
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
    }
    actions: [
      {
        actionGroupId: actionGroup.id
        webHookProperties: {}
      }
    ]
  }
}

output actionGroupId string = actionGroup.id
output alertId string = ingestFailedAlert.id
