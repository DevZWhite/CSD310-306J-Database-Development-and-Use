"""
Willson Financial — Database Entry Application
Gold Team: Kobe Alexander, Samuel Dirr, Sebastian Siqueiros, Zachary White
Professor Sue Sampson

Wilson_Financial.py
Tkinter GUI for inserting and deleting records in the willson_financial database.
- IDs are auto-incremented (hidden from form)
- Field validation with inline error highlights
- Delete selected rows from the View Table tab
Run:  python Wilson_Financial.py in your cli after setting up your .env with DB credentials.
"""

# ── Imports ─────────────────────────────────────────────────────────────────


import tkinter as tk
from tkinter import ttk, messagebox
import mysql.connector
from mysql.connector import errorcode
from datetime import datetime
from dotenv import dotenv_values
from contextlib import contextmanager
import os
import re
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Load .env ─────────────────────────────────────────────────────────────────
base_dir = os.path.dirname(os.path.abspath(__file__))
secrets  = dotenv_values(os.path.join(base_dir, ".env"))

# adding validation to ensure all required variables are present
# and not empty without it the app may crash later with a less clear 
# error when trying to connect to the database.
try:
    DB_CONFIG = {
        "user":     secrets.get("USER", ""),
        "password": secrets.get("PASSWORD", ""),
        "host":     secrets.get("HOST", ""),
        "database": secrets.get("DATABASE", ""),
    }
    if not all(DB_CONFIG.values()):
        raise ValueError("Missing required .env variables (USER, PASSWORD, HOST, DATABASE)")
except Exception as e:
    print(f"Configuration error: {e}")
    exit(1)

# ── Colour palette ────────────────────────────────────────────────────────────
BG        = "#1C1C1C"
BG2       = "#2A2A2A"
GOLD      = "#C9A227"
GOLD_DARK = "#8B6508"
WHITE     = "#FFFFFF"
GRAY      = "#AAAAAA"
ENTRY_BG  = "#333333"
ENTRY_ERR = "#4A1010"
SUCCESS   = "#2E7D32"
ERROR     = "#C62828"
WARN      = "#E65100"

# ── Validation helpers ────────────────────────────────────���───────────────────
def _is_date(v):
    try:
        datetime.strptime(v, "%Y-%m-%d")
        return True
    except ValueError:
        return False

def _is_time(v):
    try:
        datetime.strptime(v, "%H:%M:%S")
        return True
    except ValueError:
        return False

def _is_decimal(v):
    try:
        return float(v) >= 0
    except ValueError:
        return False

def _is_positive_decimal(v):
    try:
        return float(v) > 0
    except ValueError:
        return False

def _is_email(v):
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v))

def _is_phone(v):
    return bool(re.match(r"^[\d\-\(\)\+\s]{7,20}$", v))

def _is_int(v):
    return v.isdigit()

VALIDATORS = {
    "email":            (_is_email,            "Must be a valid email  (e.g. name@example.com)"),
    "phone":            (_is_phone,            "Must be a valid phone  (e.g. 505-555-0101)"),
    "enrollment_date":  (_is_date,             "Must be a valid date  YYYY-MM-DD"),
    "open_date":        (_is_date,             "Must be a valid date  YYYY-MM-DD"),
    "transaction_date": (_is_date,             "Must be a valid date  YYYY-MM-DD"),
    "review_date":      (_is_date,             "Must be a valid date  YYYY-MM-DD"),
    "appt_date":        (_is_date,             "Must be a valid date  YYYY-MM-DD"),
    "appt_time":        (_is_time,             "Must be a valid time  HH:MM:SS"),
    "balance":          (_is_decimal,          "Must be a number >= 0.00"),
    "amount":           (_is_positive_decimal, "Must be a number > 0.00"),
    "advisor_id":       (_is_int,              "Must be a numeric Advisor ID"),
    "client_id":        (_is_int,              "Must be a numeric Client ID"),
    "account_id":       (_is_int,              "Must be a numeric Account ID"),
}

