import asyncio
import threading

def run_coro():
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    async def my_coro():
        await asyncio.sleep(0)
        return "done"
        
    try:
        res = loop.run_until_complete(my_coro())
        print("Success:", res)
    except Exception as e:
        print("Error:", repr(e))

t = threading.Thread(target=run_coro)
t.start()
t.join()

t2 = threading.Thread(target=run_coro)
t2.start()
t2.join()
