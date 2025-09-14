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
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

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
        with engine.connect() as connection:
            print("✅ Database connection successful.")
        return engine
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        raise

# ==================================================
# 2. AI Agent Setup (SEQUENTIAL CHAIN)
# ==================================================
full_chain = None

def init_agent():
    """Initializes the three-agent sequential chain."""
    global full_chain
    if "GOOGLE_API_KEY" not in os.environ or not os.environ["GOOGLE_API_KEY"]:
        raise ValueError("Error: GOOGLE_API_KEY environment variable not set or empty.")

    print("🚀 Initializing Sequential AI Agent...")
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
    db_engine = get_engine()
    db = SQLDatabase(db_engine)

    # --- Chain 1: Query Reformulator ("The Analyst") ---
    reformulate_template = "Based on the user's question, reformulate it into a direct, unambiguous question for a data analyst. Include the User ID. Original Question: {question}, User ID: {user_id}. Reformulated Question:"
    reformulate_prompt = PromptTemplate.from_template(reformulate_template)
    query_reformulator_chain = reformulate_prompt | llm | StrOutputParser()

    # --- Chain 2: SQL Agent ("The Data Technician") ---
    sql_agent_executor = create_sql_agent(llm, db=db, agent_type="openai-tools", verbose=True)

    # --- Chain 3: Response Synthesizer ("The Communicator") ---
    synthesize_template = """
    You are a friendly and helpful AI financial assistant. The user asked: "{original_question}".
    The database returned the following information: "{sql_data}".

    Based on this, formulate a helpful and natural language response.
    Use visually appealing markdown formatting, such as:
    - Bolding for key terms and numbers.
    - Bullet points for lists (e.g., transaction lists).
    - Code blocks for tables if needed.

    If the data is empty, inform the user you couldn't find the information.
    """
    synthesize_prompt = PromptTemplate.from_template(synthesize_template)
    response_synthesizer_chain = synthesize_prompt | llm | StrOutputParser()

    # --- Combine into the full sequential chain ---
    full_chain = (
        {
            "reformulated_question": query_reformulator_chain,
            "original_question": lambda x: x["question"] 
        }
        | RunnablePassthrough.assign(
            sql_data=lambda x: sql_agent_executor.invoke({"input": x["reformulated_question"]})["output"]
        )
        | response_synthesizer_chain
    )
    
    print("🤖 Sequential AI Agent is ready.")

try:
    init_agent()
except Exception as e:
    print(f"🔥 Critical error during AI Agent initialization: {e}")
    full_chain = None


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

@app.get("/api/v1/users/me")
async def get_current_user(user_id: str):
    """Get current user info for dashboard with permissions"""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(
                sqlalchemy.text("""
                    SELECT user_id, name, credit_score, epf_balance,
                           perm_assets, perm_liabilities, perm_transactions,
                           perm_investments, perm_credit_score, perm_epf_balance
                    FROM Users WHERE user_id = :user_id
                """),
                {"user_id": user_id}
            ).fetchone()
            
            if result:
                return {
                    "user_id": result[0],
                    "name": result[1],
                    "email": f"{result[1].lower().replace(' ', '.')}@financio.com",
                    "credit_score": result[2],
                    "epf_balance": result[3],
                    "permissions": {
                        "perm_assets": result[4],
                        "perm_liabilities": result[5],
                        "perm_transactions": result[6],
                        "perm_investments": result[7],
                        "perm_credit_score": result[8],
                        "perm_epf_balance": result[9]
                    }
                }
            raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/users/update-permissions")