# ── Table schema ──────────────────────────────────────────────────────────────
# IDs are auto-incremented — not needed to be shown in form
# "required": False = optional field
TABLES = {
    "EMPLOYEE": {
        "pk":     "employee_id",
        "pk_seq": "SELECT COALESCE(MAX(employee_id),0)+1 FROM EMPLOYEE",
        "columns": [
            ("First Name",      "first_name",      "entry", {"required": True}),
            ("Last Name",       "last_name",       "entry", {"required": True}),
            ("Role",            "role",            "entry", {"required": True}),
            ("Employment Type", "employment_type", "combo", {"required": True,  "values": ["Full-Time","Part-Time","Contract"]}),
            ("Email",           "email",           "entry", {"required": True}),
            ("Phone",           "phone",           "entry", {"required": False, "placeholder": "505-555-0000"}),
        ],
        "sql": "INSERT INTO EMPLOYEE (employee_id,first_name,last_name,role,employment_type,email,phone) VALUES (%s,%s,%s,%s,%s,%s,%s)",
        "del": "DELETE FROM EMPLOYEE WHERE employee_id=%s",
    },
    "ADVISOR": {
        "pk":     "advisor_id",
        "pk_seq": "SELECT COALESCE(MAX(advisor_id),0)+1 FROM ADVISOR",
        "columns": [
            ("First Name",  "first_name",  "entry", {"required": True}),
            ("Last Name",   "last_name",   "entry", {"required": True}),
            ("Credentials", "credentials", "combo", {"required": True, "values": ["CFA","CFA,MBA","CFP","MBA","CPA"]}),
            ("Email",       "email",       "entry", {"required": True}),
            ("Phone",       "phone",       "entry", {"required": False, "placeholder": "505-555-0000"}),
        ],
        "sql": "INSERT INTO ADVISOR (advisor_id,first_name,last_name,credentials,email,phone) VALUES (%s,%s,%s,%s,%s,%s)",
        "del": "DELETE FROM ADVISOR WHERE advisor_id=%s",
    },
    "CLIENT": {
        "pk":     "client_id",
        "pk_seq": "SELECT COALESCE(MAX(client_id),0)+1 FROM CLIENT",
        "columns": [
            ("First Name",      "first_name",     "entry", {"required": True}),
            ("Last Name",       "last_name",      "entry", {"required": True}),
            ("Email",           "email",          "entry", {"required": True}),
            ("Phone",           "phone",          "entry", {"required": False, "placeholder": "505-555-0000"}),
            ("Enrollment Date", "enrollment_date","entry", {"required": True,  "placeholder": "YYYY-MM-DD"}),
            ("Advisor ID",      "advisor_id",     "entry", {"required": True}),
        ],
        "sql": "INSERT INTO CLIENT (client_id,first_name,last_name,email,phone,enrollment_date,advisor_id) VALUES (%s,%s,%s,%s,%s,%s,%s)",
        "del": "DELETE FROM CLIENT WHERE client_id=%s",
    },
    "ACCOUNT": {
        "pk":     "account_id",
        "pk_seq": "SELECT COALESCE(MAX(account_id),0)+1 FROM ACCOUNT",
        "columns": [
            ("Client ID",    "client_id",    "entry", {"required": True}),
            ("Account Type", "account_type", "combo", {"required": True, "values": ["Individual Brokerage","IRA","Retirement","Savings","Checking"]}),
            ("Balance",      "balance",      "entry", {"required": True, "placeholder": "0.00"}),
            ("Currency",     "currency",     "combo", {"required": True, "values": ["USD"]}),
            ("Open Date",    "open_date",    "entry", {"required": True, "placeholder": "YYYY-MM-DD"}),
        ],
        "sql": "INSERT INTO ACCOUNT (account_id,client_id,account_type,balance,currency,open_date) VALUES (%s,%s,%s,%s,%s,%s)",
        "del": "DELETE FROM ACCOUNT WHERE account_id=%s",
    },
    "TRANSACTION": {
        "pk":     "transaction_id",
        "pk_seq": "SELECT COALESCE(MAX(transaction_id),0)+1 FROM `TRANSACTION`",
        "columns": [
            ("Account ID",       "account_id",       "entry", {"required": True}),
            ("Transaction Date", "transaction_date", "entry", {"required": True,  "placeholder": "YYYY-MM-DD"}),
            ("Type",             "transaction_type", "combo", {"required": True,  "values": ["Deposit","Withdrawal"]}),
            ("Amount",           "amount",           "entry", {"required": True,  "placeholder": "0.00"}),
            ("Description",      "description",      "entry", {"required": False}),
        ],
        "sql": "INSERT INTO `TRANSACTION` (transaction_id,account_id,transaction_date,transaction_type,amount,description) VALUES (%s,%s,%s,%s,%s,%s)",
        "del": "DELETE FROM `TRANSACTION` WHERE transaction_id=%s",
    },
    "APPOINTMENT": {
        "pk":     "appointment_id",
        "pk_seq": "SELECT COALESCE(MAX(appointment_id),0)+1 FROM APPOINTMENT",
        "columns": [
            ("Client ID",  "client_id",  "entry", {"required": True}),
            ("Advisor ID", "advisor_id", "entry", {"required": True}),
            ("Date",       "appt_date",  "entry", {"required": True,  "placeholder": "YYYY-MM-DD"}),
            ("Time",       "appt_time",  "entry", {"required": True,  "placeholder": "HH:MM:SS"}),
            ("Notes",      "notes",      "entry", {"required": False}),
        ],
        "sql": "INSERT INTO APPOINTMENT (appointment_id,client_id,advisor_id,appt_date,appt_time,notes) VALUES (%s,%s,%s,%s,%s,%s)",
        "del": "DELETE FROM APPOINTMENT WHERE appointment_id=%s",
    },
    "COMPLIANCE_RECORD": {
        "pk":     "compliance_id",
        "pk_seq": "SELECT COALESCE(MAX(compliance_id),0)+1 FROM COMPLIANCE_RECORD",
        "columns": [
            ("Review Date", "review_date", "entry", {"required": True, "placeholder": "YYYY-MM-DD"}),
            ("Review Type", "review_type", "combo", {"required": True, "values": ["Account Review", "Risk Assessment", "Transaction Audit", "Policy Review", "Client Documentation", "SEC Compliance Review"]}),
            ("Outcome",     "outcome",     "combo", {"required": True, "values": ["Passed", "Needs Follow-Up", "Failed"]}),
            ("Reviewed By", "reviewed_by", "entry", {"required": True}),
        ],
        "sql": "INSERT INTO COMPLIANCE_RECORD (compliance_id,review_date,review_type,outcome,reviewed_by) VALUES (%s,%s,%s,%s,%s)",
        "del": "DELETE FROM COMPLIANCE_RECORD WHERE compliance_id=%s",
    },
}


