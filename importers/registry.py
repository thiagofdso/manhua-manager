from typing import Optional
from importers.base import BaseDomainImporter
from importers.asurascans import AsurascansImporter
from importers.ravenscans import RavenscansImporter
from importers.comix import ComixImporter
from importers.manhuaus import ManhuausImporter
from importers.arenascan import ArenascanImporter
from importers.manhuatop import ManhuatopImporter
from importers.mgeko import MgekoImporter
from importers.mangak import MangakImporter
from importers.mangafire import MangafireImporter

DOMAINS_CATALOG = [
    {"domain": "asurascans.com", "name": "Asura Scans", "supported": True},
    {"domain": "ravenscans.org", "name": "RavenScans", "supported": True},
    {"domain": "comix.to", "name": "Comix", "supported": True},
    {"domain": "manhuaus.com", "name": "ManhuaUS", "supported": True},
    {"domain": "arenascan.com", "name": "ArenaScan", "supported": True},
    {"domain": "manhuatop.org", "name": "ManhuaTop", "supported": True},
    {"domain": "mgeko.cc", "name": "MGeko", "supported": True},
    {"domain": "mangak.io", "name": "MangaK", "supported": True},
    {"domain": "mangafire.to", "name": "MangaFire", "supported": True},
    {"domain": "levelingwithgods.com", "name": "Leveling with Gods", "supported": False},
    {"domain": "pickmeupgacha.com", "name": "Pick Me Up Gacha", "supported": False},
    {"domain": "magicemperor.online", "name": "Magic Emperor", "supported": False},
]

_IMPORTERS = {
    "asurascans.com": AsurascansImporter(),
    "ravenscans.org": RavenscansImporter(),
    "comix.to": ComixImporter(),
    "manhuaus.com": ManhuausImporter(),
    "arenascan.com": ArenascanImporter(),
    "manhuatop.org": ManhuatopImporter(),
    "mgeko.cc": MgekoImporter(),
    "mangak.io": MangakImporter(),
    "mangafire.to": MangafireImporter(),
}

def get_registered_domains() -> list[dict]:
    return DOMAINS_CATALOG

def get_importer(domain: str) -> Optional[BaseDomainImporter]:
    clean_domain = domain.lower().replace("www.", "").strip()
    return _IMPORTERS.get(clean_domain)
