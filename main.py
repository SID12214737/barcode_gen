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
    
    # Fallback: disable text rendering completely
    ImageWriter.default_writer_options['write_text'] = False
    
fix_barcode_font()


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def generate_barcode(number: str, output_dir):
    """Generate a single barcode image and return its path."""
    os.makedirs(output_dir, exist_ok=True)
    filename = os.path.join(output_dir, number)
    
    # Configure writer options to prevent font issues
    writer_options = {
        'write_text': False,  # Disable text to avoid font errors
        'module_height': 15.0,
        'module_width': 0.2,
        'quiet_zone': 6.5,
    }
    
    barcode_obj = EAN13(number, writer=ImageWriter())
    barcode_obj.save(filename, options=writer_options)
    return filename + ".png"


def save_barcodes_to_pdf(start: int, end: int, rows=8, cols=3, pdf_name="barcodes.pdf",
                         draw_grid=True, progress_callback=None):
    """Generate PDF with barcodes arranged in a grid layout."""
    pdf_path = os.path.join(os.getcwd(), pdf_name)
    
    # Create temporary directory for barcode images
    temp_dir = tempfile.mkdtemp()
    
    try:
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

            # Generate barcode in temp directory
            img_path = generate_barcode(number_str, temp_dir)
            
            row = (idx // cols) % rows
            col = idx % cols

            # Start new page when grid is full
            if idx > 0 and idx % (rows * cols) == 0:
                c.showPage()

            # Draw grid if enabled
            if draw_grid:
                c.rect(col * cell_width, page_height - (row + 1) * cell_height, 
                       cell_width, cell_height)

            # Open and scale image
            with Image.open(img_path) as img:
                img_width, img_height = img.size
                scale = min(
                    (cell_width - 2 * x_margin) / img_width, 
                    (cell_height - 2 * y_margin) / img_height
                )
                img_width *= scale
                img_height *= scale

            # Center image in cell
            x = col * cell_width + (cell_width - img_width) / 2
            y = page_height - (row + 1) * cell_height + (cell_height - img_height) / 2

            c.drawImage(img_path, x, y, width=img_width, height=img_height)

            # Update progress
            if progress_callback:
                progress_callback(int((idx + 1) / total * 100))

        c.save()
        
    finally:
        # Clean up temporary directory
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
        self.root.geometry("400x480")
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
        
        # Start Number
        Label(self.root, text="Start Number:", font=self.bold_font).pack(pady=(5, 0))
        self.start_entry = Entry(self.root, font=self.base_font, width=25)
        self.start_entry.pack(pady=(0, 5))
        self.start_entry.bind("<KeyRelease>", lambda e: validate_numeric_input(self.start_entry))
        self.start_entry.bind("<FocusOut>", lambda e: validate_int(self.start_entry, 0, 999999999999))
        
        # End Number
        Label(self.root, text="End Number:", font=self.bold_font).pack(pady=(5, 0))
        self.end_entry = Entry(self.root, font=self.base_font, width=25)
        self.end_entry.pack(pady=(0, 5))
        self.end_entry.bind("<KeyRelease>", lambda e: validate_numeric_input(self.end_entry))
        self.end_entry.bind("<FocusOut>", lambda e: validate_int(self.end_entry, 0, 999999999999))
        
        # Rows and Columns Frame
        frame_rc = Frame(self.root)
        frame_rc.pack(pady=10)
        
        Label(frame_rc, text="Rows:", font=self.bold_font).grid(row=0, column=0, padx=5)
        self.rows_entry = Entry(frame_rc, width=8, font=self.base_font)
        self.rows_entry.insert(0, "8")
        self.rows_entry.grid(row=0, column=1, padx=5)
        self.rows_entry.bind("<FocusOut>", lambda e: validate_int(self.rows_entry, 1, 20))
        
        Label(frame_rc, text="Cols:", font=self.bold_font).grid(row=0, column=2, padx=5)
        self.cols_entry = Entry(frame_rc, width=8, font=self.base_font)
        self.cols_entry.insert(0, "3")
        self.cols_entry.grid(row=0, column=3, padx=5)
        self.cols_entry.bind("<FocusOut>", lambda e: validate_int(self.cols_entry, 1, 10))
        
        # Options
        self.grid_var = IntVar(value=1)
        Checkbutton(
            self.root, 
            text="Draw Grid Lines", 
            variable=self.grid_var, 
            font=self.base_font
        ).pack(pady=5)
        
        # PDF Name
        pdf_frame = Frame(self.root)
        pdf_frame.pack(pady=5)
        Label(pdf_frame, text="PDF Name:", font=self.bold_font).pack(side="left", padx=5)
        self.pdf_name_entry = Entry(pdf_frame, width=20, font=self.base_font)
        self.pdf_name_entry.insert(0, "barcodes.pdf")
        self.pdf_name_entry.pack(side="left")
        
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
    
    def validate_all_inputs(self):
        """Check that all fields are filled and valid before generating."""
        ok1 = validate_int(self.start_entry, 0, 999999999999)
        ok2 = validate_int(self.end_entry, 0, 999999999999)
        ok3 = validate_int(self.rows_entry, 1, 20)
        ok4 = validate_int(self.cols_entry, 1, 10)

        if not all([ok1, ok2, ok3, ok4]):
            messagebox.showerror("Validation Error", "Please fill all fields with valid numbers!")
            return False
        
        # Check start <= end
        start = int(self.start_entry.get())
        end = int(self.end_entry.get())
        if start > end:
            messagebox.showerror("Validation Error", "Start number must be less than or equal to end number!")
            return False
        
        # Validate PDF name
        pdf_name = self.pdf_name_entry.get().strip()
        if not pdf_name:
            messagebox.showerror("Validation Error", "Please enter a PDF filename!")
            return False
        
        if not pdf_name.endswith('.pdf'):
            pdf_name += '.pdf'
            self.pdf_name_entry.delete(0, 'end')
            self.pdf_name_entry.insert(0, pdf_name)
        
        return True
    
    def on_generate_with_validation(self):
        """Validate inputs and start generation process."""
        if not self.validate_all_inputs():
            return
        self.on_generate()
    
    def on_generate(self):
        """Generate the PDF in a separate thread."""
        try:
            start = int(self.start_entry.get())
            end = int(self.end_entry.get())
            rows = int(self.rows_entry.get())
            cols = int(self.cols_entry.get())
            draw_grid = bool(self.grid_var.get())
            pdf_name = self.pdf_name_entry.get().strip()

            self.progress_bar["value"] = 0
            self.generate_button.config(state="disabled")
            self.status_label.config(text="Generating barcodes...", fg="blue")

            def task():
                try:
                    pdf_path = save_barcodes_to_pdf(
                        start, end, rows, cols,
                        pdf_name=pdf_name,
                        draw_grid=draw_grid,
                        progress_callback=lambda p: self.root.after(
                            0, 
                            self.update_progress, 
                            p
                        )
                    )
                    
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