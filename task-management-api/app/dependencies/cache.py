from functools import lru_cache
from typing import Dict, Any, List
from datetime import datetime, timedelta
import time

# Simple in-memory cache (in production, use Redis or similar)
_cache = {}
_cache_timestamps = {}
CACHE_EXPIRY_SECONDS = 300  # 5 minutes

class CacheManager:
    """Simple cache manager for expensive operations"""
    
    @staticmethod
    def get(key: str) -> Any:
        """
        Get value from cache
        
        @staticmethod means this method belongs to the class but doesn't need
        an instance (self) to work. You can call it directly: CacheManager.get("key")
        
        Static methods are useful for utility functions that are related to the class
        but don't need access to instance data
        """
        if key not in _cache:
            return None
        
        # Check if expired - compare current time with stored timestamp
        if key in _cache_timestamps:
            if time.time() - _cache_timestamps[key] > CACHE_EXPIRY_SECONDS:
                # Remove expired item from both dictionaries
                del _cache[key]
                del _cache_timestamps[key]
                return None
        
        return _cache[key]
    
    @staticmethod
    def set(key: str, value: Any) -> None:
        """
        Set value in cache with current timestamp
        
        We store both the value and when it was cached so we can
        check expiration later in the get() method
        """
        _cache[key] = value
        _cache_timestamps[key] = time.time()  # Store current timestamp
    
    @staticmethod
    def delete(key: str) -> None:
        """Remove item from cache"""
        _cache.pop(key, None)  # .pop(key, None) removes key or does nothing if not found
        _cache_timestamps.pop(key, None)
    
    @staticmethod
    def clear() -> None:
        """Clear all cache"""
        _cache.clear()
        _cache_timestamps.clear()

@lru_cache(maxsize=128)
def get_task_statistics() -> Dict[str, Any]:
    """
    Cached dependency for expensive task statistics calculation
    
    @lru_cache is a decorator that automatically caches function results:
    - LRU = "Least Recently Used" - removes oldest unused items when cache is full
    - maxsize=128 means it keeps 128 different function call results in memory
    - If called with same parameters, returns cached result instead of recalculating
    - Perfect for expensive calculations that don't change often
    
    Example:
    - First call: get_task_statistics() -> calculates and caches result
    - Second call: get_task_statistics() -> returns cached result (fast!)
    - Cache is automatically managed by Python
    """
    from app.routers.tasks import tasks_db
    
    # Simulate expensive calculation
    time.sleep(0.1)  # Simulate database query delay
    
    total_tasks = len(tasks_db)
    completed_tasks = sum(1 for task in tasks_db if task.get("completed", False))
    pending_tasks = total_tasks - completed_tasks
    
    # Count by priority
    priority_counts = {"high": 0, "medium": 0, "low": 0}
    for task in tasks_db:
        priority = task.get("priority", "medium")
        if priority in priority_counts:
            priority_counts[priority] += 1
    
    # Overdue tasks
    now = datetime.now()
    overdue_tasks = sum(
        1 for task in tasks_db 
        if task.get("due_date") and task["due_date"] < now and not task.get("completed", False)
    )
    
    return {
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "pending_tasks": pending_tasks,
        "overdue_tasks": overdue_tasks,
        "completion_rate": completed_tasks / total_tasks if total_tasks > 0 else 0,
        "priority_breakdown": priority_counts,
        "calculated_at": datetime.now().isoformat()
    }

def get_cached_user_data(user_id: int) -> Dict[str, Any]:
    """
    Cached dependency for user data (simulates expensive user lookup)
    """
    cache_key = f"user_data_{user_id}"
    
    # Try to get from cache first
    cached_data = CacheManager.get(cache_key)
    if cached_data:
        return cached_data
    
    # Simulate expensive database/API call
    time.sleep(0.05)
    
    # Mock user data (in real app, this would be database query)
    user_data = {
        "user_id": user_id,
        "profile_data": f"Expensive profile data for user {user_id}",
        "preferences": {"theme": "dark", "notifications": True},
        "last_accessed": datetime.now().isoformat(),
        "fetched_at": datetime.now().isoformat()
    }
    
    # Store in cache
    CacheManager.set(cache_key, user_data)
    
    return user_data

def invalidate_task_cache():
    """
    Helper function to invalidate task-related caches
    Call this when tasks are created/updated/deleted
    """
    # Clear the lru_cache
    get_task_statistics.cache_clear()
    
    # Clear related cache keys
    cache_keys_to_remove = [key for key in _cache.keys() if key.startswith("task_")]
    for key in cache_keys_to_remove:
        CacheManager.delete(key)