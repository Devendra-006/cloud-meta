import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import CloudCostAction, CloudCostObservation, CloudCostState
from server.environment import CloudCostEnvironment

def test_reset_task1():
    """Test reset() returns valid observation for task1"""
    env = CloudCostEnvironment(task_id='task1')
    obs = env.reset(task_id='task1')
    assert isinstance(obs, CloudCostObservation), f'Expected CloudCostObservation, got {type(obs)}'
    assert obs.task_id == 'task1', f'Expected task_id=task1, got {obs.task_id}'
    assert len(obs.vms) == 5, f'Expected 5 VMs, got {len(obs.vms)}'
    assert obs.difficulty == 'easy', f'Expected difficulty=easy, got {obs.difficulty}'
    assert obs.max_steps == 1, f'Expected max_steps=1, got {obs.max_steps}'
    assert obs.budget_remaining > 0, f'Expected budget > 0, got {obs.budget_remaining}'
    print(f'Test 1 PASSED: reset task1 -> {len(obs.vms)} VMs, budget=${obs.budget_remaining:.2f}')

def test_step_task1_perfect():
    """Test perfect action on task1 returns high reward"""
    env = CloudCostEnvironment(task_id='task1')
    obs = env.reset(task_id='task1')
    action = CloudCostAction(shutdown=['vm-003', 'vm-005'], reasoning='Both VMs are idle: cpu under 2%, uptime over 6 hours')
    result_obs = env.step(action)
    assert result_obs.reward >= 0.7, f'Perfect action reward {result_obs.reward} < 0.7'
    assert result_obs.done == True, f'Expected done=True after perfect action'
    print(f'Test 2 PASSED: perfect action reward = {result_obs.reward:.3f}, done={result_obs.done}')

def test_step_task1_empty():
    """Test empty action on task1 returns low reward"""
    env = CloudCostEnvironment(task_id='task1')
    obs = env.reset(task_id='task1')
    action = CloudCostAction()
    result_obs = env.step(action)
    assert result_obs.reward < 0.5, f'Empty action reward {result_obs.reward} >= 0.5'
    print(f'Test 3 PASSED: empty action reward = {result_obs.reward:.3f}')

def test_step_task1_wrong():
    """Test wrong action (shutting down Tier-1) returns low reward"""
    env = CloudCostEnvironment(task_id='task1')
    obs = env.reset(task_id='task1')
    action = CloudCostAction(shutdown=['vm-001'], reasoning='Wrong action')
    result_obs = env.step(action)
    assert result_obs.reward < 0.5, f'Wrong action reward {result_obs.reward} >= 0.5'
    print(f'Test 4 PASSED: wrong action reward = {result_obs.reward:.3f}')

def test_state_property():
    """Test state property returns valid CloudCostState"""
    env = CloudCostEnvironment(task_id='task1')
    env.reset(task_id='task1')
    state = env.state
    assert isinstance(state, CloudCostState), f'Expected CloudCostState, got {type(state)}'
    assert state.task_id == 'task1', f'Expected state.task_id=task1, got {state.task_id}'
    assert state.step_count == 0, f'Expected step_count=0, got {state.step_count}'
    print(f'Test 5 PASSED: state -> task_id={state.task_id}, step_count={state.step_count}')

def test_reset_task2():
    """Test reset() returns valid observation for task2"""
    env = CloudCostEnvironment(task_id='task2')
    obs = env.reset(task_id='task2')
    assert len(obs.vms) == 15, f'Expected 15 VMs, got {len(obs.vms)}'
    assert obs.difficulty == 'medium', f'Expected difficulty=medium, got {obs.difficulty}'
    assert obs.max_steps == 3, f'Expected max_steps=3, got {obs.max_steps}'
    print(f'Test 6 PASSED: reset task2 -> {len(obs.vms)} VMs, max_steps={obs.max_steps}')

def test_reset_task3():
    """Test reset() returns valid observation for task3"""
    env = CloudCostEnvironment(task_id='task3')
    obs = env.reset(task_id='task3')
    assert len(obs.vms) == 30, f'Expected 30 VMs, got {len(obs.vms)}'
    assert obs.difficulty == 'hard', f'Expected difficulty=hard, got {obs.difficulty}'
    assert obs.max_steps == 5, f'Expected max_steps=5, got {obs.max_steps}'
    print(f'Test 7 PASSED: reset task3 -> {len(obs.vms)} VMs, max_steps={obs.max_steps}')

def test_done_after_max_steps():
    """Test episode ends after max_steps"""
    env = CloudCostEnvironment(task_id='task2')
    obs = env.reset(task_id='task2')
    for i in range(3):
        action = CloudCostAction()
        obs = env.step(action)
    assert obs.done == True, f'Expected done=True after max_steps, got {obs.done}'
    print(f'Test 8 PASSED: done after max_steps')

def test_error_after_done():
    """Test stepping after done raises RuntimeError"""
    env = CloudCostEnvironment(task_id='task1')
    env.reset(task_id='task1')
    action = CloudCostAction(shutdown=['vm-003', 'vm-005'], reasoning='Idle VMs')
    obs = env.step(action)
    assert obs.done == True
    try:
        env.step(action)
        assert False, 'Expected RuntimeError after done'
    except RuntimeError:
        pass
    print(f'Test 9 PASSED: RuntimeError raised after done')

def test_feedback_in_observation():
    """Test feedback contains score breakdown"""
    env = CloudCostEnvironment(task_id='task1')
    env.reset(task_id='task1')
    action = CloudCostAction(shutdown=['vm-003', 'vm-005'], reasoning='Idle VMs: cpu under 2%, uptime over 6 hours')
    obs = env.step(action)
    assert 'Cost Savings' in obs.feedback, f'Missing Cost Savings in feedback'
    assert 'SLA Compliance' in obs.feedback, f'Missing SLA Compliance in feedback'
    print(f'Test 10 PASSED: feedback contains score breakdown')

if __name__ == '__main__':
    test_reset_task1()
    test_step_task1_perfect()
    test_step_task1_empty()
    test_step_task1_wrong()
    test_state_property()
    test_reset_task2()
    test_reset_task3()
    test_done_after_max_steps()
    test_error_after_done()
    test_feedback_in_observation()
    print('\nALL ENVIRONMENT TESTS PASSED')
