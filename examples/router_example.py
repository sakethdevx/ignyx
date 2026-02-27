from ignyx import Ignyx, Router

app = Ignyx()
router = Router(prefix="/api/v1")

@router.get("/users")
async def get_users(request):
    return [{"id": 1, "name": "Alice"}]

@router.get("/users/{id}")
async def get_user_by_id(request, id: int):
    return {"id": id, "name": "Alice"}

app.include_router(router)
