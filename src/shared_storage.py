# Shared storage for tasks across agents
_shared_tasks = {}

def get_shared_tasks():
    return _shared_tasks

def set_shared_tasks(tasks):
    global _shared_tasks
    _shared_tasks = tasks

def add_shared_task(task_id, task):
    _shared_tasks[task_id] = task

def get_shared_task(task_id):
    return _shared_tasks.get(task_id)