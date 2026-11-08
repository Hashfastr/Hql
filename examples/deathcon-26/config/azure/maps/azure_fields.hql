// Azure Monitor / Microsoft Sentinel tables with Sigma field names. Importable on
// their own:
//
//   import maps.azure_fields;
//   azure_signin
//   | where userAgent contains 'azurehound'
//
// Every operator here is pushed to the database, as is a where after it. A field
// that already has the column's name needs no rename, it resolves to the column as
// is. Most of SecurityEvent is like this. Columns are from the Azure Monitor Logs
// table reference:
//   https://learn.microsoft.com/azure/azure-monitor/reference/tables/
//
// Sigma's dotted names are single fields, so they use the bracket form. The
// project-rename moves a column to its Sigma name, a column with more than one
// Sigma name, or a Sigma name for a field inside a dynamic column, is copied with
// an extend before it.
//
// The time bound is a where on TimeGenerated. HaC's time window is also sent as the
// query timespan for Log Analytics, Kusto has no equivalent for a table.

// Where the tables are queried:
//   'loganalytics'  Log Analytics workspace (Sentinel), fill in loganalytics.yml
//   'kusto'         Azure Data Explorer cluster, fill in kusto.yml
let azure_db = 'loganalytics';

// product: azure, service: activitylogs. Rules compare operationName against
// MICROSOFT.NETWORK/DNSZONES/WRITE, the identifier form, OperationName holds the
// display name.
let azure_activity = database(azure_db).index('AzureActivity')
    | where TimeGenerated > ago(1d)
    | project-rename operationName = OperationNameValue, category = CategoryValue,
        resourceId = ResourceId, ['properties.message'] = OperationName;

// product: azure, service: auditlogs. The dynamic columns become strings, Sigma's
// string matching fails on objects and arrays. A field inside one is then only
// reachable by contains, TargetResources is an array of objects so its members have
// no single path anyway.
let azure_audit = database(azure_db).index('AuditLogs')
    | where TimeGenerated > ago(1d)
    | extend TargetResources = tostring(TargetResources), InitiatedBy = tostring(InitiatedBy),
        AdditionalDetails = tostring(AdditionalDetails)
    | extend ['properties.message'] = OperationName, ['properties.result'] = Result,
        ActivityType = ActivityDisplayName, ['properties.targetResources'] = TargetResources,
        ['TargetResources.modifiedProperties'] = TargetResources,
        ['TargetResources.modifiedProperties.newValue'] = TargetResources,
        ['TargetResources.ModifiedProperties.NewValue'] = TargetResources
    | project-rename operationName = OperationName, category = Category, Status = Result,
        activityType = ActivityDisplayName, failure_status_reason = ResultReason,
        Initiatedby = InitiatedBy, Target = TargetResources,
        ['additionalDetails.additionalInfo'] = AdditionalDetails;

// product: azure, service: signinlogs. Also fits AADNonInteractiveUserSignInLogs.
//   - Status gets the Success rules compare it to, the column itself only holds an
//     error code and failure details. It's set before ResultType is cast.
//   - ResultType becomes an int, as rules write it unquoted.
let azure_signin = database(azure_db).index('SigninLogs')
    | where TimeGenerated > ago(1d)
    | extend Status = iff(ResultType == '0', 'Success', tostring(Status)), ResultType = toint(ResultType)
    | extend ['DeviceDetail.trusttype'] = DeviceDetail.trustType,
        ['DeviceDetail.isCompliant'] = DeviceDetail.isCompliant,
        ['DeviceDetail.deviceId'] = DeviceDetail.deviceId
    | project-rename userAgent = UserAgent, conditionalAccessStatus = ConditionalAccessStatus,
        ClientApp = ClientAppUsed, Username = UserPrincipalName,
        ['properties.message'] = AuthenticationProtocol;

// product: azure, service: riskdetection
let azure_risk = database(azure_db).index('AADUserRiskEvents')
    | where TimeGenerated > ago(1d)
    | project-rename riskEventType = RiskEventType;

// product: windows, service: security. Image, ParentImage and User are for
// process_creation over event 4688.
let azure_security_event = database(azure_db).index('SecurityEvent')
    | where TimeGenerated > ago(1d)
    | project-rename Provider_Name = EventSourceName, Image = NewProcessName,
        ParentImage = ParentProcessName, User = SubjectUserName;

// Defender's FolderPath columns hold the full path including the file name, so
// they pair with Sysmon's Image and friends despite the name.

// product: windows, category: process_creation
let azure_device_process = database(azure_db).index('DeviceProcessEvents')
    | where TimeGenerated > ago(1d)
    | project-rename Image = FolderPath, CommandLine = ProcessCommandLine,
        OriginalFileName = ProcessVersionInfoOriginalFileName,
        Description = ProcessVersionInfoFileDescription, Product = ProcessVersionInfoProductName,
        Company = ProcessVersionInfoCompanyName, FileVersion = ProcessVersionInfoProductVersion,
        IntegrityLevel = ProcessIntegrityLevel, User = AccountName,
        ParentImage = InitiatingProcessFolderPath, ParentCommandLine = InitiatingProcessCommandLine,
        ParentProcessId = InitiatingProcessId, ParentUser = InitiatingProcessAccountName,
        Computer = DeviceName;

// product: windows, category: network_connection. In the tables below the process
// is the initiating one, and the parent's column is a file name without a path.
let azure_device_network = database(azure_db).index('DeviceNetworkEvents')
    | where TimeGenerated > ago(1d)
    | extend SourceHostname = DeviceName
    | project-rename Image = InitiatingProcessFolderPath, CommandLine = InitiatingProcessCommandLine,
        ParentImage = InitiatingProcessParentFileName, ProcessId = InitiatingProcessId,
        User = InitiatingProcessAccountName, SourceIp = LocalIP, SourcePort = LocalPort,
        DestinationIp = RemoteIP, DestinationPort = RemotePort, DestinationHostname = RemoteUrl,
        Computer = DeviceName;

// product: windows, category: file_event and friends
let azure_device_file = database(azure_db).index('DeviceFileEvents')
    | where TimeGenerated > ago(1d)
    | project-rename TargetFilename = FolderPath, Image = InitiatingProcessFolderPath,
        CommandLine = InitiatingProcessCommandLine, ParentImage = InitiatingProcessParentFileName,
        ProcessId = InitiatingProcessId, User = InitiatingProcessAccountName, Computer = DeviceName;

// product: windows, category: registry_*. Sysmon's TargetObject ends in the value
// name, Defender splits that into RegistryValueName. ActionType becomes EventType.
let azure_device_registry = database(azure_db).index('DeviceRegistryEvents')
    | where TimeGenerated > ago(1d)
    | extend NewName = RegistryKey
    | project-rename TargetObject = RegistryKey, Details = RegistryValueData, EventType = ActionType,
        Image = InitiatingProcessFolderPath, ProcessId = InitiatingProcessId,
        User = InitiatingProcessAccountName, Computer = DeviceName;

// product: windows, category: image_load. Sysmon's OriginalFileName, Company,
// Product and Description describe the loaded DLL. The table only has version info
// for the initiating process, so pairing them would match the wrong file.
let azure_device_image_load = database(azure_db).index('DeviceImageLoadEvents')
    | where TimeGenerated > ago(1d)
    | project-rename ImageLoaded = FolderPath, Image = InitiatingProcessFolderPath,
        CommandLine = InitiatingProcessCommandLine, ProcessId = InitiatingProcessId,
        User = InitiatingProcessAccountName, Computer = DeviceName;
