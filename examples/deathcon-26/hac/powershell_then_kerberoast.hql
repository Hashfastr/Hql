/**
 * @title Encoded PowerShell Followed By Kerberoasting From The Same Host
 * @id e0100ccb-d327-4d3c-a8ea-626e28008700
 * @author Florian Roth (Nextron Systems), Markus Neis, Jonhnathan Ribeiro, Daniil Yugoslavskiy, Anton Kutepov, oscd.community, @kostastsale (Sigma rules), DEATHCon 2026 (HaC)
 * 
 * @status experimental
 * @level high
 * @schedule 0 * * * *
 * @description
 * Joins encoded PowerShell (Elastic) with RC4 Kerberos service ticket
 * requests (Splunk) from the same client IP. Each half is a SigmaHQ rule;
 * the cross-database join is the part Sigma can't express.
 * 
 * @tags
 * - attack.execution
 * - attack.t1059.001
 * - attack.credential-access
 * - attack.t1558.003
 * 
 * @references
 * - https://github.com/SigmaHQ/sigma/blob/master/rules/windows/process_creation/proc_creation_win_powershell_base64_encoded_cmd.yml
 * - https://github.com/SigmaHQ/sigma/blob/master/rules/windows/builtin/security/win_security_kerberoasting_activity.yml
 * 
 * @license DRL 1.1 https://github.com/SigmaHQ/Detection-Rule-License
 */
import maps.sources;

// Elastic: SigmaHQ ca2092a1 (Encoded PowerShell), condensed: the -ENCOD / reversed branch is dropped
let encoded_powershell = product('windows').category('process_creation')
| where Image endswith @'\powershell.exe' or Image endswith @'\pwsh.exe' or OriginalFileName in ('PowerShell.EXE', 'pwsh.dll')
| where CommandLine contains ' -e' and CommandLine contains_any (' JAB', ' SUVYI', ' SQBFAFgA', ' aQBlAHgA', ' aWV4I', ' IAA', ' IAB', ' UwB', ' cwB')
| where not(CommandLine contains ' -ExecutionPolicy remotesigned ');

// Splunk: SigmaHQ d04ae2b8 (Kerberoasting)
let kerberoasting = product('windows').service('security')
| where EventID == 4769 and Status == '0x0' and TicketEncryptionType == '0x17'
| where not((ServiceName endswith 'krbtgt' or ServiceName endswith '$') and TargetUserName contains '$@');

encoded_powershell
| project Computer, User, CommandLine, ClientIp = host.ip
| join (
    kerberoasting
    | project ClientIp = IpAddress, ServiceName
    | summarize Services = make_list(ServiceName), Requests = count() by ClientIp
  ) on ClientIp
