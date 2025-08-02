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
    Given the user's query, you must choose the most appropriate agent from the following list:

    - task_manager: For managing tasks, creating to-do lists, and tracking progress.
    - prioritization_engine: For prioritizing tasks and suggesting what to work on next.
    - calendar_orchestrator: For scheduling meetings, managing calendars, and coordinating events.
    - email_triage: For sorting, filtering, and responding to emails.
    - focus_support: For helping the user focus on deep work and avoiding distractions.
    - smart_reminders: For setting smart reminders and nudges.
    - sub_agents: For handling complex meeting and project-related tasks.
    - analytics_dashboard: For providing analytics and feedback on productivity.

    User Query: "{user_query}"

    Based on the user's query, which agent should be called?
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