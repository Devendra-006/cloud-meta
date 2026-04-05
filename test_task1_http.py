import os, json, time, httpx
from models import CloudCostAction
from openai import OpenAI

llm = OpenAI(api_key=os.environ['OPENROUTER_API_KEY'], base_url='https://openrouter.ai/api/v1')
ENV_URL = 'http://localhost:8000'

print('[task1] Running...')
with httpx.Client(timeout=30) as http:
    resp = http.post(f'{ENV_URL}/reset', json={'task_id': 'task1'})
    data = resp.json()
    obs = data.get('observation', data)
    vms = obs.get('vms', [])
    print(f'  VMs: {len(vms)}, Max steps: {obs.get("max_steps")}')
    
    start = time.time()
    llm_resp = llm.chat.completions.create(
        model='stepfun/step-3.5-flash:free',
        temperature=0.0,
        timeout=60,
        messages=[
            {'role': 'system', 'content': 'Cloud optimizer. Return JSON with shutdown, scale_up, scale_down, migrate, reasoning. Rules: CPU<2%+uptime>6hrs=shutdown, CPU<20%=scale_down, CPU>85%=scale_up, NEVER touch sla_tier=1.'},
            {'role': 'user', 'content': f'VMs: {json.dumps(vms)}\nBudget: {obs.get("budget_remaining")}\nInstructions: {obs.get("instructions")}'},
        ],
    )
    raw = llm_resp.choices[0].message.content
    print(f'  LLM: {time.time()-start:.1f}s')
    
    action_data = json.loads(raw.strip())
    action = CloudCostAction(**action_data)
    print(f'  Action: shutdown={action.shutdown}')
    
    resp = http.post(f'{ENV_URL}/step', json={'action': action.model_dump()})
    data = resp.json()
    obs = data.get('observation', data)
    reward = obs.get('reward')
    if reward is None:
        reward = 0.0
    print(f'  Score: {reward:.3f}')
    print(f'  Done: {obs.get("done")}')
