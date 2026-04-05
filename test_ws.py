import asyncio, json, websockets

async def test_ws():
    async with websockets.connect('ws://localhost:8000/ws') as ws:
        await ws.send(json.dumps({'type': 'reset', 'data': {'task_id': 'task1'}}))
        resp = await ws.recv()
        data = json.loads(resp)
        print('Type:', data.get('type'))
        obs = data.get('data', {})
        print('Task:', obs.get('task_id'))
        print('VMs:', len(obs.get('vms', [])))
        print('Done:', obs.get('done'))
        
        action = {
            'shutdown': ['vm-003', 'vm-005'],
            'scale_up': [],
            'scale_down': [],
            'migrate': [],
            'reasoning': 'Both VMs are idle: cpu under 2%, uptime over 6 hours'
        }
        await ws.send(json.dumps({'type': 'step', 'data': action}))
        resp = await ws.recv()
        data = json.loads(resp)
        obs = data.get('data', {})
        print('Reward:', obs.get('reward'))
        print('Done:', obs.get('done'))

asyncio.run(test_ws())
