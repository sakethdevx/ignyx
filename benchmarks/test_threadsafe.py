import asyncio
import threading
import time

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
threading.Thread(target=loop.run_forever, daemon=True).start()

async def my_coro():
    return "done"

start = time.time()
n = 50000
for _ in range(n):
    asyncio.run_coroutine_threadsafe(my_coro(), loop).result()
end = time.time()
print(f"Throughput: {n / (end - start)} ops/sec")
