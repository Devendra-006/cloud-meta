import os, json, time, httpx
from models import CloudCostAction
from openai import OpenAI

SYSTEM_PROMPT = """You are an expert Cloud Infrastructure Optimizer.
Rules:
1. IDLE VM: cpu_pct < 2% AND uptime_hrs > 6 -> ACTION: shutdown
2. OVER-PROVISIONED: cpu_pct < 20% AND NOT idle -> ACTION: scale_down
3. UNDER-PROVISIONED: cpu_pct > 85% -> ACTION: scale_up
4. NEVER take ANY action on VMs with sla_tier = 1
5. Do not exceed budget_remaining
Respond ONLY with a valid JSON object. No markdown. No explanation. Schema:
{"shutdown": [], "scale_up": [], "scale_down": [], "migrate": [], "reasoning": ""}"""

ENV_URL = os.environ.get('CLOUDCOST_ENV_URL', 'http://localhost:8000')
MODEL = 'stepfun/step-3.5-flash:free'
TASKS = ['task1', 'task2', 'task3']

def run_baseline() -> dict:
    api_key = os.environ.get('OPENROUTER_API_KEY')
    if not api_key:
        raise ValueError('OPENROUTER_API_KEY not set')
    
    llm = OpenAI(api_key=api_key, base_url='https://openrouter.ai/api/v1')
    results = {}
    
    print(f'CloudCostEnv Baseline | Model: {MODEL} | Env: {ENV_URL}')
    print('=' * 60)
    
    for task_id in TASKS:
        print(f'\n[{task_id}] Running...')
        
        with httpx.Client(timeout=30) as http:
            resp = http.post(f'{ENV_URL}/reset', json={'task_id': task_id})
            data = resp.json()
            obs = data.get('observation', data)
            
            best_score = 0.0
            for step in range(obs.get('max_steps', 1)):
                print(f'  Step {step+1}/{obs.get("max_steps", 1)}...')
                start = time.time()
                
                llm_resp = llm.chat.completions.create(
                    model=MODEL,
                    temperature=0.0,
                    timeout=60,
                    messages=[
                        {'role': 'system', 'content': SYSTEM_PROMPT},
                        {'role': 'user', 'content': f'Task: {obs.get("task_id")} ({obs.get("difficulty")})\nBudget: ${obs.get("budget_remaining", 0):,.2f}\nTraffic: {obs.get("traffic_forecast", [])}\nAlerts: {obs.get("active_alerts", [])}\nVM Fleet:\n{json.dumps(obs.get("vms", []), indent=2)}\nInstructions: {obs.get("instructions", "")}\nPrevious feedback: {obs.get("feedback", "") or "None"}\nReturn ONLY JSON.'},
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
                
                resp = http.post(f'{ENV_URL}/step', json={'action': action.model_dump()})
                data = resp.json()
                obs = data.get('observation', data)
                reward = obs.get('reward', 0.0) or 0.0
                best_score = max(best_score, reward)
                print(f'  Score: {reward:.3f}')
                
                if obs.get('done', False):
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
