"""Tests for the grader module."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from models import CloudCostAction
from graders.grader import (
    cost_savings_score,
    sla_compliance_score,
    action_precision_score,
    reasoning_score,
    budget_exceeded_score,
    grade,
    GradeResult,
)

@pytest.fixture
def sample_ground_truth():
    return {
        'idle_vms': ['vm-003', 'vm-005'],
        'active_vms': ['vm-001', 'vm-002', 'vm-004'],
        'tier1_vms': ['vm-001'],
        'max_savings_per_hr': 0.36,
        'vm_costs': {
            'vm-001': 0.48,
            'vm-002': 0.24,
            'vm-003': 0.24,
            'vm-004': 0.48,
            'vm-005': 0.12,
        },
        'correct_actions': {
            'shutdown': ['vm-003', 'vm-005'],
            'scale_up': [],
            'scale_down': [],
            'migrate': [],
        },
        'budget_remaining': 1.0,
    }

class TestCostSavingsScore:
    def test_perfect_shutdown(self, sample_ground_truth):
        action = CloudCostAction(
            shutdown=['vm-003', 'vm-005'],
            scale_up=[], scale_down=[], migrate=[], reasoning=''
        )
        score = cost_savings_score(action, sample_ground_truth)
        assert score == 1.0

    def test_partial_shutdown(self, sample_ground_truth):
        action = CloudCostAction(
            shutdown=['vm-003'],
            scale_up=[], scale_down=[], migrate=[], reasoning=''
        )
        score = cost_savings_score(action, sample_ground_truth)
        assert 0.4 < score < 0.8

    def test_no_shutdown(self, sample_ground_truth):
        action = CloudCostAction(
            shutdown=[],
            scale_up=[], scale_down=[], migrate=[], reasoning=''
        )
        score = cost_savings_score(action, sample_ground_truth)
        assert score == 0.0

class TestSLAComplianceScore:
    def test_no_violations(self, sample_ground_truth):
        action = CloudCostAction(
            shutdown=['vm-003'],
            scale_up=[], scale_down=[], migrate=[], reasoning=''
        )
        score = sla_compliance_score(action, sample_ground_truth)
        assert score == 1.0

    def test_tier1_violation(self, sample_ground_truth):
        action = CloudCostAction(
            shutdown=['vm-001'],
            scale_up=[], scale_down=[], migrate=[], reasoning=''
        )
        score = sla_compliance_score(action, sample_ground_truth)
        assert score == 0.7  # 1.0 - 0.30

    def test_active_vm_shutdown(self, sample_ground_truth):
        action = CloudCostAction(
            shutdown=['vm-002'],
            scale_up=[], scale_down=[], migrate=[], reasoning=''
        )
        score = sla_compliance_score(action, sample_ground_truth)
        assert score == 0.85  # 1.0 - 0.15

    def test_multiple_violations(self, sample_ground_truth):
        action = CloudCostAction(
            shutdown=['vm-001', 'vm-002'],
            scale_up=[], scale_down=[], migrate=[], reasoning=''
        )
        score = sla_compliance_score(action, sample_ground_truth)
        assert abs(score - 0.55) < 0.001  # 1.0 - 0.30 - 0.15 (with float tolerance)

class TestActionPrecisionScore:
    def test_perfect_precision(self, sample_ground_truth):
        action = CloudCostAction(
            shutdown=['vm-003', 'vm-005'],
            scale_up=[], scale_down=[], migrate=[], reasoning=''
        )
        score = action_precision_score(action, sample_ground_truth)
        assert score == 1.0

    def test_partial_precision(self, sample_ground_truth):
        action = CloudCostAction(
            shutdown=['vm-003'],
            scale_up=[], scale_down=[], migrate=[], reasoning=''
        )
        score = action_precision_score(action, sample_ground_truth)
        assert score == 0.5

    def test_wrong_action(self, sample_ground_truth):
        action = CloudCostAction(
            shutdown=['vm-002'],
            scale_up=[], scale_down=[], migrate=[], reasoning=''
        )
        score = action_precision_score(action, sample_ground_truth)
        assert score == 0.0

class TestReasoningScore:
    def test_good_reasoning_task1(self):
        action = CloudCostAction(
            shutdown=['vm-003'],
            scale_up=[], scale_down=[], migrate=[],
            reasoning='Shutting down idle VM with CPU below 2%.'
        )
        score = reasoning_score(action, 'task1')
        assert score > 0.0

    def test_no_reasoning(self):
        action = CloudCostAction(
            shutdown=['vm-003'],
            scale_up=[], scale_down=[], migrate=[], reasoning=''
        )
        score = reasoning_score(action, 'task1')
        assert score == 0.0

    def test_max_reasoning(self):
        action = CloudCostAction(
            shutdown=['vm-003'],
            scale_up=[], scale_down=[], migrate=[],
            reasoning='idle cpu uptime shutdown cost idle cpu idle cost'
        )
        score = reasoning_score(action, 'task1')
        assert score == 1.0

class TestBudgetExceeded:
    def test_within_budget(self, sample_ground_truth):
        action = CloudCostAction(
            shutdown=['vm-003'],
            scale_up=[], scale_down=[], migrate=[], reasoning=''
        )
        exceeded, cost = budget_exceeded_score(action, sample_ground_truth)
        assert exceeded is False

    def test_exceeds_budget(self, sample_ground_truth):
        # Set very low budget
        sample_ground_truth['budget_remaining'] = 0.1
        action = CloudCostAction(
            shutdown=['vm-001'],  # 0.48/hr > 0.1 budget
            scale_up=[], scale_down=[], migrate=[], reasoning=''
        )
        exceeded, cost = budget_exceeded_score(action, sample_ground_truth)
        assert exceeded is True

class TestGrade:
    def test_perfect_action(self, sample_ground_truth):
        action = CloudCostAction(
            shutdown=['vm-003', 'vm-005'],
            scale_up=[], scale_down=[], migrate=[],
            reasoning='Shutting down idle VMs with CPU below 2% and uptime over 6 hours.'
        )
        result = grade(action, 'task1', sample_ground_truth)
        assert isinstance(result, GradeResult)
        assert result.total_score > 0.9
        assert result.cost_savings == 1.0
        assert result.sla_compliance == 1.0

    def test_tier1_violation_penalty(self, sample_ground_truth):
        action = CloudCostAction(
            shutdown=['vm-001'],
            scale_up=[], scale_down=[], migrate=[],
            reasoning='Shutting down VM.'
        )
        result = grade(action, 'task1', sample_ground_truth)
        assert result.sla_compliance == 0.7

    def test_budget_cap(self, sample_ground_truth):
        sample_ground_truth['budget_remaining'] = 0.1
        action = CloudCostAction(
            shutdown=['vm-001'],
            scale_up=[], scale_down=[], migrate=[],
            reasoning='Test action.'
        )
        result = grade(action, 'task1', sample_ground_truth)
        assert result.budget_exceeded is True
        assert result.total_score <= 0.40

    def test_breakdown_includes_weights(self, sample_ground_truth):
        action = CloudCostAction(
            shutdown=['vm-003'],
            scale_up=[], scale_down=[], migrate=[], reasoning=''
        )
        result = grade(action, 'task1', sample_ground_truth)
        assert 'weights' in result.breakdown
        assert result.breakdown['weights']['cs'] == 0.45
        assert result.breakdown['weights']['sla'] == 0.35

class TestEdgeCases:
    def test_duplicate_vm_ids(self, sample_ground_truth):
        action = CloudCostAction(
            shutdown=['vm-003', 'vm-003', 'vm-005'],  # Duplicate
            scale_up=[], scale_down=[], migrate=[], reasoning=''
        )
        score = cost_savings_score(action, sample_ground_truth)
        # Duplicates should not double-count
        assert score <= 1.0

    def test_empty_action(self, sample_ground_truth):
        action = CloudCostAction(
            shutdown=[], scale_up=[], scale_down=[], migrate=[], reasoning=''
        )
        score = cost_savings_score(action, sample_ground_truth)
        assert score == 0.0

    def test_zero_max_savings(self, sample_ground_truth):
        sample_ground_truth['max_savings_per_hr'] = 0
        action = CloudCostAction(
            shutdown=['vm-003'],
            scale_up=[], scale_down=[], migrate=[], reasoning=''
        )
        score = cost_savings_score(action, sample_ground_truth)
        assert score == 1.0  # Nothing to save = perfect

    def test_vm_in_multiple_actions(self, sample_ground_truth):
        # Same VM in shutdown and migrate should be handled
        action = CloudCostAction(
            shutdown=['vm-003'],
            scale_up=[], scale_down=[], 
            migrate=[('vm-003', 'us-west-2')],  # Same VM
            reasoning=''
        )
        score = sla_compliance_score(action, sample_ground_truth)
        assert score == 1.0  # vm-003 is not tier-1
