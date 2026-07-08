from typing import Any, Dict, List
from lxml import etree

SEVERITY_BY_PORT = {
    21: ("high", "FTP open — often misconfigured, supports anonymous login"),
    22: ("info", "SSH service detected"),
    23: ("high", "Telnet open — credentials transmitted in plaintext"),
    25: ("medium", "SMTP open — potential relay or info disclosure"),
    53: ("info", "DNS service detected"),
    80: ("info", "HTTP web server"),
    443: ("info", "HTTPS web server"),
    445: ("high", "SMB open — potential for EternalBlue, relay attacks"),
    1433: ("high", "MSSQL exposed — potential for SQL injection, brute force"),
    1521: ("high", "Oracle DB exposed"),
    3306: ("high", "MySQL exposed — should not be internet-facing"),
    3389: ("high", "RDP open — brute force and BlueKeep risk"),
    5432: ("high", "PostgreSQL exposed"),
    6379: ("high", "Redis exposed — often unauthenticated"),
    8080: ("medium", "HTTP alternate port — may expose admin panels"),
    8443: ("medium", "HTTPS alternate port"),
    27017: ("high", "MongoDB exposed — often unauthenticated"),
}


def parse_nmap_xml(xml_path: str, target: str) -> List[Dict[str, Any]]:
    findings = []
    try:
        tree = etree.parse(xml_path)
    except Exception:
        return findings

    root = tree.getroot()

    for host in root.findall("host"):
        address_el = host.find("address")
        ip = address_el.get("addr") if address_el is not None else target

        hostname_el = host.find("hostnames/hostname")
        hostname = hostname_el.get("name") if hostname_el is not None else ""

        os_el = host.find("os/osmatch")
        if os_el is not None:
            findings.append({
                "title": f"OS Detection: {os_el.get('name', 'Unknown')}",
                "severity": "info",
                "description": f"OS fingerprint: {os_el.get('name')} (accuracy {os_el.get('accuracy')}%)",
                "evidence": {"ip": ip, "os": os_el.get("name"), "accuracy": os_el.get("accuracy")},
                "mitre_technique": "T1082",
            })

        ports_el = host.find("ports")
        if ports_el is None:
            continue

        for port_el in ports_el.findall("port"):
            state_el = port_el.find("state")
            if state_el is None or state_el.get("state") != "open":
                continue

            portid = int(port_el.get("portid", 0))
            protocol = port_el.get("protocol", "tcp")

            service_el = port_el.find("service")
            service_name = service_el.get("name", "unknown") if service_el is not None else "unknown"
            service_version = ""
            if service_el is not None:
                product = service_el.get("product", "")
                version = service_el.get("version", "")
                extrainfo = service_el.get("extrainfo", "")
                service_version = " ".join(filter(None, [product, version, extrainfo])).strip()

            severity, description = SEVERITY_BY_PORT.get(portid, ("info", f"{service_name} service"))

            findings.append({
                "title": f"Open Port {portid}/{protocol} — {service_name}",
                "severity": severity,
                "description": description + (f" ({service_version})" if service_version else ""),
                "evidence": {
                    "ip": ip,
                    "hostname": hostname,
                    "port": portid,
                    "protocol": protocol,
                    "service": service_name,
                    "version": service_version,
                },
                "mitre_technique": "T1046",
            })

            for script_el in port_el.findall("script"):
                script_id = script_el.get("id", "")
                script_output = script_el.get("output", "")

                vuln_severity = "medium"
                if any(kw in script_output.lower() for kw in ["vulnerable", "exploit", "cve-"]):
                    vuln_severity = "high"

                if script_id and script_output:
                    findings.append({
                        "title": f"NSE Script: {script_id} on {portid}/{protocol}",
                        "severity": vuln_severity,
                        "description": script_output[:1000],
                        "evidence": {
                            "ip": ip,
                            "port": portid,
                            "script": script_id,
                            "output": script_output[:2000],
                        },
                        "mitre_technique": "T1046",
                    })

    return findings
