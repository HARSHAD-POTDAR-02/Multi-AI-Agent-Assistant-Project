#!/usr/bin/env python3
"""
Comprehensive test runner for Prioritization Agent
Tests the system with rich, contextual queries
"""
import sys
import os
from datetime import datetime, timezone, timedelta

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def run_comprehensive_tests():
    """Run comprehensive tests with rich context queries"""
    print("=" * 60)
    print("COMPREHENSIVE PRIORITIZATION AGENT TESTING")
    print("=" * 60)
    
    # Test queries organized by category
    test_categories = {
        "Task Creation": [
            "Create task: Finish quarterly sales report by Friday 3pm, estimated 4 hours of work",
            "Add task: Review marketing budget proposal due tomorrow morning, should take 2 hours",
            "Create urgent task: Fix production bug in payment system, critical priority, due today",
            "New task: Prepare presentation for client meeting next Monday, complex task needing 8 hours"
        ],
        
        "Goal Management": [
            "Create goal: Learn machine learning and complete 3 online courses by December 31st for career advancement",
            "Add professional goal: Increase team productivity by 25% through process improvements by Q2 2024",
            "Show progress on my learning goals and tell me which tasks are helping me achieve them",
            "What goals need attention? Show me goals that are behind schedule"
        ],
        
        "Complex Prioritization": [
            "I have 8 tasks due this week, 3 overdue items, and 2 quick 30-minute tasks. What should I work on right now?",
            "Prioritize my tasks considering I'm most productive between 9-11am and 2-4pm, and I have a big presentation tomorrow",
            "I'm feeling overwhelmed with 15 active tasks. Help me prioritize based on deadlines, effort, and my goal to finish the project by month-end",
            "It's Monday morning, I'm fresh and focused. Show me the most important tasks that align with my professional goals"
        ],
        
        "Scheduling & Focus": [
            "When should I work on my complex 6-hour project task considering my peak focus times and other commitments?",
            "Schedule my day optimally: I have 3 urgent tasks, 2 meetings, and prefer creative work in the morning",
            "I'm tired today and can only handle easy tasks. Show me quick wins under 1 hour that still move my goals forward",
            "I have 3 hours of deep focus time available. Which complex tasks deserve this prime mental energy?"
        ],
        
        "Analytics & Insights": [
            "Show me my productivity analytics for the past month including completion rates by priority level",
            "Analyze my goal progress and tell me which areas need more attention to stay on track",
            "How am I performing against my goals this quarter? Show progress by goal type",
            "What's my success rate with different effort estimates? Do I underestimate or overestimate time?"
        ],
        
        "Real-World Scenarios": [
            "I'm a project manager with 20 tasks, 4 team goals, 3 personal goals, and 2 overdue items. It's Tuesday 10am and I have 6 hours available. What's my optimal schedule?",
            "Emergency: Production is down, I have a client presentation in 2 hours, 3 team members are waiting for my input, and I haven't prepared for tomorrow's board meeting. Help me triage!",
            "I have 50 active tasks across 10 different projects. Help me create a manageable priority system",
            "As a software developer with coding tasks, meetings, code reviews, and learning goals, help me prioritize my technical work"
        ],
        
        "Edge Cases": [
            "All my tasks are marked urgent and due today. How do I realistically prioritize when everything is critical?",
            "I have no deadlines set for any of my 20 tasks. Help me create a priority order based on effort and goal alignment",
            "Prioritize my tasks but I haven't set effort estimates for most of them",
            "My goals are conflicting - career advancement requires 60-hour weeks but health goals need work-life balance. Help me prioritize"
        ]
    }
    
    try:
        from agents.prioritization import prioritization_agent
        
        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        test_results = {}
        
        for category, queries in test_categories.items():
            print(f"\n{'='*20} {category.upper()} {'='*20}")
            category_results = []
            
            for i, query in enumerate(queries, 1):
                total_tests += 1
                print(f"\nTest {i}: {query[:80]}{'...' if len(query) > 80 else ''}")
                
                try:
                    # Create state and run agent
                    state = {"user_query": query}
                    result = prioritization_agent(state)
                    
                    response = result.get('response', '')
                    response_length = len(response)
                    
                    # Basic validation
                    if response_length > 50 and "error" not in response.lower():
                        print(f"[PASS] Response length: {response_length} chars")
                        passed_tests += 1
                        category_results.append(("PASS", query, response_length))
                    else:
                        print(f"[FAIL] Short/error response: {response_length} chars")
                        print(f"Response: {response[:100]}...")
                        failed_tests += 1
                        category_results.append(("FAIL", query, response_length))
                        
                except Exception as e:
                    print(f"[ERROR] Exception: {str(e)}")
                    failed_tests += 1
                    category_results.append(("ERROR", query, str(e)))
            
            test_results[category] = category_results
        
        # Print summary
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        # Detailed results by category
        print("\nDETAILED RESULTS BY CATEGORY:")
        print("-" * 60)
        
        for category, results in test_results.items():
            category_passed = sum(1 for r in results if r[0] == "PASS")
            category_total = len(results)
            print(f"{category}: {category_passed}/{category_total} ({(category_passed/category_total)*100:.1f}%)")
            
            # Show failed tests
            failed_in_category = [r for r in results if r[0] != "PASS"]
            if failed_in_category:
                for status, query, info in failed_in_category:
                    print(f"  [{status}] {query[:60]}...")
        
        # Feature coverage analysis
        print("\nFEATURE COVERAGE ANALYSIS:")
        print("-" * 60)
        
        feature_keywords = {
            "Task Creation": ["create", "add", "new task"],
            "Goal Management": ["goal", "objective", "progress"],
            "Priority Scoring": ["prioritize", "priority", "urgent"],
            "Time Management": ["schedule", "focus", "time", "when"],
            "Analytics": ["analytics", "progress", "insights", "performance"],
            "Multi-factor": ["deadline", "effort", "energy", "complex"],
            "Real-time": ["right now", "today", "immediate"],
            "Dependencies": ["depends", "blocks", "waiting"],
            "Context Awareness": ["considering", "based on", "given that"]
        }
        
        for feature, keywords in feature_keywords.items():
            matching_tests = 0
            for category, queries in test_categories.items():
                for query in queries:
                    if any(keyword in query.lower() for keyword in keywords):
                        matching_tests += 1
            print(f"{feature}: {matching_tests} tests")
        
        print("\n" + "="*60)
        if passed_tests == total_tests:
            print("🎉 ALL TESTS PASSED! The prioritization agent handles complex scenarios well.")
        elif passed_tests > total_tests * 0.8:
            print("✅ MOSTLY SUCCESSFUL! Good performance with room for improvement.")
        elif passed_tests > total_tests * 0.6:
            print("⚠️  MODERATE SUCCESS. Several areas need attention.")
        else:
            print("❌ NEEDS WORK. Many tests failed - system needs debugging.")
        
        return passed_tests == total_tests
        
    except Exception as e:
        print(f"[CRITICAL ERROR] Test runner failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def run_stress_test():
    """Run stress tests with extreme scenarios"""
    print("\n" + "="*60)
    print("STRESS TESTING")
    print("="*60)
    
    stress_queries = [
        "I have 100 tasks, 20 goals, 15 overdue items, and 3 hours to work. Help me prioritize the chaos!",
        "Create 10 tasks: Task1 due today 2hrs, Task2 due tomorrow 4hrs, Task3 due next week 1hr, Task4 overdue 6hrs, Task5 no deadline 3hrs, Task6 urgent 30min, Task7 depends on Task4, Task8 blocks Task9, Task9 easy win, Task10 complex project 20hrs",
        "I'm a CEO with board meetings, investor calls, product launches, team management, strategic planning, crisis management, and personal life. It's 6am Monday and I have 18 hours of work to fit into 12 hours. Prioritize my impossible day!",
        "Everything is broken: servers down, clients angry, team confused, deadlines missed, budget overrun, and I have a performance review in 1 hour. What's the priority order for damage control?",
        "I haven't used the system in 6 months. I have 200 old tasks, 50 new ones, outdated goals, changed priorities, and no idea what's current. Help me restart and prioritize from scratch."
    ]
    
    try:
        from agents.prioritization import prioritization_agent
        
        for i, query in enumerate(stress_queries, 1):
            print(f"\nStress Test {i}:")
            print(f"Query: {query}")
            
            try:
                state = {"user_query": query}
                result = prioritization_agent(state)
                response = result.get('response', '')
                
                if len(response) > 100:
                    print(f"[PASS] Handled stress scenario ({len(response)} chars)")
                else:
                    print(f"[FAIL] Poor response to stress scenario")
                    
            except Exception as e:
                print(f"[ERROR] Failed stress test: {str(e)}")
        
    except Exception as e:
        print(f"[CRITICAL] Stress test setup failed: {str(e)}")

if __name__ == "__main__":
    print("Starting comprehensive prioritization agent testing...")
    
    # Run main tests
    success = run_comprehensive_tests()
    
    # Run stress tests
    run_stress_test()
    
    print(f"\nTesting completed. Overall success: {'YES' if success else 'NO'}")
    sys.exit(0 if success else 1)