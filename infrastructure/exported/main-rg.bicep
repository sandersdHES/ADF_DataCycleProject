@secure()
param vulnerabilityAssessments_Default_storageContainerPath string
param vaults_DataCycleGroup3Keys_name string = 'DataCycleGroup3Keys'
param servers_sqlserver_bellevue_grp3_name string = 'sqlserver-bellevue-grp3'
param actionGroups_AG_Group3_Alerts_name string = 'AG-Group3-Alerts'
param metricalerts_ar_bellevue_grp3_name string = 'ar-bellevue-grp3'
param vaults_vault_mmx89ver_name string = 'vault-mmx89ver'
param workspaces_adb_bellevue_grp3_name string = 'adb-bellevue-grp3'
param storageAccounts_adlsbellevuegrp3_name string = 'adlsbellevuegrp3'
param factories_group3_df_externalid string = '/subscriptions/852f0176-1826-4957-a7fc-b1cd7e7aac73/resourceGroups/datafactory-rg505/providers/Microsoft.DataFactory/factories/group3-df'

resource workspaces_adb_bellevue_grp3_name_resource 'Microsoft.Databricks/workspaces@2026-01-01' = {
  name: workspaces_adb_bellevue_grp3_name
  location: 'switzerlandnorth'
  sku: {
    name: 'standard'
  }
  properties: {
    computeMode: 'Hybrid'
    managedResourceGroupId: '/subscriptions/852f0176-1826-4957-a7fc-b1cd7e7aac73/resourceGroups/databricks-rg-${workspaces_adb_bellevue_grp3_name}-ehdvgodpwoynu'
    parameters: {
      enableNoPublicIp: {
        type: 'Bool'
        value: true
      }
      prepareEncryption: {
        type: 'Bool'
        value: false
      }
      requireInfrastructureEncryption: {
        type: 'Bool'
        value: false
      }
      storageAccountName: {
        type: 'String'
        value: 'dbstorager3vovthg4dggs'
      }
      storageAccountSkuName: {
        type: 'String'
        value: 'Standard_ZRS'
      }
    }
    authorizations: [
      {
        principalId: '9a74af6f-d153-4348-988a-e2672920bee9'
        roleDefinitionId: '8e3af657-a8ff-443c-a75c-2fe8c4bcb635'
      }
    ]
    createdBy: {}
    updatedBy: {}
  }
}

