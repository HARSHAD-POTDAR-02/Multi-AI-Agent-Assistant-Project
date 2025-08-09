# 🎯 Intelligent Prioritization Engine

## Overview
The Intelligent Prioritization Engine is a comprehensive system that implements advanced task prioritization using multi-factor scoring, real-time re-ranking, and SMART goal alignment. It seamlessly integrates with your existing task management system to provide intelligent recommendations on what to work on next.

## 🚀 Features Implemented

### ✅ Multi-Factor Scoring System
- **Deadline Urgency**: Exponential decay scoring based on time remaining
- **Effort Estimation**: Inverse relationship (quick wins get higher priority)
- **Focus Windows**: Time-of-day multipliers based on peak performance
- **Dependencies**: Boost priority for blocking tasks, reduce for blocked tasks
- **Goal Alignment**: Higher priority for tasks advancing multiple goals

### ✅ Real-Time Re-Ranking
- **Event-Driven Updates**: Automatic re-prioritization on task changes
- **Dynamic Scoring**: Priorities update based on current context
- **Incremental Processing**: Efficient updates without full recalculation

### ✅ SMART Goal Mapping
- **Goal Hierarchy**: Link tasks to objectives and key results
- **Progress Tracking**: Automatic calculation of goal completion
- **Alignment Scoring**: Priority boost for goal-advancing tasks
- **Goal Types**: Personal, Professional, Learning, Health, Project

## 📁 Architecture

```
src/agents/prioritization/
├── prioritization_agent.py     # Main conversational agent
├── scoring_engine.py          # Multi-factor priority calculations
├── goal_mapper.py            # SMART goal management system
├── models.py                 # Data structures and types
└── __init__.py              # Package exports
```

## 🎮 Usage Examples

### Task Prioritization
```
User: "prioritize my tasks"
User: "what should I work on next?"
User: "show my priorities"
```

### Goal Management
```
User: "create goal: Learn Python programming"
User: "show my goals"
User: "goal progress"
User: "link task to goal"
```

### Smart Scheduling
```
User: "when should I work on this?"
User: "show my focus times"
User: "schedule my day"
```

### Analytics & Insights
```
User: "show my progress"
User: "task analytics"
User: "goal insights"
```

## 🔧 Technical Implementation

### Priority Scoring Formula
```python
Priority = (urgency × 0.4) + (effort × 0.2) + (focus × 0.2) + (dependency × 0.1) + (goal_alignment × 0.1)
```

### Urgency Calculation
- **Overdue**: 10.0 points
- **Due today**: 8.0 points
- **Due in 2-3 days**: 6.0 points
- **Due this week**: 4.0 points
- **Due this month**: 2.0 points
- **Due later**: 1.0 points

### Effort Scoring (Inverse)
- **≤ 30 minutes**: 8.0 points (quick wins)
- **≤ 2 hours**: 6.0 points
- **≤ 8 hours**: 4.0 points (full day)
- **≤ 24 hours**: 2.0 points (3 days)
- **> 24 hours**: 1.0 points (long-term)

### Focus Window Optimization
- **Peak windows**: Up to 2.0x productivity multiplier
- **Work hours**: 1.2x multiplier
- **Off-hours**: 1.0x multiplier

## 🎯 SMART Goals Integration

### Goal Types Supported
- **Personal**: Life goals, habits, self-improvement
- **Professional**: Career, work projects, skills
- **Learning**: Education, courses, certifications
- **Health**: Fitness, wellness, medical
- **Project**: Specific deliverables with deadlines

### Goal Progress Calculation
```python
progress = (completed_tasks + sum(task_progress)) / total_linked_tasks
```

## 📊 Analytics Features

### Task Statistics
- Completion rates by priority level
- Average completion time by effort estimate
- Overdue task identification
- Blocked task analysis

### Goal Insights
- Progress by goal type
- Goals needing attention
- Milestone tracking
- Achievement patterns

## 🔄 Real-Time Features

### Automatic Re-Ranking Triggers
- New task creation
- Task status updates
- Deadline changes
- Goal progress updates
- Time-based focus window changes

### Background Processes
- Priority score updates every 30 minutes
- Deadline notifications
- Stuck task detection
- Goal progress recalculation

## 🎨 User Experience

### Natural Language Processing
The system understands various query formats:
- "What should I focus on today?"
- "Prioritize tasks by deadline"
- "Show me quick wins"
- "Create goal: Launch product by Q2"

### Intelligent Responses
- Priority explanations with reasoning
- Focus window recommendations
- Goal alignment suggestions
- Task breakdown recommendations

## 🔧 Configuration

### User Preferences
```python
UserPreferences(
    focus_windows=[
        FocusWindow(start_time=time(9,0), end_time=time(11,0), productivity_multiplier=1.5),
        FocusWindow(start_time=time(14,0), end_time=time(16,0), productivity_multiplier=1.3)
    ],
    work_hours_start=time(9,0),
    work_hours_end=time(17,0),
    priority_weights={
        "urgency": 0.4,
        "effort": 0.2,
        "focus_window": 0.2,
        "dependency": 0.1,
        "goal_alignment": 0.1
    }
)
```

## 🚀 Integration Points

### Router Integration
- Added "prioritization" routing for priority-related queries
- Keywords: priority, prioritize, goal, objective, focus, schedule

### Task Manager Enhancement
- Enhanced `_calculate_dynamic_priority()` method
- Added `get_prioritized_tasks()` method
- Real-time priority updates on task modifications

### Graph Setup
- Added prioritization agent as graph node
- Integrated with existing conversation flow

## 📈 Performance Optimizations

### Efficient Calculations
- Incremental priority updates
- Cached scoring results
- Batch processing for multiple tasks

### Memory Management
- Lazy loading of goals and preferences
- Cleanup of expired data
- Optimized data structures

## 🧪 Testing

Run the comprehensive test suite:
```bash
python test_prioritization.py
```

### Test Coverage
- ✅ Component imports and initialization
- ✅ Priority scoring calculations
- ✅ Goal creation and management
- ✅ Agent query processing
- ✅ Integration with task manager

## 🔮 Future Enhancements

### Machine Learning Integration
- Learn from user behavior patterns
- Adaptive priority weights
- Predictive task completion times

### Advanced Analytics
- Productivity trend analysis
- Goal achievement predictions
- Optimal scheduling recommendations

### Collaboration Features
- Team goal alignment
- Shared priority contexts
- Delegation recommendations

## 📝 API Reference

### PriorityScorer Methods
- `calculate_priority(task, user_prefs, all_tasks, goals)` → PriorityScore
- `get_peak_focus_windows(user_prefs)` → List[Tuple[time, time]]
- `calculate_estimated_completion_time(task, user_prefs)` → datetime

### GoalMapper Methods
- `create_goal(title, target_date, goal_type)` → Goal
- `link_task_to_goal(task_id, goal_id)` → bool
- `calculate_goal_progress(goal_id, tasks)` → float
- `get_goals_needing_attention()` → List[Goal]

### PrioritizationAgent Methods
- `process_query(query)` → str
- Handles: prioritization, goals, scheduling, analytics queries

## 🎉 Success Metrics

The Intelligent Prioritization Engine successfully implements:

1. **Multi-factor scoring** with 5 key factors
2. **Real-time re-ranking** with automatic updates
3. **SMART goal mapping** with progress tracking
4. **Natural language processing** for user queries
5. **Focus window optimization** for peak productivity
6. **Comprehensive analytics** and insights
7. **Seamless integration** with existing systems

All features from your original requirements have been implemented and tested successfully!