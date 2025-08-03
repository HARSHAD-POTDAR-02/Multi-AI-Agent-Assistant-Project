from supervisor import AgentSupervisor
import time

def main():
    """
    The main entry point for the application.
    """
    supervisor = AgentSupervisor()

    print("🚀 Welcome to your Multi-AI Agent Personal Assistant! 🚀")
    print("BuddyAI: How can I help you today?")

    try:
        while True:
            supervisor.task_complete_event.wait() # Wait for the previous task to complete
            user_query = input("User: ")
            if user_query.lower() == "exit":
                break
            supervisor.add_task(user_query)

    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        supervisor.stop()

if __name__ == "__main__":
    main()
