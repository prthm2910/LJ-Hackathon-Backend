import os
import urllib.parse
import sqlalchemy
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

# LangChain Imports
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import create_sql_agent

# Load environment variables from the .env file
load_dotenv()

# ==================================================
# 1. Configuration & Database
# ==================================================
DB_USER = os.environ.get("DB_USER", "postgres")
raw_pass = os.environ.get("DB_PASS", "default_password")
DB_PASS = urllib.parse.quote_plus(raw_pass)
DB_NAME = os.environ.get("DB_NAME", "fintrack")
PUBLIC_IP = os.environ.get("PUBLIC_IP", "127.0.0.1")
DB_PORT = os.environ.get("DB_PORT", "5432")

def get_engine():
    """Creates a SQLAlchemy engine using a standard connection string."""
    db_uri = f"postgresql+pg8000://{DB_USER}:{DB_PASS}@{PUBLIC_IP}:{DB_PORT}/{DB_NAME}"
    try:
        engine = sqlalchemy.create_engine(db_uri)
        # Test connection on creation
        with engine.connect() as connection:
            print("✅ Database connection successful.")
        return engine
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        raise

# ==================================================
# 2. AI Agent Setup
# ==================================================
agent_executor = None

def init_agent():
    """Initializes the LangChain SQL agent with Gemini LLM."""
    global agent_executor
    if "GOOGLE_API_KEY" not in os.environ or not os.environ["GOOGLE_API_KEY"]:
        raise ValueError("Error: GOOGLE_API_KEY environment variable not set or empty.")
    print("🚀 Initializing AI Agent...")
    db_engine = get_engine()
    db = SQLDatabase(db_engine)
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0, google_api_key=os.environ.get("GOOGLE_API_KEY"))
    agent_executor = create_sql_agent(llm, db=db, agent_type="openai-tools", verbose=True)
    print("🤖 AI Agent is ready and connected to the database.")

try:
    init_agent()
except Exception as e:
    print(f"🔥 Critical error during AI Agent initialization: {e}")
    agent_executor = None

# ==================================================
# 3. FastAPI Server
# ==================================================
app = FastAPI(
    title="AI Personal Finance Assistant",
    description="A comprehensive API for your financial data.",
    version="1.0.0"
)

# Add CORS middleware to allow requests from your React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"], # Add your frontend's URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic Models for API ---
class QueryRequest(BaseModel):
    question: str
    user_id: str

class PermissionsUpdateRequest(BaseModel):
    perm_assets: bool
    perm_liabilities: bool
    perm_transactions: bool
    perm_investments: bool
    perm_credit_score: bool
    perm_epf_balance: bool

# --- API Endpoints ---
@app.get("/")
def health_check():
    """Root endpoint to check API status."""
    return {"status": "✅ API is running. See /docs for all endpoints."}

@app.post("/api/v1/ai/chat")
async def enhanced_ai_chat(request: QueryRequest):
    """Enhanced AI chat that provides financial context to the agent."""
    if not agent_executor:
        raise HTTPException(status_code=503, detail="AI Agent not initialized")
    
    try:
        engine = get_engine()
        with engine.connect() as conn:
            user_result = conn.execute(sqlalchemy.text("SELECT name, credit_score, epf_balance FROM Users WHERE user_id = :user_id"), {"user_id": request.user_id}).fetchone()
            assets_total = conn.execute(sqlalchemy.text("SELECT COALESCE(SUM(value), 0) FROM Assets WHERE user_id = :user_id"), {"user_id": request.user_id}).scalar_one()
            liabilities_total = conn.execute(sqlalchemy.text("SELECT COALESCE(SUM(outstanding_balance), 0) FROM Liabilities WHERE user_id = :user_id"), {"user_id": request.user_id}).scalar_one()
        
        context = f"User: {user_result[0] if user_result else 'Unknown'}, Total Assets: ${float(assets_total):,.2f}, Total Liabilities: ${float(liabilities_total):,.2f}, Credit Score: {user_result[1] if user_result else 'N/A'}, EPF Balance: ${float(user_result[2]):,.2f if user_result else 0}, Net Worth: ${float(assets_total) - float(liabilities_total):,.2f}. Question: {request.question}"
        
        response = agent_executor.invoke({"input": context})
        
        return {"response": response.get("output", "I'm having trouble processing that request."), "user_id": request.user_id, "context_used": True}
    except Exception as e:
        print(f"Error in enhanced chat: {e}")
        raise HTTPException(status_code=500, detail="An internal error occurred during the chat.")

@app.get("/api/v1/user/{user_id}/permissions")
def get_permissions(user_id: str):
    """Fetches the current data access permissions for a user."""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(sqlalchemy.text("SELECT perm_assets, perm_liabilities, perm_transactions, perm_investments, perm_credit_score, perm_epf_balance FROM Users WHERE user_id = :user_id"), {"user_id": user_id}).fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="User not found")
        return {"perm_assets": result[0], "perm_liabilities": result[1], "perm_transactions": result[2], "perm_investments": result[3], "perm_credit_score": result[4], "perm_epf_balance": result[5]}

@app.put("/api/v1/user/{user_id}/permissions")
def update_permissions(user_id: str, permissions: PermissionsUpdateRequest):
    """Updates the data access permissions for a user."""
    engine = get_engine()
    with engine.connect() as conn:
        with conn.begin() as transaction:
            try:
                result = conn.execute(sqlalchemy.text("UPDATE Users SET perm_assets = :perm_assets, perm_liabilities = :perm_liabilities, perm_transactions = :perm_transactions, perm_investments = :perm_investments, perm_credit_score = :perm_credit_score, perm_epf_balance = :perm_epf_balance WHERE user_id = :user_id"), {"user_id": user_id, **permissions.dict()})
                if result.rowcount == 0:
                    raise HTTPException(status_code=404, detail="User not found to update.")
                return {"status": "success", "message": "Permissions updated."}
            except Exception as e:
                transaction.rollback()
                raise HTTPException(status_code=500, detail=f"Failed to update permissions: {e}")

@app.get("/api/v1/dashboard/summary")
async def get_dashboard_summary(user_id: str = "user_001"):
    """Get financial summary for the dashboard."""
    engine = get_engine()
    with engine.connect() as conn:
        assets = conn.execute(sqlalchemy.text("SELECT COALESCE(SUM(value), 0) FROM Assets WHERE user_id = :uid"), {"uid": user_id}).scalar_one()
        liabilities = conn.execute(sqlalchemy.text("SELECT COALESCE(SUM(outstanding_balance), 0) FROM Liabilities WHERE user_id = :uid"), {"uid": user_id}).scalar_one()
        investments = conn.execute(sqlalchemy.text("SELECT COALESCE(SUM(current_value), 0) FROM Investments WHERE user_id = :uid"), {"uid": user_id}).scalar_one()
        return {"total_assets": float(assets), "total_liabilities": float(liabilities), "investment_portfolio": float(investments)}

@app.get("/api/v1/transactions/recent")
async def get_recent_transactions(user_id: str = "user_001"):
    """Get the 5 most recent transactions for the dashboard."""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(sqlalchemy.text("SELECT date, description, category, amount, type FROM Transactions WHERE user_id = :uid ORDER BY date DESC LIMIT 5"), {"uid": user_id}).fetchall()
        return [{"date": row[0], "name": row[1], "category": row[2], "amount": float(row[3]), "type": row[4]} for row in result]

