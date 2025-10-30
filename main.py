import os
import sys
import threading
import webbrowser
from tkinter import Tk, Label, Entry, Button, IntVar, Checkbutton, messagebox, ttk, Frame, filedialog
from barcode import EAN13
from barcode.writer import ImageWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from PIL import Image
import tempfile
import shutil

def fix_barcode_font():
    """Force python-barcode to use a known, bundled font file."""
    from barcode.writer import ImageWriter
    
    # Try multiple font locations
    possible_fonts = [
        os.path.join(os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else __file__), "arial.ttf"),
        "C:\\Windows\\Fonts\\arial.ttf",
        "C:\\Windows\\Fonts\\Arial.ttf",
        "C:\\Windows\\Fonts\\DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux
        "/System/Library/Fonts/Helvetica.ttc",  # macOS
    ]
    
    font_path = None
    for path in possible_fonts:
        if os.path.exists(path):
            font_path = path
            break
    
    if font_path:
        try:
            ImageWriter.font_path = font_path
            print(f"Using font: {font_path}")
        except Exception as e:
            print(f"Could not set font: {e}")
    

fix_barcode_font()


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


import random
import math

def generate_unique_barcodes(count: int) -> list[str]:
    """Generate a list of unique random 12-digit numbers."""
    barcodes = set()
    while len(barcodes) < count:
        number = ''.join(random.choices("0123456789", k=12))
        barcodes.add(number)
    return list(barcodes)


def generate_barcode(number: str, output_dir):
    """Generate a single barcode image and return its path."""
    os.makedirs(output_dir, exist_ok=True)
    filename = os.path.join(output_dir, number)
    
    # Configure writer options to prevent font issues
    writer_options = {
        'write_text': True,
        'module_height': 15.0,
        'module_width': 0.2,
        'quiet_zone': 6.5,
    }
    
    barcode_obj = EAN13(number, writer=ImageWriter())
    barcode_obj.save(filename, options=writer_options)
    return filename + ".png"


def calculate_max_rows(
    cols: int,
    page_height=A4[1],
    page_width=A4[0],
    base_barcode_width=40 * mm,
    base_barcode_height=20 * mm,
    min_barcode_height=12 * mm,
    page_margin_top=1 * mm,
    page_margin_bottom=1 * mm,
    page_margin_left=1 * mm,
    page_margin_right=1 * mm,
) -> int:
    """
    Calculate how many rows of 12-digit horizontal barcodes fit on a page,
    adjusting for the number of columns and barcode aspect ratio.
    
    Args:
        cols: Number of columns.
        page_height: Page height (default A4).
        page_width: Page width (default A4).
        base_barcode_width: Desired width of one barcode at 1 column (default 40mm).
        base_barcode_height: Desired height at 1 column (default 20mm).
        min_barcode_height: Minimum readable height (default 12mm).
        page_margin_*: Page margins.
    
    Returns:
        Maximum number of rows that fit on the page.
    """

    # Available drawing area
    available_height = page_height - page_margin_top - page_margin_bottom
    available_width = page_width - page_margin_left - page_margin_right

    # Compute actual cell width given the number of columns
    col_width = available_width / cols

    # Maintain barcode aspect ratio (horizontal)
    aspect_ratio = base_barcode_height / base_barcode_width
    adjusted_barcode_height = max(min_barcode_height, col_width * aspect_ratio)

    # Calculate how many rows fit vertically
    max_rows = int(available_height / adjusted_barcode_height)

    return max(1, max_rows)


