import base64

# A simple XOR key for basic obfuscation to prevent plain text extraction from the built binary
_KEY = b"cliptzy_secret_obfuscation_key_2026"


def obfuscate(data: str) -> str:
    """
    Obfuscate string data using XOR cipher and Base64 encoding.

    Args:
        data: The plain text string to obfuscate.

    Returns:
        The obfuscated Base64-encoded string.
    """
    if not data:
        return ""
    data_bytes = data.encode("utf-8")
    obfuscated = bytearray()
    for i, b in enumerate(data_bytes):
        obfuscated.append(b ^ _KEY[i % len(_KEY)])
    return base64.b64encode(obfuscated).decode("utf-8")


def deobfuscate(data: str) -> str:
    """
    Deobfuscate string data previously obfuscated using XOR cipher and Base64 encoding.

    Args:
        data: The obfuscated Base64-encoded string.

    Returns:
        The plain text string, or empty string on failure.
    """
    if not data:
        return ""
    try:
        obfuscated = base64.b64decode(data.encode("utf-8"))
        deobfuscated = bytearray()
        for i, b in enumerate(obfuscated):
            deobfuscated.append(b ^ _KEY[i % len(_KEY)])
        return deobfuscated.decode("utf-8")
    except Exception:
        return ""
