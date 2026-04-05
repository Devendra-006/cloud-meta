import os, json, time
from models import CloudCostAction
from client import CloudCostEnv
from openai import OpenAI

llm = OpenAI(api_key=os.environ['OPENROUTER_API_KEY'], base_url='https://openrouter.ai/api/v1')

for task_id in ['task1', 'task2', 'task3']:
    print(f'\n[{task_id}] Running...')
    try:
        with CloudCostEnv(base_url='http://localhost:8000').sync() as env:
            result = env.reset(task_id=task_id)
            obs = result.observation
            best_score = 0.0
            
            for step in range(obs.max_steps):
                print(f'  Step {step+1}/{obs.max_steps}...')
                start = time.time()
                
                prompt_lines = [
                    f"Task: {obs.task_id} ({obs.difficulty})",
                    f"Budget: ${obs.budget_remaining:,.2f}",
                    f"VM Fleet: {json.dumps(obs.vms)}",
                    f"Instructions: {obs.instructions}",
                    f"Feedback: {obs.feedback or 'None'}",
                    "Return ONLY JSON with keys: shutdown, scale_up, scale_down, migrate, reasoning.",
                    "Rules: CPU<2%+uptime>6hrs=shutdown, CPU<20%=scale_down, CPU>85%=scale_up, NEVER touch sla_tier=1."
                ]
                prompt = '\n'.join(prompt_lines)
                
                llm_resp = llm.chat.completions.create(
                    model='stepfun/step-3.5-flash:free',
                    temperature=0.0,
                    timeout=60,
                    messages=[
                        {'role': 'system', 'content': 'Cloud optimizer. Return JSON only.'},
                        {'role': 'user', 'content': prompt},
                    ],
                )
                raw = llm_resp.choices[0].message.content
                print(f'  LLM: {time.time()-start:.1f}s')
                
                action_data = json.loads(raw.strip())
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
            
            filled = int(best_score * 20)
            bar = '#' * filled + '-' * (20 - filled)
            print(f'  [{task_id}] Final: {best_score:.3f} [{bar}]')
            
    except Exception as e:
        print(f'  [ERROR] {task_id} failed: {e}')
