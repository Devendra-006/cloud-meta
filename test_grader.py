import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import CloudCostAction
from graders.grader import grade, cost_savings_score, sla_compliance_score, action_precision_score, reasoning_score

def test_perfect_action():
    """Test 1: Perfect action scores >= 0.90"""
    ground_truth = {
        'correct_actions': {'shutdown': ['vm-003', 'vm-005'], 'scale_up': [], 'scale_down': [], 'migrate': []},
        'idle_vms': ['vm-003', 'vm-005'],
        'tier1_vms': ['vm-001'],
        'vm_costs': {'vm-003': 0.24, 'vm-005': 0.12},
        'max_savings_per_hr': 0.36,
    }
    action = CloudCostAction(shutdown=['vm-003', 'vm-005'], reasoning='Both VMs are idle: cpu under 2%, uptime over 6 hours, shutting down to save cost')
    result = grade(action, 'task1', ground_truth)
    assert result.total_score >= 0.90, f'Perfect action score {result.total_score} < 0.90'
    print(f'Test 1 PASSED: perfect action score = {result.total_score:.3f}')

def test_wrong_action():
    """Test 2: Wrong action scores <= 0.40"""
    ground_truth = {
        'correct_actions': {'shutdown': ['vm-003', 'vm-005'], 'scale_up': [], 'scale_down': [], 'migrate': []},
        'idle_vms': ['vm-003', 'vm-005'],
        'tier1_vms': ['vm-001'],
        'vm_costs': {'vm-001': 0.48},
        'max_savings_per_hr': 0.36,
    }
    action = CloudCostAction(shutdown=['vm-001'], reasoning='Shutting down vm-001')
    result = grade(action, 'task1', ground_truth)
    assert result.total_score <= 0.40, f'Wrong action score {result.total_score} > 0.40'
    print(f'Test 2 PASSED: wrong action score = {result.total_score:.3f}')

def test_empty_action():
    """Test 3: Empty action has cost_savings = 0.0"""
    ground_truth = {
        'correct_actions': {'shutdown': ['vm-003', 'vm-005'], 'scale_up': [], 'scale_down': [], 'migrate': []},
        'idle_vms': ['vm-003', 'vm-005'],
        'tier1_vms': ['vm-001'],
        'vm_costs': {},
        'max_savings_per_hr': 0.36,
    }
    action = CloudCostAction()
    cs = cost_savings_score(action, ground_truth)
    assert cs == 0.0, f'Empty action cost_savings {cs} != 0.0'
    print(f'Test 3 PASSED: empty action cost_savings = {cs:.3f}')

def test_partial_action():
    """Test 4: Partial action scores between 0.30-0.90"""
    ground_truth = {
        'correct_actions': {'shutdown': ['vm-003', 'vm-005'], 'scale_up': [], 'scale_down': [], 'migrate': []},
        'idle_vms': ['vm-003', 'vm-005'],
        'tier1_vms': ['vm-001'],
        'vm_costs': {'vm-003': 0.24},
        'max_savings_per_hr': 0.36,
    }
    action = CloudCostAction(shutdown=['vm-003'], reasoning='Shutting down idle vm-003')
    result = grade(action, 'task1', ground_truth)
    assert 0.30 <= result.total_score <= 0.90, f'Partial action score {result.total_score} not in range 0.30-0.90'
    print(f'Test 4 PASSED: partial action score = {result.total_score:.3f}')

def test_scale_down_score():
    """Test scale_down contributes 50% of cost"""
    ground_truth = {
        'correct_actions': {'shutdown': [], 'scale_up': [], 'scale_down': ['vm-002'], 'migrate': []},
        'idle_vms': [],
        'tier1_vms': [],
        'vm_costs': {'vm-002': 0.48},
        'max_savings_per_hr': 0.24,
    }
    action = CloudCostAction(scale_down=['vm-002'], reasoning='Over-provisioned VM scaled down')
    result = grade(action, 'task1', ground_truth)
    assert result.cost_savings >= 0.9, f'Scale down cost_savings {result.cost_savings} < 0.9'
    print(f'Test 5 PASSED: scale_down score = {result.total_score:.3f}')

def test_tier1_penalty():
    """Test Tier-1 VM penalty"""
    ground_truth = {
        'correct_actions': {'shutdown': [], 'scale_up': [], 'scale_down': [], 'migrate': []},
        'idle_vms': [],
        'tier1_vms': ['vm-008'],
        'vm_costs': {},
        'max_savings_per_hr': 0.0,
    }
    action = CloudCostAction(shutdown=['vm-008'], reasoning='Wrong action on Tier-1')
    result = grade(action, 'task1', ground_truth)
    assert result.sla_compliance <= 0.7, f'Tier-1 penalty sla_compliance {result.sla_compliance} > 0.7'
    print(f'Test 6 PASSED: Tier-1 penalty sla_compliance = {result.sla_compliance:.3f}')

if __name__ == '__main__':
    test_perfect_action()
    test_wrong_action()
    test_empty_action()
    test_partial_action()
    test_scale_down_score()
    test_tier1_penalty()
    print('\nALL GRADER TESTS PASSED')
