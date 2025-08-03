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
        'priorization_engine': 'prioritization_engine',  # Common typo
        'prioritize_engine': 'prioritization_engine',   # Another common variation
        'priority_engine': 'prioritization_engine',     # And another
        'taskmanager': 'task_manager',                  # Missing underscore
        'email': 'email_triage',                        # Short form
        'calendar': 'calendar_orchestrator',            # Short form
        'focus': 'focus_support',                       # Short form
        'reminders': 'smart_reminders',                 # Short form
        'analytics': 'analytics_dashboard',             # Short form
    }
    prompt = f"""
    You are a master at routing a user's request to the correct agent.
    Given the user's query, you must choose the most appropriate agent from the following list.
    Read the descriptions of each agent carefully and decide which one is the best fit.

    - **task_manager**:
        - **What it does**: Manages tasks, creates to-do lists, and tracks progress.
        - **When to call it**: Call this agent for any requests related to creating, viewing, updating, or deleting tasks. For example: "add 'buy milk' to my to-do list", "show me my tasks for today", "mark 'finish report' as complete".
        - **When NOT to call it**: Do not call this agent if the user wants to prioritize their tasks; use `prioritization_engine` for that. Do not call it for scheduling events on a calendar; use `calendar_orchestrator` for that.

    - **prioritization_engine**:
        - **What it does**: Prioritizes tasks and suggests what to work on next based on importance and urgency.
        - **When to call it**: Call this agent when the user asks for help with prioritization. For example: "what should I work on next?", "prioritize my tasks", "what is the most important task?".
        - **When NOT to call it**: Do not call this agent for simply creating or viewing tasks; use `task_manager` for that.

    - **calendar_orchestrator**:
        - **What it does**: Schedules meetings, manages calendar events, and coordinates schedules.
        - **When to call it**: Call this agent for any requests related to the user's calendar. For example: "schedule a meeting with John for tomorrow at 2 PM", "what's on my calendar for today?", "create an event for a doctor's appointment".
        - **When NOT to call it**: Do not call this agent for setting simple reminders; use `smart_reminders` for that. Do not call it for managing to-do lists; use `task_manager` for that.

    - **email_triage**:
        - **What it does**: Sorts, filters, and helps respond to emails.
        - **When to call it**: Call this agent for any requests related to managing emails. For example: "check my unread emails", "summarize the latest email from my boss", "help me draft a reply to this email".
        - **When NOT to call it**: Do not call this agent for tasks that are not email-related.

    - **focus_support**:
        - **What it does**: Helps the user focus on deep work and avoid distractions.
        - **When to call it**: Call this agent when the user expresses a need to concentrate. For example: "I need to focus for the next hour", "start a deep work session", "block distracting websites".
        - **When NOT to call it**: Do not call this agent for managing tasks or calendars.

    - **smart_reminders**:
        - **What it does**: Sets smart, context-aware reminders and nudges.
        - **When to call it**: Call this agent when the user wants to be reminded of something. For example: "remind me to call my mom in 30 minutes", "set a reminder for my medication".
        - **When NOT to call it**: Do not call this agent for scheduling complex events or meetings in the calendar; use `calendar_orchestrator` for that.

    - **sub_agents**:
        - **What it does**: Handles complex, multi-step tasks related to meetings and projects by breaking them down and coordinating other agents.
        - **When to call it**: Call this agent for complex requests that require multiple actions. For example: "organize the project launch meeting" (which might involve finding a time, booking a room, sending invites, and creating an agenda), or "plan my new project" (which could involve creating tasks, setting deadlines, and scheduling milestones).
        - **When NOT to call it**: Do not call this agent for simple, single-step requests that can be handled by a more specialized agent.

    - **analytics_dashboard**:
        - **What it does**: Provides analytics and feedback on the user's productivity and work patterns.
        - **When to call it**: Call this agent when the user asks for insights into their productivity. For example: "how did I spend my time last week?", "show me my productivity dashboard", "give me a report on my completed tasks".
        - **When NOT to call it**: Do not call this agent for viewing current tasks or calendar events.

    User Query: "{user_query}"

    Based on the user's query and the detailed agent descriptions, which agent should be called?
    Return ONLY the name of the agent, without any quotes, punctuation, or additional text.
    For example, if the user wants to create a to-do list, you should return exactly: task_manager
    """

    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        model="llama3-8b-8192",
        temperature=0.1,  # Lower temperature for more deterministic output
    )

    # Clean up the response
    agent_name = chat_completion.choices[0].message.content.strip()
    # Remove any quotes and whitespace
    agent_name = agent_name.strip('"\' ')
    # Convert to lowercase and replace spaces with underscores
    agent_name = agent_name.lower().replace(' ', '_')
    
    # Check if the agent name is in our mapping of common typos
    return AGENT_NAME_MAPPING.get(agent_name, agent_name)