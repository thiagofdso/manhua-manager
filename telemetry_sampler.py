import os
import time
import threading
import psutil
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Callable

def sample_process_tree(pid: Optional[int] = None) -> List[Dict[str, Any]]:
    target_pid = pid or os.getpid()
    results = []
    now_str = datetime.now(timezone.utc).isoformat()
    
    try:
        root_proc = psutil.Process(target_pid)
        procs = [root_proc] + root_proc.children(recursive=True)
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return []
        
    for p in procs:
        try:
            with p.oneshot():
                p_pid = p.pid
                p_name = p.name()
                cpu = p.cpu_percent(interval=None)
                mem = p.memory_full_info() if hasattr(p, "memory_full_info") else p.memory_info()
                rss_mb = round(mem.rss / (1024 * 1024), 2)
                pss_mb = round(getattr(mem, "pss", mem.rss) / (1024 * 1024), 2)
                
                results.append({
                    "timestamp": now_str,
                    "pid": p_pid,
                    "process_name": p_name,
                    "cpu_percent": cpu,
                    "memory_rss_mb": rss_mb,
                    "memory_pss_mb": pss_mb
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return results

class ResourceSampler:
    def __init__(self, callback: Callable[[List[Dict[str, Any]]], None], interval: float = 1.0, target_pid: Optional[int] = None):
        self.callback = callback
        self.interval = interval
        self.target_pid = target_pid
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="ResourceSampler")
        self._thread.start()

    def _loop(self):
        while self._running:
            samples = sample_process_tree(self.target_pid)
            if samples:
                try:
                    self.callback(samples)
                except Exception:
                    pass
            time.sleep(self.interval)

    def stop(self):
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
