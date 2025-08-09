import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(
    api_key=os.environ.get("GROQ_API_KEY"),
)

def route_request(user_query: str) -> str:
    """
    Routes the user's request to the appropriate agent.
    Returns the agent name without quotes.
    """
    # Mapping of common typos to correct agent names
    AGENT_NAME_MAPPING = {
        'priorization_engine': 'prioritization_engine',
        'prioritize_engine': 'prioritization_engine',
        'priority_engine': 'prioritization_engine',
        'taskmanager': 'task_manager',
        'email': 'email_triage',
        'calendar': 'calendar_orchestrator',
        'focus': 'focus_support',
        'reminders': 'smart_reminders',
        'analytics': 'analytics_dashboard',
    }
    prompt = f"""
    You are an expert AI routing system. Carefully analyze the user's intent and route to the most appropriate specialized agent.
    
    AGENT DESCRIPTIONS:
    
    task_manager:
    - PURPOSE: CRUD operations on tasks (Create, Read, Update, Delete)
    - USE FOR: "Create task", "Add task", "New task", "Make a task", "List my tasks", "Show tasks", "Complete task", "Mark done", "Delete task", "Remove task", "Update task", "Edit task", "Change task"
    - EXAMPLES: "Create task: Build authentication", "Add task: Design wireframes", "Show me all my tasks", "Complete the API task", "Delete the old task"
    - DO NOT USE FOR: Questions about which task to work on, task importance, or priority analysis
    
    prioritization:
    - PURPOSE: Intelligent analysis of existing tasks to determine importance, urgency, and work order
    - USE FOR: "What should I work on", "Which task is urgent/important/critical", "Prioritize my tasks", "What's most important", "Which task first", "Rank my tasks", "What to focus on", "Task recommendations", "Goal management", "SMART goals", "Link tasks to goals"
    - EXAMPLES: "What should I work on next?", "Which development task is most urgent?", "Prioritize my mobile app tasks", "What's the most critical task?", "Create goal: Launch app"
    - DO NOT USE FOR: Creating new tasks or basic task management operations
    
    calendar_orchestrator:
    - PURPOSE: Calendar and scheduling operations exclusively
    - USE FOR: "Schedule meeting", "Book appointment", "Calendar event", "Set meeting", "When am I free", "Check availability", "Reschedule", "Cancel meeting"
    - EXAMPLES: "Schedule a meeting with John tomorrow", "Book a dentist appointment", "When am I available next week?"
    
    email_triage:
    - PURPOSE: Email management and communication exclusively
    - USE FOR: "Send email", "Draft email", "Check inbox", "Reply to email", "Email management", "Compose message"
    - EXAMPLES: "Send email to client about project update", "Draft a follow-up email", "Check my unread emails"
    
    focus_support:
    - PURPOSE: Concentration, productivity, and deep work assistance
    - USE FOR: "Help me focus", "Block distractions", "Deep work session", "Concentration techniques", "Productivity tips"
    - EXAMPLES: "I'm getting distracted, help me focus", "Start a deep work session", "Block social media"
    
    smart_reminders:
    - PURPOSE: Setting up notifications and reminders
    - USE FOR: "Remind me", "Set reminder", "Notification", "Alert me", "Don't forget"
    - EXAMPLES: "Remind me to call mom at 5pm", "Set a reminder for the meeting", "Alert me when it's time to leave"
    
    sub_agents:
    - PURPOSE: Complex requests requiring multiple agents (coordination of different systems)
    - USE FOR: Requests that need BOTH calendar AND email, or multiple different actions
    - EXAMPLES: "Schedule a meeting with John AND send him the agenda", "Book the conference room AND email the team"
    
    analytics_dashboard:
    - PURPOSE: Reports, statistics, and productivity analytics
    - USE FOR: "Show my productivity", "Task completion stats", "Weekly report", "Analytics", "Performance metrics", "Progress report"
    - EXAMPLES: "Show my task completion rate", "Generate a productivity report", "How many tasks did I complete this week?"
    
    general_chat:
    - PURPOSE: Casual conversation, general questions, explanations not related to specific productivity tools
    - USE FOR: Greetings, jokes, general knowledge questions, explanations, casual chat
    - EXAMPLES: "Hello", "How are you?", "What's the weather?", "Tell me a joke", "Explain quantum physics"
    
    User Query: "{user_query}"
    
    ROUTING DECISION PROCESS:
    1. Identify the PRIMARY ACTION the user wants to perform
    2. Determine if it's about CREATING/MANAGING tasks vs ANALYZING/PRIORITIZING existing tasks
    3. Check if it involves multiple systems (calendar + email = sub_agents)
    4. Match to the agent whose PURPOSE best fits the user's intent
    
    Return ONLY the agent name: task_manager, prioritization, calendar_orchestrator, email_triage, focus_support, smart_reminders, sub_agents, analytics_dashboard, or general_chat
    """

    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        model="openai/gpt-oss-120b",
        temperature=0.1,  # Low temperature for consistent routing
    )

    # Clean up the response
    agent_name = chat_completion.choices[0].message.content.strip()
    # Remove any quotes and whitespace
    agent_name = agent_name.strip('"\' ')
    # Convert to lowercase and replace spaces with underscores
    agent_name = agent_name.lower().replace(' ', '_')
    
    # Extract just the agent name if there's extra text
    valid_agents = ['task_manager', 'prioritization', 'calendar_orchestrator', 'email_triage', 'focus_support', 'smart_reminders', 'sub_agents', 'analytics_dashboard', 'general_chat']
    
    for valid_agent in valid_agents:
        if valid_agent in agent_name:
            agent_name = valid_agent
            break
    
    # Check if the agent name is in our mapping of common typos
    return AGENT_NAME_MAPPING.get(agent_name, agent_name)