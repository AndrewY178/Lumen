    #!/usr/bin/env python3
"""Entry point for running the Streamlit app"""
import subprocess
import sys
import os
from pathlib import Path

if __name__ == "__main__":
    # Get the directory where this script is located (project root)
    script_dir = Path(__file__).parent.absolute()
    app_path = script_dir / "frontend" / "app.py"
    
    # Change to the project root directory so Python can find backend/frontend packages
    os.chdir(script_dir)
    
    # Run streamlit with the app.py file
    # This ensures Python can find the backend and frontend packages
    subprocess.run([sys.executable, "-m", "streamlit", "run", str(app_path)] + sys.argv[1:])

