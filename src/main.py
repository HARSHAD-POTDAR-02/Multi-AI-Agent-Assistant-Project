from supervisor import AgentSupervisor
import time
import re

def main():
    """
    The main entry point for the application.
    """
    supervisor = AgentSupervisor()

    print("🚀 Welcome to your Multi-AI Agent Personal Assistant! 🚀")
    print("BuddyAI: How can I help you today?")
    print("Type 'exit' to quit, 'list tasks' to see all tasks, or enter your request.")

    try:
        while True:
            supervisor.task_complete_event.wait() # Wait for the previous task to complete
            user_query = input("User: ")
            
            # Handle exit command
            if user_query.lower() == "exit":
                break
                
            # Handle list tasks command
            elif user_query.lower() == "list tasks" or user_query.lower() == "tasks":
                task_list = supervisor.list_tasks()
                print(f"\nBuddyAI: {task_list}\n")
                supervisor.task_complete_event.set()  # No need to wait for task completion
                
            # Handle task status filter
            elif re.match(r'^list (pending|in_progress|completed|blocked) tasks$', user_query.lower()):
                status = re.match(r'^list (pending|in_progress|completed|blocked) tasks$', user_query.lower()).group(1)
                task_list = supervisor.list_tasks(status=status)
                print(f"\nBuddyAI: {task_list}\n")
                supervisor.task_complete_event.set()  # No need to wait for task completion
                
            # Handle complex goals that need to be broken down
            elif any(keyword in user_query.lower() for keyword in ["plan", "organize", "create", "develop", "build", "design"]):
                supervisor.handle_complex_goal(user_query)
                
            # Handle regular tasks
            else:
                # Create a simple task
                task = supervisor.task_manager.create_task(
                    title=user_query,
                    description="User requested task",
                    status="pending"
                )
                
                # Determine the best agent for this task
                agent = supervisor._determine_agent_for_subtask(user_query)
                supervisor.task_manager.assign_agent(task.id, agent)
                
                # Add the task to the queue
                task_data = task.to_dict()
                task_data['query'] = user_query
                task_data['type'] = 'task'
                supervisor.add_task(task_data)

    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"\nAn error occurred: {e}")
    finally:
        supervisor.stop()

if __name__ == "__main__":
    main()
