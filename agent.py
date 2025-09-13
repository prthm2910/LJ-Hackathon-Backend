import os
import urllib.parse
import sqlalchemy # type: ignore
from fastapi import FastAPI, HTTPException # type: ignore
from pydantic import BaseModel # type: ignore
from dotenv import load_dotenv  # Import the dotenv function

from langchain_google_genai import ChatGoogleGenerativeAI # type: ignore
from langchain_community.utilities import SQLDatabase # type: ignore
# This is the correct new import path for the SQL agent toolkit
from langchain_community.agent_toolkits import create_sql_agent # type: ignore

# Load environment variables from the .env file
load_dotenv()

# ==================================================
# 1. Configuration
# ==================================================
# Now reads credentials securely from the environment (.env file)
DB_USER = os.environ.get("DB_USER", "postgres")

# URL encode password to handle special characters
raw_pass = os.environ.get("DB_PASS", "default_password")
DB_PASS = urllib.parse.quote_plus(raw_pass)

DB_NAME = os.environ.get("DB_NAME", "fintrack")
PUBLIC_IP = os.environ.get("PUBLIC_IP", "127.0.0.1")
DB_PORT = os.environ.get("DB_PORT", "5432")


# ==================================================
# 2. Database Connection
# ==================================================
def get_engine():
    """Creates a SQLAlchemy engine using a standard connection string."""
    db_uri = f"postgresql+pg8000://{DB_USER}:{DB_PASS}@{PUBLIC_IP}:{DB_PORT}/{DB_NAME}"
    try:
        engine = sqlalchemy.create_engine(db_uri)
        with engine.connect() as connection:
            print("✅ Database connection successful.")
        return engine
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        raise


# ==================================================
# 3. AI Agent Setup
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

    # This would also work, but it's not necessary
    api_key = os.environ.get("GOOGLE_API_KEY")
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0, google_api_key=api_key)

    agent_executor = create_sql_agent(
        llm,
        db=db,
        agent_type="openai-tools",
        verbose=True
    )
    print("🤖 AI Agent is ready and connected to the database.")

# Initialize the agent when the application starts
try:
    init_agent()
except Exception as e:
    print(f"🔥 Critical error during AI Agent initialization: {e}")
    agent_executor = None


# ==================================================
# 4. FastAPI Server
# ==================================================
app = FastAPI(
    title="AI Personal Finance Assistant",
    description="An API that allows natural language questions about financial data.",
    version="1.0.0"
)

# API Request/Response Models
class QueryRequest(BaseModel):
    question: str
    user_id: str

# API Endpoints
@app.get("/")
def health_check():
    """Root endpoint to check API status."""
    return {"status": "✅ API is running. Use /ask to query, /ping-db to test DB."}

@app.get("/ping-db")
def ping_db():
    """Check if the database connection is alive."""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(sqlalchemy.text("SELECT 1"))
        return {"status": "✅ Database connection is alive and well."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"❌ Database connection failed: {e}")

@app.post("/ask")
async def ask_agent(request: QueryRequest):
    """Ask a natural language question for a specific user."""
    if not agent_executor:
        raise HTTPException(status_code=503, detail="AI Agent is not initialized. Please check server logs.")

    try:
        full_question = f"For user_id '{request.user_id}', {request.question}"
        print(f"Executing query: {full_question}")

        response = agent_executor.invoke({"input": full_question})

        return {
            "user_id": request.user_id,
            "question": request.question,
            "answer": response.get("output")
        }
    except Exception as e:
        print(f"❌ Error while processing question: {e}")
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {e}")

@app.post("/reload-agent")
def reload_agent():
    """Reload the AI Agent manually without restarting the server."""
    try:
        init_agent()
        return {"status": "✅ Agent reloaded successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"❌ Failed to reload agent: {e}")

