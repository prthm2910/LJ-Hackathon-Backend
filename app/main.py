import sqlalchemy
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Import from our new, separated modules
import ai_agent, database, models, config

# ==================================================
# FastAPI Server Setup
# ==================================================
app = FastAPI(
    title="AI Personal Finance Assistant",
    description="A comprehensive API for your financial data.",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================================================
# API Endpoints
# ==================================================

# --- Health & Utility Endpoints ---
@app.get("/")
def health_check():
    """Root endpoint to check API status."""
    return {"status": "✅ API is running. See /docs for all endpoints."}

@app.get("/ping-db")
def ping_db():
    """Check if the database connection is alive."""
    try:
        # Use the shared engine from the database module
        with database.engine.connect() as conn:
            conn.execute(sqlalchemy.text("SELECT 1"))
        return {"status": "✅ Database connection is alive and well."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"❌ Database connection failed: {e}")

# --- AI Chat Endpoint ---
@app.post("/api/v1/ai/chat")
async def enhanced_ai_chat(request: models.QueryRequest): # type: ignore
    """Enhanced AI chat using a sequential chain for higher quality responses."""
    if not ai_agent.full_chain:
        raise HTTPException(status_code=503, detail="AI Agent is not initialized. Check server logs.")
    
    try:
        print(f"Executing sequential chain for user '{request.user_id}'...")
        input_data = {"question": request.question, "user_id": request.user_id}
        final_answer = ai_agent.full_chain.invoke(input_data)
        return {
            "user_id": request.user_id,
            "question": request.question,
            "answer": final_answer
        }
    except Exception as e:
        print(f"❌ Error in sequential chain: {e}")
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {e}")

# --- User, Permissions & Dashboard Endpoints ---
@app.get("/api/v1/users/me")
async def get_current_user(user_id: str):
    """Get current user info for dashboard with permissions"""
    with database.engine.connect() as conn:
        result = conn.execute(
            sqlalchemy.text("SELECT user_id, name, credit_score, epf_balance FROM Users WHERE user_id = :user_id"),
            {"user_id": user_id}
        ).fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="User not found")

        return {
            "id": result[0],
            "name": result[1],
            "email": f"{result[1].lower().replace(' ', '.')}@financio.com",
            "credit_score": result[2],
            "epf_balance": result[3]
        }

@app.put("/api/v1/user/{user_id}/permissions")
def update_permissions(user_id: str, permissions: models.PermissionsUpdateRequest): # type: ignore
    """Updates the data access permissions for a user."""
    with database.engine.connect() as conn:
        with conn.begin() as transaction:
            try:
                stmt = sqlalchemy.text("""
                    UPDATE Users SET 
                        perm_assets = :perm_assets, perm_liabilities = :perm_liabilities,
                        perm_transactions = :perm_transactions, perm_investments = :perm_investments,
                        perm_credit_score = :perm_credit_score, perm_epf_balance = :perm_epf_balance
                    WHERE user_id = :user_id
                """)
                result = conn.execute(stmt, {"user_id": user_id, **permissions.dict()})
                if result.rowcount == 0:
                    raise HTTPException(status_code=404, detail="User not found to update.")
                return {"status": "success", "message": "Permissions updated."}
            except Exception as e:
                transaction.rollback()
                raise HTTPException(status_code=500, detail=f"Failed to update permissions: {e}")

@app.get("/api/v1/dashboard/summary")
async def get_dashboard_summary(user_id: str = "user_001"):
    """Get financial summary for the main dashboard."""
    with database.engine.connect() as conn:
        assets = conn.execute(sqlalchemy.text("SELECT COALESCE(SUM(value), 0) FROM Assets WHERE user_id = :uid"), {"uid": user_id}).scalar_one()
        liabilities = conn.execute(sqlalchemy.text("SELECT COALESCE(SUM(outstanding_balance), 0) FROM Liabilities WHERE user_id = :uid"), {"uid": user_id}).scalar_one()
        investments = conn.execute(sqlalchemy.text("SELECT COALESCE(SUM(current_value), 0) FROM Investments WHERE user_id = :uid"), {"uid": user_id}).scalar_one()
        return {"total_assets": float(assets), "total_liabilities": float(liabilities), "investment_portfolio": float(investments)}

