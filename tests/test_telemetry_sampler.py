import os
import time
import telemetry_sampler

def test_telemetry_sample_process_tree():
    current_pid = os.getpid()
    samples = telemetry_sampler.sample_process_tree(pid=current_pid)
    assert len(samples) >= 1
    
    root_sample = samples[0]
    assert root_sample["pid"] == current_pid
    assert "cpu_percent" in root_sample
    assert root_sample["memory_rss_mb"] > 0
    assert root_sample["memory_pss_mb"] is not None

def test_telemetry_sampler_thread_lifecycle():
    recorded = []
    def on_sample(batch):
        recorded.extend(batch)
        
    sampler = telemetry_sampler.ResourceSampler(callback=on_sample, interval=0.05)
    sampler.start()
    time.sleep(0.12)
    sampler.stop()
    
    assert len(recorded) >= 2
