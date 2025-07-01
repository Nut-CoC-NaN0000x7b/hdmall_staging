"""
Memory Monitoring Utility for Azure Production Environment
Prevents memory-related crashes by monitoring usage and taking proactive measures.
"""

import psutil
import os
import gc
import logging
import time
from typing import Optional, Dict
from functools import wraps
import asyncio

# Configure logging
logger = logging.getLogger(__name__)

class MemoryMonitor:
    """Monitor and manage application memory usage"""
    
    def __init__(self, 
                 warning_threshold_mb: int = 400,
                 critical_threshold_mb: int = 500,
                 force_gc_threshold_mb: int = 450):
        self.warning_threshold = warning_threshold_mb
        self.critical_threshold = critical_threshold_mb
        self.force_gc_threshold = force_gc_threshold_mb
        self.last_check_time = 0
        self.check_interval = 30  # Check every 30 seconds
        self.memory_history = []
        self.max_history = 100  # Keep last 100 measurements
        
    def get_memory_usage(self) -> Dict[str, float]:
        """Get current memory usage statistics"""
        try:
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            
            memory_stats = {
                'rss_mb': memory_info.rss / 1024 / 1024,  # Resident Set Size
                'vms_mb': memory_info.vms / 1024 / 1024,  # Virtual Memory Size
                'percent': process.memory_percent(),
                'available_mb': psutil.virtual_memory().available / 1024 / 1024,
                'timestamp': time.time()
            }
            
            # Add to history
            self.memory_history.append(memory_stats)
            if len(self.memory_history) > self.max_history:
                self.memory_history.pop(0)
            
            return memory_stats
            
        except Exception as e:
            logger.error(f"Error getting memory usage: {e}")
            return {'rss_mb': 0, 'vms_mb': 0, 'percent': 0, 'available_mb': 0, 'timestamp': time.time()}
    
    def check_memory_status(self) -> str:
        """Check current memory status and take action if needed"""
        current_time = time.time()
        
        # Rate limit checks
        if current_time - self.last_check_time < self.check_interval:
            return "OK"
        
        self.last_check_time = current_time
        memory_stats = self.get_memory_usage()
        memory_mb = memory_stats['rss_mb']
        
        status = "OK"
        
        if memory_mb > self.critical_threshold:
            status = "CRITICAL"
            logger.critical(f"🚨 CRITICAL memory usage: {memory_mb:.1f}MB (>{self.critical_threshold}MB)")
            logger.critical(f"📊 Memory stats: {memory_stats}")
            
            # Force aggressive cleanup
            self._aggressive_cleanup()
            
        elif memory_mb > self.force_gc_threshold:
            status = "HIGH"
            logger.warning(f"⚠️ High memory usage: {memory_mb:.1f}MB, forcing garbage collection")
            
            # Force garbage collection
            collected = gc.collect()
            logger.info(f"🗑️ Garbage collection freed {collected} objects")
            
        elif memory_mb > self.warning_threshold:
            status = "WARNING"
            logger.warning(f"⚠️ Warning: Memory usage {memory_mb:.1f}MB (>{self.warning_threshold}MB)")
        
        return status
    
    def _aggressive_cleanup(self):
        """Perform aggressive memory cleanup"""
        try:
            # Force garbage collection multiple times
            for i in range(3):
                collected = gc.collect()
                logger.info(f"🗑️ GC round {i+1}: freed {collected} objects")
            
            # Clear any module-level caches if possible
            import sys
            if hasattr(sys.modules.get('functools'), 'lru_cache'):
                # Clear LRU caches (if accessible)
                pass
            
            logger.info("✅ Aggressive cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during aggressive cleanup: {e}")
    
    def get_memory_trend(self, minutes: int = 10) -> Optional[str]:
        """Analyze memory usage trend over the last N minutes"""
        if len(self.memory_history) < 2:
            return None
        
        current_time = time.time()
        cutoff_time = current_time - (minutes * 60)
        
        # Filter history to last N minutes
        recent_history = [h for h in self.memory_history if h['timestamp'] > cutoff_time]
        
        if len(recent_history) < 2:
            return None
        
        # Calculate trend
        start_memory = recent_history[0]['rss_mb']
        end_memory = recent_history[-1]['rss_mb']
        change = end_memory - start_memory
        change_percent = (change / start_memory) * 100 if start_memory > 0 else 0
        
        if change_percent > 20:
            return f"INCREASING ({change:+.1f}MB, {change_percent:+.1f}%)"
        elif change_percent < -10:
            return f"DECREASING ({change:+.1f}MB, {change_percent:+.1f}%)"
        else:
            return f"STABLE ({change:+.1f}MB, {change_percent:+.1f}%)"
    
    def get_health_report(self) -> Dict:
        """Generate comprehensive memory health report"""
        stats = self.get_memory_usage()
        trend = self.get_memory_trend()
        status = self.check_memory_status()
        
        return {
            'status': status,
            'current_memory_mb': stats['rss_mb'],
            'memory_percent': stats['percent'],
            'available_memory_mb': stats['available_mb'],
            'trend_10min': trend,
            'thresholds': {
                'warning': self.warning_threshold,
                'critical': self.critical_threshold
            },
            'timestamp': stats['timestamp']
        }

# Global memory monitor instance
memory_monitor = MemoryMonitor()

def memory_check_decorator(check_interval: int = 60):
    """Decorator to automatically check memory usage"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Check memory before function execution
            status = memory_monitor.check_memory_status()
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                # Log memory stats on error
                stats = memory_monitor.get_memory_usage()
                logger.error(f"Function failed with memory at {stats['rss_mb']:.1f}MB: {e}")
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Check memory before function execution
            status = memory_monitor.check_memory_status()
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                # Log memory stats on error
                stats = memory_monitor.get_memory_usage()
                logger.error(f"Function failed with memory at {stats['rss_mb']:.1f}MB: {e}")
                raise
        
        # Return appropriate wrapper based on function type
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator

def check_memory_usage() -> float:
    """Simple function to check current memory usage"""
    return memory_monitor.get_memory_usage()['rss_mb']

def force_memory_cleanup():
    """Force immediate memory cleanup"""
    memory_monitor._aggressive_cleanup()
    return memory_monitor.get_memory_usage()

if __name__ == "__main__":
    # Test the memory monitor
    print("🔍 Memory Monitor Test")
    print("=" * 40)
    
    stats = memory_monitor.get_memory_usage()
    print(f"Current Memory: {stats['rss_mb']:.1f}MB")
    print(f"Memory Percent: {stats['percent']:.1f}%")
    print(f"Available: {stats['available_mb']:.1f}MB")
    
    status = memory_monitor.check_memory_status()
    print(f"Status: {status}")
    
    # Test health report
    report = memory_monitor.get_health_report()
    print("\n📊 Health Report:")
    for key, value in report.items():
        print(f"  {key}: {value}") 