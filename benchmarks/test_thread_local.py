import asyncio
import threading
import time

def worker():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    async def my_coro():
        await asyncio.sleep(0)
        return "done"
        
    for _ in range(20000):
        try:
            res = loop.run_until_complete(my_coro())
            if res != "done":
                print("Failed!")
        except Exception as e:
            print("Error:", repr(e))
            break

threads = [threading.Thread(target=worker) for _ in range(4)]
start = time.time()
for t in threads:
    t.start()
for t in threads:
    t.join()
end = time.time()

print(f"Throughput: {4 * 20000 / (end - start)} ops/sec")
