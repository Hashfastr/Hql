// Sigma field names on the left, Azure Monitor / Microsoft Sentinel table columns
// on the right. Importable on their own:
//
//   import maps.azure_fields;
//   database('kusto').raw('SigninLogs | where TimeGenerated > ago(1d)')
//   | map azure_signin
//   | where userAgent contains 'azurehound'
//
// A field that already has the column's name needs no entry, it resolves to the
// column as is. Most of SecurityEvent is like this. Columns are from the Azure
// Monitor Logs table reference:
//   https://learn.microsoft.com/azure/azure-monitor/reference/tables/
//
// Sigma's dotted names are single fields, so they use the bracket form.

// product: azure, service: activitylogs
map azure_activity = {
    // Rules compare against MICROSOFT.NETWORK/DNSZONES/WRITE, the identifier form.
    // OperationName holds the display name.
    operationName: OperationNameValue,
    category: CategoryValue,
    resourceId: ResourceId,
    ['properties.message']: OperationName
};

// product: azure, service: auditlogs
map azure_audit = {
    operationName: OperationName,
    ['properties.message']: OperationName,
    category: Category,
    Status: Result,
    ['properties.result']: Result,
    activityType: ActivityDisplayName,
    ActivityType: ActivityDisplayName,
    failure_status_reason: ResultReason,
    Initiatedby: InitiatedBy,
    Target: TargetResources,
    ['properties.targetResources']: TargetResources,
    ['additionalDetails.additionalInfo']: AdditionalDetails,

    // TargetResources is an array of objects, its members have no single path
    ['TargetResources.modifiedProperties']: TargetResources,
    ['TargetResources.modifiedProperties.newValue']: TargetResources,
    ['TargetResources.ModifiedProperties.NewValue']: TargetResources
};

// product: azure, service: signinlogs. Also fits AADNonInteractiveUserSignInLogs.
map azure_signin = {
    userAgent: UserAgent,
    conditionalAccessStatus: ConditionalAccessStatus,
    ClientApp: ClientAppUsed,
    Username: UserPrincipalName,
    ['properties.message']: AuthenticationProtocol,
    ['DeviceDetail.trusttype']: DeviceDetail.trustType,
    ['DeviceDetail.isCompliant']: DeviceDetail.isCompliant,
    ['DeviceDetail.deviceId']: DeviceDetail.deviceId
};

// product: azure, service: riskdetection
map azure_risk = {
    riskEventType: RiskEventType
};

// product: windows, service: security. Image, ParentImage and User are for
// process_creation over event 4688.
map azure_security_event = {
    Provider_Name: EventSourceName,
    Image: NewProcessName,
    ParentImage: ParentProcessName,
    User: SubjectUserName
};

// Defender's FolderPath columns hold the full path including the file name, so
// they pair with Sysmon's Image and friends despite the name.

// product: windows, category: process_creation
map azure_device_process = {
    Image: FolderPath,
    CommandLine: ProcessCommandLine,
    OriginalFileName: ProcessVersionInfoOriginalFileName,
    Description: ProcessVersionInfoFileDescription,
    Product: ProcessVersionInfoProductName,
    Company: ProcessVersionInfoCompanyName,
    FileVersion: ProcessVersionInfoProductVersion,
    IntegrityLevel: ProcessIntegrityLevel,
    User: AccountName,
    ParentImage: InitiatingProcessFolderPath,
    ParentCommandLine: InitiatingProcessCommandLine,
    ParentProcessId: InitiatingProcessId,
    ParentUser: InitiatingProcessAccountName,
    Computer: DeviceName
};

// product: windows, category: network_connection. In the tables below the process
// is the initiating one, and the parent's column is a file name without a path.
map azure_device_network = {
    Image: InitiatingProcessFolderPath,
    CommandLine: InitiatingProcessCommandLine,
    ParentImage: InitiatingProcessParentFileName,
    ProcessId: InitiatingProcessId,
    User: InitiatingProcessAccountName,
    SourceIp: LocalIP,
    SourcePort: LocalPort,
    SourceHostname: DeviceName,
    DestinationIp: RemoteIP,
    DestinationPort: RemotePort,
    DestinationHostname: RemoteUrl,
    Computer: DeviceName
};

// product: windows, category: file_event and friends
map azure_device_file = {
    TargetFilename: FolderPath,
    Image: InitiatingProcessFolderPath,
    CommandLine: InitiatingProcessCommandLine,
    ParentImage: InitiatingProcessParentFileName,
    ProcessId: InitiatingProcessId,
    User: InitiatingProcessAccountName,
    Computer: DeviceName
};

// product: windows, category: registry_*. Sysmon's TargetObject ends in the value
// name, Defender splits that into RegistryValueName.
map azure_device_registry = {
    TargetObject: RegistryKey,
    NewName: RegistryKey,
    Details: RegistryValueData,
    EventType: ActionType,
    Image: InitiatingProcessFolderPath,
    ProcessId: InitiatingProcessId,
    User: InitiatingProcessAccountName,
    Computer: DeviceName
};

// product: windows, category: image_load. Sysmon's OriginalFileName, Company,
// Product and Description describe the loaded DLL. The table only has version info
// for the initiating process, so pairing them would match the wrong file.
map azure_device_image_load = {
    ImageLoaded: FolderPath,
    Image: InitiatingProcessFolderPath,
    CommandLine: InitiatingProcessCommandLine,
    ProcessId: InitiatingProcessId,
    User: InitiatingProcessAccountName,
    Computer: DeviceName
};
