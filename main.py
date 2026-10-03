import os
from config import IMAGES_DIR, EXPORTS_DIR

os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(EXPORTS_DIR, exist_ok=True)

from ui.app import FashionApp

if __name__ == "__main__":
    app = FashionApp()
    app.mainloop()