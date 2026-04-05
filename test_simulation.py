"""
Test script for CloudCostEnv simulation with reasoning.
Tests different scenarios and verifies grading responses.
"""

import requests
import json

BASE_URL = "http://127.0.0.1:8000"


def test_reset(task_id="task1"):
    """Reset the environment with a task."""
    response = requests.post(f"{BASE_URL}/reset", json={"task_id": task_id})
    data = response.json()
    obs = data.get("observation", data)
    print(f"\n{'='*60}")
    print(f"RESET - Task: {task_id}")
    print(f"{'='*60}")
    print(f"Difficulty: {obs.get('difficulty')}")
    print(f"Budget: ${obs.get('budget_remaining', 0):.2f}")
    print(f"VMs: {len(obs.get('vms', []))}")
    print(f"Instructions: {obs.get('instructions', '')[:100]}...")
    
    for vm in obs.get("vms", []):
        is_idle = vm["cpu_pct"] < 2 and vm["uptime_hrs"] > 6
        status = "IDLE" if is_idle else "ACTIVE"
        print(f"  {vm['id']}: CPU={vm['cpu_pct']:.1f}% Mem={vm['mem_pct']:.1f}% "
              f"Cost=${vm['cost_per_hr']:.2f}/hr Uptime={vm['uptime_hrs']}h "
              f"SLA={vm['sla_tier']} [{status}]")
    
    return obs


def test_action(shutdown=None, scale_up=None, scale_down=None, migrate=None, reasoning=""):
    """Execute an action and get the result."""
    action = {
        "shutdown": shutdown or [],
        "scale_up": scale_up or [],
        "scale_down": scale_down or [],
        "migrate": migrate or [],
        "reasoning": reasoning,
    }
    
    print(f"\n{'='*60}")
    print(f"ACTION")
    print(f"{'='*60}")
    print(f"Shutdown: {action['shutdown']}")
    print(f"Scale Up: {action['scale_up']}")
    print(f"Scale Down: {action['scale_down']}")
    print(f"Migrate: {action['migrate']}")
    print(f"Reasoning: {reasoning}")
    
    response = requests.post(f"{BASE_URL}/step", json={"action": action})
    data = response.json()
    obs = data.get("observation", data)
    
    print(f"\nRESULT:")
    print(f"  Reward: {data.get('reward', obs.get('reward')):.3f}")
    print(f"  Done: {data.get('done', obs.get('done'))}")
    print(f"  Feedback:\n{obs.get('feedback', '')}")
    
    return data, obs


def test_scenario_1():
    """Test: Shut down correct idle VMs with good reasoning."""
    print("\n" + "="*70)
    print("SCENARIO 1: Correct idle VMs shutdown with technical reasoning")
    print("="*70)
    
    test_reset("task1")
    
    test_action(
        shutdown=["vm-003", "vm-005"],
        reasoning="Both VMs are idle: CPU utilization below 2%, uptime exceeds 6 hours. "
                  "These are prime candidates for shutdown as they consume resources "
                  "without serving any active workloads. Tier-0 SLA allows this operation."
    )


def test_scenario_2():
    """Test: Shut down wrong VMs (active VMs)."""
    print("\n" + "="*70)
    print("SCENARIO 2: Shutting down active VMs (should penalize)")
    print("="*70)
    
    test_reset("task1")
    
    test_action(
        shutdown=["vm-001", "vm-002"],
        reasoning="Shutting down VMs to save costs."
    )


def test_scenario_3():
    """Test: Shut down Tier-1 SLA VM (major penalty)."""
    print("\n" + "="*70)
    print("SCENARIO 3: Attempting to shut down Tier-1 SLA VM (major penalty)")
    print("="*70)
    
    test_reset("task1")
    
    test_action(
        shutdown=["vm-001"],
        reasoning="Shutting down vm-001 for cost optimization."
    )


def test_scenario_4():
    """Test: Empty action with no reasoning."""
    print("\n" + "="*70)
    print("SCENARIO 4: Empty action with minimal reasoning")
    print("="*70)
    
    test_reset("task1")
    
    test_action(
        shutdown=[],
        reasoning=""
    )


