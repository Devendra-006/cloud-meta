import asyncio, json, websockets

async def test_ws():
    async with websockets.connect('ws://localhost:8000/ws') as ws:
        await ws.send(json.dumps({'type': 'reset', 'data': {'task_id': 'task1'}}))
        resp = await ws.recv()
        print('=== RAW RESET RESPONSE ===')
        print(resp[:500])
        print()
        
        data = json.loads(resp)
        obs = data.get('data', {})
        print('=== PARSED OBSERVATION KEYS ===')
        print(list(obs.keys()))
        print()
        print('task_id:', obs.get('task_id'))
        print('vms count:', len(obs.get('vms', [])))
        print('done:', obs.get('done'))
        print('reward:', obs.get('reward'))

asyncio.run(test_ws())
