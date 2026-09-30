import time
import os
import psutil
try:
    import cpuinfo
except ImportError:
    cpuinfo = None

def format_time(seconds: int) -> str:
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, secs = divmod(remainder, 60)
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    parts.append(f"{secs}s")
    return " ".join(parts)

def get_system_metrics() -> dict:
    cpu_usage = psutil.cpu_percent(interval=None)
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage('/')

    cpu_model = "CPU"
    if cpuinfo:
        try:
            info = cpuinfo.get_cpu_info()
            cpu_model = info.get('brand_raw', 'CPU')
        except Exception:
            pass

    return {
        "cpu_usage": cpu_usage,
        "ram_used_mb": round(ram.used / (1024 * 1024), 1),
        "ram_total_mb": round(ram.total / (1024 * 1024), 1),
        "ram_percent": ram.percent,
        "disk_used_gb": round(disk.used / (1024 * 1024 * 1024), 2),
        "disk_total_gb": round(disk.total / (1024 * 1024 * 1024), 2),
        "disk_percent": disk.percent,
        "cpu_model": cpu_model
    }
