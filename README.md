# 🧾 Barcode Generator

A simple desktop app for generating and exporting **EAN-13 barcodes** with a clean Tkinter GUI.  
You can either use the included Windows executable (`main.exe`) or rebuild it from source using the provided `main.spec`.

---

## 📂 Included Files

| File | Description |
|------|--------------|
| `main.exe` | Ready-to-run Windows executable |
| `main.spec` | PyInstaller build file (for rebuilding the exe) |
| `main.py` | Source code |
| `README.md` | This file |

---

## 🖥️ How to Use (Windows)

### Option 1 — Run the Executable
1. Double-click **`main.exe`**
2. Enter an **EAN-13 number** (13 digits)
3. Adjust **rows** and **columns**
4. (Optional) Enable **grid lines**
5. Click **Generate**  
   → A PDF with barcodes will be created in the same folder

> 💡 You don’t need Python installed for this option.

---

### Option 2 — Run from Source (Developers)

1. Make sure Python 3.10+ is installed  
2. Install dependencies:

   ```bash
   pip install pillow python-barcode reportlab
