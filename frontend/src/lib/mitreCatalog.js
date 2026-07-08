// ATT&CK technique catalog — mirrors backend/services/mitre.py TECHNIQUES.
// Used to lay out the coverage matrix (including tactics/techniques not yet observed).

export const TACTIC_ORDER = [
  'Reconnaissance',
  'Resource Development',
  'Initial Access',
  'Execution',
  'Credential Access',
  'Discovery',
  'Lateral Movement',
  'Collection',
  'Command and Control',
]

export const TECHNIQUES = {
  'T1595':     { name: 'Active Scanning',                 tactic: 'Reconnaissance' },
  'T1595.002': { name: 'Vulnerability Scanning',          tactic: 'Reconnaissance' },
  'T1590':     { name: 'Gather Victim Network Info',      tactic: 'Reconnaissance' },
  'T1596':     { name: 'Search Open Technical Databases', tactic: 'Reconnaissance' },
  'T1593.003': { name: 'Search Code Repositories',        tactic: 'Reconnaissance' },
  'T1584':     { name: 'Compromise Infrastructure',       tactic: 'Resource Development' },
  'T1190':     { name: 'Exploit Public-Facing App',       tactic: 'Initial Access' },
  'T1078':     { name: 'Valid Accounts',                  tactic: 'Initial Access' },
  'T1059.007': { name: 'JavaScript / XSS',                tactic: 'Execution' },
  'T1552':     { name: 'Unsecured Credentials',           tactic: 'Credential Access' },
  'T1552.001': { name: 'Credentials In Files',            tactic: 'Credential Access' },
  'T1110':     { name: 'Brute Force',                     tactic: 'Credential Access' },
  'T1046':     { name: 'Network Service Discovery',       tactic: 'Discovery' },
  'T1083':     { name: 'File & Directory Discovery',      tactic: 'Discovery' },
  'T1210':     { name: 'Exploitation of Remote Services', tactic: 'Lateral Movement' },
  'T1557':     { name: 'Adversary-in-the-Middle',         tactic: 'Collection' },
  'T1213.003': { name: 'Data from Code Repositories',     tactic: 'Collection' },
  'T1071.001': { name: 'Application Layer Protocol: Web', tactic: 'Command and Control' },
}

// { tactic: [techniqueId, ...] } in catalog order
export function techniquesByTactic() {
  const out = {}
  for (const tactic of TACTIC_ORDER) out[tactic] = []
  for (const [id, meta] of Object.entries(TECHNIQUES)) {
    if (out[meta.tactic]) out[meta.tactic].push(id)
  }
  return out
}

export const attackUrl = (id) =>
  `https://attack.mitre.org/techniques/${id.replace('.', '/')}/`
