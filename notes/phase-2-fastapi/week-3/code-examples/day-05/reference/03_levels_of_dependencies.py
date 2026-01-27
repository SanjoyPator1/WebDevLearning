from fastapi import FastAPI, APIRouter, Depends, Header, HTTPException

# --- Dependencies ---
async def global_logger(user_agent: str = Header(...)):
    print(f"Global Log - User Agent: {user_agent}")

async def verify_admin(x_token: str = Header(...)):
    if x_token != "admin-secret":
        raise HTTPException(status_code=400, detail="Not an admin")
    print("Router Log - Admin verified")

async def get_current_user():
    return "Alice"

# --- App Setup (Global Dependency) ---
app = FastAPI(dependencies=[Depends(global_logger)])

# --- Router Setup (Router Dependency) ---
admin_router = APIRouter(
    prefix="/admin",
    dependencies=[Depends(verify_admin)] # Applies to all routes in this router
)

# --- Routes ---

@app.get("/public")
async def public_route():
    # Only Global Logger runs here
    return {"message": "Public area"}

@admin_router.get("/dashboard")
async def admin_dashboard(user: str = Depends(get_current_user)):
    # Global Logger + Verify Admin + Get User runs here
    return {"message": f"Welcome Admin {user}"}

app.include_router(admin_router)