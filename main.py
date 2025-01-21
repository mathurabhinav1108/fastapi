from datetime import datetime, timedelta
import jwt
import random
import asyncio
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

# Models
class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

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

@app.get("/")
def read_root():
    return {"message": "Welcome to the backend!"}
