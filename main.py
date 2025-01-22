from datetime import datetime, timedelta
import jwt
import random
import asyncio
import os
import pandas as pd
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from passlib.context import CryptContext
from database import get_db_connection

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
    """
    Add a new row to the CSV file.
    """
    try:
        df = load_csv()

        # Map API input to CSV columns
        new_row = {
            "user": row.user,
            "broker": row.broker,
            "API key": row.API_key,
            "API secret": row.API_secret,
            "pnl": row.pnl,
            "margin": row.margin,
            "max_risk": row.max_risk,
        }

        if row.user in df["user"].values:
            raise HTTPException(status_code=400, detail=f"User {row.user} already exists.")

        # Append new row
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

        save_csv(df)
        return {"message": "Row added successfully."}
    except FileNotFoundError:
        # Handle missing file case
        columns = ["user", "broker", "API key", "API secret", "pnl", "margin", "max_risk"]
        df = pd.DataFrame([new_row], columns=columns)
        save_csv(df)
        return {"message": "File created and row added successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/rows/{user}", tags=["Update"])
def update_row(user: str, row: TableRow, token: str = Depends(oauth2_scheme)):
    try:
        df = load_csv()

        if user not in df["user"].values:
            raise HTTPException(status_code=404, detail=f"User {user} not found.")

        # Clean up DataFrame: Remove extra columns if they exist
        expected_columns = ["user", "broker", "API key", "API secret", "pnl", "margin", "max_risk"]
        df = df[expected_columns]

        # Map API input to CSV columns
        updated_row = {
            "user": row.user,
            "broker": row.broker,
            "API key": row.API_key,
            "API secret": row.API_secret,
            "pnl": row.pnl,
            "margin": row.margin,
            "max_risk": row.max_risk,
        }

        # Update the row
        for key, value in updated_row.items():
            df.loc[df["user"] == user, key] = value

        save_csv(df)
        return {"message": f"Row for user {user} updated successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/rows/{user}", tags=["Delete"])
def delete_row(user: str, token: str = Depends(oauth2_scheme)):
    """
    Delete a row from the CSV file.
    """
    try:
        df = load_csv()

        if user not in df["user"].values:
            raise HTTPException(status_code=404, detail=f"User {user} not found.")

        # Remove the row where the user matches
        df = df[df["user"] != user]

        save_csv(df)
        return {"message": f"Row for user {user} deleted successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
def read_root():
    return {"message": "Welcome to the backend!"}
