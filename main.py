import os
import sys
import threading
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from barcode import Code128
from barcode.writer import ImageWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from PIL import Image
import tempfile
import shutil
import random
import json
import string


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


def generate_unique_barcodes(count: int, mode: str = "random_digits", start_code: str = None, length: int = 11) -> list:
    """
    Generate a list of unique Code128 barcodes.
    
    Args:
        count: Number of barcodes to generate
        mode: Generation mode - "random_digits", "random_alphanumeric", "random_full", "sequential"
        start_code: Starting code for sequential mode
        length: Length of generated codes
    
    Returns:
        List of barcode codes as strings
    """
    if mode == "random_digits":
        # Only digits (0-9)
        charset = string.digits
        barcodes = set()
        while len(barcodes) < count:
            code = ''.join(random.choices(charset, k=length))
            barcodes.add(code)
        return list(barcodes)
    
    elif mode == "random_alphanumeric":
        # Letters and digits (A-Z, 0-9)
        charset = string.ascii_uppercase + string.digits
        barcodes = set()
        while len(barcodes) < count:
            code = ''.join(random.choices(charset, k=length))
            barcodes.add(code)
        return list(barcodes)
    
    elif mode == "random_full":
        # Full ASCII printable characters (excluding space for readability)
        charset = string.ascii_letters + string.digits + string.punctuation.replace(' ', '')
        barcodes = set()
        while len(barcodes) < count:
            code = ''.join(random.choices(charset, k=length))
            barcodes.add(code)
        return list(barcodes)
    
    elif mode == "sequential":
        # Sequential mode - numeric only
        if start_code is None or not start_code.isdigit():
            start_code = "1".zfill(length)
        
        barcodes = []
        current = int(start_code)
        for i in range(count):
            barcodes.append(str(current).zfill(length))
            current += 1
        return barcodes
    
    else:
        raise ValueError(f"Unknown mode: {mode}")


def generate_barcode(code: str, output_dir, module_width=0.2, module_height=15.0):
    """Generate a single barcode image and return its path.
    
    Args:
        code: Barcode code string
        output_dir: Directory to save the barcode image
        module_width: Width of individual barcode modules (bars)
        module_height: Height of barcode bars in mm
    """
    os.makedirs(output_dir, exist_ok=True)
    # Use hash of code for filename to avoid filesystem issues with special chars
    safe_filename = str(abs(hash(code)))
    filename = os.path.join(output_dir, safe_filename)
    
    # Configure writer options to prevent font issues
    writer_options = {
        'write_text': True,
        'module_height': module_height,
        'module_width': module_width,
        'quiet_zone': 6.5,
    }
    
    barcode_obj = Code128(code, writer=ImageWriter())
    barcode_obj.save(filename, options=writer_options)
    return filename + ".png"


def calculate_max_rows(
    cols: int,
    page_height=A4[1],
    page_width=A4[0],
    base_barcode_width=40 * mm,
    base_barcode_height=20 * mm,
    min_barcode_height=12 * mm,
    page_margin_top=5 * mm,
    page_margin_bottom=5 * mm,
    page_margin_left=5 * mm,
    page_margin_right=5 * mm,
) -> int:
    """
    Calculate how many rows of horizontal barcodes fit on a page.
    """
    available_height = page_height - page_margin_top - page_margin_bottom
    available_width = page_width - page_margin_left - page_margin_right

    col_width = available_width / cols
    aspect_ratio = base_barcode_height / base_barcode_width
    adjusted_barcode_height = max(min_barcode_height, col_width * aspect_ratio)

    max_rows = int(available_height / adjusted_barcode_height)
    return max(1, max_rows)