def save_barcodes_to_pdf(count: int, cols=3, pdf_name="barcodes.pdf",
                         draw_grid=True, progress_callback=None):
    """Generate PDF with random unique barcodes arranged in a grid layout."""
    pdf_path = os.path.join(os.getcwd(), pdf_name)
    temp_dir = tempfile.mkdtemp()

    try:
        c = canvas.Canvas(pdf_path, pagesize=A4)
        page_width, page_height = A4

        # Random barcode numbers
        numbers = generate_unique_barcodes(count)
        
        # Calculate max rows dynamically based on number of columns
        max_rows = calculate_max_rows(cols, page_height)
        barcodes_per_page = cols * max_rows
        
        # Divide page into rows and columns
        cell_width = page_width / cols
        cell_height = page_height / max_rows

        x_margin = 1 * mm
        y_margin = 1 * mm

        for idx, number_str in enumerate(numbers):
            img_path = generate_barcode(number_str, temp_dir)
            
            # Calculate position on current page
            page_idx = idx % barcodes_per_page
            row = page_idx // cols
            col = page_idx % cols

            # Start new page when needed
            if idx > 0 and idx % barcodes_per_page == 0:
                c.showPage()

            # Draw grid cell
            if draw_grid:
                c.rect(col * cell_width, page_height - (row + 1) * cell_height,
                       cell_width, cell_height)

            # Scale and position barcode image
            with Image.open(img_path) as img:
                img_width, img_height = img.size
                scale = min(
                    (cell_width - 2 * x_margin) / img_width,
                    (cell_height - 2 * y_margin) / img_height
                )
                img_width *= scale
                img_height *= scale

            x = col * cell_width + (cell_width - img_width) / 2
            y = page_height - (row + 1) * cell_height + (cell_height - img_height) / 2
            c.drawImage(img_path, x, y, width=img_width, height=img_height)

            if progress_callback:
                progress_callback(int((idx + 1) / count * 100))

        c.save()
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    return pdf_path



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


