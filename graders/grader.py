from typing import List, Dict, Any, Tuple
from dataclasses import dataclass, field
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import CloudCostAction

REASONING_KEYWORDS = {
    'task1': ['idle', 'cpu', 'uptime', 'shutdown', 'cost'],
    'task2': ['idle', 'over-provisioned', 'under-provisioned', 'sla', 'budget', 'scale', 'tier'],
    'task3': ['forecast', 'spike', 'proactive', 'migration', 'sla', 'latency', 'pre-scale', 'failure', 'redistribute'],
}

def cost_savings_score(action: CloudCostAction, ground_truth: Dict) -> float:
    """
    Score = actual_savings / max_possible_savings
    Partial credit: each correct action contributes proportionally.
    """
    correct = ground_truth.get('correct_actions', {})
    max_savings = ground_truth.get('max_savings_per_hr', 1.0)
    if max_savings == 0:
        return 1.0  # Nothing to save = perfect score
    actual_savings = 0.0
    
    # Each correct shutdown contributes its cost_per_hr to savings
    for vm_id in action.shutdown:
        if vm_id in correct.get('shutdown', []):
            vm_cost = ground_truth.get('vm_costs', {}).get(vm_id, 0.0)
            actual_savings += vm_cost
    
    # Scale-down saves 50% of cost per VM
    for vm_id in action.scale_down:
        if vm_id in correct.get('scale_down', []):
            vm_cost = ground_truth.get('vm_costs', {}).get(vm_id, 0.0)
            actual_savings += vm_cost * 0.5
    
    return min(1.0, actual_savings / max_savings)

def sla_compliance_score(action: CloudCostAction, ground_truth: Dict) -> float:
    """
    Starts at 1.0. Deducts 0.15 per SLA violation.
    Tier-1 VM violations cost 0.30 (double penalty).
    Floor is 0.0.
    """
    tier1_vms = set(ground_truth.get('tier1_vms', []))
    score = 1.0
    all_actions = action.shutdown + action.scale_up + action.scale_down
    all_actions += [vm_id for vm_id, _ in action.migrate]
    
    for vm_id in all_actions:
        if vm_id in tier1_vms:
            score -= 0.30
    
    idle_vms = set(ground_truth.get('idle_vms', []))
    for vm_id in action.shutdown:
        if vm_id not in idle_vms and vm_id not in tier1_vms:
            score -= 0.15
    
    return max(0.0, score)

def action_precision_score(action: CloudCostAction, ground_truth: Dict) -> float:
    """
    Precision = correct_actions / total_actions_taken
    Rewards agents that take targeted, accurate actions.
    """
    correct = ground_truth.get('correct_actions', {})
    
    def score_list(taken: List[str], ground: List[str]) -> Tuple[int, int]:
        taken_set = set(taken)
        ground_set = set(ground)
        hits = len(taken_set & ground_set)
        total = len(taken_set | ground_set)
        return hits, total
    
    total_hits = 0
    total_possible = 0
    
    h, t = score_list(action.shutdown, correct.get('shutdown', []))
    total_hits += h; total_possible += t
    
    h, t = score_list(action.scale_up, correct.get('scale_up', []))
    total_hits += h; total_possible += t
    
    h, t = score_list(action.scale_down, correct.get('scale_down', []))
    total_hits += h; total_possible += t
    
    migrate_taken = [v for v, _ in action.migrate]
    migrate_correct = [v for v, _ in correct.get('migrate', [])]
    h, t = score_list(migrate_taken, migrate_correct)
    total_hits += h; total_possible += t
    
    if total_possible == 0:
        return 1.0
    
    return total_hits / total_possible

def reasoning_score(action: CloudCostAction, task_id: str) -> float:
    """
    Reasoning score normalized to [0, 1], then weighted.
    Max bonus = 0.05 (achieved with 5+ keyword matches)
    """
    keywords = REASONING_KEYWORDS.get(task_id, [])
    if not keywords:
        return 1.0
    
    text = action.reasoning.lower()
    hits = sum(1 for kw in keywords if kw in text)
    
    # Normalize to [0, 1] where 5+ hits = 1.0
    normalized = min(1.0, hits / 5.0)
    return normalized

def budget_exceeded_score(action: CloudCostAction, ground_truth: Dict) -> Tuple[bool, float]:
    """
    Check if proposed actions exceed budget.
    Returns (exceeded, actual_cost)
    """
    budget = ground_truth.get('budget_remaining', float('inf'))
    if budget == 0:
        return False, 0.0
    
    vm_costs = ground_truth.get('vm_costs', {})
    
    # Calculate cost of shutdown (we lose their cost savings, so negative impact)
    shutdown_cost = sum(vm_costs.get(vm_id, 0) for vm_id in action.shutdown)
    
    # Scale up costs more
    scale_up_cost = sum(vm_costs.get(vm_id, 0) * 1.5 for vm_id in action.scale_up)
    
    # Scale down saves money (negative cost)
    scale_down_savings = sum(vm_costs.get(vm_id, 0) * 0.5 for vm_id in action.scale_down)
    
    actual_cost = shutdown_cost + scale_up_cost - scale_down_savings
    
    # Check if any single action exceeds budget (simplified check)
    for vm_id in action.shutdown + action.scale_up:
        if vm_costs.get(vm_id, 0) > budget:
            return True, actual_cost
    
    return False, actual_cost

@dataclass
class GradeResult:
    total_score: float
    cost_savings: float
    sla_compliance: float
    action_precision: float
    reasoning: float
    budget_exceeded: bool
    breakdown: Dict[str, Any] = field(default_factory=dict)

def grade(action: CloudCostAction, task_id: str, ground_truth: Dict) -> GradeResult:
    """
    Master grading function with normalized weights.
    
    Score = 0.45*cost_savings + 0.35*sla_compliance + 0.15*action_precision + 0.05*reasoning
    
    If budget is exceeded, total score is capped at 0.40.
    """
    # Calculate component scores
    cs = cost_savings_score(action, ground_truth)
    sla = sla_compliance_score(action, ground_truth)
    ap = action_precision_score(action, ground_truth)
    rs = reasoning_score(action, task_id)
    
    # Calculate weighted total
    raw_total = 0.45*cs + 0.35*sla + 0.15*ap + 0.05*rs
    
    # Check budget constraint
    exceeded, _ = budget_exceeded_score(action, ground_truth)
    
    # Apply budget cap if exceeded
    if exceeded:
        total = min(raw_total, 0.40)
        budget_capped = True
    else:
        total = raw_total
        budget_capped = False
    
    total = round(max(0.0, min(1.0, total)), 4)
    
    return GradeResult(
        total_score=total,
        cost_savings=round(cs, 4),
        sla_compliance=round(sla, 4),
        action_precision=round(ap, 4),
        reasoning=round(rs, 4),
        budget_exceeded=budget_capped,
        breakdown={
            'cost_savings': round(cs, 4),
            'sla_compliance': round(sla, 4),
            'action_precision': round(ap, 4),
            'reasoning': round(rs, 4),
            'weights': {'cs': 0.45, 'sla': 0.35, 'ap': 0.15, 'rs': 0.05},
            'raw_total': round(raw_total, 4),
            'budget_exceeded': budget_capped,
        }
    )
