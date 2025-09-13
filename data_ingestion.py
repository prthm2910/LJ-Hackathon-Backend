import json
import sqlalchemy # type: ignore
import urllib.parse

# --- 1. Database Connection Settings (Public IP Method) ---
# ⚠️ Replace with your actual Cloud SQL details
DB_USER = "postgres"
DB_PASS = urllib.parse.quote_plus("Hapy@1234")  # URL encode special characters
DB_NAME = "fintrack"
PUBLIC_IP = "34.31.134.92"  # Find this on the instance overview page
DB_PORT = "5432"  # Default PostgreSQL port

# --- 2. Load JSON Data ---
with open('data.json', 'r') as f:
    data = json.load(f)

# --- 3. Database Connection Logic (Public IP Method) ---
def get_engine():
    """Creates a SQLAlchemy engine using a standard connection string."""
    db_uri = f"postgresql+pg8000://{DB_USER}:{DB_PASS}@{PUBLIC_IP}:{DB_PORT}/{DB_NAME}"
    engine = sqlalchemy.create_engine(db_uri)
    return engine

# --- 4. Main Insertion Logic ---
def insert_data():
    engine = get_engine()
    with engine.connect() as conn:
        # Use a transaction to ensure all or nothing is inserted
        with conn.begin() as transaction:
            try:
                for user in data:
                    print(f"Processing user: {user['name']}")

                    # Step A: Insert into the Users table FIRST
                    user_stmt = sqlalchemy.text(
                        """
                        INSERT INTO Users (user_id, name, credit_score, epf_balance)
                        VALUES (:user_id, :name, :credit_score, :epf_balance)
                        """
                    )
                    conn.execute(user_stmt, {
                        "user_id": user['user_id'],
                        "name": user['name'],
                        "credit_score": user.get('credit_score'),
                        "epf_balance": user.get('epf_balance')
                    })

                    # Step B: Insert into the Transactions table
                    if 'transactions' in user and user['transactions']:
                        trans_stmt = sqlalchemy.text(
                            """
                            INSERT INTO Transactions (user_id, date, description, category, amount, type)
                            VALUES (:user_id, :date, :description, :category, :amount, :type)
                            """
                        )
                        for trans in user['transactions']:
                            conn.execute(trans_stmt, {"user_id": user['user_id'], **trans})

                    # Step C: Insert into the Assets table
                    if 'assets' in user and user['assets']:
                        asset_stmt = sqlalchemy.text(
                            """
                            INSERT INTO Assets (user_id, name, type, value)
                            VALUES (:user_id, :name, :type, :value)
                            """
                        )
                        for asset in user['assets']:
                            conn.execute(asset_stmt, {"user_id": user['user_id'], **asset})
                    
                    # Step D: Insert into the Liabilities table
                    if 'liabilities' in user and user['liabilities']:
                        lia_stmt = sqlalchemy.text(
                            """
                            INSERT INTO Liabilities (user_id, name, type, outstanding_balance)
                            VALUES (:user_id, :name, :type, :outstanding_balance)
                            """
                        )
                        for lia in user['liabilities']:
                            conn.execute(lia_stmt, {"user_id": user['user_id'], **lia})

                    # Step E: Insert into the Investments table
                    if 'investments' in user and user['investments']:
                        inv_stmt = sqlalchemy.text(
                            """
                            INSERT INTO Investments (user_id, name, ticker, type, quantity, current_value)
                            VALUES (:user_id, :name, :ticker, :type, :quantity, :current_value)
                            """
                        )
                        for inv in user['investments']:
                            conn.execute(inv_stmt, {"user_id": user['user_id'], **inv})
                
                print("\n✅ Data insertion successful!")
            except Exception as e:
                print(f"❌ An error occurred: {e}")
                transaction.rollback()
                print("⚠️ Transaction rolled back.")

if __name__ == "__main__":
    insert_data()
