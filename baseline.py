import os, json
from models import CloudCostAction
from client import CloudCostEnv
from openai import OpenAI

SYSTEM_PROMPT = """You are an expert Cloud Infrastructure Optimizer.
Your job: analyze a fleet of virtual machines and take optimization actions.
Rules:
1. IDLE VM: cpu_pct < 2% AND uptime_hrs > 6 → ACTION: shutdown
2. OVER-PROVISIONED: cpu_pct < 20% AND NOT idle → ACTION: scale_down
3. UNDER-PROVISIONED: cpu_pct > 85% → ACTION: scale_up
4. NEVER take ANY action on VMs with sla_tier = 1
5. Do not exceed budget_remaining
Respond ONLY with a valid JSON object. No markdown. No explanation. Schema:
{
  "shutdown":  ["vm-id", ...],
  "scale_up":  ["vm-id", ...],
  "scale_down": ["vm-id", ...],
  "migrate":   [["vm-id", "region"], ...],
  "reasoning": "Your engineering explanation here"
}"""

def build_prompt(obs) -> str:
    vm_table = json.dumps(obs.vms, indent=2)
    return f"""Task: {obs.task_id} ({obs.difficulty})
Step: {obs.step_number}/{obs.max_steps}
Budget remaining: ${obs.budget_remaining:,.2f}
Traffic forecast (next 6hrs): {obs.traffic_forecast}
Active alerts: {obs.active_alerts}
VM Fleet:
{vm_table}
Instructions: {obs.instructions}
Previous feedback: {obs.feedback if obs.feedback else 'None (first step)'}
Respond ONLY with the JSON object."""

from typing import Optional

def parse_response(text: str) -> Optional[CloudCostAction]:
    """Parse LLM JSON response into a typed CloudCostAction."""
    text = text.strip()
    if text.startswith('```'):
        lines = text.split('\n')
        text = '\n'.join(lines[1:-1])
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        print(f'  [WARN] JSON parse error: {e}')
        print(f'  Raw: {text[:200]}')
        return None
    migrate = []
    for item in data.get('migrate', []):
        if isinstance(item, list) and len(item) == 2:
            migrate.append((item[0], item[1]))
    return CloudCostAction(
        shutdown=data.get('shutdown', []),
        scale_up=data.get('scale_up', []),
        scale_down=data.get('scale_down', []),
        migrate=migrate,
        reasoning=data.get('reasoning', ''),
    )

OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY')
ENV_URL = os.environ.get('CLOUDCOST_ENV_URL', 'http://localhost:8000')
MODEL = 'nvidia/nemotron-3-nano-30b-a3b:free'
TASKS = ['task1', 'task2', 'task3']

def run_baseline() -> dict:
    if not OPENROUTER_API_KEY:
        raise ValueError('OPENROUTER_API_KEY environment variable not set')
    client = OpenAI(
        api_key=OPENROUTER_API_KEY,
        base_url='https://openrouter.ai/api/v1',
    )
    results = {}
    print(f'CloudCostEnv Baseline | Model: {MODEL} | Env: {ENV_URL}')
    print('=' * 60)
    with CloudCostEnv(base_url=ENV_URL).sync() as env:
        for task_id in TASKS:
            print(f'\n[{task_id}] Running...')
            result = env.reset(task_id=task_id)
            obs = result.observation
            best_score = 0.0
            for step in range(obs.max_steps):
                print(f'  Step {step+1}/{obs.max_steps}...')
                try:
                    response = client.chat.completions.create(
                        model=MODEL,
                        temperature=0.0,
                        timeout=60,
                        messages=[
                            {'role': 'system', 'content': SYSTEM_PROMPT},
                            {'role': 'user',   'content': build_prompt(obs)},
                        ],
                    )
                    raw = response.choices[0].message.content
                except Exception as e:
                    print(f'  [ERROR] LLM call failed: {e}')
                    break
                action = parse_response(raw)
                if action is None:
                    break
                result = env.step(action)
                obs = result.observation
                best_score = max(best_score, result.reward or 0.0)
                print(f'  Score: {result.reward:.3f}')
                if obs.done:
                    break
            results[task_id] = best_score
            filled = int(best_score * 20)
            bar = '#' * filled + '-' * (20 - filled)
            print(f'  [{task_id}] Final: {best_score:.3f} [{bar}]')
    mean = sum(results.values()) / len(results)
    print(f'\nMean Score: {mean:.3f}')
    return results

if __name__ == '__main__':
    run_baseline()
