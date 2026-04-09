import customtkinter as ctk
from PIL import Image
import os
from modules.database_io import add_program, update_program, delete_record, get_all
from modules.validators import normalize_program_data, validate_program

BG_BASE     = "#0d1117"
BG_FORM     = "#1c2230"
BG_INPUT    = "#21262d"
ACCENT_PURP = "#7c3aed"
ACCENT_GREEN= "#10b981"
ACCENT_RED  = "#ef4444"
TEXT_PRIMARY= "#e6edf3"
TEXT_MUTED  = "#8b949e"
BORDER      = "#30363d"

# Get project root for asset paths
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSET_LOGO_PATH = os.path.join(PROJECT_ROOT, "assets", "logo.png")

def styled_label(parent, text):
    return ctk.CTkLabel(parent, text=text, font=ctk.CTkFont(size=12),
                        text_color=TEXT_MUTED)

def styled_entry(parent, placeholder, width=340):
    return ctk.CTkEntry(parent, placeholder_text=placeholder,
                        width=width, height=38, corner_radius=8,
                        border_color=BORDER, fg_color=BG_INPUT,
                        text_color=TEXT_PRIMARY,
                        placeholder_text_color=TEXT_MUTED)

def styled_option(parent, values, variable, width=340):
    return ctk.CTkOptionMenu(parent, values=values, variable=variable,
                             width=width, height=38, corner_radius=8,
                             fg_color=BG_INPUT, button_color=ACCENT_PURP,
                             button_hover_color=BG_BASE,
                             text_color=TEXT_PRIMARY,
                             dropdown_fg_color=BG_INPUT,
                             dropdown_text_color=TEXT_PRIMARY)

def handle_delete(app, edit_data):
    code = str(edit_data[0])
    all_students = get_all("students")
    affected = [s for s in all_students if s.get('program_code') == code]

    confirm = ctk.CTkToplevel(app)
    confirm.title("Confirm Delete")
    confirm.resizable(False, False)
    confirm.configure(fg_color=BG_FORM)
    confirm.attributes("-topmost", True)
    _cw, _ch = 500, 200
    _cx = (confirm.winfo_screenwidth()  - _cw) // 2
    _cy = (confirm.winfo_screenheight() - _ch) // 2
    confirm.geometry(f"{_cw}x{_ch}+{_cx}+{_cy}")
    confirm.after(100, confirm.grab_set)

    ctk.CTkLabel(confirm, text=f"Delete program '{code}'?",
                 font=ctk.CTkFont(size=15, weight="bold"),
                 text_color=TEXT_PRIMARY).pack(pady=(24, 4))
    msg = (f"⚠  {len(affected)} student(s) will be unassigned."
           if affected else "This cannot be undone.")
    ctk.CTkLabel(confirm, text=msg,
                 text_color="#f59e0b" if affected else TEXT_MUTED).pack()

    bf = ctk.CTkFrame(confirm, fg_color="transparent")
    bf.pack(pady=20)

    def confirm_delete():
        delete_record('programs', code)

        app.current_data = get_all(app.current_file_key)
        app.refresh_table(app.current_display_keys)
        confirm.destroy()

    ctk.CTkButton(bf, text="Yes, Delete", fg_color=ACCENT_RED,
                  hover_color="#b91c1c", width=120, height=36,
                  corner_radius=8, command=confirm_delete).pack(side="left", padx=8)
    ctk.CTkButton(bf, text="Cancel", fg_color=BG_INPUT,
                  hover_color=BORDER, width=100, height=36,
                  corner_radius=8, command=confirm.destroy).pack(side="left", padx=8)
    
def open_program_form(app, edit_data=None):
    is_edit = edit_data is not None

    form = ctk.CTkToplevel(app)
    form.title("Edit Program" if is_edit else "Add Program")
    form.resizable(False, False)
    form.configure(fg_color=BG_FORM)
    form.attributes("-topmost", True)
    _w, _h = 420, 440
    _x = (form.winfo_screenwidth()  - _w) // 2
    _y = (form.winfo_screenheight() - _h) // 2
    form.geometry(f"{_w}x{_h}+{_x}+{_y}")
    form.after(100, form.grab_set)

    # Header
    header = ctk.CTkFrame(form, fg_color=BG_BASE, corner_radius=0, height=64)
    header.pack(fill="x")
    header.pack_propagate(False)
    ctk.CTkFrame(header, width=4, fg_color=ACCENT_PURP,
                 corner_radius=0).pack(side="left", fill="y")
    logo_img = ctk.CTkImage(Image.open(ASSET_LOGO_PATH), size=(48, 48))
    ctk.CTkLabel(header, image=logo_img, text="", width=48, height=48).pack(side="left", padx=(8, 4))
    ctk.CTkLabel(header,
                 text="Edit Program" if is_edit else "Add Program",
                 font=ctk.CTkFont(size=18, weight="bold"),
                 text_color=TEXT_PRIMARY).pack(side="left", padx=8)

    body = ctk.CTkFrame(form, fg_color="transparent")
    body.pack(fill="both", expand=True, padx=28, pady=16)

    styled_label(body, "Program Code").pack(anchor="w", pady=(8, 2))
    code_entry = styled_entry(body, "e.g.  BSCS")
    code_entry.pack(anchor="w")

    styled_label(body, "Program Name").pack(anchor="w", pady=(10, 2))
    name_entry = styled_entry(body, "Full program name")
    name_entry.pack(anchor="w")

    colleges_data = get_all("colleges")
    college_list = [c['code'] for c in colleges_data] if colleges_data else ["N/A"]
    college_var = ctk.StringVar(value=college_list[0])

    styled_label(body, "College").pack(anchor="w", pady=(10, 2))
    styled_option(body, college_list, college_var).pack(anchor="w")

    error_label = ctk.CTkLabel(body, text="", text_color=ACCENT_RED,
                               wraplength=340, font=ctk.CTkFont(size=12))
    error_label.pack(anchor="w", pady=(8, 0))

    if is_edit:
        code_entry.insert(0, str(edit_data[0]))
        code_entry.configure(state="disabled")
        name_entry.insert(0, str(edit_data[1]))
        if str(edit_data[2]) in college_list:
            college_var.set(str(edit_data[2]))

    def handle_save():
        code = str(edit_data[0]) if is_edit else code_entry.get().strip().upper()
        name = name_entry.get().strip()
        program_data = {"code": code, "name": name, "college_code": college_var.get()}
        program_data = normalize_program_data(program_data)

        is_valid, msg = validate_program(program_data, is_edit=is_edit)
        if not is_valid:
            error_label.configure(text=msg)
            return

        if is_edit:
            update_program(program_data["code"], program_data["name"], program_data["college_code"])
        else:
           add_program(program_data["code"], program_data["name"], program_data["college_code"])

        app.current_data = get_all("programs")
        app.refresh_table(app.current_display_keys)
        form.destroy()


    btn_row = ctk.CTkFrame(body, fg_color="transparent")
    btn_row.pack(fill="x", pady=(12, 0))

    ctk.CTkButton(btn_row,
                  text="Save Changes" if is_edit else "Save Program",
                  fg_color=ACCENT_GREEN, hover_color="#059669",
                  height=40, corner_radius=8,
                  font=ctk.CTkFont(size=13, weight="bold"),
                  command=handle_save).pack(side="left", padx=(0, 10))

    ctk.CTkButton(btn_row,
                  text="Cancel",
                  fg_color=BG_INPUT, hover_color=BORDER,
                  height=40, corner_radius=8,
                  font=ctk.CTkFont(size=13),
                  text_color=TEXT_MUTED,
                  command=form.destroy).pack(side="left")