class BarcodeGeneratorApp:
    """Main application class for the Barcode PDF Generator."""
    
    def __init__(self, root):
        self.root = root
        self.root.title("📦 Barcode PDF Generator")
        self.root.geometry("400x520")
        self.root.resizable(False, False)
        
        self.base_font = ("Arial", 11)
        self.bold_font = ("Arial", 11, "bold")
        self.title_font = ("Arial", 14, "bold")
        
        self.setup_ui()
    
    def setup_ui(self):
        """Create and arrange all UI elements."""
        # Title
        title_label = Label(
            self.root, 
            text="Barcode PDF Generator", 
            font=self.title_font,
            pady=10
        )
        title_label.pack()

        # Number of codes
        Label(self.root, text="Number of Codes:", font=self.bold_font).pack(pady=(5, 0))
        self.count_entry = Entry(self.root, font=self.base_font, width=25)
        self.count_entry.insert(0, "24")
        self.count_entry.pack(pady=(0, 5))
        self.count_entry.bind("<KeyRelease>", lambda e: validate_numeric_input(self.count_entry))

        # Columns
        frame_rc = Frame(self.root)
        frame_rc.pack(pady=10)
        
        Label(frame_rc, text="Columns:", font=self.bold_font).grid(row=0, column=0, padx=5)
        self.cols_entry = Entry(frame_rc, width=8, font=self.base_font)
        self.cols_entry.insert(0, "3")
        self.cols_entry.grid(row=0, column=1, padx=5)
        self.cols_entry.bind("<KeyRelease>", lambda e: self.update_layout_info())
        
        # Layout info label
        self.layout_info = Label(
            self.root, 
            text="Layout: 3 cols × 5 rows = 15 per page", 
            font=self.base_font,
            fg="blue"
        )
        self.layout_info.pack(pady=5)
        
        # Options
        self.grid_var = IntVar(value=1)
        Checkbutton(
            self.root, 
            text="Draw Grid Lines", 
            variable=self.grid_var, 
            font=self.base_font
        ).pack(pady=5)
        
        
        # Generate Button
        self.generate_button = Button(
            self.root,
            text="Generate PDF",
            command=self.on_generate_with_validation,
            bg="#4CAF50",
            fg="white",
            font=self.bold_font,
            width=18
        )
        self.generate_button.pack(pady=15)
        
        # Progress Bar
        self.progress_bar = ttk.Progressbar(
            self.root, 
            orient="horizontal", 
            length=300, 
            mode="determinate"
        )
        self.progress_bar.pack(pady=10)
        
        # Status Label
        self.status_label = Label(
            self.root, 
            text="Ready", 
            font=self.base_font, 
            fg="gray"
        )
        self.status_label.pack(pady=5)
    
    def update_layout_info(self):
        """Update the layout information label when columns change."""
        try:
            cols = int(self.cols_entry.get())
            if 1 <= cols <= 10:
                rows = calculate_max_rows(cols)
                per_page = cols * rows
                self.layout_info.config(
                    text=f"Layout: {cols} cols × {rows} rows = {per_page} per page",
                    fg="blue"
                )
                self.cols_entry.config(bg="white")
            else:
                self.cols_entry.config(bg="#ffcccc")
        except ValueError:
            if self.cols_entry.get():
                self.cols_entry.config(bg="#ffcccc")
    
    
    def on_generate_with_validation(self):
       
        """Validate inputs and start generation process."""
        ok1 = validate_int(self.count_entry, 1, 500)
        ok2 = validate_int(self.cols_entry, 1, 10)
        if not all([ok1, ok2]):
            messagebox.showerror("Validation Error", "Please fill all fields with valid numbers!")
            return
        
        # Ask user where to save the file
        pdf_path = filedialog.asksaveasfilename(
            title="Save Barcode PDF As",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialfile="barcodes.pdf"
        )
        
        if not pdf_path:
            return  # user cancelled

        self.on_generate(pdf_path)
    
    def on_generate(self, pdf_path):
        """Generate the PDF in a separate thread."""
        try:
            count = int(self.count_entry.get())
            cols = int(self.cols_entry.get())
            draw_grid = bool(self.grid_var.get())

            self.progress_bar["value"] = 0
            self.generate_button.config(state="disabled")
            self.status_label.config(text="Generating barcodes...", fg="blue")

            def task():
                try:
                    pdf_result_path = save_barcodes_to_pdf(
                        count, cols,
                        pdf_name=os.path.basename(pdf_path),
                        draw_grid=draw_grid,
                        progress_callback=lambda p: self.root.after(0, self.update_progress, p)
                    )
                    # Move result to chosen location
                    shutil.move(pdf_result_path, pdf_path)

                    self.root.after(0, self.on_generation_complete, pdf_path)

                except Exception as e:
                    error_text = f"{type(e).__name__}: {str(e)}"
                    self.root.after(0, self.on_generation_error, error_text)

            threading.Thread(target=task, daemon=True).start()

        except Exception as e:
            messagebox.showerror("Error", f"{type(e).__name__}: {str(e)}")

    
    def update_progress(self, value):
        """Update progress bar value."""
        self.progress_bar["value"] = value
        self.status_label.config(text=f"Progress: {value}%", fg="blue")
    
    def on_generation_complete(self, pdf_path):
        """Handle successful PDF generation."""
        self.generate_button.config(state="normal")
        self.progress_bar["value"] = 100
        self.status_label.config(text="✅ Generation complete!", fg="green")
        
        result = messagebox.askyesno(
            "Success", 
            "PDF generated successfully!\n\nWould you like to open it now?"
        )
        
        if result:
            webbrowser.open_new(pdf_path)
        
        self.progress_bar["value"] = 0
        self.status_label.config(text="Ready", fg="gray")
    
    def on_generation_error(self, error_text):
        """Handle generation errors."""
        self.generate_button.config(state="normal")
        self.progress_bar["value"] = 0
        self.status_label.config(text="❌ Generation failed", fg="red")
        messagebox.showerror("Error", error_text)
        self.status_label.config(text="Ready", fg="gray")


def main():
    """Main entry point for the application."""
    root = Tk()
    app = BarcodeGeneratorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()