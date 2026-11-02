/**
 * @title Kerberoasting Activity - Initial Query
 * @author @kostastsale
 * @id d04ae2b8-ad54-4de0-bd87-4bc1da66aa59
 * 
 * @status test
 * @level medium
 * @schedule 0 * * * *
 * @description
 * This rule will collect the data needed to start looking into possible kerberoasting activity.
 * Further analysis or computation within the query is needed focusing on requests from one specific host/IP towards multiple service names within a time period of 5 seconds.
 * You can then set a threshold for the number of requests and time between the requests to turn this into an alert.
 * 
 * @tags
 * - attack.credential-access
 * - attack.t1558.003
 * 
 * @falsepositives
 * - Legacy applications.
 * 
 * @references
 * - https://www.trustedsec.com/blog/art_of_kerberoast/
 * - https://adsecurity.org/?p=3513
 * 
 * @license DRL 1.1 https://github.com/SigmaHQ/Detection-Rule-License
 * @date 2022-01-21
 */
import maps.sources;
product('windows').service('security')
| where EventID == 4769 and TicketEncryptionType == @'0x17' and Status == @'0x0' and not((ServiceName endswith @'krbtgt' or ServiceName endswith @'$') and TargetUserName contains @'$@')
