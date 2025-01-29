from datetime import datetime, timedelta
import jwt
import random
import asyncio
from filelock import FileLock
import shutil
import os
import pandas as pd
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from passlib.context import CryptContext
from database import get_db_connection
import time
import threading

# Initialize a threading lock
csv_lock = threading.Lock()

# Secret key and algorithm for JWT
SECRET_KEY = "123456789"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

# FastAPI app
app = FastAPI()

# CSV File Path
CSV_FILE_PATH = "public/backend_table.csv"
BACKUP_FILE_PATH = "public/backend_table_backup.csv"
LOCK_FILE_PATH = f"{CSV_FILE_PATH}.lock"

# JWT helper functions
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_jwt(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )

def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = decode_jwt(token)
    username = payload.get("sub")
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )
    return username

# Models
class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

# TableRow model
class TableRow(BaseModel):
    user: str
    broker: str
    API_key: str
    API_secret: str
    pnl: float
    margin: float
    max_risk: float

# Helper functions
def load_csv():
    if os.path.exists(CSV_FILE_PATH):
        return pd.read_csv(CSV_FILE_PATH)
    else:
        raise FileNotFoundError(f"File {CSV_FILE_PATH} not found.")

def save_csv(df):
    df.to_csv(CSV_FILE_PATH, index=False)

def create_backup():
    """
    Creates a backup of the original CSV file.
    If a backup already exists, it will be overwritten.
    """
    try:
        if os.path.exists(CSV_FILE_PATH):
            shutil.copy(CSV_FILE_PATH, BACKUP_FILE_PATH)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating backup: {str(e)}")

def load_csv_with_lock():
    """
    Loads the CSV file with a file lock to ensure exclusive access.
    """
    try:
        print(f"Checking lock file: {LOCK_FILE_PATH}")
        if os.path.exists(LOCK_FILE_PATH):
            print(f"Lock file exists. Checking its status...")

        print("Acquiring lock to load CSV...")
        with FileLock(LOCK_FILE_PATH):
            print("Lock acquired for loading CSV.")
            time.sleep(0.5)  # Small delay for testing
            if not os.path.exists(CSV_FILE_PATH):
                print("CSV file not found.")
                raise HTTPException(status_code=404, detail="CSV file not found.")
            print(f"Loading CSV from {CSV_FILE_PATH}...")
            df = pd.read_csv(CSV_FILE_PATH)
            print("CSV loaded successfully.")
            return df
    except Exception as e:
        print(f"Error during load_csv_with_lock: {e}")
        raise HTTPException(status_code=500, detail=f"Error loading CSV: {str(e)}")

def save_csv_with_lock(df):
    """
    Saves the CSV file with a file lock to ensure exclusive access.
    """
    try:
        print("Acquiring lock to save CSV...")
        with FileLock(LOCK_FILE_PATH):
            print("Lock acquired for saving CSV.")
            time.sleep(0.5)  # Small delay for testing
            print(f"Saving CSV to {CSV_FILE_PATH}...")
            df.to_csv(CSV_FILE_PATH, index=False)
            print("CSV saved successfully.")
    except Exception as e:
        print(f"Error during save_csv_with_lock: {e}")
        raise HTTPException(status_code=500, detail=f"Error saving CSV: {str(e)}")

# Routes
@app.post("/login")
async def login(credentials: UserLogin, db=Depends(get_db_connection)):
    username = credentials.username
    password = credentials.password

    # Accept any username/password (for demonstration)
    access_token = create_access_token(data={"sub": username})
    try:
        with db as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO user_sessions (username, session_token) VALUES (?, ?)",
                (username, access_token),
            )
            conn.commit()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Database error: " + str(e))

    return Token(access_token=access_token, token_type="bearer")

