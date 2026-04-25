import tkinter as tk
import sys
import os
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from gui.main_window import MainApplication
from utils.config_manager import ConfigManager
from utils.logging_setup import setup_logging

class TradingBotApp:
    def __init__(self):
        self.config = ConfigManager()
        self.setup_directories()
    
    def setup_directories(self):
        directories = ['data/historical', 'data/live', 'data/models', 'logs', 'config']
        for directory in directories:
            os.makedirs(os.path.join(project_root, directory), exist_ok=True)
    
    def run(self):
        root = tk.Tk()
        app = MainApplication(root, self.config)
        root.mainloop()

if __name__ == "__main__":
    setup_logging()
    app = TradingBotApp()
    app.run()
