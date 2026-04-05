import os, json, time
from models import CloudCostAction
from client import CloudCostEnv
from openai import OpenAI

SYSTEM_PROMPT = """You are an expert Cloud Infrastructure Optimizer.
Rules:
1. IDLE VM: cpu_pct < 2% AND uptime_hrs > 6 -> ACTION: shutdown
2. OVER-PROVISIONED: cpu_pct < 20% AND NOT idle -> ACTION: scale_down
3. UNDER-PROVISIONED: cpu_pct > 85% -> ACTION: scale_up
4. NEVER take ANY action on VMs with sla_tier = 1
Respond ONLY with JSON: {"shutdown": [], "scale_up": [], "scale_down": [], "migrate": [], "reasoning": ""}"""

ENV_URL = os.environ.get('CLOUDCOST_ENV_URL', 'http://localhost:8000')
MODEL = 'nvidia/nemotron-3-nano-30b-a3b:free'
TASKS = ['task1', 'task2', 'task3']

def run_baseline():
    api_key = os.environ.get('OPENROUTER_API_KEY')
    if not api_key:
        raise ValueError('OPENROUTER_API_KEY not set')
    
    llm = OpenAI(api_key=api_key, base_url='https://openrouter.ai/api/v1')
    results = {}
    
    print(f'CloudCostEnv Baseline | Model: {MODEL} | Env: {ENV_URL}')
    print('=' * 60)
    
    for task_id in TASKS:
        print(f'\n[{task_id}] Running...')
        try:
            with CloudCostEnv(base_url=ENV_URL).sync() as env:
                result = env.reset(task_id=task_id)
                obs = result.observation
                best_score = 0.0
                
                for step in range(obs.max_steps):
                    print(f'  Step {step+1}/{obs.max_steps}...')
                    start = time.time()
                    
                    prompt = (
                        f"Task: {obs.task_id} ({obs.difficulty})\n"
                        f"Budget: ${obs.budget_remaining:,.2f}\n"
                        f"Traffic: {obs.traffic_forecast}\n"
                        f"Alerts: {obs.active_alerts}\n"
                        f"VM Fleet:\n{json.dumps(obs.vms, indent=2)}\n"
                        f"Instructions: {obs.instructions}\n"
                        f"Feedback: {obs.feedback or 'None'}\n"
                        f"Return ONLY JSON."
                    )
                    
                    llm_resp = llm.chat.completions.create(
                        model=MODEL,
                        temperature=0.0,
                        timeout=60,
                        messages=[
                            {'role': 'system', 'content': SYSTEM_PROMPT},
                            {'role': 'user', 'content': prompt},
                        ],
                    )
                    raw = llm_resp.choices[0].message.content
                    print(f'  LLM: {time.time()-start:.1f}s ({len(raw)} chars)')
                    
                    try:
                        action_data = json.loads(raw.strip())
                    except json.JSONDecodeError as e:
                        print(f'  [WARN] JSON parse error: {e}')
                        break
                    
                    action = CloudCostAction(
                        shutdown=action_data.get('shutdown', []),
                        scale_up=action_data.get('scale_up', []),
                        scale_down=action_data.get('scale_down', []),
                        migrate=[tuple(m) for m in action_data.get('migrate', [])],
                        reasoning=action_data.get('reasoning', ''),
                    )
                    
                    result = env.step(action)
                    obs = result.observation
                    reward = result.reward or 0.0
                    best_score = max(best_score, reward)
                    print(f'  Score: {reward:.3f}')
                    
                    if obs.done:
                        break
                
                results[task_id] = best_score
                filled = int(best_score * 20)
                bar = '#' * filled + '-' * (20 - filled)
                print(f'  [{task_id}] Final: {best_score:.3f} [{bar}]')
                
        except Exception as e:
            print(f'  [ERROR] {task_id} failed: {e}')
            results[task_id] = 0.0
    
    mean = sum(results.values()) / len(results)
    print(f'\nMean Score: {mean:.3f}')
    return results

if __name__ == '__main__':
    run_baseline()
