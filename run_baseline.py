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
5. Do not exceed budget_remaining
Respond ONLY with a valid JSON object. No markdown. No explanation. Schema:
{"shutdown": [], "scale_up": [], "scale_down": [], "migrate": [], "reasoning": ""}"""

client = OpenAI(api_key=os.environ['OPENROUTER_API_KEY'], base_url='https://openrouter.ai/api/v1')
results = {}

for task_id in ['task1', 'task2', 'task3']:
    print(f'\n[{task_id}] Starting...')
    try:
        with CloudCostEnv(base_url='http://localhost:8000').sync() as env:
            result = env.reset(task_id=task_id)
            obs = result.observation
            best_score = 0.0
            
            for step in range(obs.max_steps):
                print(f'  Step {step+1}/{obs.max_steps}...')
                start = time.time()
                
                resp = client.chat.completions.create(
                    model='stepfun/step-3.5-flash:free',
                    temperature=0.0,
                    timeout=60,
                    messages=[
                        {'role': 'system', 'content': SYSTEM_PROMPT},
                        {'role': 'user', 'content': f'Task: {obs.task_id} ({obs.difficulty})\nBudget: ${obs.budget_remaining:,.2f}\nTraffic: {obs.traffic_forecast}\nAlerts: {obs.active_alerts}\nVM Fleet:\n{json.dumps(obs.vms, indent=2)}\nInstructions: {obs.instructions}\nPrevious feedback: {obs.feedback or "None"}\nReturn ONLY JSON.'},
                    ],
                )
                raw = resp.choices[0].message.content
                print(f'  LLM response in {time.time()-start:.1f}s ({len(raw)} chars)')
                
                try:
                    data = json.loads(raw.strip())
                    action = CloudCostAction(
                        shutdown=data.get('shutdown', []),
                        scale_up=data.get('scale_up', []),
                        scale_down=data.get('scale_down', []),
                        migrate=[tuple(m) for m in data.get('migrate', [])],
                        reasoning=data.get('reasoning', ''),
                    )
                except Exception as e:
                    print(f'  [WARN] Parse error: {e}')
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
            
    except Exception as e:
        print(f'  [ERROR] {task_id} failed: {e}')
        results[task_id] = 0.0

mean = sum(results.values()) / len(results)
print(f'\n=== RESULTS ===')
for tid, score in results.items():
    print(f'  {tid}: {score:.3f}')
print(f'  Mean: {mean:.3f}')
