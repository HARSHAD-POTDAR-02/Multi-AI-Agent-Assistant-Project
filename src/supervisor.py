import collections
import threading
import time
from graph_setup import build_graph
from agents.router import route_request

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
        self.dispatcher_thread = threading.Thread(target=self._dispatch_loop)
        self.dispatcher_thread.daemon = True
        self.dispatcher_thread.start()

    def add_task(self, user_query):
        self.task_complete_event.clear()
        self.task_queue.append(user_query)
        print(f"\n[INBOX] Task added to queue: '{user_query}'")

    def _dispatch_loop(self):
        while not self.stop_event.is_set():
            if self.task_queue:
                user_query = self.task_queue.popleft()
                print(f"[PROCESSING] Processing task: '{user_query}'")
                routed_agent = route_request(user_query)
                print(f"  - Task routed to: **{routed_agent}**")

                agent_is_busy = True
                while agent_is_busy:
                    with self.lock:
                        if self.agents.get(routed_agent) == "idle":
                            self.agents[routed_agent] = "busy"
                            agent_is_busy = False
                        
                    if agent_is_busy:
                        print(f"  - [WAITING] Agent '{routed_agent}' is busy. Waiting...")
                        time.sleep(5) # Wait for the agent to become free

                print(f"  - [BUSY] Agent '{routed_agent}' is now **busy**.")
                try:
                    # Create state with conversation history and context
                    state = {
                        "user_query": user_query, 
                        "routed_agent": routed_agent,
                        "conversation_history": self.conversation_history,
                        "context": self.context
                    }
                    response = self.graph.invoke(state)
                    
                    # Update conversation history
                    self.conversation_history.append({
                        "user_query": user_query,
                        "agent": routed_agent,
                        "response": response.get('response', 'No response'),
                        "timestamp": time.time()
                    })
                    
                    # Update context if agent provided any
                    if 'context' in response:
                        self.context.update(response['context'])
                    
                    print(f"BuddyAI: {response.get('response', 'No response from agent.')}")
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

