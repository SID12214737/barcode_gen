import os
import sys
import threading
import webbrowser
from tkinter import Tk, Label, Entry, Button, IntVar, Checkbutton, messagebox, ttk, Frame
import barcode
from barcode import EAN13
from barcode.writer import ImageWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from PIL import Image

import os, sys
def fix_barcode_font():
    """Force python-barcode to use a known, bundled font file."""
    font_path = os.path.join(os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else __file__), "arial.ttf")
    if not os.path.exists(font_path):
        # fallback: use system font if running locally
        font_path = "C:\\Windows\\Fonts\\arial.ttf"
    ImageWriter.font_path = font_path
    barcode.writer.ImageWriter.font_path = font_path

fix_barcode_font()

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def generate_barcode(number: str, output_dir="barcodes"):
    output_dir = resource_path(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    filename = os.path.join(output_dir, number)
    barcode = EAN13(number, writer=ImageWriter())
    barcode.save(filename)
    return filename + ".png"


def save_barcodes_to_pdf(start: int, end: int, rows=8, cols=3, pdf_name="barcodes.pdf",
                         draw_grid=True, progress_callback=None):
    pdf_path = os.path.join(os.getcwd(), pdf_name)
    c = canvas.Canvas(pdf_path, pagesize=A4)
    page_width, page_height = A4
    cell_width = page_width / cols
    cell_height = page_height / rows
    numbers = range(start, end + 1)

    x_margin = 5 * mm
    y_margin = 5 * mm

    total = len(numbers)
    for idx, num in enumerate(numbers):
        number_str = str(num).zfill(12)
        if len(number_str) > 12:
            raise ValueError("Number too long for EAN-13 (max 12 digits).")

        img_path = generate_barcode(number_str)
        row = (idx // cols) % rows
        col = idx % cols

        if idx > 0 and idx % (rows * cols) == 0:
            c.showPage()

        if draw_grid:
            c.rect(col * cell_width, page_height - (row + 1) * cell_height, cell_width, cell_height)

        img = Image.open(img_path)
        img_width, img_height = img.size
        scale = min((cell_width - 2 * x_margin) / img_width, (cell_height - 2 * y_margin) / img_height)
        img_width *= scale
        img_height *= scale
        img.close()

        x = col * cell_width + (cell_width - img_width) / 2
        y = page_height - (row + 1) * cell_height + (cell_height - img_height) / 2

        c.drawImage(img_path, x, y, width=img_width, height=img_height)

        if progress_callback:
            progress_callback(int((idx + 1) / total * 100))

    c.save()
    return pdf_path


def on_generate():
    try:
        start = int(start_entry.get())
        end = int(end_entry.get())
        rows = int(rows_entry.get())
        cols = int(cols_entry.get())
        draw_grid = bool(grid_var.get())

        if start > end:
            messagebox.showerror("Error", "Start number must be <= end number")
            return

        progress_bar["value"] = 0
        generate_button.config(state="disabled", text="Generating...")

        def task():
            try:
                pdf_path = save_barcodes_to_pdf(
                    start, end, rows, cols,
                    draw_grid=draw_grid,
                    progress_callback=lambda p: progress_bar.after(0, progress_bar.config, {"value": p})
                )
                messagebox.showinfo("Done", "✅ PDF generated successfully!")
                webbrowser.open_new(pdf_path)
            except Exception as e:
                messagebox.showerror("Error", str(e))
            finally:
                generate_button.config(state="normal", text="Generate PDF")
                progress_bar["value"] = 0

        threading.Thread(target=task, daemon=True).start()

    except Exception as e:
        messagebox.showerror("Error", str(e))


from tkinter import Tk, Label, Entry, Button, IntVar, Checkbutton, messagebox, ttk, Frame

# --- Smart Input Validation Helpers ---
def validate_int(entry_widget, min_val, max_val, required=True):
    """Validate numeric input with min/max and optional required check."""
    value = entry_widget.get().strip()
    if required and not value:
        entry_widget.config(bg="#ffcccc")
        return False

    try:
        val = int(value)
        if val < min_val or val > max_val:
            entry_widget.config(bg="#ffcccc")
            return False
        entry_widget.config(bg="white")
        return True
    except ValueError:
        entry_widget.config(bg="#ffcccc")
        return False


def validate_numeric_input(entry_widget):
    """Allow only digits in real time."""
    value = entry_widget.get()
    if not value.isdigit() and value != "":
        entry_widget.delete(0, 'end')
        entry_widget.config(bg="#ffcccc")
    else:
        entry_widget.config(bg="white")


def validate_all_inputs():
    """Check that all fields are filled and valid before generating."""
    ok1 = validate_int(start_entry, 0, 999999999999)
    ok2 = validate_int(end_entry, 0, 999999999999)
    ok3 = validate_int(rows_entry, 1, 20)
    ok4 = validate_int(cols_entry, 1, 10)

    if not all([ok1, ok2, ok3, ok4]):
        messagebox.showerror("Error", "Please fill all fields with valid numbers!")
        return False
    return True


# --- GUI Setup ---
root = Tk()
root.title("📦 Barcode PDF Generator")
root.geometry("380x420")

base_font = ("Arial", 12)
bold_font = ("Arial", 12, "bold")

Label(root, text="Start Number:", font=bold_font).pack(pady=3)
start_entry = Entry(root, font=base_font)
start_entry.pack()
start_entry.bind("<KeyRelease>", lambda e: validate_numeric_input(start_entry))
start_entry.bind("<FocusOut>", lambda e: validate_int(start_entry, 0, 999999999999))

Label(root, text="End Number:", font=bold_font).pack(pady=3)
end_entry = Entry(root, font=base_font)
end_entry.pack()
end_entry.bind("<KeyRelease>", lambda e: validate_numeric_input(end_entry))
end_entry.bind("<FocusOut>", lambda e: validate_int(end_entry, 0, 999999999999))

# --- Rows and Columns Frame ---
frame_rc = Frame(root)
frame_rc.pack(pady=5)

Label(frame_rc, text="Rows:", font=bold_font).grid(row=0, column=0, padx=5)
rows_entry = Entry(frame_rc, width=5, font=base_font)
rows_entry.insert(0, "8")
rows_entry.grid(row=0, column=1)
rows_entry.bind("<FocusOut>", lambda e: validate_int(rows_entry, 1, 20))

Label(frame_rc, text="Cols:", font=bold_font).grid(row=0, column=2, padx=5)
cols_entry = Entry(frame_rc, width=5, font=base_font)
cols_entry.insert(0, "3")
cols_entry.grid(row=0, column=3)
cols_entry.bind("<FocusOut>", lambda e: validate_int(cols_entry, 1, 10))

grid_var = IntVar(value=1)
Checkbutton(root, text="Draw Grid", variable=grid_var, font=base_font).pack(pady=5)

def on_generate_with_validation():
    if not validate_all_inputs():
        return
    on_generate()  # call your existing function

generate_button = Button(
    root,
    text="Generate PDF",
    command=on_generate_with_validation,
    bg="#4CAF50",
    fg="white",
    font=("Arial", 12, "bold")
)
generate_button.pack(pady=10)

progress_bar = ttk.Progressbar(root, orient="horizontal", length=250, mode="determinate")
progress_bar.pack(pady=10)

root.mainloop()