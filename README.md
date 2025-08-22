# PayU Starter

PayU Starter is a FastAPI-based example which demostrate integrating PayU payments with a simple admin interface and transaction tracking.

## Features

- PayU payment form and processing
- Admin UI for managing PayU credentials and reviewing transactions
- Secure admin login/logout
- Transaction history stored in SQLite
- Modern, unified UI

## Requirements

- Python 3.11+
- Conda (recommended) or virtualenv
- See `requirements.txt` for Python dependencies

## Quick Start

1. **Create and activate Conda environment**  
   ```powershell
   conda create -p .\.conda python=3.11 -y
   conda activate .\.conda
   ```

2. **Install dependencies**  
   ```powershell
   pip install -r requirements.txt
   ```

3. **Run the app**  
   ```powershell
   uvicorn app.main:app --reload
   ```

4. **Access the app**  
   - Home: [http://localhost:8000/](http://localhost:8000/)
   - Payment: [http://localhost:8000/pay](http://localhost:8000/pay)
   - Admin: [http://localhost:8000/admin](http://localhost:8000/admin)

## Usage

- Set up your PayU credentials in the admin panel (`/admin`).
- Create payments via the payment page (`/pay`).
- Review transactions and manage settings in the admin UI.

##