# dpp-backend

This is a Python backend project that uses Poetry for dependency management.

## Getting Started

### Prerequisites

* Python 3.8+
* Poetry

### Installation

1. **Install Poetry:**

   If you don't have Poetry installed, you can install it by following the official instructions [here](https://python-poetry.org/docs/#installation).

2. **Clone the repository:**

   ```bash
   git clone <repository-url>
   cd dpp-backend
   ```

3. **Install dependencies:**

   ```bash
   poetry install
   ```

### Running the application

1. **Activate the virtual environment:**

   ```bash
   poetry shell
   ```

2. **Run the application:**

   ```bash
   poetry run uvicorn app.main:app --reload
   ```
   