def save_barcodes_to_pdf(
    count: int,
    cols=3,
    pdf_name="barcodes.pdf",
    draw_grid=True,
    progress_callback=None,
    mode="random_digits",
    start_code=None,
    code_length=11,
    margin_top=5 * mm,
    margin_bottom=5 * mm,
    margin_left=5 * mm,
    margin_right=5 * mm,
    barcode_width=40 * mm,
    barcode_height=20 * mm,
):
    """Generate PDF with unique barcodes arranged in a grid layout."""
    pdf_path = os.path.join(os.getcwd(), pdf_name)
    temp_dir = tempfile.mkdtemp()

    try:
        c = canvas.Canvas(pdf_path, pagesize=A4)
        page_width, page_height = A4

        codes = generate_unique_barcodes(count, mode, start_code, code_length)
        
        max_rows = calculate_max_rows(
            cols,
            page_height,
            page_width,
            base_barcode_width=barcode_width,
            base_barcode_height=barcode_height,
            page_margin_top=margin_top,
            page_margin_bottom=margin_bottom,
            page_margin_left=margin_left,
            page_margin_right=margin_right
        )

        barcodes_per_page = cols * max_rows
        
        usable_width = page_width - margin_left - margin_right
        usable_height = page_height - margin_top - margin_bottom

        cell_width = usable_width / cols
        cell_height = usable_height / max_rows

        x_margin = 1 * mm
        y_margin = 1 * mm

        module_width = (barcode_width / mm) / 95.0
        module_height = barcode_height / mm

        for idx, code_str in enumerate(codes):
            img_path = generate_barcode(code_str, temp_dir, module_width, module_height)
            
            page_idx = idx % barcodes_per_page
            row = page_idx // cols
            col = page_idx % cols

            if idx > 0 and idx % barcodes_per_page == 0:
                c.showPage()

            x0 = margin_left + col * cell_width
            y0 = page_height - margin_top - (row + 1) * cell_height

            if draw_grid:
                c.setDash(2, 2)
                c.rect(x0, y0, cell_width, cell_height)
                c.setDash()

            with Image.open(img_path) as img:
                img_width, img_height = img.size
                scale = min(
                    (cell_width - 2 * x_margin) / img_width,
                    (cell_height - 2 * y_margin) / img_height
                )
                img_width *= scale
                img_height *= scale

            x = x0 + (cell_width - img_width) / 2
            y = y0 + (cell_height - img_height) / 2
            c.drawImage(img_path, x, y, width=img_width, height=img_height)

            if progress_callback:
                progress_callback(int((idx + 1) / count * 100))

        c.save()
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    return pdf_path


