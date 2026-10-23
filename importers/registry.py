from typing import Optional
from importers.base import BaseDomainImporter
from importers.asurascans import AsurascansImporter

DOMAINS_CATALOG = [
    {"domain": "asurascans.com", "name": "Asura Scans", "supported": True},
    {"domain": "mangafire.to", "name": "MangaFire", "supported": False},
    {"domain": "comix.to", "name": "Comix", "supported": False},
    {"domain": "manhuaus.com", "name": "ManhuaUS", "supported": False},
    {"domain": "manhuatop.org", "name": "ManhuaTop", "supported": False},
    {"domain": "ravenscans.org", "name": "RavenScans", "supported": False},
    {"domain": "arenascan.com", "name": "ArenaScan", "supported": False},
    {"domain": "mgeko.cc", "name": "MGeko", "supported": False},
    {"domain": "levelingwithgods.com", "name": "Leveling with Gods", "supported": False},
    {"domain": "pickmeupgacha.com", "name": "Pick Me Up Gacha", "supported": False},
    {"domain": "magicemperor.online", "name": "Magic Emperor", "supported": False},
]

_IMPORTERS = {
    "asurascans.com": AsurascansImporter()
}

def get_registered_domains() -> list[dict]:
    return DOMAINS_CATALOG

def get_importer(domain: str) -> Optional[BaseDomainImporter]:
    clean_domain = domain.lower().replace("www.", "").strip()
    return _IMPORTERS.get(clean_domain)
