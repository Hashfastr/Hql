// Sigma field names on the left, the names in our data on the right.

// ECS process events (Elastic Defend / Elastic Agent)
map ecs_proc = {
    Image: process.executable,
    CommandLine: process.command_line,
    OriginalFileName: process.pe.original_file_name,
    ParentImage: process.parent.executable,
    User: user.name,
    Computer: host.name
};

// Splunk Add-on for Microsoft Windows, Security event log
map splunk_sec = {
    EventID: EventCode,
    Status: Failure_Code,
    TicketEncryptionType: Ticket_Encryption_Type,
    ServiceName: Service_Name,
    TargetUserName: Account_Name,
    IpAddress: Client_Address,
    Computer: host
};