class BarcodeGeneratorApp:
    """Modern ergonomic Shtrix-kod PDF Generator with full Code128 support"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Shtrix-kod PDF Generatori (Code128 To'liq)")
        self.root.geometry("420x810")
        self.root.resizable(False, False)

        # Styling
        style = ttk.Style()
        style.configure("TLabel", font=("Segoe UI", 10))
        style.configure("Bold.TLabel", font=("Segoe UI", 10, "bold"))
        style.configure("Title.TLabel", font=("Segoe UI", 14, "bold"))
        style.configure("TButton", font=("Segoe UI", 10))
        
        self.settings_file = "barcode_settings.json"
        self._settings = {}
        self._load_settings()

        self._build_ui()

    def _load_settings(self):
        """Load saved settings from JSON file."""
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    self._settings = json.load(f)
            except Exception:
                self._settings = {}
        else:
            self._settings = {}

    def _save_settings(self):
        """Save current UI settings to JSON file."""
        try:
            data = {
                "count": self.count_entry.get(),
                "cols": self.cols_entry.get(),
                "code_length": self.length_entry.get(),
                "barcode_width": self.barcode_width_entry.get(),
                "barcode_height": self.barcode_height_entry.get(),
                "margin_top": self.margin_top_entry.get(),
                "margin_bottom": self.margin_bottom_entry.get(),
                "margin_left": self.margin_left_entry.get(),
                "margin_right": self.margin_right_entry.get(),
                "mode": self.mode_var.get(),
                "start_code": self.start_entry.get(),
                "draw_grid": self.grid_var.get(),
            }
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Settings save failed: {e}")

    def _apply_settings(self):
        """Apply loaded settings to UI fields."""
        s = self._settings
        entries = {
            self.count_entry: s.get("count"),
            self.cols_entry: s.get("cols"),
            self.length_entry: s.get("code_length"),
            self.barcode_width_entry: s.get("barcode_width"),
            self.barcode_height_entry: s.get("barcode_height"),
            self.margin_top_entry: s.get("margin_top"),
            self.margin_bottom_entry: s.get("margin_bottom"),
            self.margin_left_entry: s.get("margin_left"),
            self.margin_right_entry: s.get("margin_right"),
        }
        for entry, value in entries.items():
            if value:
                entry.delete(0, "end")
                entry.insert(0, value)
        
        if s.get("mode"):
            self.mode_var.set(s["mode"])
        if s.get("start_code"):
            self.start_entry.delete(0, "end")
            self.start_entry.insert(0, s["start_code"])
        self.grid_var.set(s.get("draw_grid", True))
        self._toggle_mode()
        self._update_layout_info()

    def _build_ui(self):
        # --- Title ---
        ttk.Label(self.root, text="Shtrix-kod PDF Generatori", style="Title.TLabel").pack(pady=(10, 5))

        # --- Basic settings ---
        frame_basic = ttk.LabelFrame(self.root, text="Asosiy sozlamalar", padding=10)
        frame_basic.pack(padx=15, pady=5, fill="x")

        self.count_entry = self._labeled_entry(frame_basic, "Kodlar soni:", "24")
        self.count_entry.bind("<KeyRelease>", lambda e: self._update_layout_info())
        
        self.cols_entry = self._labeled_entry(frame_basic, "Ustunlar soni:", "3")
        self.cols_entry.bind("<KeyRelease>", lambda e: self._update_layout_info())

        self.length_entry = self._labeled_entry(frame_basic, "Kod uzunligi:", "11")

        self.layout_info = ttk.Label(frame_basic, text="Joylashuv: 3 ustun × 5 qator = 15 sahifada", foreground="blue")
        self.layout_info.pack(anchor="w", pady=(4, 0))

        # --- Barcode size ---
        frame_size = ttk.LabelFrame(self.root, text="Shtrix-kod o'lchamlari (mm)", padding=10)
        frame_size.pack(padx=15, pady=5, fill="x")

        self.barcode_width_entry = self._labeled_entry(frame_size, "Kenglik:", "40")
        self.barcode_width_entry.bind("<KeyRelease>", lambda e: self._update_layout_info())
        
        self.barcode_height_entry = self._labeled_entry(frame_size, "Balandlik:", "20")
        self.barcode_height_entry.bind("<KeyRelease>", lambda e: self._update_layout_info())

        # --- Page margins ---
        frame_margin = ttk.LabelFrame(self.root, text="Sahifa chegaralari (mm)", padding=10)
        frame_margin.pack(padx=15, pady=5, fill="x")

        self.margin_top_entry = self._labeled_entry(frame_margin, "Yuqori:", "5")
        self.margin_top_entry.bind("<KeyRelease>", lambda e: self._update_layout_info())
        
        self.margin_bottom_entry = self._labeled_entry(frame_margin, "Pastki:", "5")
        self.margin_bottom_entry.bind("<KeyRelease>", lambda e: self._update_layout_info())
        
        self.margin_left_entry = self._labeled_entry(frame_margin, "Chap:", "5")
        self.margin_left_entry.bind("<KeyRelease>", lambda e: self._update_layout_info())
        
        self.margin_right_entry = self._labeled_entry(frame_margin, "O'ng:", "5")
        self.margin_right_entry.bind("<KeyRelease>", lambda e: self._update_layout_info())

        # --- Mode selection ---
        frame_mode = ttk.LabelFrame(self.root, text="Shtrix-kod rejimi", padding=10)
        frame_mode.pack(padx=15, pady=5, fill="x")

        self.mode_var = tk.StringVar(value="random_digits")
        ttk.Radiobutton(frame_mode, text="Tasodifiy raqamlar (0-9)", variable=self.mode_var, 
                        value="random_digits", command=self._toggle_mode).pack(anchor="w")
        ttk.Radiobutton(frame_mode, text="Tasodifiy harf-raqamlar (A-Z, 0-9)", variable=self.mode_var, 
                        value="random_alphanumeric", command=self._toggle_mode).pack(anchor="w")
        ttk.Radiobutton(frame_mode, text="To'liq ASCII belgilar", variable=self.mode_var, 
                        value="random_full", command=self._toggle_mode).pack(anchor="w")
        ttk.Radiobutton(frame_mode, text="Ketma-ket raqamlar", variable=self.mode_var, 
                        value="sequential", command=self._toggle_mode).pack(anchor="w")

        self.start_entry = self._labeled_entry(frame_mode, "Boshlang'ich kod:", "0")
        self.start_entry.config(state="disabled")

        # --- Grid option ---
        self.grid_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(self.root, text="To'r chiziqlar chizilsin", variable=self.grid_var).pack(anchor="w", padx=20, pady=5)

        # --- Generate button ---
        self.btn_generate = ttk.Button(self.root, text="PDF yaratish", command=self._on_generate_clicked)
        self.btn_generate.pack(pady=10)

        # --- Progress and status ---
        self.progress = ttk.Progressbar(self.root, length=300, mode="determinate")
        self.progress.pack(pady=5)
        self.status = ttk.Label(self.root, text="Tayyor", foreground="gray")
        self.status.pack(pady=(0, 10))
        
        ttk.Label(self.root, text="SID12214737", foreground="gray").pack(side="bottom", pady=3, anchor='w')
        
        self._apply_settings()

        # Initialize layout info
        self._update_layout_info()

    def _labeled_entry(self, parent, text, default=""):
        """Create a labeled entry widget."""
        frame = ttk.Frame(parent)
        frame.pack(fill="x", pady=2)
        ttk.Label(frame, text=text, width=25, anchor="w").pack(side="left")
        entry = ttk.Entry(frame, width=15)
        entry.insert(0, default)
        entry.pack(side="left", fill="x", expand=True)
        return entry

    def _toggle_mode(self):
        """Toggle the start code entry based on mode."""
        if self.mode_var.get() == "sequential":
            self.start_entry.config(state="normal")
        else:
            self.start_entry.config(state="disabled")

    def _update_layout_info(self):
        """Update the layout information label."""
        try:
            cols = int(self.cols_entry.get())
            barcode_width = float(self.barcode_width_entry.get()) * mm
            barcode_height = float(self.barcode_height_entry.get()) * mm
            margin_top = float(self.margin_top_entry.get()) * mm
            margin_bottom = float(self.margin_bottom_entry.get()) * mm
            margin_left = float(self.margin_left_entry.get()) * mm
            margin_right = float(self.margin_right_entry.get()) * mm
            
            rows = calculate_max_rows(
                cols,
                base_barcode_width=barcode_width,
                base_barcode_height=barcode_height,
                page_margin_top=margin_top,
                page_margin_bottom=margin_bottom,
                page_margin_left=margin_left,
                page_margin_right=margin_right
            )
            per_page = cols * rows
            self.layout_info.config(
                text=f"Joylashuv: {cols} ustun × {rows} qator = {per_page} sahifada",
                foreground="blue"
            )
            
        except (ValueError, ZeroDivisionError):
            pass

    def _validate_inputs(self):
        """Validate all input fields."""
        try:
            
            code_length = int(self.length_entry.get())
            if not (4 <= code_length <= 20):
                messagebox.showerror("Xatolik", "Kod uzunligi 4 va 20 orasida bo'lishi kerak!")
                return False
            
            barcode_width = float(self.barcode_width_entry.get())
            if not (10 <= barcode_width <= 200):
                messagebox.showerror("Xatolik", "Shtrix-kod kengligi 10 va 200 mm orasida bo'lishi kerak!")
                return False
            
            barcode_height = float(self.barcode_height_entry.get())
            if not (5 <= barcode_height <= 100):
                messagebox.showerror("Xatolik", "Shtrix-kod balandligi 5 va 100 mm orasida bo'lishi kerak!")
                return False
            
            for entry, name in [
                (self.margin_top_entry, "Yuqori chegara"),
                (self.margin_bottom_entry, "Pastki chegara"),
                (self.margin_left_entry, "Chap chegara"),
                (self.margin_right_entry, "O'ng chegara")
            ]:
                val = float(entry.get())
                if not (0 <= val <= 50):
                    messagebox.showerror("Xatolik", f"{name} 0 va 50 mm orasida bo'lishi kerak!")
                    return False
            
            if self.mode_var.get() == "sequential":
                start_code = self.start_entry.get()
                if not start_code or not start_code.isdigit():
                    messagebox.showerror("Xatolik", "Ketma-ket rejimda boshlang'ich kod raqamlardan iborat bo'lishi kerak!")
                    return False
            
            return True
            
        except ValueError:
            messagebox.showerror("Xatolik", "Iltimos, barcha maydonlarni to'g'ri to'ldiring!")
            return False

    def _on_generate_clicked(self):
        """Handle the generate button click."""
        if not self._validate_inputs():
            return
        
        # Ask user where to save the PDF
        pdf_path = filedialog.asksaveasfilename(
            title="Shtrix-kodni PDF sifatida saqlash",
            defaultextension=".pdf",
            filetypes=[("PDF fayllar", "*.pdf")],
            initialfile="shtrix_kodlar.pdf"
        )

        if not pdf_path:
            return
        
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        
        self._save_settings()

        self._generate_pdf(pdf_path)

    def _on_close(self):
        self._save_settings()
        self.root.destroy()

    def _generate_pdf(self, pdf_path):
        """Generate the PDF in a separate thread."""
        try:
            count = int(self.count_entry.get())
            cols = int(self.cols_entry.get())
            code_length = int(self.length_entry.get())
            draw_grid = self.grid_var.get()
            mode = self.mode_var.get()
            start_code = self.start_entry.get() if mode == "sequential" else None
            
            barcode_width = float(self.barcode_width_entry.get()) * mm
            barcode_height = float(self.barcode_height_entry.get()) * mm
            margin_top = float(self.margin_top_entry.get()) * mm
            margin_bottom = float(self.margin_bottom_entry.get()) * mm
            margin_left = float(self.margin_left_entry.get()) * mm
            margin_right = float(self.margin_right_entry.get()) * mm

            self.progress["value"] = 0
            self.btn_generate.config(state="disabled")
            
            mode_names = {
                "random_digits": "tasodifiy raqamlar",
                "random_alphanumeric": "tasodifiy harf-raqamlar",
                "random_full": "to'liq ASCII",
                "sequential": "ketma-ket"
            }
            mode_text = mode_names.get(mode, "noma'lum")
            self.status.config(text=f"{mode_text} shtrix-kodlar yaratilmoqda...", foreground="blue")

            def task():
                try:
                    pdf_result_path = save_barcodes_to_pdf(
                        count, cols,
                        pdf_name=os.path.basename(pdf_path),
                        draw_grid=draw_grid,
                        mode=mode,
                        start_code=start_code,
                        code_length=code_length,
                        margin_top=margin_top,
                        margin_bottom=margin_bottom,
                        margin_left=margin_left,
                        margin_right=margin_right,
                        barcode_width=barcode_width,
                        barcode_height=barcode_height,
                        progress_callback=lambda p: self.root.after(0, self._update_progress, p)
                    )
                    shutil.move(pdf_result_path, pdf_path)
                    self.root.after(0, self._on_generation_complete, pdf_path)

                except Exception as e:
                    error_text = f"{type(e).__name__}: {str(e)}"
                    self.root.after(0, self._on_generation_error, error_text)

            threading.Thread(target=task, daemon=True).start()

        except Exception as e:
            messagebox.showerror("Xatolik", f"{type(e).__name__}: {str(e)}")

    def _update_progress(self, value):
        """Update the progress bar."""
        self.progress["value"] = value
        self.status.config(text=f"Jarayon: {value}%", foreground="blue")

    def _on_generation_complete(self, pdf_path):
        """Handle successful PDF generation."""
        self.btn_generate.config(state="normal")
        self.progress["value"] = 100
        self.status.config(text="Tayyor!", foreground="green")
        
        result = messagebox.askyesno(
            "Muvaffaqiyatli", 
            "PDF fayl muvaffaqiyatli yaratildi!\n\nHozir uni ochmoqchimisiz?"
        )
        
        if result:
            webbrowser.open_new(pdf_path)
        
        self.progress["value"] = 0
        self.status.config(text="Tayyor", foreground="gray")

    def _on_generation_error(self, error_text):
        """Handle generation errors."""
        self.btn_generate.config(state="normal")
        self.progress["value"] = 0
        self.status.config(text="Xatolik", foreground="red")
        messagebox.showerror("Xatolik", error_text)
        self.status.config(text="Tayyor", foreground="gray")


def main():
    root = tk.Tk()
    app = BarcodeGeneratorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()