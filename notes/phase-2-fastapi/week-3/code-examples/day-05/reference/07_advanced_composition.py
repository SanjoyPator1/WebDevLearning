from fastapi import FastAPI, Depends

app = FastAPI()

# --- 1. Service Container (Composition) ---
class Database:
    def query(self): return "DB Data"

class Logger:
    def log(self, msg): print(f"LOG: {msg}")

# Container class that initializes other dependencies
class ServiceContainer:
    def __init__(
        self,
        db: Database = Depends(Database),
        logger: Logger = Depends(Logger)
    ):
        self.db = db
        self.logger = logger

@app.get("/composition")
async def endpoint(services: ServiceContainer = Depends()):
    # We only inject one object, but get access to all services
    services.logger.log("Querying DB")
    return {"data": services.db.query()}


# --- 2. Factory Pattern ---
class EmailService:
    def send(self, msg): return f"Emailing: {msg}"

class SMSService:
    def send(self, msg): return f"SMSing: {msg}"

def get_notification_service(channel: str):
    """
    Returns a dependency function based on config/param
    """
    def dependency():
        if channel == "email":
            return EmailService()
        elif channel == "sms":
            return SMSService()
    return dependency

@app.get("/notify/email")
async def notify_email(service = Depends(get_notification_service("email"))):
    return {"result": service.send("Hello")}

@app.get("/notify/sms")
async def notify_sms(service = Depends(get_notification_service("sms"))):
    return {"result": service.send("Hello")}