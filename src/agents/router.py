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
    You are an intelligent routing system. Analyze the user's query and route it to the most appropriate agent.
    
    Available agents:
    - task_manager: Creating, managing, viewing tasks and to-do lists
    - prioritization_engine: Prioritizing existing tasks, deciding what to work on next
    - calendar_orchestrator: Scheduling meetings, calendar events, appointments ONLY
    - email_triage: Managing emails, drafting, sending, organizing inbox ONLY
    - focus_support: Help with concentration, deep work, blocking distractions
    - smart_reminders: Setting reminders and notifications
    - sub_agents: Multiple actions in one request (schedule meeting AND send email, meeting AND mail)
    - analytics_dashboard: Productivity reports, analytics, insights
    - general_chat: Casual conversation, general questions, explanations, jokes, greetings
    
    IMPORTANT: If the request contains BOTH scheduling/meeting AND email/mail actions, use sub_agents
    
    User Query: "{user_query}"
    
    Think about what the user is asking for. If it's:
    - A greeting, casual chat, joke, general question, or explanation → general_chat
    - About tasks, to-dos, creating lists → task_manager  
    - About email only → email_triage
    - About calendar/scheduling only → calendar_orchestrator
    - About focus/concentration → focus_support
    - About reminders → smart_reminders
    - About prioritizing → prioritization_engine
    - About analytics/reports → analytics_dashboard
    - Multiple actions (schedule AND email, meeting AND mail) → sub_agents
    - Anything else → general_chat
    
    Return ONLY the agent name: task_manager, prioritization_engine, calendar_orchestrator, email_triage, focus_support, smart_reminders, sub_agents, analytics_dashboard, or general_chat
    """

    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        model="llama3-8b-8192",
        temperature=0.0,  # Deterministic routing
    )

    # Clean up the response
    agent_name = chat_completion.choices[0].message.content.strip()
    # Remove any quotes and whitespace
    agent_name = agent_name.strip('"\' ')
    # Convert to lowercase and replace spaces with underscores
    agent_name = agent_name.lower().replace(' ', '_')
    
    # Check if the agent name is in our mapping of common typos
    return AGENT_NAME_MAPPING.get(agent_name, agent_name)