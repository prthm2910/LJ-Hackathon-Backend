from fastapi import APIRouter, HTTPException, Query # type: ignore
import sqlalchemy # type: ignore
import os
import sys

# Add parent directory to path to import from agent.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath("agent.py"))))
from agent import get_engine

router = APIRouter()

@router.get("/me")
async def get_current_user(user_id: str = Query(..., description="Firebase UID")):
    """Get current user profile with permissions"""
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
            
            if not result:
                raise HTTPException(status_code=404, detail="User not found")
            
            return {
                "user_id": result[0],
                "name": result[1],
                "email": f"{result[1].lower().replace(' ', '.')}@financio.com",
                "credit_score": result[2],
                "epf_balance": float(result[3]),
                "permissions": {
                    "perm_assets": bool(result[4]),
                    "perm_liabilities": bool(result[5]),
                    "perm_transactions": bool(result[6]),
                    "perm_investments": bool(result[7]),
                    "perm_credit_score": bool(result[8]),
                    "perm_epf_balance": bool(result[9])
                }
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.post("/update-profile")
async def update_user_profile(request: dict, user_id: str = Query(..., description="Firebase UID")):
    """Update user credit score and EPF balance"""
    try:
        if not request.get("credit_score") and not request.get("epf_balance"):
            raise HTTPException(status_code=400, detail="At least one field (credit_score or epf_balance) is required")
        
        engine = get_engine()
        with engine.connect() as conn:
            # Check if user exists first
            user_check = conn.execute(
                sqlalchemy.text("SELECT user_id FROM Users WHERE user_id = :user_id"),
                {"user_id": user_id}
            ).fetchone()
            
            if not user_check:
                raise HTTPException(status_code=404, detail="User not found")
            
            # Update profile
            stmt = sqlalchemy.text("""
                UPDATE Users 
                SET credit_score = :credit_score, epf_balance = :epf_balance
                WHERE user_id = :user_id
            """)
            
            conn.execute(stmt, {
                "user_id": user_id,
                "credit_score": request.get("credit_score"),
                "epf_balance": request.get("epf_balance")
            })
            conn.commit()
            
            return {
                "message": "Profile updated successfully",
                "status": "success",
                "updated_fields": {
                    "credit_score": request.get("credit_score"),
                    "epf_balance": request.get("epf_balance")
                }
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.post("/update-permissions")
async def update_ai_permissions(permissions: dict, user_id: str = Query(..., description="Firebase UID")):
    """Update AI access permissions for user data"""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            # Check if user exists first
            user_check = conn.execute(
                sqlalchemy.text("SELECT user_id FROM Users WHERE user_id = :user_id"),
                {"user_id": user_id}
            ).fetchone()
            
            if not user_check:
                raise HTTPException(status_code=404, detail="User not found")
            
            # Update permissions
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
            
            conn.execute(stmt, {
                "user_id": user_id,
                "perm_assets": permissions.get("perm_assets", True),
                "perm_liabilities": permissions.get("perm_liabilities", True),
                "perm_transactions": permissions.get("perm_transactions", True),
                "perm_investments": permissions.get("perm_investments", True),
                "perm_credit_score": permissions.get("perm_credit_score", True),
                "perm_epf_balance": permissions.get("perm_epf_balance", True)
            })
            conn.commit()
            
            return {
                "message": "AI permissions updated successfully",
                "status": "success",
                "updated_permissions": permissions
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/profile-summary")
async def get_profile_summary(user_id: str = Query(..., description="Firebase UID")):
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
                "initials": initials
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.delete("/delete-account")
async def delete_user_account(user_id: str = Query(..., description="Firebase UID")):
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
            tables = ['Transactions', 'Assets', 'Liabilities', 'Investments']
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
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.post("/create-user")
async def create_user(user_data: dict):
    """Create new user account"""
    try:
        required_fields = ["user_id", "name"]
        for field in required_fields:
            if field not in user_data:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        
        engine = get_engine()
        with engine.connect() as conn:
            # Check if user already exists
            existing_user = conn.execute(
                sqlalchemy.text("SELECT user_id FROM Users WHERE user_id = :user_id"),
                {"user_id": user_data["user_id"]}
            ).fetchone()
            
            if existing_user:
                raise HTTPException(status_code=409, detail="User already exists")
            
            # Create user
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
                "credit_score": user_data.get("credit_score", 750),
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
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")