# Task Management Agent

Enhanced task management agent with CRUD operations, natural language processing, and JSON storage.

## Features

- **Natural Language Processing**: Uses `openai/gpt-oss-120b` model to understand task requests
- **CRUD Operations**: Create, Read, Update, Delete tasks
- **Smart Parsing**: Extracts due dates, priorities, and descriptions from natural language
- **JSON Storage**: Simple file-based storage system
- **Task Statistics**: Shows completion rates and suggestions
- **Priority Management**: Automatic priority detection from text

## Usage Examples

### Creating Tasks
```
"create task Buy groceries"
"add high priority task Finish project report"
"create task Call dentist due tomorrow"
"new task Review code in 3 days"
```

### Listing Tasks
```
"list all tasks"
"show me my tasks"
"list pending tasks"
"show completed tasks"
```

### Updating Tasks
```
"update task #1 priority high"
"change task #2 due date to next week"
"update task #3 description Add more details"
```

### Completing Tasks
```
"complete task #1"
"finish task #2"
"mark task #3 as done"
```

### Deleting Tasks
```
"delete task #1"
"remove task #2"
```

## File Structure

- `task_agent.py` - Main agent with LLM integration
- `task_storage.py` - JSON-based storage system
- `task_utils.py` - Utility functions for parsing and formatting
- `README.md` - This documentation

## Storage Format

Tasks are stored in `data/tasks.json`:

```json
{
  "tasks": [
    {
      "id": 1,
      "title": "Buy groceries",
      "description": "",
      "priority": "medium",
      "status": "pending",
      "created_at": "2024-01-01T10:00:00",
      "due_date": "2024-01-02",
      "completed_at": null
    }
  ],
  "next_id": 2,
  "metadata": {
    "created_at": "2024-01-01T10:00:00",
    "version": "1.0"
  }
}
```

## Integration

The task agent integrates with the supervisor-based architecture and uses the same LLM model (`openai/gpt-oss-120b`) for consistency across the system.