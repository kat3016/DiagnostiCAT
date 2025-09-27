"""
Script simple para iniciar el servidor sin dependencias adicionales
"""
import uvicorn
from main import app

if __name__ == "__main__":
    print("🚀 Iniciando DiagnostiCAT...")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)