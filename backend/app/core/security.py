"""
Job Operating System - Core Security & Hardening Utilities
Enforces SSRF prevention, URL validation, and input sanitization.
"""
import ipaddress
import socket
import urllib.parse
from typing import Tuple, Optional


# Disallowed IPv4/IPv6 networks for external requests
BLOCKED_IP_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),       # Loopback
    ipaddress.ip_network("10.0.0.0/8"),        # RFC 1918 Private
    ipaddress.ip_network("172.16.0.0/12"),     # RFC 1918 Private
    ipaddress.ip_network("192.168.0.0/16"),    # RFC 1918 Private
    ipaddress.ip_network("169.254.0.0/16"),    # Link-local / Cloud metadata
    ipaddress.ip_network("0.0.0.0/8"),         # Broadcast / Current network
    ipaddress.ip_network("100.64.0.0/10"),     # Carrier-grade NAT
    ipaddress.ip_network("192.0.0.0/24"),      # IETF Protocol Assignments
    ipaddress.ip_network("192.0.2.0/24"),      # TEST-NET-1
    ipaddress.ip_network("198.51.100.0/24"),   # TEST-NET-2
    ipaddress.ip_network("203.0.113.0/24"),    # TEST-NET-3
    ipaddress.ip_network("224.0.0.0/4"),       # Multicast
    ipaddress.ip_network("240.0.0.0/4"),       # Reserved
    ipaddress.ip_network("255.255.255.255/32"),# Broadcast
    ipaddress.ip_network("::1/128"),           # IPv6 Loopback
    ipaddress.ip_network("fc00::/7"),          # IPv6 Unique Local Address
    ipaddress.ip_network("fe80::/10"),         # IPv6 Link-local
    ipaddress.ip_network("::/128"),            # IPv6 Unspecified
]


def is_ip_blocked(ip_obj: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Checks if IP belongs to any private, loopback, or reserved network."""
    if ip_obj.is_loopback or ip_obj.is_private or ip_obj.is_link_local or ip_obj.is_multicast or ip_obj.is_reserved:
        return True
    for net in BLOCKED_IP_NETWORKS:
        if ip_obj in net:
            return True
    return False


def is_safe_external_url(url: Optional[str]) -> Tuple[bool, str]:
    """
    Validates whether an external URL is safe to fetch or navigate to.
    Rejects:
      - None or empty URLs
      - Non-http/https schemes (e.g. file://, gopher://, ftp://, javascript:, data:)
      - Localhost, 127.0.0.1, 0.0.0.0, [::1], and internal domain names (.local, .internal, .localhost)
      - Hostnames resolving to private/loopback/cloud metadata IP addresses
    Returns:
      (True, "Safe") if the URL is a valid public web destination.
      (False, reason_str) if the URL is blocked by security policy.
    """
    if not url or not isinstance(url, str) or not url.strip():
        return False, "URL is empty or missing."

    url = url.strip()
    try:
        parsed = urllib.parse.urlsplit(url)
    except Exception as e:
        return False, f"Malformed URL: {e}"

    # 1. Scheme Check
    if parsed.scheme.lower() not in ("http", "https"):
        return False, f"Disallowed URL scheme '{parsed.scheme}'. Only http and https are permitted."

    hostname = parsed.hostname
    if not hostname:
        return False, "URL hostname is missing."

    hostname_lower = hostname.lower()

    # 2. Hostname Literal Checks
    if hostname_lower in ("localhost", "127.0.0.1", "0.0.0.0", "::1", "metadata.google.internal"):
        return False, f"Direct access to internal/loopback host '{hostname}' is blocked."

    if any(hostname_lower.endswith(suffix) for suffix in (".localhost", ".local", ".internal", ".corp", ".lan", ".home")):
        return False, f"Access to private/internal domain '{hostname}' is blocked."

    # 3. If hostname is already an IP address
    try:
        ip_addr = ipaddress.ip_address(hostname)
        if is_ip_blocked(ip_addr):
            return False, f"Access to private/loopback IP '{hostname}' is blocked by SSRF policy."
        return True, "Safe"
    except ValueError:
        # Not a raw IP literal, proceed to DNS resolution
        pass

    # 4. DNS Resolution & Resolved IP Check
    try:
        # Resolve all addresses (IPv4 & IPv6)
        addr_info = socket.getaddrinfo(hostname, None)
        resolved_ips = set()
        for family, _, _, _, sockaddr in addr_info:
            ip_str = sockaddr[0]
            resolved_ips.add(ip_str)

        if not resolved_ips:
            return False, f"Could not resolve hostname '{hostname}'."

        for ip_str in resolved_ips:
            try:
                ip_obj = ipaddress.ip_address(ip_str)
                if is_ip_blocked(ip_obj):
                    return False, f"Hostname '{hostname}' resolves to private/blocked IP '{ip_str}'."
            except ValueError:
                return False, f"Invalid resolved IP address: '{ip_str}'."

    except socket.gaierror:
        # DNS resolution failure: safe to allow caller to handle as unreachable or reject
        return False, f"DNS resolution failed for hostname '{hostname}'."
    except Exception as e:
        return False, f"SSRF resolution check failed: {e}"

    return True, "Safe"


def sanitize_filename(filename: str) -> str:
    """Strips path traversal components and returns safe basename."""
    import re
    if not filename:
        return "unnamed_file"
    clean = filename.replace("\\", "/").split("/")[-1]
    clean = re.sub(r'[\x00-\x1f\x7f]', '', clean).strip()
    return clean or "unnamed_file"


def is_safe_storage_path(file_path: str, allow_default_downloads: bool = False) -> Tuple[bool, str]:
    """
    Validates that a file path resides strictly inside authorized storage directories on F: drive.
    Rejects:
      - Path traversal patterns ('..', '%2e%2e')
      - Paths outside F: storage or project workspace
      - Windows system directories (C:\\Windows, etc.)
    """
    from pathlib import Path
    from app.core.config import settings

    if not file_path or not isinstance(file_path, str) or not file_path.strip():
        return False, "File path is empty."

    if ".." in file_path or "%2e%2e" in file_path.lower():
        return False, "Path traversal sequence ('..') detected."

    try:
        resolved = Path(file_path).resolve()
    except Exception as e:
        return False, f"Invalid path syntax: {e}"

    allowed_roots = [
        Path(settings.STORAGE_DIR).resolve(),
        Path(settings.DOCUMENTS_DIR).resolve(),
        Path(settings.WORKSPACE_ROOT).resolve(),
    ]
    if allow_default_downloads:
        allowed_roots.append(Path(r"C:\Users\Admin\Downloads").resolve())

    for root in allowed_roots:
        try:
            resolved.relative_to(root)
            return True, "Safe"
        except ValueError:
            continue

    return False, f"Access denied: Path '{resolved}' is outside authorized storage roots."


def validate_pdf_bytes(content: bytes, max_size_mb: int = 10) -> Tuple[bool, str]:
    """
    Validates PDF file content:
      - Non-empty
      - Maximum size limit (default 10MB)
      - PDF magic header bytes (%PDF-)
    """
    if not content or len(content) == 0:
        return False, "File content is empty."

    max_bytes = max_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        return False, f"File size exceeds maximum allowed limit of {max_size_mb} MB."

    if not content.startswith(b"%PDF-"):
        return False, "Invalid file format: File header must start with '%PDF-'."

    return True, "Safe"