@app.get("/sessions")
async def get_sessions(db=Depends(get_db_connection)):
    """
    Retrieves all user sessions.
    """
    try:
        with db as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, username, session_token FROM user_sessions")
            sessions = cursor.fetchall()

        # Convert the query results to a list of dictionaries
        session_list = [{"id":row["id"],"username": row["username"], "token": row["session_token"]} for row in sessions]

        return {"sessions": session_list}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Database error: " + str(e))

@app.get("/random-numbers")
async def generate_random_numbers(current_user: str = Depends(get_current_user)):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Generate and store random numbers
            for _ in range(10):  # Generate 10 random numbers for demonstration
                random_number = random.randint(1, 100)
                timestamp = datetime.utcnow().isoformat()

                cursor.execute(
                    "INSERT INTO random_numbers (timestamp, random_number) VALUES (?, ?)",
                    (timestamp, random_number),
                )
                conn.commit()

                await asyncio.sleep(1)  # Pause for 1 second
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

    return {"message": "Random numbers generated and stored successfully."}

@app.get("/get-random-numbers", tags=["Random Numbers"])
async def get_random_numbers(db=Depends(get_db_connection)):
    try:
        with db as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT timestamp, random_number
                FROM random_numbers
                ORDER BY id ASC
                """
            )
            numbers = cursor.fetchall()

        result = [
            {"timestamp": row["timestamp"], "random_number": row["random_number"]}
            for row in numbers
        ]
        return {"data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching random numbers: {str(e)}")

# CRUD operations for CSV
@app.get("/rows", tags=["Read"])
def read_all_rows(token: str = Depends(oauth2_scheme)):
    """
    Fetch all rows from the CSV file.
    """
    try:
        df = load_csv()
        return df.to_dict(orient="records")  # Convert rows into a list of dictionaries
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/rows", tags=["Create"])
def create_row(row: TableRow, token: str = Depends(oauth2_scheme)):
    try:
        print("Received request to create a row.")
        
        with threading.Lock():  # Use threading lock for concurrency safety
            print("Lock acquired, proceeding with backup and CSV operation.")
            
            # Create a backup before making changes
            create_backup()
            print("Backup created successfully.")
            
            # Load CSV
            try:
                print("Attempting to load CSV...")
                df = load_csv()
                print(f"CSV loaded. Current shape: {df.shape}.")
            except Exception as e:
                print(f"Error while loading CSV: {e}")
                raise HTTPException(status_code=500, detail="Error loading CSV.")
            
            # Check if user exists
            if row.user in df["user"].values:
                print(f"User {row.user} already exists in CSV.")
                raise HTTPException(status_code=400, detail=f"User {row.user} already exists.")
            
            # Add new row
            print(f"Adding new row for user: {row.user}")
            new_row = pd.DataFrame([{
                "user": row.user,
                "broker": row.broker,
                "API key": row.API_key,
                "API secret": row.API_secret,
                "pnl": row.pnl,
                "margin": row.margin,
                "max_risk": row.max_risk,
            }])
            df = pd.concat([df, new_row], ignore_index=True)
            print(f"New row added: {new_row.to_dict(orient='records')}")
            
            # Save CSV
            try:
                print("Attempting to save updated CSV...")
                save_csv(df)
                print("CSV updated and saved successfully.")
            except Exception as e:
                print(f"Error while saving CSV: {e}")
                raise HTTPException(status_code=500, detail="Error saving CSV.")
            
            return {"message": "Row added successfully."}
    except Exception as e:
        print(f"Error occurred: {e}")
        raise HTTPException(status_code=500, detail=f"An error occurred while adding the row: {str(e)}")

@app.put("/rows/{user}", tags=["Update"])
def update_row(user: str, row: TableRow, token: str = Depends(oauth2_scheme)):
    try:
        print("Received request to update a row.")
        
        with threading.Lock():  # Use threading lock for concurrency safety
            print("Lock acquired, proceeding with backup and CSV operation.")
            
            # Create a backup before making changes
            create_backup()
            print("Backup created successfully.")
            
            # Load CSV
            try:
                print("Attempting to load CSV...")
                df = load_csv()
                print(f"CSV loaded. Current shape: {df.shape}.")
            except Exception as e:
                print(f"Error while loading CSV: {e}")
                raise HTTPException(status_code=500, detail="Error loading CSV.")
            
            # Check if user exists
            if user not in df["user"].values:
                print(f"User {user} not found in CSV.")
                raise HTTPException(status_code=404, detail=f"User {user} not found.")
            
            # Prepare updated row data
            updated_row = {
                "user": row.user,
                "broker": row.broker,
                "API key": row.API_key,
                "API secret": row.API_secret,
                "pnl": row.pnl,
                "margin": row.margin,
                "max_risk": row.max_risk,
            }
            
            # Update the row in the DataFrame
            for key, value in updated_row.items():
                df.loc[df["user"] == user, key] = value
            print(f"Row for user {user} updated: {updated_row}")
            
            # Save updated DataFrame
            try:
                print("Attempting to save updated CSV...")
                save_csv(df)
                print("CSV updated and saved successfully.")
            except Exception as e:
                print(f"Error while saving CSV: {e}")
                raise HTTPException(status_code=500, detail="Error saving CSV.")
            
            return {"message": f"Row for user {user} updated successfully."}
    except Exception as e:
        print(f"Error occurred: {e}")
        raise HTTPException(status_code=500, detail=f"An error occurred while updating the row: {str(e)}")

@app.delete("/rows/{user}", tags=["Delete"])
def delete_row(user: str, token: str = Depends(oauth2_scheme)):
    try:
        print("Received request to delete a row.")
        
        with threading.Lock():  # Use threading lock for concurrency safety
            print("Lock acquired, proceeding with backup and CSV operation.")
            
            # Create a backup before making changes
            create_backup()
            print("Backup created successfully.")
            
            # Load CSV
            try:
                print("Attempting to load CSV...")
                df = load_csv()
                print(f"CSV loaded. Current shape: {df.shape}.")
            except Exception as e:
                print(f"Error while loading CSV: {e}")
                raise HTTPException(status_code=500, detail="Error loading CSV.")
            
            # Check if user exists
            if user not in df["user"].values:
                print(f"User {user} not found in CSV.")
                raise HTTPException(status_code=404, detail=f"User {user} not found.")
            
            # Delete the row for the specified user
            df = df[df["user"] != user]
            print(f"Row for user {user} deleted.")
            
            # Save updated DataFrame
            try:
                print("Attempting to save updated CSV...")
                save_csv(df)
                print("CSV updated and saved successfully.")
            except Exception as e:
                print(f"Error while saving CSV: {e}")
                raise HTTPException(status_code=500, detail="Error saving CSV.")
            
            return {"message": f"Row for user {user} deleted successfully."}
    except Exception as e:
        print(f"Error occurred: {e}")
        raise HTTPException(status_code=500, detail=f"An error occurred while deleting the row: {str(e)}")

@app.post("/restore-backup", tags=["Backup"])
def restore_backup(token: str = Depends(oauth2_scheme)):
    try:
        with FileLock(LOCK_FILE_PATH):  # Locking
            if not os.path.exists(BACKUP_FILE_PATH):
                raise HTTPException(status_code=404, detail="Backup file not found.")
            
            # Copy backup file data to the main file
            shutil.copy(BACKUP_FILE_PATH, CSV_FILE_PATH)
            print("Backup restored successfully.")
            
            # Delete the backup file after successful copy
            os.remove(BACKUP_FILE_PATH)
            print("Backup file deleted successfully.")
            
            return {"message": "Backup restored and backup file deleted successfully."}
    except Exception as e:
        print(f"Error occurred while restoring backup: {e}")
        raise HTTPException(status_code=500, detail=f"Error restoring backup: {str(e)}")

@app.get("/")
def read_root():
    return {"message": "Welcome to the backend!"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))  # Default to 8000 if $PORT not set
    uvicorn.run(app, host="0.0.0.0", port=port)
