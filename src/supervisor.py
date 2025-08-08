import collections
import threading
import time
from graph_setup import build_graph
from agents.router import route_request
from agents.task_manager import TaskManager

class AgentSupervisor:
    def __init__(self):
        self.task_queue = collections.deque()
        self.agents = {
            "task_manager": "idle",
            "prioritization_engine": "idle",
            "calendar_orchestrator": "idle",
            "email_triage": "idle",
            "focus_support": "idle",
            "smart_reminders": "idle",
            "sub_agents": "idle",
            "analytics_dashboard": "idle",
        }
        self.conversation_history = []
        self.context = {}
        self.graph = build_graph()
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.task_complete_event = threading.Event()
        self.task_complete_event.set()  # Initially set to allow the first prompt
        self.task_manager = TaskManager(supervisor=self)  # Initialize the task manager
        self.dispatcher_thread = threading.Thread(target=self._dispatch_loop)
        self.dispatcher_thread.daemon = True
        self.dispatcher_thread.start()

    def add_task(self, task_data):
        """
        Add a task to the queue
        
        Args:
            task_data: Dictionary containing task information
                - If it's a string, it's treated as a simple query
                - If it's a dict, it should contain at least 'query' key
        """
        self.task_complete_event.clear()
        
        # Handle both string queries and task data dictionaries
        if isinstance(task_data, str):
            task_data = {'query': task_data, 'type': 'query'}
        elif isinstance(task_data, dict) and 'query' not in task_data and 'id' in task_data:
            # If it's a task from the task manager without a query field
            task_data['query'] = task_data.get('title', '')
            
        self.task_queue.append(task_data)
        print(f"\n📥 Task added to queue: '{task_data.get('query', 'No query')}'")
        
    def handle_complex_goal(self, complex_goal):
        """
        Break down a complex goal into subtasks and add them to the queue
        
        Args:
            complex_goal: The complex goal to break down
        """
        print(f"🔍 Breaking down complex goal: '{complex_goal}'")
        tasks = self.task_manager.break_down_task(complex_goal)
        
        # Check if tasks is None or empty
        if not tasks:
            print("❌ Failed to break down the complex goal - no tasks returned")
            self._create_fallback_task(complex_goal)
            return
            
        # Check if we have a valid parent task
        if len(tasks) > 0 and tasks[0] is not None:
            parent_task = tasks[0]
            print(f"📋 Created parent task: '{parent_task.title}' with {len(tasks)-1} subtasks")
            
            # For each subtask, determine the best agent and add it to the queue
            for subtask in tasks[1:]:
                if subtask is None:
                    continue
                    
                agent = self._determine_agent_for_subtask(subtask.title)
                self.task_manager.assign_agent(subtask.id, agent)
                
                # Add the subtask to the queue
                task_data = subtask.to_dict()
                task_data['query'] = subtask.title
                task_data['type'] = 'task'
                self.add_task(task_data)
                
                print(f"  - Subtask '{subtask.title}' assigned to agent '{agent}'")
        else:
            print("❌ Failed to break down the complex goal - invalid parent task")
            self._create_fallback_task(complex_goal)
    
    def _create_fallback_task(self, complex_goal):
        """Create a simple task as fallback when complex goal breakdown fails"""
        # Create a simple task as fallback
        task = self.task_manager.create_task(
            title=complex_goal,
            description="Complex goal that couldn't be broken down",
            status="pending"
        )
        
        if task:
            # Determine the best agent for this task
            agent = self._determine_agent_for_subtask(complex_goal)
            self.task_manager.assign_agent(task.id, agent)
            
            # Add the task to the queue
            task_data = task.to_dict()
            task_data['query'] = complex_goal
            task_data['type'] = 'task'
            self.add_task(task_data)
        else:
            print("❌ Failed to create fallback task")
            # Last resort: add the raw query to the queue
            self.add_task(complex_goal)

    def _determine_agent_for_subtask(self, subtask_title):
        """
        Determine the best agent for a subtask based on its title/description
        
        Args:
            subtask_title: The title of the subtask
            
        Returns:
            The name of the agent to assign the subtask to
        """
        return route_request(subtask_title)

    def _dispatch_loop(self):
        while not self.stop_event.is_set():
            if self.task_queue:
                task_metadata = self.task_queue.popleft()
                
                # Extract query from task metadata
                if isinstance(task_metadata, str):
                    user_query = task_metadata
                    task_metadata = {'query': user_query, 'type': 'query'}
                else:
                    user_query = task_metadata.get('query', '')
                    
                # Skip empty queries
                if not user_query:
                    continue
                    
                print(f"🔄 Processing task: '{user_query}'")
                
                # If this is a task with an assigned agent, use that agent
                if task_metadata.get('type') == 'task' and task_metadata.get('assigned_agent'):
                    routed_agent = task_metadata.get('assigned_agent')
                else:
                    # Otherwise, route the request based on the query
                    routed_agent = route_request(user_query)
                    
                print(f"  - Task routed to: **{routed_agent}**")
                
                # Update task status if it's a managed task
                task_id = task_metadata.get('id')
                if task_id and hasattr(self, 'task_manager'):
                    self.task_manager.update_task_status(task_id, 'in_progress')
                    # Save the updated task to database
                    task = self.task_manager.get_task(task_id)
                    if task:
                        self.task_manager.save_to_database(task)

                # Try to assign the agent, with a maximum number of retries
                agent_is_busy = True
                retry_count = 0
                max_retries = 5  # Maximum number of retries to prevent infinite loops
                
                while agent_is_busy and retry_count < max_retries:
                    with self.lock:
                        if self.agents.get(routed_agent) == "idle":
                            self.agents[routed_agent] = "busy"
                            agent_is_busy = False
                        
                    if agent_is_busy:
                        print(f"  - ⏳ Agent '{routed_agent}' is busy. Waiting... (Attempt {retry_count + 1}/{max_retries})")
                        time.sleep(5)  # Wait for the agent to become free
                        retry_count += 1
                
                # If we've reached max retries, skip this task
                if agent_is_busy:
                    print(f"  - ❌ Agent '{routed_agent}' is still busy after {max_retries} attempts. Skipping task.")
                    if task_id and hasattr(self, 'task_manager'):
                        self.task_manager.update_task_status(task_id, 'blocked')
                        # Save the updated task to database
                        task = self.task_manager.get_task(task_id)
                        if task:
                            self.task_manager.save_to_database(task)
                    continue

                print(f"  - [BUSY] Agent '{routed_agent}' is now **busy**.")
                try:
                    # Include the full task metadata in the graph invocation
                    graph_input = {
                        "user_query": user_query,
                        "routed_agent": routed_agent,
                        "task_metadata": task_metadata
                    }
                    
                    response = self.graph.invoke(graph_input)
                    print(f"BuddyAI: {response.get('response', 'No response from agent.')}")
                    
                    # Update task status if it's a managed task
                    if task_id and hasattr(self, 'task_manager'):
                        self.task_manager.update_task_status(task_id, 'completed')
                        self.task_manager.update_task_progress(task_id, 100)
                        # Save the updated task to database
                        task = self.task_manager.get_task(task_id)
                        if task:
                            self.task_manager.save_to_database(task)
                finally:
                    with self.lock:
                        self.agents[routed_agent] = "idle"
                        print(f"  - [IDLE] Agent '{routed_agent}' is now **idle**.")
                    print("\n" + "="*80 + "\n")
                    self.task_complete_event.set()
            else:
                time.sleep(1)

    def stop(self):
        self.stop_event.set()
        self.task_complete_event.set() # Unblock main thread if waiting
        self.dispatcher_thread.join()
        
    def list_tasks(self, status=None, parent_id=None):
        """
        List all tasks, optionally filtered by status and/or parent_id
        
        Args:
            status: Filter tasks by status (pending, in_progress, completed, blocked)
            parent_id: Filter tasks by parent_id
            
        Returns:
            A formatted string with the list of tasks
        """
        if hasattr(self, 'task_manager'):
            tasks = self.task_manager.list_tasks(status, parent_id)
            
            if not tasks:
                return "No tasks found."
                
            result = "📋 Task List:\n"
            for task in tasks:
                status_emoji = {
                    "pending": "⏳",
                    "in_progress": "🔄",
                    "completed": "✅",
                    "blocked": "🚫",
                    "assigned": "📌"
                }.get(task.get('status', 'pending'), "⏳")
                
                agent = f" [Agent: {task.get('assigned_agent')}]" if task.get('assigned_agent') else ""
                progress = f" - {task.get('progress')}%" if task.get('progress') > 0 else ""
                
                result += f"\n{status_emoji} {task.get('title')}{agent}{progress}"
                
                # Add description if available
                if task.get('description'):
                    result += f"\n   {task.get('description')}"
                    
                # Add subtasks if available
                if task.get('subtasks'):
                    subtasks = []
                    for subtask_id in task.get('subtasks', []):
                        subtask = self.task_manager.get_task(subtask_id)
                        if subtask:
                            subtask_status = {
                                "pending": "⏳",
                                "in_progress": "🔄",
                                "completed": "✅",
                                "blocked": "🚫",
                                "assigned": "📌"
                            }.get(subtask.status.value if hasattr(subtask.status, 'value') else subtask.status, "⏳")
                            subtasks.append(f"\n   - {subtask_status} {subtask.title}")
                    if subtasks:
                        result += "\n   Subtasks:" + "".join(subtasks)
                        
            return result
        else:
            return "Task manager not initialized."

