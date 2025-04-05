from fastapi import HTTPException, status
import time
import os

class Progress:
    progress: str
    message: str
    
class TaskManager:
    def __init__(self):
        self.active_tasks = {}
        self.max_concurrent = (os.cpu_count() or 2) * 2  # Allow 2x CPU cores
        
    def create_task(self, task_id: str, url: str):
        if len(self.active_tasks) >= self.max_concurrent:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="System busy, try again later"
            )
            
        self.active_tasks[task_id] = {
            "status": "processing",
            "start_time": time.time(),
            "url": url,
            "progress": 0,
            "error": None,
            "result": None
        }
        
    def update_progress(self, task_id: str, progress: Progress):
        if task_id in self.active_tasks:
            self.active_tasks[task_id]["progress"] = progress
            
    def complete_task(self, task_id: str, result: dict):
        if task_id in self.active_tasks:
            self.active_tasks[task_id].update({
                "status": "completed",
                "result": result,
                "completion_time": time.time(),
                "progress": 100
            })
            
    def fail_task(self, task_id: str, error: str):
        if task_id in self.active_tasks:
            self.active_tasks[task_id].update({
                "status": "failed",
                "error": error,
                "completion_time": time.time()
            })
task_manager = TaskManager()