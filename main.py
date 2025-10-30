import os
import threading
import webbrowser
from tkinter import Tk, Label, Entry, Button, IntVar, Checkbutton, messagebox, ttk
from barcode import EAN13
from barcode.writer import ImageWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from PIL import Image


def generate_barcode(number: str, output_dir="barcodes"):
    os.makedirs(output_dir, exist_ok=True)
    filename = os.path.join(output_dir, number)
    barcode = EAN13(number, writer=ImageWriter())
    barcode.save(filename)
    return filename + ".png"


def save_barcodes_to_pdf(start: int, end: int, rows=8, cols=3, pdf_name="barcodes.pdf",
                         draw_grid=True, progress_callback=None):
    c = canvas.Canvas(pdf_name, pagesize=A4)
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

        # Update progress bar
        if progress_callback:
            progress_callback(int((idx + 1) / total * 100))

    c.save()
    return pdf_name


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
                webbrowser.open_new(pdf_path)  # open the PDF after done
            except Exception as e:
                messagebox.showerror("Error", str(e))
            finally:
                generate_button.config(state="normal", text="Generate PDF")
                progress_bar["value"] = 0

        threading.Thread(target=task, daemon=True).start()

    except Exception as e:
        messagebox.showerror("Error", str(e))


# --- GUI Setup ---
root = Tk()
root.title("📦 Barcode PDF Generator")
root.geometry("320x360")

Label(root, text="Start Number:").pack(pady=3)
start_entry = Entry(root)
start_entry.pack()

Label(root, text="End Number:").pack(pady=3)
end_entry = Entry(root)
end_entry.pack()

Label(root, text="Rows per page:").pack(pady=3)
rows_entry = Entry(root)
rows_entry.insert(0, "8")
rows_entry.pack()

Label(root, text="Columns per page:").pack(pady=3)
cols_entry = Entry(root)
cols_entry.insert(0, "3")
cols_entry.pack()

grid_var = IntVar(value=1)
Checkbutton(root, text="Draw Grid", variable=grid_var).pack(pady=5)

generate_button = Button(root, text="Generate PDF", command=on_generate, bg="#4CAF50", fg="white")
generate_button.pack(pady=10)

# Progress Bar
progress_bar = ttk.Progressbar(root, orient="horizontal", length=250, mode="determinate")
progress_bar.pack(pady=10)

root.mainloop()
