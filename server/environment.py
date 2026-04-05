import json, uuid, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from openenv.core.env_server import Environment
from models import CloudCostAction, CloudCostObservation, CloudCostState
from graders.grader import grade

TASKS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'tasks')
MAX_STEPS = {'task1': 1, 'task2': 3, 'task3': 5}

class CloudCostEnvironment(Environment):
    def __init__(self, task_id: str = 'task1'):
        self._task_id = task_id
        self._task_data = {}
        self._state = CloudCostState.model_construct(
            episode_id=None,
            step_count=0,
            task_id=task_id,
            ground_truth={},
            cumulative_reward=0.0,
            best_step_reward=0.0,
            task_data={},
        )
        self._done = False
        self._last_reward = 0.0

    def reset(self, task_id: str = None) -> CloudCostObservation:
        if task_id:
            self._task_id = task_id
        task_file = os.path.join(TASKS_DIR, f'{self._task_id}.json')
        with open(task_file) as f:
            self._task_data = json.load(f)
        gt = self._task_data['ground_truth']
        gt['vm_costs'] = {v['id']: v['cost_per_hr'] for v in self._task_data['vms']}
        self._done = False
        self._last_reward = 0.0
        self._state = CloudCostState.model_construct(
            episode_id=str(uuid.uuid4()),
            step_count=0,
            task_id=self._task_id,
            ground_truth=gt,
            cumulative_reward=0.0,
            best_step_reward=0.0,
            task_data=self._task_data,
        )
        return self._make_obs(feedback='')

    def step(self, action: CloudCostAction) -> CloudCostObservation:
        if self._done:
            raise RuntimeError('Episode done. Call reset() to start a new episode.')
        self._state.step_count += 1
        result = grade(action, self._task_id, self._state.ground_truth)
        self._last_reward = result.total_score
        self._state.cumulative_reward = max(
            self._state.cumulative_reward, result.total_score
        )
        self._state.best_step_reward = max(
            self._state.best_step_reward, result.total_score
        )
        max_steps = MAX_STEPS.get(self._task_id, 1)
        done = result.total_score >= 0.95 or self._state.step_count >= max_steps
        self._done = done
        feedback = self._build_feedback(action, result)
        obs = self._make_obs(feedback=feedback)
        obs.done = done
        obs.reward = result.total_score
        obs.step_number = self._state.step_count
        return obs

    @property
    def state(self) -> CloudCostState:
        return self._state

    def _generate_alerts(self) -> list:
        """Generate alerts based on VM state."""
        alerts = []
        vms = self._task_data.get('vms', [])
        gt = self._state.ground_truth
        
        for vm in vms:
            vm_id = vm['id']
            cpu = vm.get('cpu_pct', 0)
            mem = vm.get('mem_pct', 0)
            sla_tier = vm.get('sla_tier', 0)
            uptime = vm.get('uptime_hrs', 0)
            cost = vm.get('cost_per_hr', 0)
            
            # Idle VM alert
            if cpu < 2 and uptime > 6:
                alerts.append({
                    "type": "warning",
                    "severity": "low",
                    "vm_id": vm_id,
                    "title": f"Idle VM Detected: {vm_id}",
                    "message": f"CPU at {cpu}%, uptime {uptime}h. Potential cost savings: ${cost}/hr",
                    "action": "shutdown",
                    "potential_savings": cost
                })
            
            # Critical CPU alert
            if cpu > 85:
                alerts.append({
                    "type": "danger",
                    "severity": "high",
                    "vm_id": vm_id,
                    "title": f"Critical CPU: {vm_id}",
                    "message": f"CPU usage at {cpu}%! SLA violation risk. Immediate action required.",
                    "action": "scale_up",
                    "risk": "sla_violation"
                })
            
            # Over-provisioned alert
            if cpu < 30 and mem < 40 and uptime > 24:
                alerts.append({
                    "type": "info",
                    "severity": "medium",
                    "vm_id": vm_id,
                    "title": f"Over-provisioned: {vm_id}",
                    "message": f"Low utilization (CPU {cpu}%, Mem {mem}%). Consider scaling down.",
                    "action": "scale_down",
                    "potential_savings": cost * 0.5
                })
            
            # Tier-1 SLA protected alert
            if sla_tier == 1:
                alerts.append({
                    "type": "protected",
                    "severity": "critical",
                    "vm_id": vm_id,
                    "title": f"Tier-1 SLA Protected: {vm_id}",
                    "message": "DO NOT SHUTDOWN. This VM has SLA compliance requirements.",
                    "action": "none",
                    "risk": "sla_violation"
                })
        
        return alerts

    def _make_obs(self, feedback: str) -> CloudCostObservation:
        td = self._task_data
        max_steps = MAX_STEPS.get(self._task_id, 1)
        alerts = self._generate_alerts()
        
        # Add summary stats to observations
        vms = td.get('vms', [])
        total_cost = sum(vm.get('cost_per_hr', 0) for vm in vms)
        idle_count = len([vm for vm in vms if vm.get('cpu_pct', 100) < 2 and vm.get('uptime_hrs', 0) > 6])
        potential_savings = sum(alert.get('potential_savings', 0) for alert in alerts if alert.get('action') == 'shutdown')
        
        obs = CloudCostObservation.model_construct(
            done=self._done,
            reward=self._last_reward if self._state.step_count > 0 else None,
            task_id=self._task_id,
            difficulty=td.get('difficulty', ''),
            vms=vms,
            budget_remaining=td.get('budget_remaining', 0.0),
            traffic_forecast=td.get('traffic_forecast', []),
            active_alerts=alerts,
            time_step=self._state.step_count,
            instructions=td.get('instructions', ''),
            feedback=feedback,
            step_number=self._state.step_count,
            max_steps=max_steps,
        )
        
        # Add extra fields for UI
        obs.total_hourly_cost = total_cost
        obs.idle_vm_count = idle_count
        obs.potential_savings = potential_savings
        
        return obs

    def _build_feedback(self, action, result) -> str:
        """Build detailed feedback based on action taken."""
        lines = []
        lines.append("=" * 50)
        lines.append(f"STEP {self._state.step_count} RESULTS")
        lines.append("=" * 50)
        lines.append("")
        
        # Overall score
        if result.total_score >= 0.9:
            score_emoji = "🎉"
            score_text = "EXCELLENT!"
        elif result.total_score >= 0.7:
            score_emoji = "✅"
            score_text = "GOOD"
        elif result.total_score >= 0.5:
            score_emoji = "⚠️"
            score_text = "NEEDS IMPROVEMENT"
        else:
            score_emoji = "❌"
            score_text = "POOR"
        
        lines.append(f"{score_emoji} Total Score: {result.total_score:.3f} ({score_text})")
        lines.append("")
        
        # Component breakdown
        lines.append("SCORE BREAKDOWN:")
        lines.append("-" * 30)
        
        cs_score = result.cost_savings * 0.45
        sla_score = result.sla_compliance * 0.35
        ap_score = result.action_precision * 0.15
        rs_score = result.reasoning
        
        lines.append(f"  💰 Cost Savings:     {result.cost_savings:.3f} x 0.45 = {cs_score:.3f}")
        lines.append(f"  🛡️  SLA Compliance:   {result.sla_compliance:.3f} x 0.35 = {sla_score:.3f}")
        lines.append(f"  🎯 Action Precision: {result.action_precision:.3f} x 0.15 = {ap_score:.3f}")
        lines.append(f"  📝 Reasoning:        {result.reasoning:.3f} x 0.05 = {rs_score:.3f}")
        lines.append("")
        
        # Action taken
        lines.append("ACTIONS TAKEN:")
        lines.append("-" * 30)
        if action.shutdown:
            lines.append(f"  🔴 Shutdown: {', '.join(action.shutdown)}")
        if action.scale_up:
            lines.append(f"  🟢 Scale Up: {', '.join(action.scale_up)}")
        if action.scale_down:
            lines.append(f"  🟡 Scale Down: {', '.join(action.scale_down)}")
        if action.migrate:
            lines.append(f"  🔵 Migrate: {', '.join([f'{v}->{r}' for v,r in action.migrate])}")
        if not any([action.shutdown, action.scale_up, action.scale_down, action.migrate]):
            lines.append("  No actions taken")
        lines.append("")
        
        # Recommendations
        lines.append("RECOMMENDATIONS:")
        lines.append("-" * 30)
        
        gt = self._state.ground_truth
        correct = gt.get('correct_actions', {})
        
        # What was correct
        for vm_id in action.shutdown:
            if vm_id in correct.get('shutdown', []):
                lines.append(f"  ✅ {vm_id}: Correct shutdown (idle VM)")
        
        for vm_id in action.shutdown:
            if vm_id in gt.get('tier1_vms', []):
                lines.append(f"  ❌ {vm_id}: VIOLATION - Tier-1 SLA protected!")
        
        for vm_id in action.shutdown:
            if vm_id not in correct.get('shutdown', []) and vm_id not in gt.get('tier1_vms', []):
                lines.append(f"  ⚠️  {vm_id}: Warning - Active VM being shutdown!")
        
        # What should have been done
        if self._state.step_count < MAX_STEPS.get(self._task_id, 1):
            still_idle = [v for v in gt.get('idle_vms', []) if v not in action.shutdown]
            if still_idle:
                lines.append(f"  💡 Still idle: {', '.join(still_idle)}")
        
        lines.append("")
        
        return '\n'.join(lines)