resource actionGroups_AG_Group3_Alerts_name_resource 'microsoft.insights/actionGroups@2024-10-01-preview' = {
  name: actionGroups_AG_Group3_Alerts_name
  location: 'Global'
  properties: {
    groupShortName: 'Alerts'
    enabled: true
    emailReceivers: [
      {
        name: 'Dylan NotifEmail'
        emailAddress: 'dylan.sanderson@students.hevs.ch'
        useCommonAlertSchema: false
      }
      {
        name: 'Adriel NotifEmail'
        emailAddress: 'adriel.ferreira02@e-uvt.ro'
        useCommonAlertSchema: false
      }
      {
        name: 'Abril NotifEmail'
        emailAddress: 'abrilpalau14@gmail.com'
        useCommonAlertSchema: false
      }
      {
        name: 'Francisco NotifEmail'
        emailAddress: 'francisco.s.mesquita@ubi.pt'
        useCommonAlertSchema: false
      }
    ]
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

resource vaults_DataCycleGroup3Keys_name_resource 'Microsoft.KeyVault/vaults@2025-05-01' = {
  name: vaults_DataCycleGroup3Keys_name
  location: 'switzerlandnorth'
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: 'a372f724-c0b2-4ea0-abfb-0eb8c6f84e40'
    networkAcls: {
      bypass: 'None'
      defaultAction: 'Allow'
      ipRules: []
      virtualNetworkRules: []
    }
    accessPolicies: [
      {
        tenantId: 'a372f724-c0b2-4ea0-abfb-0eb8c6f84e40'
        objectId: 'f3523385-b650-41b2-af75-13e6c0fe49f1'
        permissions: {
          secrets: [
            'get'
            'list'
          ]
        }
      }
    ]
    enabledForDeployment: false
    enabledForDiskEncryption: false
    enabledForTemplateDeployment: false
    enableSoftDelete: true
    softDeleteRetentionInDays: 90
    enableRbacAuthorization: true
    vaultUri: 'https://datacyclegroup3keys.vault.azure.net/'
    provisioningState: 'Succeeded'
    publicNetworkAccess: 'Enabled'
  }
}

resource vaults_vault_mmx89ver_name_resource 'Microsoft.RecoveryServices/vaults@2025-08-01' = {
  name: vaults_vault_mmx89ver_name
  location: 'switzerlandnorth'
  sku: {
    name: 'RS0'
    tier: 'Standard'
  }
  properties: {
    securitySettings: {
      softDeleteSettings: {
        softDeleteRetentionPeriodInDays: 14
        softDeleteState: 'Enabled'
        enhancedSecurityState: 'Enabled'
      }
      sourceScanConfiguration: {
        state: 'Disabled'
      }
    }
    redundancySettings: {
      standardTierStorageRedundancy: 'GeoRedundant'
      crossRegionRestore: 'Disabled'
    }
    publicNetworkAccess: 'Enabled'
    restoreSettings: {
      crossSubscriptionRestoreSettings: {
        crossSubscriptionRestoreState: 'Enabled'
      }
    }
  }
}

resource servers_sqlserver_bellevue_grp3_name_resource 'Microsoft.Sql/servers@2024-11-01-preview' = {
  name: servers_sqlserver_bellevue_grp3_name
  location: 'switzerlandnorth'
  kind: 'v12.0'
  properties: {
    administratorLogin: 'dylan.sanderso'
    version: '12.0'
    minimalTlsVersion: '1.2'
    publicNetworkAccess: 'Enabled'
    restrictOutboundNetworkAccess: 'Disabled'
    retentionDays: -1
  }
}

resource storageAccounts_adlsbellevuegrp3_name_resource 'Microsoft.Storage/storageAccounts@2025-06-01' = {
  name: storageAccounts_adlsbellevuegrp3_name
  location: 'switzerlandnorth'
  sku: {
    name: 'Standard_LRS'
    tier: 'Standard'
  }
  kind: 'StorageV2'
  properties: {
    dualStackEndpointPreference: {
      publishIpv6Endpoint: false
    }
    dnsEndpointType: 'Standard'
    defaultToOAuthAuthentication: false
    publicNetworkAccess: 'Enabled'
    allowCrossTenantReplication: false
    isSftpEnabled: false
    azureFilesIdentityBasedAuthentication: {
      smbOAuthSettings: {
        isSmbOAuthEnabled: true
      }
      directoryServiceOptions: 'None'
    }
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    allowSharedKeyAccess: true
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
      requireInfrastructureEncryption: false
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

resource metricalerts_ar_bellevue_grp3_name_resource 'Microsoft.Insights/metricalerts@2018-03-01' = {
  name: metricalerts_ar_bellevue_grp3_name
  location: 'global'
  properties: {
    severity: 0
    enabled: true
    scopes: [
      factories_group3_df_externalid
    ]
    evaluationFrequency: 'PT1H'
    windowSize: 'PT1H'
    criteria: {
      allOf: [
        {
          threshold: json('0')
          name: '7a3ce684-0411-4d8d-8d9d-660421d68598'
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
        actionGroupId: actionGroups_AG_Group3_Alerts_name_resource.id
        webHookProperties: {}
      }
    ]
  }
}

resource vaults_DataCycleGroup3Keys_name_adls_access_key 'Microsoft.KeyVault/vaults/secrets@2025-05-01' = {
  parent: vaults_DataCycleGroup3Keys_name_resource
  name: 'adls-access-key'
  location: 'switzerlandnorth'
  properties: {
    attributes: {
      enabled: true
    }
  }
}

resource vaults_DataCycleGroup3Keys_name_Admin_SQL_Password 'Microsoft.KeyVault/vaults/secrets@2025-05-01' = {
  parent: vaults_DataCycleGroup3Keys_name_resource
  name: 'Admin-SQL-Password'
  location: 'switzerlandnorth'
  properties: {
    attributes: {
      enabled: true
    }
  }
}

resource vaults_DataCycleGroup3Keys_name_Admin_VM_Password 'Microsoft.KeyVault/vaults/secrets@2025-05-01' = {
  parent: vaults_DataCycleGroup3Keys_name_resource
  name: 'Admin-VM-Password'
  location: 'switzerlandnorth'
  properties: {
    attributes: {
      enabled: true
    }
  }
}

resource vaults_DataCycleGroup3Keys_name_Databricks_Access_Token 'Microsoft.KeyVault/vaults/secrets@2025-05-01' = {
  parent: vaults_DataCycleGroup3Keys_name_resource
  name: 'Databricks-Access-Token'
  location: 'switzerlandnorth'
  properties: {
    attributes: {
      enabled: true
    }
  }
}

resource vaults_DataCycleGroup3Keys_name_knime 'Microsoft.KeyVault/vaults/secrets@2025-05-01' = {
  parent: vaults_DataCycleGroup3Keys_name_resource
  name: 'knime'
  location: 'switzerlandnorth'
  properties: {
    attributes: {
      enabled: true
    }
  }
}

resource vaults_DataCycleGroup3Keys_name_knimeappid 'Microsoft.KeyVault/vaults/secrets@2025-05-01' = {
  parent: vaults_DataCycleGroup3Keys_name_resource
  name: 'knimeappid'
  location: 'switzerlandnorth'
  properties: {
    attributes: {
      enabled: true
    }
  }
}

resource vaults_DataCycleGroup3Keys_name_knimeappsecret 'Microsoft.KeyVault/vaults/secrets@2025-05-01' = {
  parent: vaults_DataCycleGroup3Keys_name_resource
  name: 'knimeappsecret'
  location: 'switzerlandnorth'
  properties: {
    attributes: {
      enabled: true
    }
  }
}

resource vaults_DataCycleGroup3Keys_name_sacpassword 'Microsoft.KeyVault/vaults/secrets@2025-05-01' = {
  parent: vaults_DataCycleGroup3Keys_name_resource
  name: 'sacpassword'
  location: 'switzerlandnorth'
  properties: {
    contentType: 'ABA_LEARN_239'
    attributes: {
      enabled: true
    }
  }
}

resource vaults_DataCycleGroup3Keys_name_Student_VM_Password 'Microsoft.KeyVault/vaults/secrets@2025-05-01' = {
  parent: vaults_DataCycleGroup3Keys_name_resource
  name: 'Student-VM-Password'
  location: 'switzerlandnorth'
  properties: {
    attributes: {
      enabled: true
    }
  }
}

resource vaults_vault_mmx89ver_name_DailyPolicy_mmx89vnf 'Microsoft.RecoveryServices/vaults/backupPolicies@2025-08-01' = {
  parent: vaults_vault_mmx89ver_name_resource
  name: 'DailyPolicy-mmx89vnf'
  properties: {
    backupManagementType: 'AzureStorage'
    workLoadType: 'AzureFileShare'
    schedulePolicy: {
      schedulePolicyType: 'SimpleSchedulePolicy'
      scheduleRunFrequency: 'Daily'
      scheduleRunTimes: [
        '2026-03-19T19:30:00Z'
      ]
      scheduleWeeklyFrequency: 0
    }
    retentionPolicy: {
      retentionPolicyType: 'LongTermRetentionPolicy'
      dailySchedule: {
        retentionTimes: [
          '2026-03-19T19:30:00Z'
        ]
        retentionDuration: {
          count: 30
          durationType: 'Days'
        }
      }
    }
    timeZone: 'UTC'
    protectedItemsCount: 0
  }
}

resource vaults_vault_mmx89ver_name_DefaultPolicy 'Microsoft.RecoveryServices/vaults/backupPolicies@2025-08-01' = {
  parent: vaults_vault_mmx89ver_name_resource
  name: 'DefaultPolicy'
  properties: {
    backupManagementType: 'AzureIaasVM'
    policyType: 'V1'
    instantRPDetails: {}
    schedulePolicy: {
      schedulePolicyType: 'SimpleSchedulePolicy'
      scheduleRunFrequency: 'Daily'
      scheduleRunTimes: [
        '2026-03-19T18:30:00Z'
      ]
      scheduleWeeklyFrequency: 0
    }
    retentionPolicy: {
      retentionPolicyType: 'LongTermRetentionPolicy'
      dailySchedule: {
        retentionTimes: [
          '2026-03-19T18:30:00Z'
        ]
        retentionDuration: {
          count: 30
          durationType: 'Days'
        }
      }
    }
    instantRpRetentionRangeInDays: 2
    timeZone: 'UTC'
    protectedItemsCount: 0
  }
}

resource vaults_vault_mmx89ver_name_EnhancedPolicy 'Microsoft.RecoveryServices/vaults/backupPolicies@2025-08-01' = {
  parent: vaults_vault_mmx89ver_name_resource
  name: 'EnhancedPolicy'
  properties: {
    backupManagementType: 'AzureIaasVM'
    policyType: 'V2'
    instantRPDetails: {}
    schedulePolicy: {
      schedulePolicyType: 'SimpleSchedulePolicyV2'
      scheduleRunFrequency: 'Hourly'
      hourlySchedule: {
        interval: 4
        scheduleWindowStartTime: '2026-03-19T08:00:00Z'
        scheduleWindowDuration: 12
      }
    }
    retentionPolicy: {
      retentionPolicyType: 'LongTermRetentionPolicy'
      dailySchedule: {
        retentionTimes: [
          '2026-03-19T08:00:00Z'
        ]
        retentionDuration: {
          count: 30
          durationType: 'Days'
        }
      }
    }
    instantRpRetentionRangeInDays: 2
    timeZone: 'UTC'
    protectedItemsCount: 0
  }
}

resource vaults_vault_mmx89ver_name_HourlyLogBackup 'Microsoft.RecoveryServices/vaults/backupPolicies@2025-08-01' = {
  parent: vaults_vault_mmx89ver_name_resource
  name: 'HourlyLogBackup'
  properties: {
    backupManagementType: 'AzureWorkload'
    workLoadType: 'SQLDataBase'
    settings: {
      timeZone: 'UTC'
      issqlcompression: false
      isCompression: false
    }
    subProtectionPolicy: [
      {
        policyType: 'Full'
        schedulePolicy: {
          schedulePolicyType: 'SimpleSchedulePolicy'
          scheduleRunFrequency: 'Daily'
          scheduleRunTimes: [
            '2026-03-19T18:30:00Z'
          ]
          scheduleWeeklyFrequency: 0
        }
        retentionPolicy: {
          retentionPolicyType: 'LongTermRetentionPolicy'
          dailySchedule: {
            retentionTimes: [
              '2026-03-19T18:30:00Z'
            ]
            retentionDuration: {
              count: 30
              durationType: 'Days'
            }
          }
        }
      }
      {
        policyType: 'Log'
        schedulePolicy: {
          schedulePolicyType: 'LogSchedulePolicy'
          scheduleFrequencyInMins: 60
        }
        retentionPolicy: {
          retentionPolicyType: 'SimpleRetentionPolicy'
          retentionDuration: {
            count: 30
            durationType: 'Days'
          }
        }
      }
    ]
    protectedItemsCount: 0
  }
}

resource vaults_vault_mmx89ver_name_defaultAlertSetting 'Microsoft.RecoveryServices/vaults/replicationAlertSettings@2025-08-01' = {
  parent: vaults_vault_mmx89ver_name_resource
  name: 'defaultAlertSetting'
  properties: {
    sendToOwners: 'DoNotSend'
    customEmailAddresses: []
  }
}

resource vaults_vault_mmx89ver_name_default 'Microsoft.RecoveryServices/vaults/replicationVaultSettings@2025-08-01' = {
  parent: vaults_vault_mmx89ver_name_resource
  name: 'default'
  properties: {}
}

resource servers_sqlserver_bellevue_grp3_name_Default 'Microsoft.Sql/servers/advancedThreatProtectionSettings@2024-11-01-preview' = {
  parent: servers_sqlserver_bellevue_grp3_name_resource
  name: 'Default'
  properties: {
    state: 'Disabled'
  }
}

resource servers_sqlserver_bellevue_grp3_name_CreateIndex 'Microsoft.Sql/servers/advisors@2014-04-01' = {
  parent: servers_sqlserver_bellevue_grp3_name_resource
  name: 'CreateIndex'
  properties: {
    autoExecuteValue: 'Disabled'
  }
}

resource servers_sqlserver_bellevue_grp3_name_DbParameterization 'Microsoft.Sql/servers/advisors@2014-04-01' = {
  parent: servers_sqlserver_bellevue_grp3_name_resource
  name: 'DbParameterization'
  properties: {
    autoExecuteValue: 'Disabled'
  }
}

resource servers_sqlserver_bellevue_grp3_name_DefragmentIndex 'Microsoft.Sql/servers/advisors@2014-04-01' = {
  parent: servers_sqlserver_bellevue_grp3_name_resource
  name: 'DefragmentIndex'
  properties: {
    autoExecuteValue: 'Disabled'
  }
}

resource servers_sqlserver_bellevue_grp3_name_DropIndex 'Microsoft.Sql/servers/advisors@2014-04-01' = {
  parent: servers_sqlserver_bellevue_grp3_name_resource
  name: 'DropIndex'
  properties: {
    autoExecuteValue: 'Disabled'
  }
}

resource servers_sqlserver_bellevue_grp3_name_ForceLastGoodPlan 'Microsoft.Sql/servers/advisors@2014-04-01' = {
  parent: servers_sqlserver_bellevue_grp3_name_resource
  name: 'ForceLastGoodPlan'
  properties: {
    autoExecuteValue: 'Enabled'
  }
}

resource Microsoft_Sql_servers_auditingPolicies_servers_sqlserver_bellevue_grp3_name_Default 'Microsoft.Sql/servers/auditingPolicies@2014-04-01' = {
  parent: servers_sqlserver_bellevue_grp3_name_resource
  name: 'Default'
  location: 'Switzerland North'
  properties: {
    auditingState: 'Disabled'
  }
}

resource Microsoft_Sql_servers_auditingSettings_servers_sqlserver_bellevue_grp3_name_Default 'Microsoft.Sql/servers/auditingSettings@2024-11-01-preview' = {
  parent: servers_sqlserver_bellevue_grp3_name_resource
  name: 'Default'
  properties: {
    retentionDays: 0
    auditActionsAndGroups: []
    isStorageSecondaryKeyInUse: false
    isAzureMonitorTargetEnabled: false
    isManagedIdentityInUse: false
    state: 'Disabled'
    storageAccountSubscriptionId: '00000000-0000-0000-0000-000000000000'
  }
}

resource Microsoft_Sql_servers_connectionPolicies_servers_sqlserver_bellevue_grp3_name_default 'Microsoft.Sql/servers/connectionPolicies@2024-11-01-preview' = {
  parent: servers_sqlserver_bellevue_grp3_name_resource
  name: 'default'
  location: 'switzerlandnorth'
  properties: {
    connectionType: 'Proxy'
  }
}

resource servers_sqlserver_bellevue_grp3_name_DevDB 'Microsoft.Sql/servers/databases@2024-11-01-preview' = {
  parent: servers_sqlserver_bellevue_grp3_name_resource
  name: 'DevDB'
  location: 'switzerlandnorth'
  sku: {
    name: 'GP_S_Gen5'
    tier: 'GeneralPurpose'
    family: 'Gen5'
    capacity: 2
  }
  kind: 'v12.0,user,vcore,serverless,freelimit'
  properties: {
    collation: 'SQL_Latin1_General_CP1_CI_AS'
    maxSizeBytes: 34359738368
    catalogCollation: 'SQL_Latin1_General_CP1_CI_AS'
    zoneRedundant: false
    readScale: 'Disabled'
    autoPauseDelay: 60
    requestedBackupStorageRedundancy: 'Local'
    minCapacity: json('0.5')
    maintenanceConfigurationId: '/subscriptions/852f0176-1826-4957-a7fc-b1cd7e7aac73/providers/Microsoft.Maintenance/publicMaintenanceConfigurations/SQL_Default'
    isLedgerOn: false
    useFreeLimit: true
    freeLimitExhaustionBehavior: 'AutoPause'
    availabilityZone: 'NoPreference'
  }
}

resource servers_sqlserver_bellevue_grp3_name_master_Default 'Microsoft.Sql/servers/databases/advancedThreatProtectionSettings@2024-11-01-preview' = {
  name: '${servers_sqlserver_bellevue_grp3_name}/master/Default'
  properties: {
    state: 'Disabled'
  }
  dependsOn: [
    servers_sqlserver_bellevue_grp3_name_resource
  ]
}

resource Microsoft_Sql_servers_databases_auditingPolicies_servers_sqlserver_bellevue_grp3_name_master_Default 'Microsoft.Sql/servers/databases/auditingPolicies@2014-04-01' = {
  name: '${servers_sqlserver_bellevue_grp3_name}/master/Default'
  location: 'Switzerland North'
  properties: {
    auditingState: 'Disabled'
  }
  dependsOn: [
    servers_sqlserver_bellevue_grp3_name_resource
  ]
}

resource Microsoft_Sql_servers_databases_auditingSettings_servers_sqlserver_bellevue_grp3_name_master_Default 'Microsoft.Sql/servers/databases/auditingSettings@2024-11-01-preview' = {
  name: '${servers_sqlserver_bellevue_grp3_name}/master/Default'
  properties: {
    retentionDays: 0
    isAzureMonitorTargetEnabled: false
    state: 'Disabled'
    storageAccountSubscriptionId: '00000000-0000-0000-0000-000000000000'
  }
  dependsOn: [
    servers_sqlserver_bellevue_grp3_name_resource
  ]
}

resource Microsoft_Sql_servers_databases_extendedAuditingSettings_servers_sqlserver_bellevue_grp3_name_master_Default 'Microsoft.Sql/servers/databases/extendedAuditingSettings@2024-11-01-preview' = {
  name: '${servers_sqlserver_bellevue_grp3_name}/master/Default'
  properties: {
    retentionDays: 0
    isAzureMonitorTargetEnabled: false
    state: 'Disabled'
    storageAccountSubscriptionId: '00000000-0000-0000-0000-000000000000'
  }
  dependsOn: [
    servers_sqlserver_bellevue_grp3_name_resource
  ]
}

resource Microsoft_Sql_servers_databases_geoBackupPolicies_servers_sqlserver_bellevue_grp3_name_master_Default 'Microsoft.Sql/servers/databases/geoBackupPolicies@2024-11-01-preview' = {
  name: '${servers_sqlserver_bellevue_grp3_name}/master/Default'
  properties: {
    state: 'Disabled'
  }
  dependsOn: [
    servers_sqlserver_bellevue_grp3_name_resource
  ]
}

resource servers_sqlserver_bellevue_grp3_name_master_Current 'Microsoft.Sql/servers/databases/ledgerDigestUploads@2024-11-01-preview' = {
  name: '${servers_sqlserver_bellevue_grp3_name}/master/Current'
  properties: {}
  dependsOn: [
    servers_sqlserver_bellevue_grp3_name_resource
  ]
}

resource Microsoft_Sql_servers_databases_securityAlertPolicies_servers_sqlserver_bellevue_grp3_name_master_Default 'Microsoft.Sql/servers/databases/securityAlertPolicies@2024-11-01-preview' = {
  name: '${servers_sqlserver_bellevue_grp3_name}/master/Default'
  properties: {
    state: 'Disabled'
    disabledAlerts: [
      ''
    ]
    emailAddresses: [
      ''
    ]
    emailAccountAdmins: false
    retentionDays: 0
  }
  dependsOn: [
    servers_sqlserver_bellevue_grp3_name_resource
  ]
}

resource Microsoft_Sql_servers_databases_transparentDataEncryption_servers_sqlserver_bellevue_grp3_name_master_Current 'Microsoft.Sql/servers/databases/transparentDataEncryption@2024-11-01-preview' = {
  name: '${servers_sqlserver_bellevue_grp3_name}/master/Current'
  properties: {
    state: 'Disabled'
  }
  dependsOn: [
    servers_sqlserver_bellevue_grp3_name_resource
  ]
}

resource Microsoft_Sql_servers_databases_vulnerabilityAssessments_servers_sqlserver_bellevue_grp3_name_master_Default 'Microsoft.Sql/servers/databases/vulnerabilityAssessments@2024-11-01-preview' = {
  name: '${servers_sqlserver_bellevue_grp3_name}/master/Default'
  properties: {
    recurringScans: {
      isEnabled: false
      emailSubscriptionAdmins: true
    }
  }
  dependsOn: [
    servers_sqlserver_bellevue_grp3_name_resource
  ]
}

resource Microsoft_Sql_servers_devOpsAuditingSettings_servers_sqlserver_bellevue_grp3_name_Default 'Microsoft.Sql/servers/devOpsAuditingSettings@2024-11-01-preview' = {
  parent: servers_sqlserver_bellevue_grp3_name_resource
  name: 'Default'
  properties: {
    isAzureMonitorTargetEnabled: false
    isManagedIdentityInUse: false
    state: 'Disabled'
    storageAccountSubscriptionId: '00000000-0000-0000-0000-000000000000'
  }
}

resource servers_sqlserver_bellevue_grp3_name_current 'Microsoft.Sql/servers/encryptionProtector@2024-11-01-preview' = {
  parent: servers_sqlserver_bellevue_grp3_name_resource
  name: 'current'
  kind: 'servicemanaged'
  properties: {
    serverKeyName: 'ServiceManaged'
    serverKeyType: 'ServiceManaged'
    autoRotationEnabled: false
  }
}

resource Microsoft_Sql_servers_extendedAuditingSettings_servers_sqlserver_bellevue_grp3_name_Default 'Microsoft.Sql/servers/extendedAuditingSettings@2024-11-01-preview' = {
  parent: servers_sqlserver_bellevue_grp3_name_resource
  name: 'Default'
  properties: {
    retentionDays: 0
    auditActionsAndGroups: []
    isStorageSecondaryKeyInUse: false
    isAzureMonitorTargetEnabled: false
    isManagedIdentityInUse: false
    state: 'Disabled'
    storageAccountSubscriptionId: '00000000-0000-0000-0000-000000000000'
  }
}

resource servers_sqlserver_bellevue_grp3_name_AllowAllWindowsAzureIps 'Microsoft.Sql/servers/firewallRules@2024-11-01-preview' = {
  parent: servers_sqlserver_bellevue_grp3_name_resource
  name: 'AllowAllWindowsAzureIps'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

resource servers_sqlserver_bellevue_grp3_name_ClientIPAddress_2026_3_17_10_48_3 'Microsoft.Sql/servers/firewallRules@2024-11-01-preview' = {
  parent: servers_sqlserver_bellevue_grp3_name_resource
  name: 'ClientIPAddress_2026-3-17_10-48-3'
  properties: {
    startIpAddress: '153.109.1.211'
    endIpAddress: '153.109.1.211'
  }
}

resource servers_sqlserver_bellevue_grp3_name_ClientIPAddress_2026_3_18_10_43_59 'Microsoft.Sql/servers/firewallRules@2024-11-01-preview' = {
  parent: servers_sqlserver_bellevue_grp3_name_resource
  name: 'ClientIPAddress_2026-3-18_10-43-59'
  properties: {
    startIpAddress: '85.120.207.251'
    endIpAddress: '85.120.207.251'
  }
}

resource servers_sqlserver_bellevue_grp3_name_ClientIPAddress_2026_3_2_8_18_16 'Microsoft.Sql/servers/firewallRules@2024-11-01-preview' = {
  parent: servers_sqlserver_bellevue_grp3_name_resource
  name: 'ClientIPAddress_2026-3-2_8-18-16'
  properties: {
    startIpAddress: '185.249.189.232'
    endIpAddress: '185.249.189.232'
  }
}

resource servers_sqlserver_bellevue_grp3_name_Group3_VM_Access 'Microsoft.Sql/servers/firewallRules@2024-11-01-preview' = {
  parent: servers_sqlserver_bellevue_grp3_name_resource
  name: 'Group3_VM_Access'
  properties: {
    startIpAddress: '10.130.25.155'
    endIpAddress: '10.130.25.155'
  }
}

resource servers_sqlserver_bellevue_grp3_name_query_editor_39dec6 'Microsoft.Sql/servers/firewallRules@2024-11-01-preview' = {
  parent: servers_sqlserver_bellevue_grp3_name_resource
  name: 'query-editor-39dec6'
  properties: {
    startIpAddress: '153.109.1.93'
    endIpAddress: '153.109.1.93'
  }
}

resource servers_sqlserver_bellevue_grp3_name_QueryEditorClientIPAddress_1776338955323 'Microsoft.Sql/servers/firewallRules@2024-11-01-preview' = {
  parent: servers_sqlserver_bellevue_grp3_name_resource
  name: 'QueryEditorClientIPAddress_1776338955323'
  properties: {
    startIpAddress: '153.109.68.124'
    endIpAddress: '153.109.68.124'
  }
}

resource servers_sqlserver_bellevue_grp3_name_Timisoara 'Microsoft.Sql/servers/firewallRules@2024-11-01-preview' = {
  parent: servers_sqlserver_bellevue_grp3_name_resource
  name: 'Timisoara'
  properties: {
    startIpAddress: '85.120.207.252'
    endIpAddress: '85.120.207.252'
  }
}

resource servers_sqlserver_bellevue_grp3_name_ServiceManaged 'Microsoft.Sql/servers/keys@2024-11-01-preview' = {
  parent: servers_sqlserver_bellevue_grp3_name_resource
  name: 'ServiceManaged'
  kind: 'servicemanaged'
  properties: {
    serverKeyType: 'ServiceManaged'
  }
}

resource Microsoft_Sql_servers_securityAlertPolicies_servers_sqlserver_bellevue_grp3_name_Default 'Microsoft.Sql/servers/securityAlertPolicies@2024-11-01-preview' = {
  parent: servers_sqlserver_bellevue_grp3_name_resource
  name: 'Default'
  properties: {
    state: 'Disabled'
    disabledAlerts: [
      ''
    ]
    emailAddresses: [
      ''
    ]
    emailAccountAdmins: false
    retentionDays: 0
  }
}

resource Microsoft_Sql_servers_sqlVulnerabilityAssessments_servers_sqlserver_bellevue_grp3_name_Default 'Microsoft.Sql/servers/sqlVulnerabilityAssessments@2024-11-01-preview' = {
  parent: servers_sqlserver_bellevue_grp3_name_resource
  name: 'Default'
  properties: {
    state: 'Disabled'
  }
}

resource Microsoft_Sql_servers_vulnerabilityAssessments_servers_sqlserver_bellevue_grp3_name_Default 'Microsoft.Sql/servers/vulnerabilityAssessments@2024-11-01-preview' = {
  parent: servers_sqlserver_bellevue_grp3_name_resource
  name: 'Default'
  properties: {
    recurringScans: {
      isEnabled: false
      emailSubscriptionAdmins: true
    }
    storageContainerPath: vulnerabilityAssessments_Default_storageContainerPath
  }
}

resource storageAccounts_adlsbellevuegrp3_name_default 'Microsoft.Storage/storageAccounts/blobServices@2025-06-01' = {
  parent: storageAccounts_adlsbellevuegrp3_name_resource
  name: 'default'
  sku: {
    name: 'Standard_LRS'
    tier: 'Standard'
  }
  properties: {
    containerDeleteRetentionPolicy: {
      enabled: true
      days: 7
    }
    cors: {
      corsRules: []
    }
    deleteRetentionPolicy: {
      allowPermanentDelete: false
      enabled: true
      days: 7
    }
  }
}

resource Microsoft_Storage_storageAccounts_fileServices_storageAccounts_adlsbellevuegrp3_name_default 'Microsoft.Storage/storageAccounts/fileServices@2025-06-01' = {
  parent: storageAccounts_adlsbellevuegrp3_name_resource
  name: 'default'
  sku: {
    name: 'Standard_LRS'
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
      days: 14
    }
  }
}

resource Microsoft_Storage_storageAccounts_queueServices_storageAccounts_adlsbellevuegrp3_name_default 'Microsoft.Storage/storageAccounts/queueServices@2025-06-01' = {
  parent: storageAccounts_adlsbellevuegrp3_name_resource
  name: 'default'
  properties: {
    cors: {
      corsRules: []
    }
  }
}

resource Microsoft_Storage_storageAccounts_tableServices_storageAccounts_adlsbellevuegrp3_name_default 'Microsoft.Storage/storageAccounts/tableServices@2025-06-01' = {
  parent: storageAccounts_adlsbellevuegrp3_name_resource
  name: 'default'
  properties: {
    cors: {
      corsRules: []
    }
  }
}

resource servers_sqlserver_bellevue_grp3_name_DevDB_Default 'Microsoft.Sql/servers/databases/advancedThreatProtectionSettings@2024-11-01-preview' = {
  parent: servers_sqlserver_bellevue_grp3_name_DevDB
  name: 'Default'
  properties: {
    state: 'Disabled'
  }
  dependsOn: [
    servers_sqlserver_bellevue_grp3_name_resource
  ]
}

resource Microsoft_Sql_servers_databases_auditingPolicies_servers_sqlserver_bellevue_grp3_name_DevDB_Default 'Microsoft.Sql/servers/databases/auditingPolicies@2014-04-01' = {
  parent: servers_sqlserver_bellevue_grp3_name_DevDB
  name: 'Default'
  location: 'Switzerland North'
  properties: {
    auditingState: 'Disabled'
  }
  dependsOn: [
    servers_sqlserver_bellevue_grp3_name_resource
  ]
}

resource Microsoft_Sql_servers_databases_auditingSettings_servers_sqlserver_bellevue_grp3_name_DevDB_Default 'Microsoft.Sql/servers/databases/auditingSettings@2024-11-01-preview' = {
  parent: servers_sqlserver_bellevue_grp3_name_DevDB
  name: 'Default'
  properties: {
    retentionDays: 0
    isAzureMonitorTargetEnabled: false
    state: 'Disabled'
    storageAccountSubscriptionId: '00000000-0000-0000-0000-000000000000'
  }
  dependsOn: [
    servers_sqlserver_bellevue_grp3_name_resource
  ]
}

resource Microsoft_Sql_servers_databases_backupLongTermRetentionPolicies_servers_sqlserver_bellevue_grp3_name_DevDB_default 'Microsoft.Sql/servers/databases/backupLongTermRetentionPolicies@2024-11-01-preview' = {
  parent: servers_sqlserver_bellevue_grp3_name_DevDB
  name: 'default'
  properties: {
    timeBasedImmutability: 'Disabled'
    weeklyRetention: 'PT0S'
    monthlyRetention: 'PT0S'
    yearlyRetention: 'PT0S'
    weekOfYear: 0
  }
  dependsOn: [
    servers_sqlserver_bellevue_grp3_name_resource
  ]
}

resource Microsoft_Sql_servers_databases_backupShortTermRetentionPolicies_servers_sqlserver_bellevue_grp3_name_DevDB_default 'Microsoft.Sql/servers/databases/backupShortTermRetentionPolicies@2024-11-01-preview' = {
  parent: servers_sqlserver_bellevue_grp3_name_DevDB
  name: 'default'
  properties: {
    retentionDays: 7
    diffBackupIntervalInHours: 12
  }
  dependsOn: [
    servers_sqlserver_bellevue_grp3_name_resource
  ]
}

resource Microsoft_Sql_servers_databases_extendedAuditingSettings_servers_sqlserver_bellevue_grp3_name_DevDB_Default 'Microsoft.Sql/servers/databases/extendedAuditingSettings@2024-11-01-preview' = {
  parent: servers_sqlserver_bellevue_grp3_name_DevDB
  name: 'Default'
  properties: {
    retentionDays: 0
    isAzureMonitorTargetEnabled: false
    state: 'Disabled'
    storageAccountSubscriptionId: '00000000-0000-0000-0000-000000000000'
  }
  dependsOn: [
    servers_sqlserver_bellevue_grp3_name_resource
  ]
}

resource Microsoft_Sql_servers_databases_geoBackupPolicies_servers_sqlserver_bellevue_grp3_name_DevDB_Default 'Microsoft.Sql/servers/databases/geoBackupPolicies@2024-11-01-preview' = {
  parent: servers_sqlserver_bellevue_grp3_name_DevDB
  name: 'Default'
  properties: {
    state: 'Disabled'
  }
  dependsOn: [
    servers_sqlserver_bellevue_grp3_name_resource
  ]
}

resource servers_sqlserver_bellevue_grp3_name_DevDB_Current 'Microsoft.Sql/servers/databases/ledgerDigestUploads@2024-11-01-preview' = {
  parent: servers_sqlserver_bellevue_grp3_name_DevDB
  name: 'Current'
  properties: {}
  dependsOn: [
    servers_sqlserver_bellevue_grp3_name_resource
  ]
}

resource Microsoft_Sql_servers_databases_securityAlertPolicies_servers_sqlserver_bellevue_grp3_name_DevDB_Default 'Microsoft.Sql/servers/databases/securityAlertPolicies@2024-11-01-preview' = {
  parent: servers_sqlserver_bellevue_grp3_name_DevDB
  name: 'Default'
  properties: {
    state: 'Disabled'
    disabledAlerts: [
      ''
    ]
    emailAddresses: [
      ''
    ]
    emailAccountAdmins: false
    retentionDays: 0
  }
  dependsOn: [
    servers_sqlserver_bellevue_grp3_name_resource
  ]
}

resource Microsoft_Sql_servers_databases_transparentDataEncryption_servers_sqlserver_bellevue_grp3_name_DevDB_Current 'Microsoft.Sql/servers/databases/transparentDataEncryption@2024-11-01-preview' = {
  parent: servers_sqlserver_bellevue_grp3_name_DevDB
  name: 'Current'
  properties: {
    state: 'Enabled'
  }
  dependsOn: [
    servers_sqlserver_bellevue_grp3_name_resource
  ]
}

resource Microsoft_Sql_servers_databases_vulnerabilityAssessments_servers_sqlserver_bellevue_grp3_name_DevDB_Default 'Microsoft.Sql/servers/databases/vulnerabilityAssessments@2024-11-01-preview' = {
  parent: servers_sqlserver_bellevue_grp3_name_DevDB
  name: 'Default'
  properties: {
    recurringScans: {
      isEnabled: false
      emailSubscriptionAdmins: true
    }
  }
  dependsOn: [
    servers_sqlserver_bellevue_grp3_name_resource
  ]
}

resource storageAccounts_adlsbellevuegrp3_name_default_bronze 'Microsoft.Storage/storageAccounts/blobServices/containers@2025-06-01' = {
  parent: storageAccounts_adlsbellevuegrp3_name_default
  name: 'bronze'
  properties: {
    immutableStorageWithVersioning: {
      enabled: false
    }
    defaultEncryptionScope: '$account-encryption-key'
    denyEncryptionScopeOverride: false
    publicAccess: 'None'
  }
  dependsOn: [
    storageAccounts_adlsbellevuegrp3_name_resource
  ]
}

resource storageAccounts_adlsbellevuegrp3_name_default_mldata 'Microsoft.Storage/storageAccounts/blobServices/containers@2025-06-01' = {
  parent: storageAccounts_adlsbellevuegrp3_name_default
  name: 'mldata'
  properties: {
    immutableStorageWithVersioning: {
      enabled: false
    }
    defaultEncryptionScope: '$account-encryption-key'
    denyEncryptionScopeOverride: false
    publicAccess: 'None'
  }
  dependsOn: [
    storageAccounts_adlsbellevuegrp3_name_resource
  ]
}

resource storageAccounts_adlsbellevuegrp3_name_default_sacexport 'Microsoft.Storage/storageAccounts/blobServices/containers@2025-06-01' = {
  parent: storageAccounts_adlsbellevuegrp3_name_default
  name: 'sacexport'
  properties: {
    immutableStorageWithVersioning: {
      enabled: false
    }
    defaultEncryptionScope: '$account-encryption-key'
    denyEncryptionScopeOverride: false
    publicAccess: 'None'
  }
  dependsOn: [
    storageAccounts_adlsbellevuegrp3_name_resource
  ]
}

resource storageAccounts_adlsbellevuegrp3_name_default_silver 'Microsoft.Storage/storageAccounts/blobServices/containers@2025-06-01' = {
  parent: storageAccounts_adlsbellevuegrp3_name_default
  name: 'silver'
  properties: {
    immutableStorageWithVersioning: {
      enabled: false
    }
    defaultEncryptionScope: '$account-encryption-key'
    denyEncryptionScopeOverride: false
    publicAccess: 'None'
  }
  dependsOn: [
    storageAccounts_adlsbellevuegrp3_name_resource
  ]
}

resource storageAccounts_adlsbellevuegrp3_name_default_sac_export_share 'Microsoft.Storage/storageAccounts/fileServices/shares@2025-06-01' = {
  parent: Microsoft_Storage_storageAccounts_fileServices_storageAccounts_adlsbellevuegrp3_name_default
  name: 'sac-export-share'
  properties: {
    accessTier: 'TransactionOptimized'
    shareQuota: 102400
    enabledProtocols: 'SMB'
  }
  dependsOn: [
    storageAccounts_adlsbellevuegrp3_name_resource
  ]
}
