from datetime import datetime, timedelta
import jwt
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from passlib.context import CryptContext

# Replace 'your_secret_key' with a strong, random secret key
SECRET_KEY = "123456789"  # Replace with a strong, unique key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours in minutes

# Hashing context for password security
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Define a model for login credentials
class UserLogin(BaseModel):
    username: str
    password: str

# Define a model for the JWT token schema
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

# Create an OAuth2 password bearer object for token-based authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

# Fake user database (replace with actual authentication logic)
fake_users_db = {
    "Abhinav": {"username": "Abhinav", "hashed_password": pwd_context.hash("Abhinav@2001")}
}


app = FastAPI()


# Verify user credentials and generate JWT token
def verify_password(username: str, plain_password: str) -> bool:
    if username in fake_users_db:
        hashed_password = fake_users_db[username]["hashed_password"]
        return pwd_context.verify(plain_password, hashed_password)
    return False


def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# Function to decode and validate the JWT token
def decode_jwt(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # Check if the token has expired
        if datetime.utcnow() > datetime.fromtimestamp(payload["exp"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError: 
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        ) 

# Get current user from the JWT token
def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_jwt(token)
    except HTTPException as exc:
        raise exc
    username = payload.get("sub")
    if username is None:
        raise credentials_exception
    return {"username": username}


# Login route with JWT token generation
@app.post("/login")
async def login(credentials: UserLogin):
    username = credentials.username
    password = credentials.password

    if not verify_password(username, password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create JWT token with expiry time
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": username}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer")


@app.get("/hello")
async def hello_user(current_user: dict = Depends(get_current_user)):
    return {"message": f"Hello, {current_user['username']}!"}


@app.get("/")
def read_root():
    return {"message": "Welcome to the backend!"}