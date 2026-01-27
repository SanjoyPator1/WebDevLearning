from fastapi import FastAPI, status, HTTPException, Response

app = FastAPI()

tasks = {"1": "Buy milk"}

@app.get("/tasks/{task_id}", status_code=status.HTTP_200_OK)
async def get_task(task_id: str):
    if task_id not in tasks:
        # Standard 404 Error
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Task not found"
        )
    return {"id": task_id, "task": tasks[task_id]}

@app.post("/tasks/", status_code=status.HTTP_201_CREATED)
async def create_task(task_id: str, name: str):
    """
    Returns HTTP 201 Created.
    Used when a resource is successfully created.
    """
    tasks[task_id] = name
    return {"id": task_id, "task": name}

@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: str):
    """
    Returns HTTP 204 No Content.
    Used for actions that have no response body (like deletion).
    """
    if task_id in tasks:
        del tasks[task_id]
    # We return standard Response with 204 to ensure body is empty
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@app.put("/tasks/{task_id}")
async def upsert_task(task_id: str, name: str, response: Response):
    """
    Dynamic Status Code:
    - 201 if we created a new task
    - 200 if we updated an existing one
    """
    if task_id not in tasks:
        tasks[task_id] = name
        response.status_code = status.HTTP_201_CREATED
        return {"msg": "Created new task"}
    else:
        tasks[task_id] = name
        response.status_code = status.HTTP_200_OK
        return {"msg": "Updated existing task"}