def test_scenario_5():
    """Test: Partial correct action with detailed reasoning."""
    print("\n" + "="*70)
    print("SCENARIO 5: Only one correct idle VM with detailed analysis")
    print("="*70)
    
    test_reset("task1")
    
    test_action(
        shutdown=["vm-003"],
        reasoning="Analysis of vm-003 reveals critical inefficiency: CPU usage at 0.8%, "
                  "memory at 3.1%, running for 187 hours with no active processes. "
                  "This represents pure cost overhead with zero service contribution. "
                  "Immediate shutdown recommended. vm-005 also shows similar patterns "
                  "but will be evaluated in next optimization cycle."
    )


def test_scenario_6():
    """Test: Shut down one correct + one wrong VM."""
    print("\n" + "="*70)
    print("SCENARIO 6: Mixed action - one correct idle VM + one active VM")
    print("="*70)
    
    test_reset("task1")
    
    test_action(
        shutdown=["vm-003", "vm-004"],
        reasoning="Optimizing fleet by shutting down idle and low-priority VMs."
    )


def test_scenario_7():
    """Test: All tasks with identical action."""
    print("\n" + "="*70)
    print("SCENARIO 7: Testing same action across all tasks")
    print("="*70)
    
    for task_id in ["task1", "task2", "task3"]:
        test_reset(task_id)
        test_action(
            shutdown=["vm-003"],
            reasoning="Removing underutilized resource to reduce operational costs."
        )


def interactive_mode():
    """Interactive mode for manual testing."""
    print("\n" + "="*70)
    print("INTERACTIVE MODE")
    print("="*70)
    print("Commands: reset <task_id>, action <shutdown> <reasoning>, quit")
    print()
    
    obs = test_reset("task1")
    
    while True:
        print("\n> ", end="")
        cmd = input().strip()
        
        if cmd == "quit":
            break
        elif cmd.startswith("reset"):
            parts = cmd.split()
            task_id = parts[1] if len(parts) > 1 else "task1"
            obs = test_reset(task_id)
        elif cmd.startswith("action"):
            parts = cmd.split("|")
            shutdown_str = parts[0].replace("action", "").strip()
            shutdown = [v.strip() for v in shutdown_str.split()] if shutdown_str else []
            reasoning = parts[1].strip() if len(parts) > 1 else ""
            test_action(shutdown=shutdown, reasoning=reasoning)
        elif cmd == "help":
            print("Commands:")
            print("  reset <task_id>     - Reset environment (task1, task2, task3)")
            print("  action <vms> | reasoning - Execute action")
            print("  quit                - Exit")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "interactive":
            interactive_mode()
        elif sys.argv[1] == "1":
            test_scenario_1()
        elif sys.argv[1] == "2":
            test_scenario_2()
        elif sys.argv[1] == "3":
            test_scenario_3()
        elif sys.argv[1] == "4":
            test_scenario_4()
        elif sys.argv[1] == "5":
            test_scenario_5()
        elif sys.argv[1] == "6":
            test_scenario_6()
        elif sys.argv[1] == "7":
            test_scenario_7()
        elif sys.argv[1] == "all":
            test_scenario_1()
            test_scenario_2()
            test_scenario_3()
            test_scenario_4()
            test_scenario_5()
            test_scenario_6()
            test_scenario_7()
        else:
            print(f"Unknown scenario: {sys.argv[1]}")
            print("Usage: python test_simulation.py [1-7|all|interactive]")
    else:
        print("CloudCostEnv Simulation Test")
        print("="*50)
        print("Usage: python test_simulation.py [scenario]")
        print()
        print("Scenarios:")
        print("  1 - Correct idle VMs with good reasoning")
        print("  2 - Shutting down active VMs")
        print("  3 - Shutting down Tier-1 SLA VM")
        print("  4 - Empty action with no reasoning")
        print("  5 - Partial correct with detailed analysis")
        print("  6 - Mixed action (correct + wrong)")
        print("  7 - Same action across all tasks")
        print("  all - Run all scenarios")
        print("  interactive - Manual testing mode")
        print()
        print("Example: python test_simulation.py 1")
