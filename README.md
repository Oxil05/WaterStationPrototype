# AquaFlow Water Station Management System

A unified Water Refill Station Point of Sale (POS) and Customer Order Web Portal. Built with Flask (Web Backend), CustomTkinter (Desktop GUI), and SQLite.

---

## Prerequisites
Ensure you have the following installed on your machine:
*   [Python 3.10 or higher](https://www.python.org/downloads/)
*   [Git](https://git-scm.com/downloads)

---

## Installation & Setup

### 1. Clone the Repository
Clone the repository from GitHub and navigate into the project directory:
```bash
git clone https://github.com/Oxil05/WaterStationPrototype.git
cd WaterStationPrototype
```

### 2. Create a Virtual Environment
It is highly recommended to isolate dependencies inside a virtual environment:
```bash
# Create environment
python -m venv venv

# Activate on Windows (Command Prompt/PowerShell)
.\venv\Scripts\activate

# Activate on macOS/Linux
source venv/bin/activate
```

### 3. Install Dependencies
Install all required Python libraries:
```bash
pip install -r requirements.txt
```

### 4. Seed the Database
Initialize the SQLite database with seed tables, default products, admin accounts, and sample transactions:
```bash
python seed.py
```

---

## Running the Applications

### 1. Start the Web Portal (Flask Server)
Run the Flask server to host the customer portal and admin dashboard:
```bash
python run.py
```
Open your web browser and navigate to:
👉 **[http://127.0.0.1:5000](http://127.0.0.1:5000)**

*   **Admin Console Login**: Username: `admin` | Password: `admin123`
*   **Customer Login**: Username: `juan` | Password: `password123`

---

### 2. Start the Desktop POS Console
The desktop app connects to the same database. You can launch it using either method:

#### Method A: Run via Python (Recommended for Developers)
With your virtual environment activated, run:
```bash
python desktop_app.py
```

#### Method B: Run Standalone Executable (For Operators)
Launch the precompiled Windows application directly:
```bash
# Double-click the file in File Explorer or run:
.\dist\AquaFlow_POS.exe
```

*   **Operator Login**: Username: `admin` | Password: `admin123`