# ── Database helpers ──────────────────────────────────────────────────────────
def get_connection():
    return mysql.connector.connect(**DB_CONFIG)

def next_id(table_key):
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute(TABLES[table_key]["pk_seq"])
    val = cur.fetchone()[0]
    cur.close(); conn.close()
    return int(val)

def insert_record(table_key, values):
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute(TABLES[table_key]["sql"], values)
    conn.commit()
    cur.close(); conn.close()

def delete_record(table_key, pk_value):
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute(TABLES[table_key]["del"], (pk_value,))
    affected = cur.rowcount
    conn.commit()
    cur.close(); conn.close()
    return affected

def fetch_table(table_key):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM `{table_key}`")  # Always use backticks
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    cur.close()
    conn.close()
    return cols, rows


# ── Application ───────────────────────────────────────────────────────────────
class WillsonApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Willson Financial DEA - Developed by Gold Team")
        self.geometry("1160x740")
        self.minsize(960, 620)
        self.configure(bg=BG)
        self.resizable(True, True)

        self.current_table = tk.StringVar(value="CLIENT")
        self.field_vars    = {}
        self.field_widgets = {}
        self.error_labels  = {}
        self.next_id_label = None

        self._apply_styles()
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
        self._build_ui()
        self._switch_table("CLIENT")

    # ── Styles ────────────────────────────────────────────────────────────────
    def _apply_styles(self):
        self.option_add("*TCombobox*Listbox.background",       ENTRY_BG)
        self.option_add("*TCombobox*Listbox.foreground",       WHITE)
        self.option_add("*TCombobox*Listbox.selectBackground", GOLD_DARK)
        self.option_add("*TCombobox*Listbox.selectForeground", WHITE)
        self.option_add("*TCombobox*Listbox.font",             ("Arial", 10))

        s = ttk.Style()
        s.theme_use("clam")
        s.configure("Dark.TCombobox",
                    fieldbackground=ENTRY_BG, background=ENTRY_BG,
                    foreground=WHITE, selectbackground=GOLD_DARK,
                    selectforeground=WHITE, bordercolor=GOLD_DARK, arrowcolor=GOLD)
        s.map("Dark.TCombobox",
              fieldbackground =[("readonly", ENTRY_BG)],
              foreground      =[("readonly", WHITE)],
              selectbackground=[("readonly", GOLD_DARK)],
              background      =[("readonly", ENTRY_BG)])
        s.configure("TNotebook",     background=BG,  borderwidth=0)
        s.configure("TNotebook.Tab", background=BG2, foreground=GRAY,
                    padding=[16, 8], font=("Arial", 10, "bold"))
        s.map("TNotebook.Tab",
              background=[("selected", GOLD_DARK)],
              foreground=[("selected", WHITE)])
        s.configure("Treeview", background=BG2, foreground=WHITE,
                    fieldbackground=BG2, rowheight=28, font=("Arial", 10))
        s.configure("Treeview.Heading", background=GOLD_DARK, foreground=WHITE,
                    font=("Arial", 10, "bold"))
        s.map("Treeview", background=[("selected", GOLD_DARK)])
        s.configure("TScrollbar", background=BG2, troughcolor=BG)

    def _create_button(self, parent, text, bg, fg, command):
        """Helper to create consistently styled buttons."""
        return tk.Button(
            parent, text=text, bg=bg, fg=fg, font=("Arial", 10, "bold"),
            relief="flat", cursor="hand2", padx=14, pady=8,
            activebackground=GOLD, activeforeground=WHITE, command=command
        )

    def _create_placeholder_handlers(self, widget, placeholder):
        """Create focus handlers for placeholder text in entry fields."""
        def on_focus_in(event):
            if widget.get() == placeholder:
                widget.delete(0, "end")
            widget.config(fg=WHITE, bg=ENTRY_BG)

        def on_focus_out(event):
            if not widget.get():
                widget.insert(0, placeholder)
                widget.config(fg="#666666")

        return on_focus_in, on_focus_out

    # ── Main UI ───────────────────────────────────────────────────────────────
    def _build_ui(self):
        topbar = tk.Frame(self, bg=GOLD_DARK, height=60)
        topbar.pack(fill="x", side="top")
        topbar.pack_propagate(False)
        tk.Label(topbar, text="Willson",   bg=GOLD_DARK, fg=GOLD,
                 font=("Georgia", 18, "bold")).pack(side="left", padx=(20,2), pady=10)
        tk.Label(topbar, text="Financial", bg=GOLD_DARK, fg=WHITE,
                 font=("Georgia", 18, "bold")).pack(side="left", pady=10)
        tk.Label(topbar, text="Database Entry Application",
                 bg=GOLD_DARK, fg="#CCCCCC",
                 font=("Arial", 11)).pack(side="left", padx=20, pady=10)

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True)

        # Sidebar
        sidebar = tk.Frame(body, bg=BG2, width=188)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        tk.Label(sidebar, text="SELECT TABLE", bg=BG2, fg=GOLD,
                 font=("Arial", 9, "bold")).pack(pady=(18, 8), padx=10)

        self.tab_buttons = {}
        for tname in TABLES:
            disp = tname.replace("_", "\n") if "_" in tname else tname
            btn  = tk.Button(sidebar, text=disp,
                             bg=BG2, fg=GRAY, font=("Courier New", 10, "bold"),
                             relief="flat", cursor="hand2",
                             pady=10, padx=8, wraplength=165,
                             activebackground=GOLD_DARK, activeforeground=WHITE,
                             command=lambda t=tname: self._switch_table(t))
            btn.pack(fill="x", padx=8, pady=3)
            self.tab_buttons[tname] = btn

        right = tk.Frame(body, bg=BG)
        right.pack(side="left", fill="both", expand=True)

        self.notebook = ttk.Notebook(right)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_change)

        self.insert_tab = tk.Frame(self.notebook, bg=BG)
        self.notebook.add(self.insert_tab, text="  ➕  Insert Record  ")

        self.view_tab = tk.Frame(self.notebook, bg=BG)
        self.notebook.add(self.view_tab, text="  📋  View / Delete  ")

        self._build_view_tab()

    # ── Insert Tab ────────────────────────────────────────────────────────────
    def _build_insert_tab(self, table_key):
        for w in self.insert_tab.winfo_children():
            w.destroy()
        self.field_vars   = {}
        self.field_widgets= {}
        self.error_labels = {}

        schema = TABLES[table_key]

        hdr = tk.Frame(self.insert_tab, bg=BG)
        hdr.pack(fill="x", padx=20, pady=(16, 2))
        tk.Label(hdr, text="Insert into  ", bg=BG, fg=GRAY,
                 font=("Arial", 13)).pack(side="left")
        tk.Label(hdr, text=table_key, bg=BG, fg=GOLD,
                 font=("Courier New", 13, "bold")).pack(side="left")

        try:
            nid      = next_id(table_key)
            id_text  = f"Auto ID: {nid}"
        except Exception as e:
            logger.error(f"Database error: {e}")
            id_text  = "Auto ID: —"
        self.next_id_label = tk.Label(hdr, text=f"  [ {id_text} ]",
                                      bg=BG, fg=GOLD_DARK,
                                      font=("Courier New", 11, "italic"))
        self.next_id_label.pack(side="left", padx=10)

        tk.Frame(self.insert_tab, bg=GOLD_DARK, height=2).pack(fill="x", padx=20, pady=(4, 10))

        # Scrollable canvas
        canvas = tk.Canvas(self.insert_tab, bg=BG, highlightthickness=0)
        scroll = ttk.Scrollbar(self.insert_tab, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True, padx=(20, 0))

        form    = tk.Frame(canvas, bg=BG)
        form_id = canvas.create_window((0, 0), window=form, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(form_id, width=e.width))
        form.bind("<Configure>",   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind_all("<MouseWheel>",
                        lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        for label, col, wtype, opts in schema["columns"]:
            required = opts.get("required", True)
            ph       = opts.get("placeholder", "")

            row_f = tk.Frame(form, bg=BG)
            row_f.pack(fill="x", pady=(6, 0))

            lbl_text = label if required else f"{label}  (optional)"
            tk.Label(row_f, text=lbl_text, bg=BG,
                     fg=GRAY if required else "#777777",
                     font=("Arial", 10), width=22, anchor="w").pack(side="left")

            var = tk.StringVar()
            self.field_vars[col] = var

            if wtype == "combo":
                w = ttk.Combobox(row_f, textvariable=var,
                                 values=opts.get("values", []),
                                 state="readonly", width=34,
                                 font=("Arial", 10), style="Dark.TCombobox")

                def _fix(event, widget=w):
                    try:
                        widget.tk.eval(f"""
                            set pd [ttk::combobox::PopdownWindow {widget}]
                            $pd.f.l configure \
                                -background {ENTRY_BG} -foreground {WHITE} \
                                -selectbackground {GOLD_DARK} -selectforeground {WHITE}
                        """)
                    except Exception:
                        pass
                w.bind("<ButtonPress>", _fix)
                if opts.get("values"):
                    w.current(0)

            else:
                w = tk.Entry(row_f, textvariable=var, bg=ENTRY_BG, fg=WHITE,
                             insertbackground=GOLD, font=("Arial", 10),
                             width=36, relief="flat", bd=4)
                if ph:
                    w.insert(0, ph)
                    w.config(fg="#666666")

                    on_focus_in, on_focus_out = self._create_placeholder_handlers(w, ph)
                    w.bind("<FocusIn>",  on_focus_in)
                    w.bind("<FocusOut>", on_focus_out)
                else:
                    w.bind("<FocusIn>",  lambda e, widget=w: widget.config(bg=ENTRY_BG))

            w.pack(side="left", ipady=4)
            self.field_widgets[col] = w

            # Inline error label
            err = tk.Label(row_f, text="", bg=BG, fg=ERROR,
                           font=("Arial", 9, "italic"))
            err.pack(side="left", padx=(10, 0))
            self.error_labels[col] = err

            tk.Frame(form, bg="#3A3A3A", height=1).pack(fill="x", pady=(4, 0))

        # Buttons
        btn_row = tk.Frame(form, bg=BG)
        btn_row.pack(fill="x", pady=20)
        self._create_button(btn_row, "  ✓  Insert Record", GOLD_DARK, WHITE, self._submit).pack(side="left", padx=(0, 10))
        self._create_button(btn_row, "  ✕  Clear Form", BG2, GRAY, self._clear).pack(side="left")

        self.status_var = tk.StringVar()
        self.status_lbl = tk.Label(form, textvariable=self.status_var,
                                   bg=BG, fg=SUCCESS, font=("Arial", 10, "bold"))
        self.status_lbl.pack(anchor="w", pady=4)

    # ── View / Delete Tab ─────────────────────────────────────────────────────
    def _build_view_tab(self):
        for w in self.view_tab.winfo_children():
            w.destroy()

        toolbar = tk.Frame(self.view_tab, bg=BG2, height=46)
        toolbar.pack(fill="x")
        toolbar.pack_propagate(False)

        self._create_button(toolbar, "  ⟳  Refresh", GOLD_DARK, WHITE, self._load_view).pack(side="left", padx=10, pady=8)
        self._create_button(toolbar, "  🗑  Delete Selected", ERROR, WHITE, self._delete_selected).pack(side="left", pady=8)

        self.del_status_var = tk.StringVar()
        tk.Label(toolbar, textvariable=self.del_status_var,
                 bg=BG2, fg=WARN, font=("Arial", 9, "bold")).pack(side="left", padx=14)

        frame = tk.Frame(self.view_tab, bg=BG)
        frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.tree = ttk.Treeview(frame, show="headings", selectmode="extended")
        vsb = ttk.Scrollbar(frame, orient="vertical",   command=self.tree.yview)
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        hsb.pack(side="bottom", fill="x")
        vsb.pack(side="right",  fill="y")
        self.tree.pack(side="left", fill="both", expand=True)

        # Right-click context menu
        self.ctx = tk.Menu(self, tearoff=0, bg=BG2, fg=WHITE,
                           activebackground=ERROR, activeforeground=WHITE)
        self.ctx.add_command(label="🗑  Delete Selected Row(s)",
                             command=self._delete_selected)
        self.tree.bind("<Button-3>", self._show_ctx)

    # ── Logic ─────────────────────────────────────────────────────────────────
    def _switch_table(self, table_key):
        self.current_table.set(table_key)
        for t, btn in self.tab_buttons.items():
            btn.config(bg=GOLD_DARK if t == table_key else BG2,
                       fg=WHITE     if t == table_key else GRAY)
        self._build_insert_tab(table_key)
        self._load_view()

    def _on_tab_change(self, event):
        if self.notebook.index(self.notebook.select()) == 1:
            self._load_view()

    def _load_view(self):
        table_key = self.current_table.get()
        try:
            cols, rows = fetch_table(table_key)
            self.tree["columns"] = cols
            for col in cols:
                self.tree.heading(col, text=col)
                self.tree.column(col, width=130, anchor="w", minwidth=80)
            self.tree.delete(*self.tree.get_children())
            for i, row in enumerate(rows):
                tag = "even" if i % 2 == 0 else "odd"
                self.tree.insert("", "end", values=[str(v) for v in row], tags=(tag,))
            self.tree.tag_configure("even", background=BG2)
            self.tree.tag_configure("odd",  background="#222222")
            self.del_status_var.set("")
        except Exception as e:
            messagebox.showerror("Connection Error", str(e))

    def _validate(self):
        """Validate all fields. Returns (ok, values_list)."""
        table_key = self.current_table.get()
        schema    = TABLES[table_key]
        values    = []
        ok        = True

# Clear previous errors
# Combobox doesn't support bg — skip it please keep this logic 
# as without it the entire database fails to insert if you select a 
# combo box field with an error and then try to fix it by selecting a 
# value from the combo box instead of typing in the entry field. 
# The error is that the code tries to set the background color of the 
# combo box which raises a TclError since ttk Combobox 
# does not support changing background color. 
# By catching this specific exception and passing, 
# we allow the validation to continue without crashing the app, 
# while still highlighting errors in entry fields where possible.
        for col in self.error_labels:
                self.error_labels[col].config(text="")
        for col, w in self.field_widgets.items():
            try:
                w.config(bg=ENTRY_BG)
            except tk.TclError:
                pass
        for label, col, wtype, opts in schema["columns"]:
            required = opts.get("required", True)
            ph       = opts.get("placeholder", "")
            raw      = self.field_vars[col].get().strip()
            if raw == ph:
                raw = ""

            # Required check
            if required and not raw:
                self._field_error(col, wtype, f"Required — please enter {label}")
                ok = False
                continue

            # Optional and empty — pass None
            if not required and not raw:
                values.append(None)
                continue

            # Format checks
            if col in VALIDATORS:
                fn, msg = VALIDATORS[col]
                if not fn(raw):
                    self._field_error(col, wtype, msg)
                    ok = False
                    continue

            values.append(raw)

        return ok, values

    def _field_error(self, col, wtype, msg):
        if col in self.field_widgets and isinstance(self.field_widgets[col], tk.Entry):
            self.field_widgets[col].config(bg=ENTRY_ERR)
        if col in self.error_labels:
            self.error_labels[col].config(text=f"⚠  {msg}")

    def _submit(self):
        table_key    = self.current_table.get()
        ok, values   = self._validate()

        if not ok:
            self.status_var.set("✕  Fix the highlighted fields before inserting.")
            self.status_lbl.config(fg=ERROR)
            return

        try:
            new_id = next_id(table_key)
        except Exception as e:
            self.status_var.set(f"✕  Could not generate ID: {e}")
            self.status_lbl.config(fg=ERROR)
            return

        try:
            insert_record(table_key, [new_id] + values)
            self.status_var.set(
                f"✓  Record inserted into {table_key}  (ID: {new_id})")
            self.status_lbl.config(fg=SUCCESS)
            self._clear()
            self._load_view()
            self._bump_id(table_key)
        except mysql.connector.Error as err:
            msgs = {
                1062: "Duplicate entry — that record already exists.",
                1452: "Foreign key error — the referenced ID does not exist.",
                1406: "Data too long for one of the fields.",
            }
            self.status_var.set(f"✕  {msgs.get(err.errno, str(err))}")
            self.status_lbl.config(fg=ERROR)

    def _bump_id(self, table_key):
        if self.next_id_label:
            try:
                self.next_id_label.config(
                    text=f"  [ Auto ID: {next_id(table_key)} ]")
            except Exception:
                pass

    def _clear(self):
        table_key = self.current_table.get()
        for label, col, wtype, opts in TABLES[table_key]["columns"]:
            ph = opts.get("placeholder", "")
            w  = self.field_widgets[col]
            if isinstance(w, tk.Entry):
                w.delete(0, "end")
                w.config(bg=ENTRY_BG)
                if ph:
                    w.insert(0, ph)
                    w.config(fg="#666666")
                else:
                    w.config(fg=WHITE)
            else:
                self.field_vars[col].set(opts["values"][0] if opts.get("values") else "")
            if col in self.error_labels:
                self.error_labels[col].config(text="")
        self.status_var.set("")

    def _delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            self.del_status_var.set("⚠  Select a row first.")
            return

        table_key = self.current_table.get()
        pk_col    = TABLES[table_key]["pk"]
        cols, _   = fetch_table(table_key)

        try:
            pk_idx = cols.index(pk_col)
        except ValueError:
            messagebox.showerror("Error", f"Cannot find primary key column '{pk_col}'.")
            return

        count   = len(selected)
        noun    = "record" if count == 1 else "records"
        confirm = messagebox.askyesno(
            "Confirm Delete",
            f"Delete {count} selected {noun} from {table_key}?\n\nThis cannot be undone.",
            icon="warning")
        if not confirm:
            return

        deleted, errors = 0, []
        for item in selected:
            pk_val = self.tree.item(item, "values")[pk_idx]
            try:
                if delete_record(table_key, pk_val):
                    deleted += 1
            except mysql.connector.Error as err:
                if err.errno == 1451:
                    errors.append(f"ID {pk_val}: referenced by another table.")
                else:
                    errors.append(f"ID {pk_val}: {err}")

        self._load_view()
        self._bump_id(table_key)

        if errors:
            messagebox.showerror("Delete Errors",
                f"Deleted {deleted} record(s).\n\nCould not delete:\n" + "\n".join(errors))
        else:
            self.del_status_var.set(
                f"✓  Deleted {deleted} {('record' if deleted==1 else 'records')} from {table_key}.")

    def _show_ctx(self, event):
        row = self.tree.identify_row(event.y)
        if row:
            if row not in self.tree.selection():
                self.tree.selection_set(row)
            self.ctx.post(event.x_root, event.y_root)

    def _on_closing(self):
        """Handle application cleanup when window is closed."""
        self.destroy()


if __name__ == "__main__":
    app = WillsonApp()
    app.mainloop()

# End of file

"""
This application provides a user-friendly interface for managing the Willson Financial database. 
It allows users to insert new records into the EMPLOYEE, ADVISOR, CLIENT, ACCOUNT, TRANSACTION, APPOINTMENT, and COMPLIANCE_RECORD tables, 
as well as view and delete existing records. The application includes robust validation for input fields, clear error messages, 
and a consistent dark-themed design for an enhanced user experience.
it also serves as a final representation of my ability to integrate Python with MySQL, implement a GUI using Tkinter, 
and apply best practices in software development such as error handling, logging, and user experience design.
please leave any feedback on the code and the application as a whole, as I am eager to learn and improve my skills further.
thanks for the opportunity to work on this project and for your guidance throughout the course! - Zachary White
"""