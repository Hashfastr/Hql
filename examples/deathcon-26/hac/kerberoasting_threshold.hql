/**
 * @title Kerberoasting - Many RC4 Service Tickets From One Client
 * @id 412b2de1-7911-4e1f-ae6c-53500621c67a
 * @author @kostastsale (Sigma rule), DEATHCon 2026 (HaC)
 * 
 * @status experimental
 * @level high
 * @schedule 0,15,30,45 * * * *
 * @description
 * SigmaHQ d04ae2b8 collects RC4 service ticket requests and says a threshold
 * on requests per client is needed to turn it into an alert. Sigma can't
 * express that; this adds it.
 * 
 * @tags
 * - attack.credential-access
 * - attack.t1558.003
 * 
 * @triage
 * Check whether the client IP and account normally request these services.
 * Several RC4 tickets for different SPNs in a short burst from one user is
 * typical of Rubeus/GetUserSPNs. Look at that host for the tool that ran.
 * 
 * @references
 * - https://github.com/SigmaHQ/sigma/blob/master/rules/windows/builtin/security/win_security_kerberoasting_activity.yml
 * 
 * @license DRL 1.1 https://github.com/SigmaHQ/Detection-Rule-License
 * 
 * @changelog
 * - 2026-11-02 Converted from SigmaHQ d04ae2b8 and added threshold
 */
import maps.sources;

let threshold = 3;
product('windows').service('security')
| where EventID == 4769 and Status == '0x0' and TicketEncryptionType == '0x17'
| where not((ServiceName endswith 'krbtgt' or ServiceName endswith '$') and TargetUserName contains '$@')
| summarize Requests = count(), Services = make_list(ServiceName) by IpAddress, TargetUserName
| where Requests >= threshold
