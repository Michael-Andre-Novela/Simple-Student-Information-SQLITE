import sys
import os

# This line tells Python to look in the current folder for our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from gui.main_window import MainWindow
from modules.database_io import db_initialization, migration, get_count

if __name__ == "__main__":
    db_initialization()
    if not get_count("colleges") > 0:
        migration()
    app = MainWindow()
    app.mainloop()