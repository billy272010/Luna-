"""
Contrôle direct d'iPhone via pymobiledevice3 (connexion USB ou WiFi).
Fonctionnalités : infos appareil, batterie, capture d'écran, liste d'apps.

Installation : pip install pymobiledevice3
"""

from pathlib import Path
from typing import Optional

# Import optionnel — fonctionne sans si non installé
try:
    from pymobiledevice3.lockdown import create_using_usbmux
    from pymobiledevice3.services.screenshot import ScreenshotService
    from pymobiledevice3.services.installation_proxy import InstallationProxyService
    from pymobiledevice3.services.diagnostics import DiagnosticsService
    from pymobiledevice3.services.dvt.instruments.device_info import DeviceInfo
    _PMD3_AVAILABLE = True
except ImportError:
    _PMD3_AVAILABLE = False

SCREENSHOTS_DIR = Path(__file__).parent.parent / "data" / "screenshots"


def is_available() -> bool:
    return _PMD3_AVAILABLE


def _connect(udid: str = None):
    """Connexion au premier iPhone trouvé ou au UDID précisé."""
    if not _PMD3_AVAILABLE:
        raise RuntimeError("pymobiledevice3 non installé (pip install pymobiledevice3)")
    return create_using_usbmux(serial=udid)


def list_connected_devices() -> list[dict]:
    """Retourne la liste des iPhones connectés en USB."""
    if not _PMD3_AVAILABLE:
        return []
    try:
        from pymobiledevice3.usbmux import list_devices as _list
        devices = _list()
        return [{"udid": d.serial, "connection": "usb"} for d in devices]
    except Exception as e:
        return [{"error": str(e)}]


def get_device_info(udid: str = None) -> dict:
    """
    Retourne les informations de l'iPhone :
    modèle, iOS, batterie, stockage, numéro de série.
    """
    try:
        lockdown = _connect(udid)
        info = lockdown.all_values
        battery = {}
        try:
            diag = DiagnosticsService(lockdown)
            battery = diag.get_battery() or {}
        except Exception:
            pass

        return {
            "name": info.get("DeviceName"),
            "model": info.get("ProductType"),
            "ios_version": info.get("ProductVersion"),
            "serial": info.get("SerialNumber"),
            "udid": info.get("UniqueDeviceID"),
            "storage_gb": round(info.get("TotalDiskCapacity", 0) / 1e9, 1),
            "free_gb": round(info.get("TotalSystemAvailable", 0) / 1e9, 1),
            "battery_level": battery.get("BatteryCurrentCapacity"),
            "charging": battery.get("ExternalChargeCapable"),
        }
    except RuntimeError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": f"Connexion échouée : {e}"}


def take_screenshot(udid: str = None, save: bool = True) -> dict:
    """
    Capture l'écran de l'iPhone.
    Retourne le chemin du fichier PNG sauvegardé.
    """
    try:
        lockdown = _connect(udid)
        data = ScreenshotService(lockdown).take_screenshot()

        if not save:
            return {"ok": True, "bytes": len(data)}

        SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        from datetime import datetime
        fname = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        path = SCREENSHOTS_DIR / fname
        path.write_bytes(data)
        return {"ok": True, "path": str(path), "size_kb": round(len(data) / 1024, 1)}
    except RuntimeError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": f"Screenshot échoué : {e}"}


def list_apps(udid: str = None, include_system: bool = False) -> list[dict]:
    """
    Retourne la liste des apps installées.
    """
    try:
        lockdown = _connect(udid)
        apps = InstallationProxyService(lockdown).get_apps()
        result = []
        for bundle_id, info in apps.items():
            if not include_system and info.get("ApplicationType") == "System":
                continue
            result.append({
                "name": info.get("CFBundleDisplayName") or info.get("CFBundleName", ""),
                "bundle_id": bundle_id,
                "version": info.get("CFBundleShortVersionString", ""),
                "type": info.get("ApplicationType", ""),
            })
        return sorted(result, key=lambda x: x["name"].lower())
    except RuntimeError as e:
        return [{"error": str(e)}]
    except Exception as e:
        return [{"error": f"Impossible de lister les apps : {e}"}]


def get_battery_level(udid: str = None) -> dict:
    """Retourne uniquement le niveau de batterie."""
    try:
        lockdown = _connect(udid)
        diag = DiagnosticsService(lockdown)
        battery = diag.get_battery() or {}
        return {
            "level": battery.get("BatteryCurrentCapacity"),
            "charging": battery.get("ExternalChargeCapable"),
            "fully_charged": battery.get("FullyCharged"),
        }
    except RuntimeError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": str(e)}
