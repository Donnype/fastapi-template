from fastapi import Depends, FastAPI, HTTPException
from starlette.responses import RedirectResponse
from starlette.status import HTTP_201_CREATED

from api.repository import Todo, TodoFilter, TodoRepository, create_todo_repository

app = FastAPI(swagger_ui_parameters={"tryItOutEnabled": True})


@app.get("/")
async def root():
    return RedirectResponse(app.docs_url)


@app.post("/create/{key}", status_code=HTTP_201_CREATED)
def create(key: str, value: str, todo_repository: TodoRepository = Depends(create_todo_repository)):
    with todo_repository as repo:
        repo.save(Todo(key=key, value=value))


@app.get("/get/{key}", response_model=Todo | None)
def get(key: str, todo_repository: TodoRepository = Depends(create_todo_repository)):
    with todo_repository as repo:
        todo = repo.get_by_key(key)

        if not todo:
            raise HTTPException(status_code=404, detail="Todo not found")

        return todo


@app.get("/find", response_model=list[Todo])
def find(todo_filter: TodoFilter = Depends(), todo_repository: TodoRepository = Depends(create_todo_repository)):
    with todo_repository as repo:
        return repo.get(todo_filter)
