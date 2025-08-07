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
    print("\nAvailable commands:")
    print("  - 'exit' to quit")
    print("  - 'list tasks' or 'tasks' to see all tasks")
    print("  - 'search [query]' to search tasks")
    print("  - 'analytics' to see task analytics")
    print("  - 'summary' to get an AI summary of tasks")
    print("  - 'overdue' to see overdue tasks")
    print("  - 'high priority' to see high priority tasks")
    print("  - Or enter any request to create and execute a task\n")

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
                supervisor.task_complete_event.set()
                
            # Handle task status filter
            elif re.match(r'^list (pending|in_progress|completed|blocked|on_hold|cancelled|review) tasks$', user_query.lower()):
                status = re.match(r'^list (pending|in_progress|completed|blocked|on_hold|cancelled|review) tasks$', user_query.lower()).group(1)
                task_list = supervisor.list_tasks(status=status)
                print(f"\nBuddyAI: {task_list}\n")
                supervisor.task_complete_event.set()
                
            # Handle search command
            elif user_query.lower().startswith("search "):
                search_query = user_query[7:].strip()
                if search_query:
                    matching_tasks = supervisor.task_manager.search_tasks(search_query)
                    if matching_tasks:
                        result = f"🔍 Found {len(matching_tasks)} matching tasks:\n"
                        for task in matching_tasks[:10]:  # Limit to 10 results
                            status_emoji = {
                                "pending": "⏳", "in_progress": "🔄", "completed": "✅",
                                "blocked": "🚫", "on_hold": "⏸️", "cancelled": "❌", "review": "📝"
                            }.get(task.status.value, "⏳")
                            result += f"\n{status_emoji} {task.title}"
                            if task.description:
                                result += f"\n   {task.description[:100]}{'...' if len(task.description) > 100 else ''}"
                        print(f"\nBuddyAI: {result}\n")
                    else:
                        print(f"\nBuddyAI: No tasks found matching '{search_query}'\n")
                else:
                    print("\nBuddyAI: Please provide a search query. Usage: 'search [your query]'\n")
                supervisor.task_complete_event.set()
                
            # Handle analytics command
            elif user_query.lower() == "analytics":
                analytics = supervisor.task_manager.get_task_analytics_summary()
                result = "📊 Task Analytics Summary:\n"
                result += f"\n📋 Total Tasks: {analytics['total_tasks']}"
                result += f"\n⏰ Overdue Tasks: {analytics['overdue_tasks']}"
                
                result += "\n\n📈 Status Breakdown:"
                for status, count in analytics['status_breakdown'].items():
                    emoji = {"pending": "⏳", "in_progress": "🔄", "completed": "✅", "blocked": "🚫"}.get(status, "📋")
                    result += f"\n  {emoji} {status.title()}: {count}"
                    
                result += "\n\n🎯 Priority Breakdown:"
                priority_names = {0: "Critical", 1: "High", 2: "Medium", 3: "Low"}
                for priority, count in analytics['priority_breakdown'].items():
                    name = priority_names.get(priority, f"Priority {priority}")
                    result += f"\n  🔥 {name}: {count}"
                    
                velocity = analytics['completion_velocity']
                result += f"\n\n📈 Completion Velocity (last 30 days):"
                result += f"\n  Completed: {velocity['completed_count']} tasks"
                result += f"\n  Daily Rate: {velocity['velocity_per_day']:.1f} tasks/day"
                result += f"\n  Avg Time: {velocity['avg_completion_time']:.1f} hours"
                
                print(f"\nBuddyAI: {result}\n")
                supervisor.task_complete_event.set()
                
            # Handle summary command
            elif user_query.lower() == "summary":
                print("\n🤖 Generating AI summary of your tasks...")
                summary = supervisor.task_manager.get_natural_language_summary()
                print(f"\nBuddyAI: 📝 Task Summary:\n{summary}\n")
                supervisor.task_complete_event.set()
                
            # Handle overdue command
            elif user_query.lower() == "overdue":
                overdue_tasks = supervisor.task_manager.analytics.get_overdue_tasks()
                if overdue_tasks:
                    result = f"⚠️ You have {len(overdue_tasks)} overdue tasks:\n"
                    for task in overdue_tasks:
                        days_overdue = abs(task.days_until_due())
                        result += f"\n🚨 {task.title} (Overdue by {days_overdue} days)"
                        if task.assigned_agent:
                            result += f" - Assigned to: {task.assigned_agent}"
                    print(f"\nBuddyAI: {result}\n")
                else:
                    print("\nBuddyAI: 🎉 No overdue tasks! You're all caught up.\n")
                supervisor.task_complete_event.set()
                
            # Handle high priority command
            elif user_query.lower() in ["high priority", "priority", "urgent"]:
                priority_tasks = supervisor.task_manager.get_tasks_by_priority(sort_by_dynamic=True)
                high_priority = [t for t in priority_tasks if t.dynamic_priority_score >= 5.0][:10]
                if high_priority:
                    result = f"🔥 Top {len(high_priority)} high priority tasks:\n"
                    for i, task in enumerate(high_priority, 1):
                        status_emoji = {
                            "pending": "⏳", "in_progress": "🔄", "completed": "✅",
                            "blocked": "🚫", "on_hold": "⏸️"
                        }.get(task.status.value, "⏳")
                        result += f"\n{i}. {status_emoji} {task.title} (Score: {task.dynamic_priority_score})"
                        if task.due_date:
                            days = task.days_until_due()
                            if days is not None:
                                if days < 0:
                                    result += f" - ⚠️ Overdue by {abs(days)} days"
                                elif days == 0:
                                    result += f" - ⚠️ Due today"
                                else:
                                    result += f" - 📅 Due in {days} days"
                    print(f"\nBuddyAI: {result}\n")
                else:
                    print("\nBuddyAI: No high priority tasks found.\n")
                supervisor.task_complete_event.set()
                
            # Handle complex goals that need to be broken down
            elif any(keyword in user_query.lower() for keyword in ["plan", "organize", "create", "develop", "build", "design"]):
                supervisor.handle_complex_goal(user_query)
                
            # Handle regular tasks
            else:
                # Create a task in the task manager first
                task = supervisor.task_manager.create_task(
                    title=user_query,
                    description="User requested task",
                    status="pending",
                    add_to_queue=False  # Don't add to queue automatically
                )
                
                if task:
                    # Determine the best agent for this task
                    agent = supervisor._determine_agent_for_subtask(user_query)
                    supervisor.task_manager.assign_agent(task.id, agent)
                    
                    # Save the task to database
                    supervisor.task_manager.save_to_database(task)
                    
                    # Add the task to the supervisor queue with all necessary data
                    task_data = {
                        'id': task.id,
                        'query': user_query,
                        'description': task.description,
                        'priority': task.priority,
                        'parent_id': task.parent_id,
                        'dependencies': task.dependencies,
                        'status': task.status,
                        'assigned_agent': agent,
                        'type': 'task'  # Explicitly mark as a task type
                    }
                    supervisor.add_task(task_data)
                else:
                    print("\nError: Failed to create task. Please try again.\n")
                    supervisor.task_complete_event.set()

    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"\nAn error occurred: {e}")
    finally:
        supervisor.stop()

if __name__ == "__main__":
    main()
