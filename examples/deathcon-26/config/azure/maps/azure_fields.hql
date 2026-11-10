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
// The time bound is HaC's time window, so a rule's lookback decides it: Log Analytics
// gets it as the query timespan, Kusto as a where on TimeGenerated. A Sigma run looks
// back an hour unless given --lookback. Nothing here bounds time itself, a fixed
// window would cap a longer lookback, so a query without HaC reads every row the
// table keeps. Bound one yourself:
//
//   azure_signin
//   | where TimeGenerated > ago(1h) and userAgent contains 'azurehound'

// Where the tables are queried:
//   'loganalytics'  Log Analytics workspace (Sentinel), fill in loganalytics.yml
//   'kusto'         Azure Data Explorer cluster, fill in kusto.yml
let azure_db = 'loganalytics';

// product: azure, service: activitylogs. Rules compare operationName against
// MICROSOFT.NETWORK/DNSZONES/WRITE, the identifier form, OperationName holds the
// display name.
let azure_activity = database(azure_db).index('AzureActivity')
    | project-rename operationName = OperationNameValue, category = CategoryValue,
        resourceId = ResourceId, ['properties.message'] = OperationName;

// product: azure, service: auditlogs. The dynamic columns become strings, Sigma's
// string matching fails on objects and arrays. A field inside one is then only
// reachable by contains, TargetResources is an array of objects so its members have
// no single path anyway.
//
// Rules name OperationName, Category, ActivityDisplayName and TargetResources both as
// the column and in another case or form, so those are copied, never renamed. A
// renamed column is gone: a where on it can't be pushed, so the whole table comes
// back to be filtered locally, where the field is missing and nothing matches.
//
// targetResources.type is read before TargetResources becomes a string. Role
// assignments list the assignee first, then the role, so it's the first entry's.
let azure_audit = database(azure_db).index('AuditLogs')
    | extend ['targetResources.type'] = tostring(TargetResources[0].type)
    | extend TargetResources = tostring(TargetResources), InitiatedBy = tostring(InitiatedBy),
        AdditionalDetails = tostring(AdditionalDetails)
    | extend ['properties.message'] = OperationName, ['properties.result'] = Result,
        operationName = OperationName, category = Category,
        ActivityType = ActivityDisplayName, activityType = ActivityDisplayName,
        Target = TargetResources, ['properties.targetResources'] = TargetResources,
        ['TargetResources.modifiedProperties'] = TargetResources,
        ['TargetResources.modifiedProperties.newValue'] = TargetResources,
        ['TargetResources.ModifiedProperties.NewValue'] = TargetResources
    | project-rename Status = Result, failure_status_reason = ResultReason,
        Initiatedby = InitiatedBy, ['additionalDetails.additionalInfo'] = AdditionalDetails;

// product: azure, service: signinlogs. Also fits AADNonInteractiveUserSignInLogs.
//   - Status gets the Success rules compare it to, the column itself only holds an
//     error code and failure details. It's set before ResultType is cast.
//   - ResultType becomes an int, as rules write it unquoted.
let azure_signin = database(azure_db).index('SigninLogs')
    | extend Status = iff(ResultType == '0', 'Success', tostring(Status)), ResultType = toint(ResultType)
    | extend ['DeviceDetail.trusttype'] = DeviceDetail.trustType,
        ['DeviceDetail.isCompliant'] = DeviceDetail.isCompliant,
        ['DeviceDetail.deviceId'] = DeviceDetail.deviceId
    | project-rename userAgent = UserAgent, conditionalAccessStatus = ConditionalAccessStatus,
        ClientApp = ClientAppUsed, Username = UserPrincipalName,
        ['properties.message'] = AuthenticationProtocol;

// product: azure, service: riskdetection
let azure_risk = database(azure_db).index('AADUserRiskEvents')
    | project-rename riskEventType = RiskEventType;

// product: windows, service: security. Image, ParentImage and User are for
// process_creation over event 4688.
let azure_security_event = database(azure_db).index('SecurityEvent')
    | project-rename Provider_Name = EventSourceName, Image = NewProcessName,
        ParentImage = ParentProcessName, User = SubjectUserName;

// Defender's FolderPath columns hold the full path including the file name, so
// they pair with Sysmon's Image and friends despite the name.

// product: windows, category: process_creation
let azure_device_process = database(azure_db).index('DeviceProcessEvents')
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
    | extend SourceHostname = DeviceName
    | project-rename Image = InitiatingProcessFolderPath, CommandLine = InitiatingProcessCommandLine,
        ParentImage = InitiatingProcessParentFileName, ProcessId = InitiatingProcessId,
        User = InitiatingProcessAccountName, SourceIp = LocalIP, SourcePort = LocalPort,
        DestinationIp = RemoteIP, DestinationPort = RemotePort, DestinationHostname = RemoteUrl,
        Computer = DeviceName;

// product: windows, category: file_event and friends
let azure_device_file = database(azure_db).index('DeviceFileEvents')
    | project-rename TargetFilename = FolderPath, Image = InitiatingProcessFolderPath,
        CommandLine = InitiatingProcessCommandLine, ParentImage = InitiatingProcessParentFileName,
        ProcessId = InitiatingProcessId, User = InitiatingProcessAccountName, Computer = DeviceName;

// product: windows, category: registry_*. Sysmon's TargetObject ends in the value
// name, Defender splits that into RegistryValueName. ActionType becomes EventType.
let azure_device_registry = database(azure_db).index('DeviceRegistryEvents')
    | extend NewName = RegistryKey
    | project-rename TargetObject = RegistryKey, Details = RegistryValueData, EventType = ActionType,
        Image = InitiatingProcessFolderPath, ProcessId = InitiatingProcessId,
        User = InitiatingProcessAccountName, Computer = DeviceName;

// product: windows, category: image_load. Sysmon's OriginalFileName, Company,
// Product and Description describe the loaded DLL. The table only has version info
// for the initiating process, so pairing them would match the wrong file.
let azure_device_image_load = database(azure_db).index('DeviceImageLoadEvents')
    | project-rename ImageLoaded = FolderPath, Image = InitiatingProcessFolderPath,
        CommandLine = InitiatingProcessCommandLine, ProcessId = InitiatingProcessId,
        User = InitiatingProcessAccountName, Computer = DeviceName;
