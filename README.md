# Project Title: FastAPI Basic Backend

## Description
This is a backend project built with **FastAPI** to manage a CSV file with **CRUD operations**. The project also incorporates **JWT authentication**, **database integration**, and **backup management**. It allows secure access to modify the data in a CSV file while ensuring concurrency control with locks.

### Features
- JWT Authentication
- CRUD operations for CSV data (Create, Read, Update, Delete)
- Backup and restore functionalities for CSV data
- Random number generation and storage with timestamp

## Getting Started

### Prerequisites
Make sure you have the following installed:
- Python 3.7 or higher
- pip (Python package manager)

### Installation
1. Clone this repository to your local machine:
    ```bash
    git clone [https://github.com/yourusername/projectname.git](https://github.com/mathurabhinav1108/fastapi.git)
    ```

2. Navigate into the project directory:
    ```bash
    cd fastapi
    ```

3. Install the required dependencies:
    ```bash
    pip install -r requirements.txt
    ```

### Environment Variables
Set up the following environment variables:
- `SECRET_KEY`: A secret key used for signing JWT tokens.
- `DATABASE_URL`: Connection string for your database (e.g., SQLite or PostgreSQL).

### Running the Application
To start the server, run:
```bash
uvicorn main:app --reload
```

## API Endpoints

## Authentication

### POST /login
Description: Login endpoint to authenticate a user and generate a JWT token.
Request:
```bash
{
  "username": "your_username",
  "password": "your_password"
}
```
Response:
```bash
{
  "access_token": "jwt_token",
  "token_type": "bearer"
}
```
### GET /check-token
Description: Verify the validity of a JWT token.
Response:
```bash
{
  "status": true,
  "message": "Token is valid"
}
```

## CSV Operations

### GET /rows
Description: Fetch all rows from the CSV file.
Authentication: Requires JWT token.
Response: A list of rows in the CSV file.

### POST /rows
Description: Add a new row to the CSV file.
Request:
```bash
{
  "user": "username",
  "broker": "broker_name",
  "API_key": "api_key",
  "API_secret": "api_secret",
  "pnl": 10.5,
  "margin": 20.0,
  "max_risk": 15.0
}
```

### PUT /rows/{user}
Description: Update an existing row for a user in the CSV file.

### DELETE /rows/{user}
Description: Delete a specific row from the CSV file.

## Backup

### POST /restore-backup
Description: Restore the CSV file from the backup.

## Concurrency Control
The project ensures safe access to the CSV file using file locks. This prevents multiple processes from modifying the file simultaneously, avoiding race conditions and ensuring data integrity.

## Database Integration
This project integrates a database for storing:
1) User authentication data
2) Session management
3) Random number generation logs The database ensures persistent storage and retrieval of essential data.

## Error Handling
The API includes built-in error handling mechanisms:
1) FileNotFoundError: Triggered when the CSV file is missing.
2) HTTPException: Raised for unauthorized access, invalid JWT tokens, or incorrect operations.
3) Validation Errors: Handled using FastAPI's built-in validation system to ensure API requests meet expected formats.

## Technologies Used
1) FastAPI: A modern Python web framework for high-performance APIs.
2) SQLite/PostgreSQL: Used for database integration and data persistence.
3) JWT (JSON Web Tokens): For secure authentication and authorization.
4) pandas: Used to handle and process CSV file operations efficiently.

## License
This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments
This version follows your formatting preference for **Concurrency Control, Database Integration, Error Handling, and Technologies Used** while keeping everything clean and structured for easy readability in `README.md`. 🚀
