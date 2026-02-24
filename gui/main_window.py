from tkinter import ttk
import tkinter as tk
import customtkinter as ctk
from modules.database_io import read_csv
from gui.student_forms import open_student_form
from gui.programs_forms import open_program_form
from gui.college_forms import open_college_form

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ************************************ Palette ************************************
BG_BASE      = "#0d1117"
BG_SIDEBAR   = "#161b22"
BG_CARD      = "#1c2230"
BG_ROW_ALT   = "#1e2736"
ACCENT_CYAN  = "#00d4ff"
ACCENT_PURP  = "#7c3aed"
ACCENT_GREEN = "#10b981"
ACCENT_RED   = "#ef4444"
TEXT_PRIMARY = "#e6edf3"
TEXT_MUTED   = "#8b949e"
SELECTED_ROW = "#1d3a5f"


class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.current_data  = []
        self.current_page  = 1
        self.sort_reverse  = False   # False = ascending, True = descending
        self.configure(fg_color=BG_BASE)

        self.title("Student Information System")
        self.geometry("1200x700")
        self.update_idletasks()
        try:
            self.state("zoomed")           # Windows / Mac
        except:
            try:
                self.attributes("-zoomed", True)   # Linux
            except:
                pass

        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_content_frame()

        self.show_students_view()
        self.tree.bind("<<TreeviewSelect>>", self.on_row_select)

    # ************************************Sidebar *************************************
    def _build_sidebar(self):
        self.sidebar_frame = ctk.CTkFrame(self, width=220, corner_radius=0,
                                          fg_color=BG_SIDEBAR)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_propagate(False)

        brand = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        brand.pack(fill="x", padx=20, pady=(28, 24))
        ctk.CTkLabel(brand, text="●", font=ctk.CTkFont(size=14),
                     text_color=ACCENT_CYAN).pack(side="left")
        ctk.CTkLabel(brand, text="  SIS Admin",
                     font=ctk.CTkFont(family="Courier", size=18, weight="bold"),
                     text_color=TEXT_PRIMARY).pack(side="left")

        ctk.CTkFrame(self.sidebar_frame, height=1,
                     fg_color="#30363d").pack(fill="x", padx=16, pady=(0, 20))

        ctk.CTkLabel(self.sidebar_frame, text="NAVIGATION",
                     font=ctk.CTkFont(size=10, weight="bold"),
                     text_color=TEXT_MUTED).pack(anchor="w", padx=24, pady=(0, 8))

        nav_items = [
            ("👤  Students", self.show_students_view, ACCENT_CYAN),
            ("📚  Programs", self.show_programs_view, ACCENT_PURP),
            ("🏛  Colleges", self.show_colleges_view, ACCENT_GREEN),
        ]
        self.nav_buttons = []
        for label, cmd, color in nav_items:
            btn = ctk.CTkButton(
                self.sidebar_frame, text=label, anchor="w",
                font=ctk.CTkFont(size=13), height=44,
                corner_radius=10, border_width=0,
                fg_color="transparent", hover_color="#21262d",
                text_color=TEXT_PRIMARY, command=cmd
            )
            btn.pack(fill="x", padx=12, pady=3)
            self.nav_buttons.append((btn, color))

        ctk.CTkLabel(self.sidebar_frame, text="v1.0.0",
                     font=ctk.CTkFont(size=10),
                     text_color=TEXT_MUTED).pack(side="bottom", pady=16)

    def _set_active_nav(self, index):
        for i, (btn, color) in enumerate(self.nav_buttons):
            if i == index:
                btn.configure(fg_color="#21262d", text_color=color,
                              border_width=1, border_color=color)
            else:
                btn.configure(fg_color="transparent", text_color=TEXT_PRIMARY,
                              border_width=0)

    # ************************************ Content Frame ************************************
    def _build_content_frame(self):
        self.content_frame = ctk.CTkFrame(self, corner_radius=16,
                                          fg_color=BG_CARD)
        self.content_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(0, weight=0)
        self.content_frame.grid_rowconfigure(1, weight=0)
        self.content_frame.grid_rowconfigure(2, weight=0)
        self.content_frame.grid_rowconfigure(3, weight=1)
        self.content_frame.grid_rowconfigure(4, weight=0)

    def clear_content(self):
        self.close_active_menu()
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(0, weight=0)
        self.content_frame.grid_rowconfigure(1, weight=0)
        self.content_frame.grid_rowconfigure(2, weight=0)
        self.content_frame.grid_rowconfigure(3, weight=1)
        self.content_frame.grid_rowconfigure(4, weight=0)

    def close_active_menu(self, event=None):
        if hasattr(self, 'active_menu'):
            try:
                self.active_menu.destroy()
            except:
                pass

    def on_row_select(self, event):
        pass

    # ************************************Common Controls ************************************
    def create_common_controls(self, title, accent, search_options, sort_options,
                               file_key, display_keys, add_command=None):
        self.clear_content()

        # Row 0 — header
        header = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(22, 0))

        accent_bar = ctk.CTkFrame(header, width=4, height=32,
                                  fg_color=accent, corner_radius=2)
        accent_bar.pack(side="left", padx=(0, 10))
        accent_bar.pack_propagate(False)

        ctk.CTkLabel(header, text=title,
                     font=ctk.CTkFont(size=22, weight="bold"),
                     text_color=TEXT_PRIMARY).pack(side="left")

        self.count_label = ctk.CTkLabel(
            header, text="",
            font=ctk.CTkFont(size=11),
            text_color=TEXT_MUTED,
            fg_color="#21262d", corner_radius=8
        )
        self.count_label.pack(side="right", ipadx=10, ipady=3)

        # Row 1 — divider
        ctk.CTkFrame(self.content_frame, height=1,
                     fg_color="#30363d").grid(row=1, column=0, sticky="ew",
                                              padx=24, pady=(12, 0))

        # Row 2 — controls
        ctrl = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        ctrl.grid(row=2, column=0, sticky="ew", padx=24, pady=12)

        entity = title.split()[0]
        ctk.CTkButton(
            ctrl, text=f"＋  Add {entity}", width=130, height=36,
            corner_radius=8, font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=ACCENT_GREEN, hover_color="#059669",
            text_color="white", command=add_command
        ).pack(side="left", padx=(0, 12))

        self.search_entry = ctk.CTkEntry(
            ctrl, placeholder_text=f"Search {entity.lower()}s…",
            width=210, height=36, corner_radius=8,
            border_color="#30363d", fg_color="#21262d",
            text_color=TEXT_PRIMARY, placeholder_text_color=TEXT_MUTED
        )
        self.search_entry.pack(side="left", padx=(0, 6))

        self.search_var = ctk.StringVar(value=list(search_options.keys())[0])
        ctk.CTkOptionMenu(
            ctrl, values=list(search_options.keys()),
            variable=self.search_var, width=130, height=36,
            corner_radius=8, fg_color="#21262d",
            button_color=accent, button_hover_color=BG_CARD,
            text_color=TEXT_PRIMARY, dropdown_fg_color="#21262d",
            dropdown_text_color=TEXT_PRIMARY
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            ctrl, text="Search", width=80, height=36,
            corner_radius=8, fg_color=accent, hover_color=BG_CARD,
            text_color="white", font=ctk.CTkFont(size=13),
            command=lambda: self.search_view_data(file_key, search_options, display_keys)
        ).pack(side="left")

        #  Sort controls (right side) ************************************
        self.sort_var     = ctk.StringVar(value=list(sort_options.keys())[0])
        self.sort_reverse = False  # reset on view switch

        # Order toggle button — updates its own label when clicked
        self.order_btn = ctk.CTkButton(
            ctrl, text="↑ ASC", width=76, height=36,
            corner_radius=8, fg_color="#21262d", hover_color="#30363d",
            text_color=ACCENT_CYAN, font=ctk.CTkFont(size=12, weight="bold"),
            command=lambda: self._toggle_order(file_key,
                                               sort_options,
                                               display_keys)
        )
        self.order_btn.pack(side="right", padx=(4, 0))

        # Sort button
        ctk.CTkButton(
            ctrl, text="Sort", width=70, height=36,
            corner_radius=8, fg_color="#21262d", hover_color="#30363d",
            text_color=TEXT_PRIMARY, font=ctk.CTkFont(size=13),
            command=lambda: self.sort_view_data(file_key,
                                                sort_options[self.sort_var.get()],
                                                display_keys)
        ).pack(side="right", padx=(4, 0))

        ctk.CTkOptionMenu(
            ctrl, values=list(sort_options.keys()),
            variable=self.sort_var, width=130, height=36,
            corner_radius=8, fg_color="#21262d",
            button_color="#30363d", button_hover_color=BG_CARD,
            text_color=TEXT_PRIMARY, dropdown_fg_color="#21262d",
            dropdown_text_color=TEXT_PRIMARY
        ).pack(side="right", padx=(0, 4))

        ctk.CTkLabel(ctrl, text="Sort by:", font=ctk.CTkFont(size=12),
                     text_color=TEXT_MUTED).pack(side="right", padx=(0, 4))

    def _toggle_order(self, file_key, sort_options, display_keys):
        #Toggle between ascending and descending, then re-sort.
        self.sort_reverse = not self.sort_reverse
        if self.sort_reverse:
            self.order_btn.configure(text="↓ DESC", text_color=ACCENT_PURP)
        else:
            self.order_btn.configure(text="↑ ASC",  text_color=ACCENT_CYAN)
        self.sort_view_data(file_key,
                            sort_options[self.sort_var.get()],
                            display_keys)

    # ************************************Treeview ************************************
    def setup_treeview(self, columns, accent=ACCENT_CYAN):
        all_cols = columns + ("actions",)

        style = ttk.Style()
        style.theme_use("default")
        style.configure("Modern.Treeview",
                        background=BG_CARD, foreground=TEXT_PRIMARY,
                        fieldbackground=BG_CARD, borderwidth=0,
                        rowheight=46, font=("Courier", 11))
        style.configure("Modern.Treeview.Heading",
                        background="#21262d", foreground=TEXT_MUTED,
                        borderwidth=0, font=("Courier", 10, "bold"),
                        relief="flat")
        style.map("Modern.Treeview",
                  background=[('selected', SELECTED_ROW)],
                  foreground=[('selected', ACCENT_CYAN)])
        style.map("Modern.Treeview.Heading",
                  background=[('active', '#30363d')])
        style.layout("Modern.Treeview", [
            ('Modern.Treeview.treearea', {'sticky': 'nswe'})
        ])

        # Row 3 — expands with window
        container = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        container.grid(row=3, column=0, sticky="nsew", padx=24, pady=(0, 4))
        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(0, weight=1)
        container.grid_rowconfigure(1, weight=0)

        self.tree = ttk.Treeview(container, columns=all_cols,
                                 show="headings", style="Modern.Treeview",
                                 selectmode="browse")
        v_scroll = ctk.CTkScrollbar(container, command=self.tree.yview,
                             button_color=accent, button_hover_color=BG_CARD)
        h_scroll = ctk.CTkScrollbar(container, orientation="horizontal",
                             command=self.tree.xview,
                             button_color=accent, button_hover_color=BG_CARD)
        self.tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")

        for col in all_cols:
            display = col.replace("_", " ").upper()
            self.tree.heading(col, text=display)
            if col == "actions":
                self.tree.column(col, width=130, anchor="center", stretch=False)
            elif col in ["name", "firstname", "lastname"]:
                self.tree.column(col, width=180, anchor="w", minwidth=120)
            elif col == "id":
                self.tree.column(col, width=110, anchor="center", minwidth=90)
            elif col == "program_code":
                self.tree.column(col, width=200, anchor="center", minwidth=160)
            else:
                self.tree.column(col, width=120, anchor="center", minwidth=80)

        self.tree.tag_configure("oddrow",  background=BG_CARD)
        self.tree.tag_configure("evenrow", background=BG_ROW_ALT)
        self.tree.tag_configure("empty",   background=BG_CARD, foreground=TEXT_MUTED)

        self.tree.unbind("<Button-1>")
        self.tree.bind("<Button-1>", self.on_tree_click)

    # ************************************ Pagination ************************************

    def setup_pagination(self, display_keys):
        rows_per_page = self._get_rows_per_page()
        
        if hasattr(self, 'pagination_frame') and self.pagination_frame.winfo_exists():
            self.pagination_frame.destroy()

        self.pagination_frame = ctk.CTkFrame(self.content_frame,
                                             fg_color="transparent")
        self.pagination_frame.grid(row=4, column=0, sticky="ew",
                                   padx=24, pady=(0, 16))

        total       = len(self.current_data)
        total_pages = max(1, -(-total //  rows_per_page))
        start = (self.current_page - 1) * rows_per_page + 1 if total else 0
        end   = min(self.current_page * rows_per_page, total)

        ctk.CTkLabel(
            self.pagination_frame,
            text=f"Showing {start}–{end} of {total} records",
            font=ctk.CTkFont(size=12), text_color=TEXT_MUTED
        ).pack(side="left")

        nav = ctk.CTkFrame(self.pagination_frame, fg_color="transparent")
        nav.pack(side="right")

        def go_to(page):
            self.current_page = page
            self.refresh_table(display_keys)

        ctk.CTkButton(
            nav, text="←", width=36, height=30, corner_radius=6,
            fg_color="#21262d", hover_color="#30363d",
            text_color=TEXT_PRIMARY if self.current_page > 1 else TEXT_MUTED,
            state="normal" if self.current_page > 1 else "disabled",
            command=lambda: go_to(self.current_page - 1)
        ).pack(side="left", padx=2)

        page_range_start = max(1, self.current_page - 2)
        page_range_end   = min(total_pages, self.current_page + 2)

        if page_range_start > 1:
            ctk.CTkButton(nav, text="1", width=36, height=30, corner_radius=6,
                          fg_color="#21262d", hover_color="#30363d",
                          text_color=TEXT_PRIMARY,
                          command=lambda: go_to(1)).pack(side="left", padx=2)
            if page_range_start > 2:
                ctk.CTkLabel(nav, text="…", text_color=TEXT_MUTED,
                             font=ctk.CTkFont(size=12)).pack(side="left", padx=2)

        for p in range(page_range_start, page_range_end + 1):
            is_current = p == self.current_page
            ctk.CTkButton(
                nav, text=str(p), width=36, height=30, corner_radius=6,
                fg_color=ACCENT_CYAN if is_current else "#21262d",
                hover_color="#30363d",
                text_color="#0d1117" if is_current else TEXT_PRIMARY,
                font=ctk.CTkFont(size=12,
                                 weight="bold" if is_current else "normal"),
                command=lambda pg=p: go_to(pg)
            ).pack(side="left", padx=2)

        if page_range_end < total_pages:
            if page_range_end < total_pages - 1:
                ctk.CTkLabel(nav, text="…", text_color=TEXT_MUTED,
                             font=ctk.CTkFont(size=12)).pack(side="left", padx=2)
            ctk.CTkButton(nav, text=str(total_pages), width=36, height=30,
                          corner_radius=6, fg_color="#21262d",
                          hover_color="#30363d", text_color=TEXT_PRIMARY,
                          command=lambda: go_to(total_pages)).pack(side="left", padx=2)

        ctk.CTkButton(
            nav, text="→", width=36, height=30, corner_radius=6,
            fg_color="#21262d", hover_color="#30363d",
            text_color=TEXT_PRIMARY if self.current_page < total_pages else TEXT_MUTED,
            state="normal" if self.current_page < total_pages else "disabled",
            command=lambda: go_to(self.current_page + 1)
        ).pack(side="left", padx=2)
       
    # ************************************ Views ************************************
    def show_students_view(self):
        self._set_active_nav(0)
        self.clear_content()
        self.current_page  = 1
        self.sort_reverse  = False
        search_opts = {"ID": "id", "First Name": "firstname",
                       "Last Name": "lastname", "Program Code": "program_code",
                       "Year": "year", "Gender": "gender", "College": "college"}
        sort_opts    = search_opts.copy()
        display_keys = ["id", "firstname", "lastname", "program_code",
                        "year", "gender", "college"]

        self.current_file_key     = "students"
        self.current_display_keys = display_keys[:]

        self.create_common_controls("Student Records", ACCENT_CYAN,
                                    search_opts, sort_opts, "students",
                                    display_keys, lambda: open_student_form(self))
        self.setup_treeview(("id", "firstname", "lastname",
                             "program_code", "year", "gender", "college"),
                            accent=ACCENT_CYAN)
        self.tree.column("firstname", width=160)
        self.current_data = read_csv("students")
        self.update_idletasks() 
        self.after(150, lambda: self.refresh_table(display_keys))

    def show_programs_view(self):
        self._set_active_nav(1)
        self.clear_content()
        self.current_page  = 1
        self.sort_reverse  = False
        self.current_data  = read_csv("programs")
        self.update_idletasks() 
        search_opts  = {"Code": "code", "Name": "name", "College": "college_code"}
        display_keys = ["code", "name", "college_code"]

        self.current_file_key     = "programs"
        self.current_display_keys = display_keys[:]

        self.create_common_controls("Program Management", ACCENT_PURP,
                                    search_opts, search_opts, "programs",
                                    display_keys, lambda: open_program_form(self))
        self.setup_treeview(("code", "name", "college_code"), accent=ACCENT_PURP)
        self.tree.column("name", width=420, anchor="w")
        self.after(150, lambda: self.refresh_table(display_keys))

    def show_colleges_view(self):
        self._set_active_nav(2)
        self.clear_content()
        self.current_page  = 1
        self.sort_reverse  = False
        self.current_data  = read_csv("colleges")
        search_opts  = {"Code": "code", "Name": "name"}
        display_keys = ["code", "name"]
        self.update_idletasks() 
        self.current_file_key     = "colleges"
        self.current_display_keys = display_keys[:]

        self.create_common_controls("College Management", ACCENT_GREEN,
                                    search_opts, search_opts, "colleges",
                                    display_keys, lambda: open_college_form(self))
        self.setup_treeview(("code", "name"), accent=ACCENT_GREEN)
        self.tree.column("name", width=520, anchor="w")
        self.after(150, lambda: self.refresh_table(display_keys))

    # ************************************ Data Operations ************************************
    def sort_view_data(self, file_key, sort_col, display_keys):
        if not hasattr(self, 'current_data') or not self.current_data:
            self.current_data = read_csv(file_key)

        if sort_col == "college" and file_key == "students":
            programs_list = read_csv("programs")
            prog_to_col   = {p['code']: p.get('college_code', '') for p in programs_list}
            self.current_data.sort(
                key=lambda x: str(prog_to_col.get(x.get('program_code'), "")).lower(),
                reverse=self.sort_reverse
            )
        else:
            self.current_data.sort(
                key=lambda x: str(x.get(sort_col, "")).lower(),
                reverse=self.sort_reverse
            )

        self.current_page = 1
        self.refresh_table(display_keys)

    def search_view_data(self, file_key, search_map, display_keys):
        query            = self.search_entry.get().strip().lower()
        column_to_search = search_map[self.search_var.get()]
        all_data         = read_csv(file_key)

        if not query:
            self.current_data = all_data
        else:
            self.current_data = []
            if column_to_search == "college" and file_key == "students":
                progs   = read_csv("programs")
                mapping = {p['code']: p.get('college_code', '').lower() for p in progs}
                for row in all_data:
                    if query in mapping.get(row.get('program_code', ''), ''):
                        self.current_data.append(row)
            else:
                for row in all_data:
                    cell_value = str(row.get(column_to_search, "")).lower()
                    if cell_value.startswith(query):
                        self.current_data.append(row)

        self.current_page = 1
        self.refresh_table(display_keys)

    def refresh_table(self, display_keys):
        rows_per_page = self._get_rows_per_page()
        try:
            programs_list = read_csv("programs")
            prog_to_col   = {p['code']: p.get('college_code', 'N/A') for p in programs_list}
        except:
            prog_to_col = {}

        for item in self.tree.get_children():
            self.tree.delete(item)
        
        start_idx = (self.current_page - 1) * rows_per_page
        end_idx   = start_idx + rows_per_page
        page_data = self.current_data[start_idx:end_idx]

        if not page_data:
            num_cols   = len(display_keys) + 1
            empty_vals = [""] * num_cols
            empty_vals[num_cols // 2] = "No records found"
            self.tree.insert("", "end", values=empty_vals, tags=("empty",))
        else:
            for i, s in enumerate(page_data):
                row_values = []
                for key in display_keys:
                    if key == "college" and self.current_file_key == "students":
                        val = prog_to_col.get(s.get('program_code'), "—")
                    else:
                        val = s.get(key, "—")
                    if isinstance(val, str) and val.startswith("__deleted__"):
                        val = f"[Deleted] {val[len('__deleted__'):]}"
                    row_values.append(val)
                row_values.append("⋯  Actions")
                tag = "evenrow" if i % 2 == 0 else "oddrow"
                self.tree.insert("", "end", values=row_values, tags=(tag,))

        if hasattr(self, 'count_label'):
            total = len(self.current_data)
            self.count_label.configure(text=f"  {total} record{'s' if total != 1 else ''}  ")

        self.setup_pagination(display_keys)

    # ************************************ Edit / Delete ************************************
    def handle_delete(self, file_key, display_keys):
        rows_per_page=self._get_rows_per_page()
        selected_item = self.tree.selection()
        if not selected_item:
            return
        item_values  = self.tree.item(selected_item)['values']
        target_id    = str(item_values[0])
        all_data     = read_csv(file_key)
        pk           = "id" if file_key == "students" else "code"
        updated_data = [row for row in all_data if str(row.get(pk)) != target_id]
        from modules.database_io import write_csv
        write_csv(file_key, updated_data)
        self.current_data = updated_data
        
        total_pages = max(1, -(-len(updated_data) // rows_per_page))
        if self.current_page > total_pages:
            self.current_page = total_pages
        self.refresh_table(display_keys)
        

    def handle_edit(self, file_key, display_keys):
        selected_item = self.tree.selection()
        if not selected_item:
            return
        item_values = self.tree.item(selected_item)['values']

        pk = "id" if file_key == "students" else "code"
        all_data = read_csv(file_key)
        raw = next((row for row in all_data if str(row.get(pk)) == str(item_values[0])), None)
        if raw is None:
            return
        raw_values = [raw.get(k, "") for k in display_keys] + ["⋯  Actions"]
        
        if file_key == "students":
            open_student_form(self, edit_data=item_values)
        elif file_key == "programs":
            open_program_form(self, edit_data=item_values)
        elif file_key == "colleges":
            open_college_form(self, edit_data=item_values)

    def _open_delete_confirm(self):
        selected_item = self.tree.selection()
        if not selected_item:
            return
        item_values = self.tree.item(selected_item)['values']
        if self.current_file_key == "students":
            from gui.student_forms import handle_delete
            handle_delete(self, item_values)
        elif self.current_file_key == "programs":
            from gui.programs_forms import handle_delete
            handle_delete(self, item_values)
        elif self.current_file_key == "colleges":
            from gui.college_forms import handle_delete
            handle_delete(self, item_values)

    # ************************************ Tree Click & Action Menu ************************************
    def on_tree_click(self, event):
        region = self.tree.identify_region(event.x, event.y)
        if region == "cell":
            column  = self.tree.identify_column(event.x)
            columns = self.tree["columns"]
            action_col_index = f"#{len(columns)}"
            if column == action_col_index:
                item_id = self.tree.identify_row(event.y)
                self.tree.selection_set(item_id)
                self.show_action_menu(item_id)

    def show_action_menu(self, item_id):
        self.close_active_menu()

        columns = self.tree["columns"]
        bbox    = self.tree.bbox(item_id, column=f"#{len(columns)}")
        if not bbox:
            return

        x, y, width, height = bbox
        tree_x = self.tree.winfo_rootx()
        tree_y = self.tree.winfo_rooty()

        menu_x = tree_x + x + (width // 2)
        menu_y = tree_y + y + height

        self.active_menu = tk.Menu(
            self, tearoff=0,
            bg="#1c2230", fg=TEXT_PRIMARY,
            activebackground=ACCENT_CYAN, activeforeground="#0d1117",
            bd=0, relief="flat", font=("Courier", 12)
        )
        self.active_menu.add_command(
            label="  ✎   Edit Record  ",
            command=lambda: self.handle_edit(self.current_file_key,
                                             self.current_display_keys)
        )
        self.active_menu.add_separator()
        self.active_menu.add_command(
            label="  🗑   Delete Record",
            foreground=ACCENT_RED,
            activebackground=ACCENT_RED, activeforeground="white",
            command=lambda: self._open_delete_confirm()
        )
        self.active_menu.post(menu_x, menu_y) 
        
    def _get_rows_per_page(self):
            #Calculate how many rows fit in the current treeview height.
            try:
                tree_height = self.tree.winfo_height()
                row_height  = 46  # must match rowheight in setup_treeview
                rows        = max(1, tree_height // row_height)
                return rows
            except:
                return 10  # fallback
    
if __name__ == "__main__":
    app = MainWindow()
    app.mainloop()