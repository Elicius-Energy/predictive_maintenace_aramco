import asyncio
import websockets
import json
import time

async def measure():
    try:
        async with websockets.connect("ws://localhost:8000/ws/stream") as websocket:
            print("Connected to WS. Waiting for messages...")
            count = 0
            start = time.time()
            while True:
                msg = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                data = json.loads(msg)
                count += 1
                now = time.time()
                if data['type'] == 'sensor_data':
                    energy = data['data'].get('energy', {})
                    accel = data['data'].get('accel', {})
                    print(f"[{now - start:.2f}s] {data['data'].get('machine_id')} | P: {energy.get('P')}, V: {energy.get('V')}, I: {energy.get('I')} | ax: {accel.get('ax')}")
                if count >= 10:
                    break
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(measure())
