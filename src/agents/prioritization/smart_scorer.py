import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from .enhanced_models import UserBehavior, ContextState, SmartPriorityScore, TaskPattern, ProactiveInsight

class SmartPriorityScorer:
    def __init__(self):
        self.user_behavior = self._load_user_behavior()
        self.task_patterns = self._load_task_patterns()
        
    def calculate_smart_priority(self, task: Dict, context: ContextState, all_tasks: List = None) -> SmartPriorityScore:
        """Calculate priority with context awareness and learning"""
        
        # Base priority calculation
        base_score = self._calculate_base_score(task)
        
        # Context multipliers
        context_multiplier = self._calculate_context_multiplier(task, context)
        energy_match = self._calculate_energy_match(task, context)
        momentum_bonus = self._calculate_momentum_bonus(task, context)
        urgency_factor = self._calculate_urgency_factor(task)
        
        # Final score calculation
        final_score = (base_score * context_multiplier * energy_match) + momentum_bonus + urgency_factor
        final_score = min(10.0, max(0.0, final_score))
        
        # Generate reasoning
        reasoning = self._generate_smart_reasoning(task, context, {
            'base': base_score,
            'context': context_multiplier,
            'energy': energy_match,
            'momentum': momentum_bonus,
            'urgency': urgency_factor
        })
        
        # Calculate confidence based on data availability
        confidence = self._calculate_confidence(task)
        
        # Suggest next best time if not optimal now
        next_best_time = self._suggest_next_best_time(task, context) if final_score < 6.0 else None
        
        return SmartPriorityScore(
            base_score=base_score,
            context_multiplier=context_multiplier,
            energy_match=energy_match,
            momentum_bonus=momentum_bonus,
            urgency_factor=urgency_factor,
            final_score=round(final_score, 1),
            confidence=confidence,
            reasoning=reasoning,
            next_best_time=next_best_time
        )
    
    def _calculate_base_score(self, task: Dict) -> float:
        """Calculate base priority score"""
        score = 5.0  # Default
        
        # Priority level
        priority = task.get('priority', 'medium').lower()
        if priority == 'high':
            score += 2.0
        elif priority == 'low':
            score -= 1.0
        
        # Due date urgency
        due_date = task.get('due_date')
        if due_date:
            try:
                if isinstance(due_date, str):
                    due_dt = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                    days_until = (due_dt - datetime.now()).days
                    
                    if days_until < 0:  # Overdue
                        score += 3.0
                    elif days_until == 0:  # Due today
                        score += 2.0
                    elif days_until <= 2:  # Due soon
                        score += 1.0
            except:
                pass
        
        return min(10.0, max(1.0, score))
    
    def _calculate_context_multiplier(self, task: Dict, context: ContextState) -> float:
        """Calculate context-based multiplier"""
        multiplier = 1.0
        
        # Time availability match
        estimated_hours = task.get('estimated_hours', 1.0)
        available_hours = context.available_time_block / 60.0
        
        if estimated_hours <= available_hours:
            if estimated_hours <= available_hours * 0.5:  # Quick task
                multiplier += 0.3
            else:  # Good fit
                multiplier += 0.1
        else:  # Won't fit
            multiplier -= 0.4
        
        # Focus mode bonus
        if context.focus_mode:
            if estimated_hours >= 1.0:  # Deep work task
                multiplier += 0.5
            else:  # Quick task during focus
                multiplier -= 0.2
        
        return max(0.5, min(2.0, multiplier))
    
    def _calculate_energy_match(self, task: Dict, context: ContextState) -> float:
        """Match task complexity with current energy"""
        task_complexity = self._estimate_task_complexity(task)
        energy_level = context.energy_level
        
        # Perfect match bonus
        if abs(task_complexity - energy_level) <= 2.0:
            return 1.2
        elif abs(task_complexity - energy_level) <= 4.0:
            return 1.0
        else:
            return 0.7
    
    def _calculate_momentum_bonus(self, task: Dict, context: ContextState) -> float:
        """Bonus for maintaining momentum"""
        bonus = 0.0
        
        # Recent completion momentum
        if context.current_momentum == "high":
            bonus += 1.0
        elif context.current_momentum == "low":
            bonus -= 0.5
        
        # Similar task momentum
        task_type = self._categorize_task(task)
        recent_types = [self._categorize_task({'title': t}) for t in context.recent_completions[-3:]]
        
        if task_type in recent_types:
            bonus += 0.5  # Continue similar work
        
        return bonus
    
    def _calculate_urgency_factor(self, task: Dict) -> float:
        """Calculate urgency boost"""
        urgency = 0.0
        
        # Deadline pressure
        due_date = task.get('due_date')
        if due_date:
            try:
                if isinstance(due_date, str):
                    due_dt = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                    hours_until = (due_dt - datetime.now()).total_seconds() / 3600
                    
                    if hours_until < 0:  # Overdue
                        urgency += 2.0
                    elif hours_until < 24:  # Due today
                        urgency += 1.5
                    elif hours_until < 48:  # Due tomorrow
                        urgency += 1.0
            except:
                pass
        
        return urgency
    
    def _generate_smart_reasoning(self, task: Dict, context: ContextState, scores: Dict) -> str:
        """Generate human-readable reasoning"""
        reasons = []
        
        # Energy matching
        if scores['energy'] > 1.1:
            reasons.append("perfect energy match")
        elif scores['energy'] < 0.8:
            reasons.append("energy mismatch")
        
        # Time fit
        if scores['context'] > 1.2:
            reasons.append("fits available time perfectly")
        elif scores['context'] < 0.8:
            reasons.append("might not fit current time slot")
        
        # Momentum
        if scores['momentum'] > 0.5:
            reasons.append("builds on recent momentum")
        elif scores['momentum'] < -0.2:
            reasons.append("breaks current flow")
        
        # Urgency
        if scores['urgency'] > 1.5:
            reasons.append("urgent deadline")
        elif scores['urgency'] > 0.5:
            reasons.append("approaching deadline")
        
        # Focus mode
        if context.focus_mode:
            estimated_hours = task.get('estimated_hours', 1.0)
            if estimated_hours >= 1.0:
                reasons.append("good for deep focus")
            else:
                reasons.append("too quick for focus mode")
        
        return ", ".join(reasons) if reasons else "standard priority"
    
    def _estimate_task_complexity(self, task: Dict) -> float:
        """Estimate task complexity (1-10 scale)"""
        # Simple heuristics - in production, use ML
        title = task.get('title', '').lower()
        description = task.get('description', '').lower()
        
        complexity = 5.0  # Default
        
        # High complexity indicators
        high_complexity_words = ['design', 'architecture', 'research', 'analysis', 'strategy', 'complex', 'difficult']
        if any(word in title + description for word in high_complexity_words):
            complexity += 2.0
        
        # Low complexity indicators
        low_complexity_words = ['email', 'call', 'quick', 'simple', 'update', 'check', 'review']
        if any(word in title + description for word in low_complexity_words):
            complexity -= 2.0
        
        # Estimated hours
        estimated_hours = task.get('estimated_hours', 1.0)
        if estimated_hours > 4:
            complexity += 1.0
        elif estimated_hours < 0.5:
            complexity -= 1.0
        
        return max(1.0, min(10.0, complexity))
    
    def _categorize_task(self, task: Dict) -> str:
        """Categorize task type for momentum tracking"""
        title = task.get('title', '').lower()
        
        if any(word in title for word in ['email', 'message', 'call', 'meeting']):
            return 'communication'
        elif any(word in title for word in ['code', 'develop', 'program', 'bug', 'fix']):
            return 'development'
        elif any(word in title for word in ['design', 'create', 'draft', 'write']):
            return 'creative'
        elif any(word in title for word in ['review', 'analyze', 'research', 'study']):
            return 'analytical'
        else:
            return 'general'
    
    def _suggest_next_best_time(self, task: Dict, context: ContextState) -> Optional[datetime]:
        """Suggest when this task would be better to do"""
        current_hour = context.current_time.hour
        task_complexity = self._estimate_task_complexity(task)
        
        # Find next peak productivity hour that matches task complexity
        for peak_hour in self.user_behavior.productivity_peaks:
            if peak_hour > current_hour:
                # Check if energy level at that time would match task
                expected_energy = self.user_behavior.energy_patterns.get(peak_hour, 7.0)
                if abs(expected_energy - task_complexity) <= 2.0:
                    next_time = context.current_time.replace(hour=peak_hour, minute=0, second=0)
                    return next_time
        
        # If no good time today, suggest tomorrow morning
        tomorrow = context.current_time + timedelta(days=1)
        return tomorrow.replace(hour=9, minute=0, second=0)
    
    def _calculate_confidence(self, task: Dict) -> float:
        """Calculate confidence in the priority score"""
        confidence = 0.7  # Base confidence
        
        # More data = higher confidence
        if task.get('due_date'):
            confidence += 0.1
        if task.get('estimated_hours'):
            confidence += 0.1
        if task.get('description'):
            confidence += 0.1
        
        return min(1.0, confidence)
    
    def generate_proactive_insights(self, tasks: List[Dict], context: ContextState) -> List[ProactiveInsight]:
        """Generate proactive insights and suggestions"""
        insights = []
        
        # Check for overdue tasks
        overdue_tasks = []
        for task in tasks:
            if task.get('status') != 'completed' and task.get('due_date'):
                try:
                    due_dt = datetime.fromisoformat(task['due_date'].replace('Z', '+00:00'))
                    if due_dt < datetime.now():
                        overdue_tasks.append(task)
                except:
                    pass
        
        if overdue_tasks:
            insights.append(ProactiveInsight(
                type="warning",
                message=f"⚠️ You have {len(overdue_tasks)} overdue tasks that need immediate attention!",
                priority=5,
                action_required=True
            ))
        
        # Check for perfect timing opportunities
        if context.energy_level >= 8.0 and context.available_time_block >= 120:
            insights.append(ProactiveInsight(
                type="opportunity",
                message="🚀 Perfect time for deep work! Your energy is high and you have a good time block.",
                priority=4
            ))
        
        # Check for low energy with complex tasks
        complex_tasks = [t for t in tasks if self._estimate_task_complexity(t) >= 7.0 and t.get('status') != 'completed']
        if context.energy_level <= 4.0 and complex_tasks:
            insights.append(ProactiveInsight(
                type="suggestion",
                message="💡 Your energy is low. Consider doing quick wins first to build momentum.",
                priority=3
            ))
        
        # Celebrate recent completions
        if len(context.recent_completions) >= 3:
            insights.append(ProactiveInsight(
                type="celebration",
                message="🎉 Great momentum! You've completed 3 tasks recently. Keep it up!",
                priority=2
            ))
        
        return insights
    
    def learn_from_completion(self, task: Dict, actual_duration: float, user_satisfaction: float):
        """Learn from task completion to improve future predictions"""
        task_id = task.get('id', 'unknown')
        
        # Update task patterns
        if task_id not in self.task_patterns:
            self.task_patterns[task_id] = TaskPattern(task_id=task_id)
        
        pattern = self.task_patterns[task_id]
        pattern.actual_duration.append(actual_duration)
        pattern.completion_times.append(datetime.now().hour)
        pattern.user_satisfaction = user_satisfaction
        
        # Update user behavior
        current_hour = datetime.now().hour
        if current_hour not in self.user_behavior.energy_patterns:
            self.user_behavior.energy_patterns[current_hour] = 7.0
        
        # Adjust energy pattern based on satisfaction
        if user_satisfaction >= 8.0:
            self.user_behavior.energy_patterns[current_hour] += 0.1
        elif user_satisfaction <= 4.0:
            self.user_behavior.energy_patterns[current_hour] -= 0.1
        
        # Save learning data
        self._save_user_behavior()
        self._save_task_patterns()
    
    def _load_user_behavior(self) -> UserBehavior:
        """Load user behavior from storage"""
        try:
            behavior_file = "src/data/user_behavior.json"
            if os.path.exists(behavior_file):
                with open(behavior_file, 'r') as f:
                    data = json.load(f)
                    return UserBehavior(**data)
        except:
            pass
        return UserBehavior()
    
    def _save_user_behavior(self):
        """Save user behavior to storage"""
        try:
            os.makedirs("src/data", exist_ok=True)
            with open("src/data/user_behavior.json", 'w') as f:
                json.dump(self.user_behavior.dict(), f, default=str, indent=2)
        except Exception as e:
            print(f"Failed to save user behavior: {e}")
    
    def _load_task_patterns(self) -> Dict[str, TaskPattern]:
        """Load task patterns from storage"""
        try:
            patterns_file = "src/data/task_patterns.json"
            if os.path.exists(patterns_file):
                with open(patterns_file, 'r') as f:
                    data = json.load(f)
                    return {k: TaskPattern(**v) for k, v in data.items()}
        except:
            pass
        return {}
    
    def _save_task_patterns(self):
        """Save task patterns to storage"""
        try:
            os.makedirs("src/data", exist_ok=True)
            patterns_dict = {k: v.dict() for k, v in self.task_patterns.items()}
            with open("src/data/task_patterns.json", 'w') as f:
                json.dump(patterns_dict, f, default=str, indent=2)
        except Exception as e:
            print(f"Failed to save task patterns: {e}")