@app.get("/api/v1/transactions")
async def get_transactions(user_id: str = "user_001", limit: int = 50):
    """Get a list of user transactions with a limit."""
    with database.engine.connect() as conn:
        result = conn.execute(sqlalchemy.text("SELECT date, description, category, amount, type FROM Transactions WHERE user_id = :uid ORDER BY date DESC LIMIT :lim"), {"uid": user_id, "lim": limit}).fetchall()
        return [{"date": str(row[0]), "name": row[1], "category": row[2], "amount": float(row[3]), "type": row[4]} for row in result]

@app.get("/api/v1/transactions/recent")
async def get_recent_transactions(user_id: str = "user_001"):
    """Get the 5 most recent transactions for the dashboard."""
    with database.engine.connect() as conn:
        result = conn.execute(sqlalchemy.text("SELECT date, description, category, amount, type FROM Transactions WHERE user_id = :uid ORDER BY date DESC LIMIT 5"), {"uid": user_id}).fetchall()
        return [{"date": str(row[0]), "name": row[1], "category": row[2], "amount": float(row[3]), "type": row[4]} for row in result]
        
@app.get("/api/v1/ai/templates")
async def get_ai_templates():
    """Get AI Studio templates for frontend suggestions."""
    return [
        {"id": "investment-review", "title": "Investment Portfolio Review", "category": "investment", "icon": "show_chart", "description": "Get personalized advice on your investment mix"},
        {"id": "budget-optimizer", "title": "Monthly Budget Optimizer", "category": "budgeting", "icon": "pie_chart", "description": "Optimize your monthly spending"},
        {"id": "spending-analysis", "title": "Spending Pattern Analysis", "category": "budgeting", "icon": "analytics", "description": "Analyze your spending habits"},
        {"id": "savings-goal", "title": "Savings Goal Planner", "category": "savings", "icon": "savings", "description": "Plan your savings goals"},
    ]

# --- CRUD Endpoints for Creating Records ---
@app.post("/api/v1/transactions", status_code=201)
def create_transaction(user_id: str, transaction: models.TransactionCreate): # type: ignore
    with database.engine.connect() as conn:
        with conn.begin() as trans:
            conn.execute(
                sqlalchemy.text("""
                    INSERT INTO Transactions (user_id, date, description, category, amount, type)
                    VALUES (:user_id, :date, :description, :category, :amount, :type)
                """),
                {"user_id": user_id, **transaction.dict()}
            )
            return {"status": "success", "message": "Transaction created."}

@app.post("/api/v1/assets", status_code=201)
def create_asset(user_id: str, asset: models.AssetCreate): # type: ignore
    with database.engine.connect() as conn:
        with conn.begin() as trans:
            conn.execute(
                sqlalchemy.text("INSERT INTO Assets (user_id, name, type, value) VALUES (:user_id, :name, :type, :value)"),
                {"user_id": user_id, **asset.dict()}
            )
            return {"status": "success", "message": "Asset created."}

@app.post("/api/v1/liabilities", status_code=201)
def create_liability(user_id: str, liability: models.LiabilityCreate): # type: ignore
    with database.engine.connect() as conn:
        with conn.begin() as trans:
            conn.execute(
                sqlalchemy.text("INSERT INTO Liabilities (user_id, name, type, outstanding_balance) VALUES (:user_id, :name, :type, :outstanding_balance)"),
                {"user_id": user_id, **liability.dict(by_alias=True)}
            )
            return {"status": "success", "message": "Liability created."}

@app.post("/api/v1/investments", status_code=201)
def create_investment(user_id: str, investment: models.InvestmentCreate): # type: ignore
    with database.engine.connect() as conn:
        with conn.begin() as trans:
            conn.execute(
                sqlalchemy.text("INSERT INTO Investments (user_id, name, ticker, type, quantity, current_value) VALUES (:user_id, :name, :ticker, :type, :quantity, :current_value)"),
                {"user_id": user_id, **investment.dict(by_alias=True)}
            )
            return {"status": "success", "message": "Investment created."}

