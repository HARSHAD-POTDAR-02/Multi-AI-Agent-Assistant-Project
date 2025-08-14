# Shared storage for tasks across agents
_shared_tasks = {}
_focus_manager = None

def get_shared_tasks():
    return _shared_tasks

def set_shared_tasks(tasks):
    global _shared_tasks
    _shared_tasks = tasks

def add_shared_task(task_id, task):
    _shared_tasks[task_id] = task

def get_shared_task(task_id):
    return _shared_tasks.get(task_id)

def get_focus_manager():
    global _focus_manager
    if _focus_manager is None:
        from agents.focus import FocusManager
        _focus_manager = FocusManager()
    return _focus_manager