async def update_ai_permissions(permissions: dict, user_id: str):
    """Update AI access permissions for user data"""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            stmt = sqlalchemy.text("""
                UPDATE Users 
                SET perm_assets = :perm_assets,
                    perm_liabilities = :perm_liabilities,
                    perm_transactions = :perm_transactions,
                    perm_investments = :perm_investments,
                    perm_credit_score = :perm_credit_score,
                    perm_epf_balance = :perm_epf_balance
                WHERE user_id = :user_id
            """)
            
            result = conn.execute(stmt, {
                "user_id": user_id,
                "perm_assets": permissions.get("perm_assets", True),
                "perm_liabilities": permissions.get("perm_liabilities", True),
                "perm_transactions": permissions.get("perm_transactions", True),
                "perm_investments": permissions.get("perm_investments", True),
                "perm_credit_score": permissions.get("perm_credit_score", True),
                "perm_epf_balance": permissions.get("perm_epf_balance", True)
            })
            conn.commit()
            
            if result.rowcount == 0:
                raise HTTPException(status_code=404, detail="User not found")
            
            return {
                "message": "AI permissions updated successfully",
                "status": "success"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/users/update-profile")
async def update_user_profile(request: dict, user_id: str):
    """Update user credit score and EPF balance"""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            stmt = sqlalchemy.text("""
                UPDATE Users 
                SET credit_score = :credit_score, epf_balance = :epf_balance
                WHERE user_id = :user_id
            """)
            
            result = conn.execute(stmt, {
                "user_id": user_id,
                "credit_score": request.get("credit_score"),
                "epf_balance": request.get("epf_balance")
            })
            conn.commit()
            
            if result.rowcount == 0:
                raise HTTPException(status_code=404, detail="User not found")
            
            return {
                "message": "Profile updated successfully",
                "status": "success"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/dashboard/summary")
async def get_dashboard_summary(user_id: str = "user_001"):
    """Get financial summary for dashboard"""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            # Get user basic info
            user_result = conn.execute(
                sqlalchemy.text("SELECT credit_score, epf_balance FROM Users WHERE user_id = :user_id"),
                {"user_id": user_id}
            ).fetchone()
            
            # Calculate total assets
            assets_result = conn.execute(
                sqlalchemy.text("SELECT COALESCE(SUM(value), 0) FROM Assets WHERE user_id = :user_id"),
                {"user_id": user_id}
            ).fetchone()
            
            # Calculate total liabilities
            liabilities_result = conn.execute(
                sqlalchemy.text("SELECT COALESCE(SUM(outstanding_balance), 0) FROM Liabilities WHERE user_id = :user_id"),
                {"user_id": user_id}
            ).fetchone()
            
            # Calculate investment portfolio
            investments_result = conn.execute(
                sqlalchemy.text("SELECT COALESCE(SUM(current_value), 0) FROM Investments WHERE user_id = :user_id"),
                {"user_id": user_id}
            ).fetchone()
            
            total_assets = float(assets_result[0]) if assets_result else 0
            total_liabilities = float(liabilities_result[0]) if liabilities_result else 0
            investment_portfolio = float(investments_result[0]) if investments_result else 0
            
            return {
                "total_assets": total_assets,
                "total_liabilities": total_liabilities,
                "epf_balance": float(user_result[1]) if user_result else 0,
                "credit_score": int(user_result[0]) if user_result else 750,
                "investment_portfolio": investment_portfolio
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/transactions")
async def add_transaction(transaction: dict, user_id: str):
    """Add new transaction"""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            stmt = sqlalchemy.text("""
                INSERT INTO Transactions (user_id, date, description, category, amount, type)
                VALUES (:user_id, :date, :description, :category, :amount, :type)
            """)
            
            conn.execute(stmt, {
                "user_id": user_id,
                "date": transaction["date"],
                "description": transaction["description"], 
                "category": transaction["category"],
                "amount": transaction["amount"],
                "type": transaction["type"]
            })
            conn.commit()
            
            return {"message": "Transaction added successfully", "status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/api/v1/assets")
async def add_asset(asset: dict, user_id: str):
    """Add new asset"""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            stmt = sqlalchemy.text("""
                INSERT INTO Assets (user_id, name, type, value)
                VALUES (:user_id, :name, :type, :value)
            """)
            
            conn.execute(stmt, {
                "user_id": user_id,
                "name": asset["name"],
                "type": asset["type"],
                "value": asset["value"]
            })
            conn.commit()
            
            return {"message": "Asset added successfully", "status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/api/v1/investments")
async def add_investment(investment: dict, user_id: str):
    """Add new investment with purchase date"""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            stmt = sqlalchemy.text("""
                INSERT INTO Investments (user_id, name, ticker, type, quantity, current_value, purchase_date)
                VALUES (:user_id, :name, :ticker, :type, :quantity, :current_value, :purchase_date)
            """)
            
            conn.execute(stmt, {
                "user_id": user_id,
                "name": investment["name"],
                "ticker": investment["ticker"],
                "type": investment["type"],
                "quantity": investment["quantity"],
                "current_value": investment["current_value"],
                "purchase_date": investment.get("purchase_date")
            })
            conn.commit()
            
            return {"message": "Investment added successfully", "status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@app.post("/api/v1/liabilities")
async def add_liability(liability: dict, user_id: str):
    """Add new liability"""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            stmt = sqlalchemy.text("""
                INSERT INTO Liabilities (user_id, name, type, outstanding_balance)
                VALUES (:user_id, :name, :type, :outstanding_balance)
            """)
            
            conn.execute(stmt, {
                "user_id": user_id,
                "name": liability["name"],
                "type": liability["type"],
                "outstanding_balance": liability["outstanding_balance"]
            })
            conn.commit()
            
            return {"message": "Liability added successfully", "status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500,detail=str(e))


@app.get("/api/v1/dashboard")
async def get_dashboard_overview(user_id: str):
    """Complete dashboard data - summary, charts, transactions, everything!"""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            # 1. USER BASIC INFO
            user_info = conn.execute(
                sqlalchemy.text("SELECT name, credit_score, epf_balance FROM Users WHERE user_id = :user_id"),
                {"user_id": user_id}
            ).fetchone()
            
            if not user_info:
                raise HTTPException(status_code=404, detail="User not found")

            # 2. FINANCIAL SUMMARY
            total_assets = conn.execute(
                sqlalchemy.text("SELECT COALESCE(SUM(value), 0) FROM Assets WHERE user_id = :user_id"),
                {"user_id": user_id}
            ).fetchone()[0]

            total_liabilities = conn.execute(
                sqlalchemy.text("SELECT COALESCE(SUM(outstanding_balance), 0) FROM Liabilities WHERE user_id = :user_id"),
                {"user_id": user_id}
            ).fetchone()[0]

            total_investments = conn.execute(
                sqlalchemy.text("SELECT COALESCE(SUM(current_value), 0) FROM Investments WHERE user_id = :user_id"),
                {"user_id": user_id}
            ).fetchone()[0]

            # 3. RECENT TRANSACTIONS (Last 10)
            recent_transactions = conn.execute(
                sqlalchemy.text("""
                    SELECT date, description, category, amount, type 
                    FROM Transactions 
                    WHERE user_id = :user_id 
                    ORDER BY date DESC 
                    LIMIT 10
                """),
                {"user_id": user_id}
            ).fetchall()

            transactions_list = []
            for row in recent_transactions:
                transactions_list.append({
                    "date": str(row[0]),
                    "name": row[1],
                    "category": row[2],
                    "amount": float(row[3]),
                    "type": row[4]
                })

            # 4. MONTHLY CHART DATA (Last 6 months)
            monthly_data = conn.execute(
                sqlalchemy.text("""
                    SELECT 
                        DATE_TRUNC('month', date) as month,
                        SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END) as income,
                        SUM(CASE WHEN type = 'expense' THEN ABS(amount) ELSE 0 END) as expenses
                    FROM Transactions 
                    WHERE user_id = :user_id 
                        AND date >= CURRENT_DATE - INTERVAL '6 months'
                    GROUP BY DATE_TRUNC('month', date)
                    ORDER BY month
                """),
                {"user_id": user_id}
            ).fetchall()

            monthly_chart = []
            for row in monthly_data:
                monthly_chart.append({
                    "month": row[0].strftime("%Y-%m"),
                    "income": float(row[1]),
                    "expenses": float(row[2])
                })

            # 5. CATEGORY BREAKDOWN (Expenses by category)
            category_data = conn.execute(
                sqlalchemy.text("""
                    SELECT category, SUM(ABS(amount)) as total
                    FROM Transactions 
                    WHERE user_id = :user_id 
                        AND type = 'expense'
                        AND date >= CURRENT_DATE - INTERVAL '30 days'
                    GROUP BY category
                    ORDER BY total DESC
                    LIMIT 8
                """),
                {"user_id": user_id}
            ).fetchall()

            category_breakdown = []
            for row in category_data:
                category_breakdown.append({
                    "category": row[0],
                    "amount": float(row[1])
                })

            # 6. INVESTMENT BREAKDOWN
            investment_data = conn.execute(
                sqlalchemy.text("""
                    SELECT type, SUM(current_value) as total_value, COUNT(*) as count
                    FROM Investments 
                    WHERE user_id = :user_id
                    GROUP BY type
                    ORDER BY total_value DESC
                """),
                {"user_id": user_id}
            ).fetchall()

            investment_breakdown = []
            for row in investment_data:
                investment_breakdown.append({
                    "type": row[0],
                    "value": float(row[1]),
                    "count": int(row[2])
                })

            # 7. ASSET BREAKDOWN
            asset_data = conn.execute(
                sqlalchemy.text("""
                    SELECT type, SUM(value) as total_value, COUNT(*) as count
                    FROM Assets 
                    WHERE user_id = :user_id
                    GROUP BY type
                    ORDER BY total_value DESC
                """),
                {"user_id": user_id}
            ).fetchall()

            asset_breakdown = []
            for row in asset_data:
                asset_breakdown.append({
                    "type": row[0],
                    "value": float(row[1]),
                    "count": int(row[2])
                })

            # 8. LIABILITY BREAKDOWN
            liability_data = conn.execute(
                sqlalchemy.text("""
                    SELECT type, SUM(outstanding_balance) as total_balance, COUNT(*) as count
                    FROM Liabilities 
                    WHERE user_id = :user_id
                    GROUP BY type
                    ORDER BY total_balance DESC
                """),
                {"user_id": user_id}
            ).fetchall()

            liability_breakdown = []
            for row in liability_data:
                liability_breakdown.append({
                    "type": row[0],
                    "balance": float(row[1]),
                    "count": int(row[2])
                })

            # 9. STATS COUNTERS
            transaction_count = conn.execute(
                sqlalchemy.text("SELECT COUNT(*) FROM Transactions WHERE user_id = :user_id"),
                {"user_id": user_id}
            ).fetchone()[0]

            asset_count = conn.execute(
                sqlalchemy.text("SELECT COUNT(*) FROM Assets WHERE user_id = :user_id"),
                {"user_id": user_id}
            ).fetchone()[0]

            investment_count = conn.execute(
                sqlalchemy.text("SELECT COUNT(*) FROM Investments WHERE user_id = :user_id"),
                {"user_id": user_id}
            ).fetchone()[0]

            liability_count = conn.execute(
                sqlalchemy.text("SELECT COUNT(*) FROM Liabilities WHERE user_id = :user_id"),
                {"user_id": user_id}
            ).fetchone()[0]

            # Calculate net worth
            net_worth = float(total_assets) + float(total_investments) - float(total_liabilities)

            return {
                "user_info": {
                    "name": user_info[0],
                    "credit_score": user_info[1],
                    "epf_balance": float(user_info[2])
                },
                "financial_summary": {
                    "total_assets": float(total_assets),
                    "total_liabilities": float(total_liabilities),
                    "total_investments": float(total_investments),
                    "net_worth": net_worth,
                    "epf_balance": float(user_info[2])
                },
                "recent_transactions": transactions_list,
                "monthly_chart_data": monthly_chart,
                "category_breakdown": category_breakdown,
                "investment_breakdown": investment_breakdown,
                "asset_breakdown": asset_breakdown,
                "liability_breakdown": liability_breakdown,
                "stats": {
                    "transaction_count": transaction_count,
                    "asset_count": asset_count,
                    "investment_count": investment_count,
                    "liability_count": liability_count,
                    "total_records": transaction_count + asset_count + investment_count + liability_count
                }
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/dashboard/charts")
async def get_dashboard_charts(user_id: str, period: str = "6months"):
    """
    Get chart data for dashboard - optimized for your React Charts component
    
    Parameters:
    - user_id: Firebase UID 
    - period: 3months, 6months, 1year, 2years
    
    Returns data formatted exactly for your Charts component
    """
    try:
        engine = get_engine()
        with engine.connect() as conn:
            # Map period to SQL interval
            interval_map = {
                "3months": "3 months",
                "6months": "6 months", 
                "1year": "12 months",
                "2years": "24 months"
            }
            interval_value = interval_map.get(period.lower(), "6 months")
            
            # 1. MONTHLY SPENDING TRENDS (Bar Chart)
            spending_data = conn.execute(
                sqlalchemy.text("""
                    SELECT 
                        TO_CHAR(DATE_TRUNC('month', date), 'Mon') AS month,
                        SUM(ABS(amount)) AS total_spending
                    FROM Transactions 
                    WHERE user_id = :user_id 
                        AND type = 'expense'
                        AND date >= CURRENT_DATE - INTERVAL :interval_val
                    GROUP BY DATE_TRUNC('month', date), month
                    ORDER BY DATE_TRUNC('month', date)
                """.replace(":interval_val", f"'{interval_value}'")),
                {"user_id": user_id}
            ).fetchall()
            
            spending_labels = [row[0] for row in spending_data] if spending_data else ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
            spending_values = [float(row[1]) for row in spending_data] if spending_data else [1200, 1900, 1500, 1700, 1600, 2100]
            
            # 2. MONTHLY SAVINGS TRENDS (Line Chart)
            savings_data = conn.execute(
                sqlalchemy.text("""
                    SELECT 
                        TO_CHAR(DATE_TRUNC('month', date), 'Mon') AS month,
                        SUM(CASE WHEN type = 'income' THEN amount ELSE -ABS(amount) END) AS net_savings
                    FROM Transactions 
                    WHERE user_id = :user_id 
                        AND date >= CURRENT_DATE - INTERVAL :interval_val
                    GROUP BY DATE_TRUNC('month', date), month
                    ORDER BY DATE_TRUNC('month', date)
                """.replace(":interval_val", f"'{interval_value}'")),
                {"user_id": user_id}
            ).fetchall()
            
            savings_labels = [row[0] for row in savings_data] if savings_data else ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
            savings_values = [float(row[1]) for row in savings_data] if savings_data else [500, 600, 800, 750, 900, 1100]
            
            # 3. INVESTMENT PORTFOLIO TRENDS (Line Chart)
            # Get current total portfolio value, then simulate monthly growth
            current_portfolio = conn.execute(
                sqlalchemy.text("SELECT COALESCE(SUM(current_value), 65000) FROM Investments WHERE user_id = :user_id"),
                {"user_id": user_id}
            ).fetchone()[0]
            
            portfolio_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
            base_value = float(current_portfolio) * 0.9  # Start 10% lower
            portfolio_values = [
                base_value + (i * base_value * 0.02) for i in range(6)  # 2% growth per month
            ]
            
            # 4. PORTFOLIO ALLOCATION (Pie Chart)
            allocation_data = conn.execute(
                sqlalchemy.text("""
                    SELECT 
                        CASE 
                            WHEN type = 'stock' THEN 'Stocks'
                            WHEN type = 'mutual_fund' THEN 'Bonds'
                            WHEN type = 'etf' THEN 'Real Estate'
                            ELSE 'Crypto'
                        END AS allocation_category,
                        SUM(current_value) AS total_value
                    FROM Investments 
                    WHERE user_id = :user_id
                    GROUP BY allocation_category
                    ORDER BY total_value DESC
                """),
                {"user_id": user_id}
            ).fetchall()
            
            allocation_labels = [row[0] for row in allocation_data] if allocation_data else ["Stocks", "Bonds", "Real Estate", "Crypto"]
            allocation_values = [float(row[1]) for row in allocation_data] if allocation_data else [35000, 20000, 10000, 5000]
            
            return {
                "spending_chart": {
                    "labels": spending_labels,
                    "data": spending_values
                },
                "savings_chart": {
                    "labels": savings_labels,
                    "data": savings_values
                },
                "investment_chart": {
                    "labels": portfolio_labels,
                    "data": portfolio_values
                },
                "allocation_chart": {
                    "labels": allocation_labels,
                    "data": allocation_values
                },
                "period": period
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/api/v1/dashboard/charts/category-breakdown")
async def get_category_breakdown(user_id: str, period: str = "3months"):
    """
    Get detailed expense breakdown by category for pie charts
    """
    try:
        engine = get_engine()
        with engine.connect() as conn:
            interval_map = {
                "1month": "1 month",
                "3months": "3 months",
                "6months": "6 months",
                "1year": "12 months"
            }
            interval_value = interval_map.get(period.lower(), "3 months")
            
            category_data = conn.execute(
                sqlalchemy.text("""
                    SELECT 
                        category,
                        SUM(ABS(amount)) AS total_amount,
                        COUNT(*) AS transaction_count
                    FROM Transactions 
                    WHERE user_id = :user_id 
                        AND type = 'expense'
                        AND date >= CURRENT_DATE - INTERVAL :interval_val
                    GROUP BY category
                    ORDER BY total_amount DESC
                    LIMIT 10
                """.replace(":interval_val", f"'{interval_value}'")),
                {"user_id": user_id}
            ).fetchall()
            
            if category_data:
                return {
                    "labels": [row[0] for row in category_data],
                    "data": [float(row[1]) for row in category_data],
                    "counts": [int(row[2]) for row in category_data],
                    "period": period
                }
            else:
                # Fallback data
                return {
                    "labels": ["Groceries", "Transport", "Utilities", "Dining", "Shopping"],
                    "data": [3500, 2800, 1500, 1200, 2000],
                    "counts": [15, 8, 3, 6, 4],
                    "period": period
                }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/dashboard/charts/income-vs-expense")
async def get_income_vs_expense(user_id: str, period: str = "6months"):
    """
    Get income vs expense comparison data
    """
    try:
        engine = get_engine()
        with engine.connect() as conn:
            interval_map = {
                "3months": "3 months",
                "6months": "6 months",
                "1year": "12 months"
            }
            interval_value = interval_map.get(period.lower(), "6 months")
            
            monthly_comparison = conn.execute(
                sqlalchemy.text("""
                    SELECT 
                        TO_CHAR(DATE_TRUNC('month', date), 'Mon YYYY') AS month,
                        SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END) AS total_income,
                        SUM(CASE WHEN type = 'expense' THEN ABS(amount) ELSE 0 END) AS total_expense
                    FROM Transactions 
                    WHERE user_id = :user_id 
                        AND date >= CURRENT_DATE - INTERVAL :interval_val
                    GROUP BY DATE_TRUNC('month', date), month
                    ORDER BY DATE_TRUNC('month', date)
                """.replace(":interval_val", f"'{interval_value}'")),
                {"user_id": user_id}
            ).fetchall()
            
            if monthly_comparison:
                return {
                    "labels": [row[0] for row in monthly_comparison],
                    "income_data": [float(row[1]) for row in monthly_comparison],
                    "expense_data": [float(row[2]) for row in monthly_comparison],
                    "net_data": [float(row[1]) - float(row[2]) for row in monthly_comparison],
                    "period": period
                }
            else:
                # Fallback data
                return {
                    "labels": ["Jan 2025", "Feb 2025", "Mar 2025", "Apr 2025", "May 2025", "Jun 2025"],
                    "income_data": [50000, 52000, 50000, 55000, 50000, 53000],
                    "expense_data": [35000, 38000, 32000, 42000, 36000, 39000],
                    "net_data": [15000, 14000, 18000, 13000, 14000, 14000],
                    "period": period
                }
            
    except Exception as e:
        raise HTTPException(status_code=500,detail=str(e))

@app.get("/api/v1/dashboard/recent-transactions")
async def get_recent_transactions(user_id: str = "user_001"):
    """Get recent 5 transactions for dashboard"""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(
                sqlalchemy.text("""
                    SELECT date, description, category, amount 
                    FROM Transactions 
                    WHERE user_id = :user_id 
                    ORDER BY date DESC 
                    LIMIT 5
                """),
                {"user_id": user_id}
            ).fetchall()
            
            transactions = []
            for row in result:
                transactions.append({
                    "date": row[0],
                    "name": row[1], 
                    "category": row[2],
                    "amount": float(row[3])
                })
            
            return transactions
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/ai/templates")
async def get_ai_templates():
    """Get AI Studio templates"""
    return [
        {"id": "investment-review", "title": "Investment Portfolio Review", "category": "investment", "icon": "show_chart", "description": "Get personalized advice on your investment mix"},
        {"id": "budget-optimizer", "title": "Monthly Budget Optimizer", "category": "budgeting", "icon": "pie_chart", "description": "Optimize your monthly spending"},
        {"id": "spending-analysis", "title": "Spending Pattern Analysis", "category": "budgeting", "icon": "analytics", "description": "Analyze your spending habits"},
        {"id": "savings-goal", "title": "Savings Goal Planner", "category": "savings", "icon": "savings", "description": "Plan your savings goals"},
        {"id": "debt-payoff", "title": "Debt Payoff Strategy", "category": "loans", "icon": "payments", "description": "Create a debt elimination plan"},
        {"id": "retirement-planning", "title": "Retirement Planning", "category": "retirement", "icon": "elderly", "description": "Plan for your retirement"},
    ]

@app.post("/api/v1/users/create")
async def create_user(user_data: dict):
    """Create new user account (called when user signs up)"""
    try:
        required_fields = ["user_id", "name"]
        for field in required_fields:
            if field not in user_data:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        
        engine = get_engine()
        with engine.connect() as conn:
            # Check if user already exists
            existing = conn.execute(
                sqlalchemy.text("SELECT user_id FROM Users WHERE user_id = :user_id"),
                {"user_id": user_data["user_id"]}
            ).fetchone()
            
            if existing:
                raise HTTPException(status_code=409, detail="User already exists")
            
            # Create new user with default permissions
            stmt = sqlalchemy.text("""
                INSERT INTO Users 
                (user_id, name, credit_score, epf_balance, perm_assets, perm_liabilities, 
                 perm_transactions, perm_investments, perm_credit_score, perm_epf_balance)
                VALUES 
                (:user_id, :name, :credit_score, :epf_balance, :perm_assets, :perm_liabilities,
                 :perm_transactions, :perm_investments, :perm_credit_score, :perm_epf_balance)
            """)
            
            conn.execute(stmt, {
                "user_id": user_data["user_id"],
                "name": user_data["name"],
                "credit_score": user_data.get("credit_score", 0),
                "epf_balance": user_data.get("epf_balance", 0.0),
                "perm_assets": user_data.get("perm_assets", True),
                "perm_liabilities": user_data.get("perm_liabilities", True),
                "perm_transactions": user_data.get("perm_transactions", True),
                "perm_investments": user_data.get("perm_investments", True),
                "perm_credit_score": user_data.get("perm_credit_score", True),
                "perm_epf_balance": user_data.get("perm_epf_balance", True)
            })
            conn.commit()
            
            return {
                "message": "User created successfully",
                "status": "success", 
                "user_id": user_data["user_id"]
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.delete("/api/v1/users/delete-account")
async def delete_user_account(user_id: str):
    """Delete user account and all associated data"""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            # Check if user exists
            user_check = conn.execute(
                sqlalchemy.text("SELECT user_id FROM Users WHERE user_id = :user_id"),
                {"user_id": user_id}
            ).fetchone()
            
            if not user_check:
                raise HTTPException(status_code=404, detail="User not found")
            
            # Delete all user data (foreign keys will cascade)
            tables = ["Transactions", "Assets", "Liabilities", "Investments"]
            for table in tables:
                conn.execute(
                    sqlalchemy.text(f"DELETE FROM {table} WHERE user_id = :user_id"),
                    {"user_id": user_id}
                )
            
            # Delete user
            conn.execute(
                sqlalchemy.text("DELETE FROM Users WHERE user_id = :user_id"),
                {"user_id": user_id}
            )
            conn.commit()
            
            return {
                "message": "User account deleted successfully",
                "status": "success"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@app.get("/api/v1/users/profile-summary")
async def get_profile_summary(user_id: str):
    """Get quick profile summary for header/navigation"""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(
                sqlalchemy.text("SELECT name, credit_score FROM Users WHERE user_id = :user_id"),
                {"user_id": user_id}
            ).fetchone()
            
            if not result:
                raise HTTPException(status_code=404, detail="User not found")
            
            # Generate initials from name
            name_parts = result[0].split()
            initials = "".join([part[0].upper() for part in name_parts[:2]]) if name_parts else "U"
            
            return {
                "name": result[0],
                "credit_score": result[1],
                "initials": initials,
                "email": f"{result[0].lower().replace(' ', '.')}@financio.com"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/api/v1/users/stats")
async def get_user_stats(user_id: str):
    """Get user statistics (total records, etc.)"""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            # Get counts for each data type
            transaction_count = conn.execute(
                sqlalchemy.text("SELECT COUNT(*) FROM Transactions WHERE user_id = :user_id"),
                {"user_id": user_id}
            ).fetchone()[0]
            
            asset_count = conn.execute(
                sqlalchemy.text("SELECT COUNT(*) FROM Assets WHERE user_id = :user_id"),
                {"user_id": user_id}
            ).fetchone()[0]
            
            investment_count = conn.execute(
                sqlalchemy.text("SELECT COUNT(*) FROM Investments WHERE user_id = :user_id"),
                {"user_id": user_id}
            ).fetchone()[0]
            
            liability_count = conn.execute(
                sqlalchemy.text("SELECT COUNT(*) FROM Liabilities WHERE user_id = :user_id"),
                {"user_id": user_id}
            ).fetchone()[0]
            
            return {
                "transaction_count": transaction_count,
                "asset_count": asset_count,
                "investment_count": investment_count,
                "liability_count": liability_count,
                "total_records": transaction_count + asset_count + investment_count + liability_count
            }
    except Exception as e:
        raise HTTPException(status_code=500,detail=str(e))

# --- REFACTORED AI Chat Endpoint ---
@app.post("/api/v1/ai/chat")
async def enhanced_ai_chat(request: QueryRequest):
    """Enhanced AI chat using a sequential chain for higher quality responses."""
    if not full_chain:
        raise HTTPException(status_code=503, detail="AI Agent is not initialized. Check server logs.")
    
    try:
        print(f"Executing sequential chain for user '{request.user_id}'...")
        input_data = {"question": request.question, "user_id": request.user_id}
        
        final_answer = full_chain.invoke(input_data)
        
        return {
            "user_id": request.user_id,
            "question": request.question,
            "answer": final_answer
        }
    except Exception as e:
        print(f"❌ Error in sequential chain: {e}")
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {e}")


# Add CORS middleware for React frontend


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)