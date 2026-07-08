import os
import sqlite3
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import messagebox, ttk
import customtkinter as ctk

# Matplotlib setup for embedding in Tkinter
import matplotlib
matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

# Import our AI and weather utilities
from app.ai_predictor import predict_customer_refills, forecast_water_demand
from app.weather_service import get_weather_forecast

# CustomTkinter theme setup
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# Path to the shared SQLite database
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'water_station.db')

class WaterStationApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("AquaFlow - Mineral Water Station POS & AI Console")
        self.geometry("1100x680")
        self.minsize(1000, 600)
        self.configure(fg_color="#090d16")
        
        # Verify database connection
        if not os.path.exists(DB_PATH):
            messagebox.showerror(
                "Database Error", 
                f"Database file not found at:\n{DB_PATH}\n\nPlease run the Flask web app or seed.py first."
            )
            self.destroy()
            return
            
        self.db_path = DB_PATH
        
        # Setup modern sidebar layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Sidebar Frame
        self.sidebar_frame = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color="#0d1321")
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(6, weight=1)
        
        # Brand title
        self.brand_label = ctk.CTkLabel(
            self.sidebar_frame, 
            text="AquaFlow POS", 
            font=ctk.CTkFont(size=20, weight="bold")
        )
        self.brand_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        
        self.loc_label = ctk.CTkLabel(
            self.sidebar_frame, 
            text="Bancal, Meycauayan", 
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        self.loc_label.grid(row=1, column=0, padx=20, pady=(0, 20))
        
        # Sidebar navigation buttons
        self.btn_dashboard = ctk.CTkButton(
            self.sidebar_frame, text="Dashboard", anchor="w", command=self.show_dashboard
        )
        self.btn_dashboard.grid(row=2, column=0, padx=20, pady=5, sticky="ew")
        
        self.btn_pos = ctk.CTkButton(
            self.sidebar_frame, text="POS Sales Terminal", anchor="w", command=self.show_pos
        )
        self.btn_pos.grid(row=3, column=0, padx=20, pady=5, sticky="ew")
        
        self.btn_monitor = ctk.CTkButton(
            self.sidebar_frame, text="Web Order Monitor", anchor="w", command=self.show_monitor
        )
        self.btn_monitor.grid(row=4, column=0, padx=20, pady=5, sticky="ew")
        
        self.btn_history = ctk.CTkButton(
            self.sidebar_frame, text="Transaction History", anchor="w", command=self.show_history
        )
        self.btn_history.grid(row=5, column=0, padx=20, pady=5, sticky="ew")
        
        self.btn_ai = ctk.CTkButton(
            self.sidebar_frame, text="AI Predictions", anchor="w", command=self.show_ai
        )
        self.btn_ai.grid(row=6, column=0, padx=20, pady=5, sticky="ew")
        
        # App Version Label
        self.version_label = ctk.CTkLabel(
            self.sidebar_frame, text="v1.0.0 (Bulacan Edition)", font=ctk.CTkFont(size=10), text_color="gray"
        )
        self.version_label.grid(row=7, column=0, pady=15)
        
        # Main Container Frame
        self.main_container = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_container.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(0, weight=1)
        
        # Initialize views
        self.views = {}
        self.create_dashboard_view()
        self.create_pos_view()
        self.create_monitor_view()
        self.create_history_view()
        self.create_ai_view()
        
        # Show Dashboard initially
        self.show_dashboard()
        
    def select_sidebar_button(self, active_button):
        # Deselect all buttons
        buttons = [self.btn_dashboard, self.btn_pos, self.btn_monitor, self.btn_history, self.btn_ai]
        for btn in buttons:
            if btn == active_button:
                btn.configure(fg_color="#3b82f6", text_color="white")
            else:
                btn.configure(fg_color="transparent", text_color="#cbd5e1")
                
    def get_db_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # ==========================================
    # VIEW NAVIGATION
    # ==========================================
    def show_view(self, name):
        for view_name, view_frame in self.views.items():
            if view_name == name:
                view_frame.grid(row=0, column=0, sticky="nsew")
            else:
                view_frame.grid_forget()
                
    def show_dashboard(self):
        self.select_sidebar_button(self.btn_dashboard)
        self.refresh_dashboard_data()
        self.show_view("dashboard")
        
    def show_pos(self):
        self.select_sidebar_button(self.btn_pos)
        self.refresh_pos_customers()
        self.show_view("pos")
        
    def show_monitor(self):
        self.select_sidebar_button(self.btn_monitor)
        self.refresh_monitor_data()
        self.show_view("monitor")
        
    def show_history(self):
        self.select_sidebar_button(self.btn_history)
        self.refresh_history_data()
        self.show_view("history")
        
    def show_ai(self):
        self.select_sidebar_button(self.btn_ai)
        self.refresh_ai_data()
        self.show_view("ai")

    # ==========================================
    # 1. DASHBOARD VIEW
    # ==========================================
    def create_dashboard_view(self):
        view = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.views["dashboard"] = view
        
        # Header
        header = ctk.CTkLabel(view, text="Operator Command Dashboard", font=ctk.CTkFont(size=22, weight="bold"))
        header.pack(anchor="w", pady=(0, 20))
        
        # KPI Container
        kpi_frame = ctk.CTkFrame(view, fg_color="transparent")
        kpi_frame.pack(fill="x", pady=(0, 20))
        
        # KPI Card 1: Today's Revenue
        self.kpi_rev = ctk.CTkFrame(kpi_frame, width=220, height=100, fg_color="#131c2e", border_width=1, border_color="#1e293b")
        self.kpi_rev.pack(side="left", expand=True, fill="both", padx=5)
        self.kpi_rev_lbl = ctk.CTkLabel(self.kpi_rev, text="TODAY'S REVENUE", font=ctk.CTkFont(size=10, weight="bold"), text_color="gray")
        self.kpi_rev_lbl.pack(anchor="w", padx=15, pady=(15, 0))
        self.kpi_rev_val = ctk.CTkLabel(self.kpi_rev, text="₱0.00", font=ctk.CTkFont(size=24, weight="bold"), text_color="#10b981")
        self.kpi_rev_val.pack(anchor="w", padx=15, pady=(5, 15))
        
        # KPI Card 2: Pending Orders
        self.kpi_orders = ctk.CTkFrame(kpi_frame, width=220, height=100, fg_color="#131c2e", border_width=1, border_color="#1e293b")
        self.kpi_orders.pack(side="left", expand=True, fill="both", padx=5)
        self.kpi_orders_lbl = ctk.CTkLabel(self.kpi_orders, text="PENDING WEB ORDERS", font=ctk.CTkFont(size=10, weight="bold"), text_color="gray")
        self.kpi_orders_lbl.pack(anchor="w", padx=15, pady=(15, 0))
        self.kpi_orders_val = ctk.CTkLabel(self.kpi_orders, text="0", font=ctk.CTkFont(size=24, weight="bold"), text_color="#3b82f6")
        self.kpi_orders_val.pack(anchor="w", padx=15, pady=(5, 15))
        
        # KPI Card 3: Stock Status
        self.kpi_stock = ctk.CTkFrame(kpi_frame, width=220, height=100, fg_color="#131c2e", border_width=1, border_color="#1e293b")
        self.kpi_stock.pack(side="left", expand=True, fill="both", padx=5)
        self.kpi_stock_lbl = ctk.CTkLabel(self.kpi_stock, text="LOW INVENTORY ALERTS", font=ctk.CTkFont(size=10, weight="bold"), text_color="gray")
        self.kpi_stock_lbl.pack(anchor="w", padx=15, pady=(15, 0))
        self.kpi_stock_val = ctk.CTkLabel(self.kpi_stock, text="OK", font=ctk.CTkFont(size=24, weight="bold"), text_color="#ef4444")
        self.kpi_stock_val.pack(anchor="w", padx=15, pady=(5, 15))
        
        # Split pane (Weather & Recent orders)
        split_frame = ctk.CTkFrame(view, fg_color="transparent")
        split_frame.pack(fill="both", expand=True)
        
        # Weather Display Box (Left)
        weather_box = ctk.CTkFrame(split_frame, width=300, fg_color="#131c2e", border_width=1, border_color="#1e293b")
        weather_box.pack(side="left", fill="both", expand=False, padx=(0, 10))
        
        w_lbl = ctk.CTkLabel(weather_box, text="LIVE WEATHER (MEYCAUAYAN)", font=ctk.CTkFont(size=11, weight="bold"), text_color="gray")
        w_lbl.pack(anchor="w", padx=15, pady=(15, 10))
        
        self.dash_weather_temp = ctk.CTkLabel(weather_box, text="--°C", font=ctk.CTkFont(size=36, weight="bold"))
        self.dash_weather_temp.pack(anchor="w", padx=15, pady=5)
        
        self.dash_weather_desc = ctk.CTkLabel(weather_box, text="Fetching...", font=ctk.CTkFont(size=14, weight="bold"), text_color="gray")
        self.dash_weather_desc.pack(anchor="w", padx=15, pady=5)
        
        self.dash_weather_tips = ctk.CTkLabel(
            weather_box, 
            text="AI is processing weather features...", 
            font=ctk.CTkFont(size=10), 
            text_color="gray",
            wraplength=200,
            justify="left"
        )
        self.dash_weather_tips.pack(anchor="w", padx=15, pady=(10, 15))
        
        # Stock Summary details inside weather box
        stock_header = ctk.CTkLabel(weather_box, text="CURRENT STOCK LEVELS", font=ctk.CTkFont(size=11, weight="bold"), text_color="gray")
        stock_header.pack(anchor="w", padx=15, pady=(15, 5))
        
        self.dash_stock_round_lbl = ctk.CTkLabel(weather_box, text="Round Blue: --/500 units", font=ctk.CTkFont(size=11, weight="bold"))
        self.dash_stock_round_lbl.pack(anchor="w", padx=15, pady=(5, 2))
        
        self.dash_stock_round_progress = ctk.CTkProgressBar(weather_box, width=260, height=8)
        self.dash_stock_round_progress.pack(anchor="w", padx=15, pady=(0, 10))
        
        self.dash_stock_slim_lbl = ctk.CTkLabel(weather_box, text="Slim Blue: --/300 units", font=ctk.CTkFont(size=11, weight="bold"))
        self.dash_stock_slim_lbl.pack(anchor="w", padx=15, pady=(5, 2))
        
        self.dash_stock_slim_progress = ctk.CTkProgressBar(weather_box, width=260, height=8)
        self.dash_stock_slim_progress.pack(anchor="w", padx=15, pady=(0, 15))
        
        # Recent Completed Sales Table (Right)
        sales_box = ctk.CTkFrame(split_frame, fg_color="#131c2e", border_width=1, border_color="#1e293b")
        sales_box.pack(side="right", fill="both", expand=True, padx=(10, 0))
        
        sales_lbl = ctk.CTkLabel(sales_box, text="RECENT REGISTERED TRANSACTIONS", font=ctk.CTkFont(size=11, weight="bold"), text_color="gray")
        sales_lbl.pack(anchor="w", padx=15, pady=(15, 10))
        
        # Tkinter Treeview for styling
        self.dash_tree = self.create_custom_tree(
            sales_box, 
            ["Order #", "Recipient", "Total Cost", "Order Status", "Date"],
            [60, 150, 100, 100, 150]
        )
        self.dash_tree.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        
    def refresh_dashboard_data(self):
        # 1. Weather
        w_data = get_weather_forecast()
        self.dash_weather_temp.configure(text=f"{w_data['current_temp']}°C")
        self.dash_weather_desc.configure(text=w_data['current_condition'])
        
        if w_data['current_temp'] >= 32.5:
            self.dash_weather_tips.configure(
                text="⚠️ Heatwave condition: AI predicts a spike in drinking water demand. Keep inventory topped up!",
                text_color="#ffa726"
            )
        else:
            self.dash_weather_tips.configure(
                text="ℹ️ Normal temperatures. Customer refills are proceeding on standard schedules.",
                text_color="gray"
            )
            
        # 2. Database statistics
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        # Today's Revenue (completed/confirmed orders date is today)
        today_str = datetime.now().strftime('%Y-%m-%d')
        cursor.execute(
            "SELECT SUM(total_amount) FROM orders WHERE status IN ('completed', 'confirmed') AND DATE(order_date) = DATE(?)",
            (today_str,)
        )
        todays_rev = cursor.fetchone()[0] or 0.0
        self.kpi_rev_val.configure(text=f"₱{todays_rev:,.2f}")
        
        # Pending Orders count
        cursor.execute("SELECT COUNT(*) FROM orders WHERE status = 'pending'")
        pending_count = cursor.fetchone()[0]
        self.kpi_orders_val.configure(text=str(pending_count))
        
        # Inventory levels
        cursor.execute("SELECT id, name, stock_quantity FROM products")
        products = cursor.fetchall()
        low_stock = 0
        for p in products:
            qty = p['stock_quantity']
            p_id = p['id']
            if qty < 50:
                low_stock += 1
            if 'Round' in p['name']:
                self.dash_stock_round_lbl.configure(text=f"Round Blue: {qty}/500 units")
                prog = max(0.0, min(float(qty) / 500.0, 1.0))
                self.dash_stock_round_progress.set(prog)
                if prog < 0.15:
                    self.dash_stock_round_progress.configure(progress_color="#ef4444") # Red
                elif prog < 0.4:
                    self.dash_stock_round_progress.configure(progress_color="#f59e0b") # Orange
                else:
                    self.dash_stock_round_progress.configure(progress_color="#06b6d4") # Cyan
            else:
                self.dash_stock_slim_lbl.configure(text=f"Slim Blue: {qty}/300 units")
                prog = max(0.0, min(float(qty) / 300.0, 1.0))
                self.dash_stock_slim_progress.set(prog)
                if prog < 0.15:
                    self.dash_stock_slim_progress.configure(progress_color="#ef4444")
                elif prog < 0.4:
                    self.dash_stock_slim_progress.configure(progress_color="#f59e0b")
                else:
                    self.dash_stock_slim_progress.configure(progress_color="#3b82f6") # Blue
                
        if low_stock > 0:
            self.kpi_stock_val.configure(text=f"{low_stock} WARNINGS", text_color="#ef4444")
        else:
            self.kpi_stock_val.configure(text="HEALTHY", text_color="#10b981")
            
        # Recent transactions tree
        cursor.execute("""
            SELECT o.id, c.full_name, o.total_amount, o.status, o.order_date
            FROM orders o
            JOIN customers c ON o.customer_id = c.id
            ORDER BY o.order_date DESC
            LIMIT 6
        """)
        rows = cursor.fetchall()
        
        # Clear tree
        for item in self.dash_tree.get_children():
            self.dash_tree.delete(item)
            
        for row in rows:
            # Parse date format
            try:
                dt = datetime.fromisoformat(row['order_date'].replace('Z', '+00:00'))
                dt_str = dt.strftime('%b %d, %H:%M')
            except ValueError:
                dt_str = row['order_date'][:16]
                
            self.dash_tree.insert(
                "", "end", 
                values=(
                    f"#{row['id']}", 
                    row['full_name'], 
                    f"₱{row['total_amount']:.2f}", 
                    row['status'].capitalize(), 
                    dt_str
                )
            )
            
        conn.close()

    # ==========================================
    # 2. POS SALES TERMINAL
    # ==========================================
    def create_pos_view(self):
        view = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.views["pos"] = view
        
        # Layout
        view.grid_columnconfigure(0, weight=2)
        view.grid_columnconfigure(1, weight=1)
        
        # Left Panel: POS inputs
        left_panel = ctk.CTkFrame(view, fg_color="#131c2e", border_width=1, border_color="#1e293b")
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=10)
        
        lbl_pos_title = ctk.CTkLabel(left_panel, text="New Sales Transaction", font=ctk.CTkFont(size=18, weight="bold"))
        lbl_pos_title.pack(anchor="w", padx=20, pady=20)
        
        # Customer Dropdown Selector
        ct_lbl = ctk.CTkLabel(left_panel, text="Select Customer Profile:", font=ctk.CTkFont(size=11, weight="bold"), text_color="gray")
        ct_lbl.pack(anchor="w", padx=20, pady=(0, 5))
        
        self.pos_customer_dropdown = ctk.CTkComboBox(left_panel, width=350, state="readonly")
        self.pos_customer_dropdown.pack(anchor="w", padx=20, pady=(0, 20))
        
        # Product Refill Item Row 1 (Round Container)
        prod1_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        prod1_frame.pack(fill="x", padx=20, pady=10)
        
        self.prod1_name = ctk.CTkLabel(prod1_frame, text="5-Gallon Round Blue Container Refill (₱25.00)", font=ctk.CTkFont(size=13, weight="bold"))
        self.prod1_name.pack(side="left")
        
        # Qty Picker
        self.prod1_qty = ctk.CTkSpinbox = self.create_qty_picker(prod1_frame, "qty1")
        prod1_frame.grid_columnconfigure(0, weight=1)
        
        # Product Refill Item Row 2 (Slim Blue Container)
        prod2_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        prod2_frame.pack(fill="x", padx=20, pady=10)
        
        self.prod2_name = ctk.CTkLabel(prod2_frame, text="5-Gallon Slim Blue Container Refill (₱30.00)", font=ctk.CTkFont(size=13, weight="bold"))
        self.prod2_name.pack(side="left")
        
        self.prod2_qty = self.create_qty_picker(prod2_frame, "qty2")
        
        # Order Notes
        notes_lbl = ctk.CTkLabel(left_panel, text="Optional Sales Notes / Driver Info:", font=ctk.CTkFont(size=11, weight="bold"), text_color="gray")
        notes_lbl.pack(anchor="w", padx=20, pady=(15, 5))
        self.pos_notes = ctk.CTkTextbox(left_panel, height=80, width=400)
        self.pos_notes.pack(anchor="w", padx=20, pady=(0, 20))
        
        # Right Panel: Sales Receipt / Checkout Summary
        right_panel = ctk.CTkFrame(view, fg_color="#131c2e", border_width=1, border_color="#1e293b")
        right_panel.grid(row=0, column=1, sticky="nsew", padx=(10, 0), pady=10)
        
        lbl_summary_title = ctk.CTkLabel(right_panel, text="Checkout Summary", font=ctk.CTkFont(size=18, weight="bold"))
        lbl_summary_title.pack(anchor="w", padx=20, pady=20)
        
        # Total Box
        total_frame = ctk.CTkFrame(right_panel, fg_color="#1a2233", border_width=1, border_color="#2b3a55")
        total_frame.pack(fill="x", padx=20, pady=10)
        
        t_lbl = ctk.CTkLabel(total_frame, text="TOTAL AMOUNT DUE", font=ctk.CTkFont(size=10, weight="bold"), text_color="gray")
        t_lbl.pack(anchor="w", padx=15, pady=(15, 0))
        
        self.pos_total_label = ctk.CTkLabel(total_frame, text="₱0.00", font=ctk.CTkFont(size=30, weight="bold"), text_color="#3b82f6")
        self.pos_total_label.pack(anchor="w", padx=15, pady=(5, 15))
        
        # Delivery Driver Dropdown (If walkin, set driver to None)
        drv_lbl = ctk.CTkLabel(right_panel, text="Delivery / Walk-in Mode:", font=ctk.CTkFont(size=11, weight="bold"), text_color="gray")
        drv_lbl.pack(anchor="w", padx=20, pady=(10, 5))
        
        self.pos_delivery_mode = ctk.CTkComboBox(
            right_panel, 
            values=["Over-the-Counter (Walk-in)", "Delivery: Carlos", "Delivery: Miguel", "Delivery: Ramon"],
            state="readonly"
        )
        self.pos_delivery_mode.set("Over-the-Counter (Walk-in)")
        self.pos_delivery_mode.pack(fill="x", padx=20, pady=(0, 20))
        
        # Checkout actions
        self.btn_checkout = ctk.CTkButton(
            right_panel, 
            text="Confirm and Process Sale", 
            fg_color="#10b981", 
            hover_color="#059669",
            height=45,
            font=ctk.CTkFont(weight="bold"),
            command=self.process_pos_checkout
        )
        self.btn_checkout.pack(fill="x", padx=20, pady=10)
        
        self.btn_reset_pos = ctk.CTkButton(
            right_panel, 
            text="Clear Form", 
            fg_color="transparent", 
            border_width=1, 
            border_color="gray",
            command=self.reset_pos_fields
        )
        self.btn_reset_pos.pack(fill="x", padx=20, pady=5)
        
    def create_qty_picker(self, parent, tag):
        picker_frame = ctk.CTkFrame(parent, fg_color="transparent")
        picker_frame.pack(side="right")
        
        # Minus Button
        btn_minus = ctk.CTkButton(
            picker_frame, text="-", width=30, height=28, 
            fg_color=["#cbd5e1", "#334155"], 
            text_color=["black", "white"],
            command=lambda: self.adjust_pos_qty(tag, -1)
        )
        btn_minus.pack(side="left")
        
        # Qty Input display
        lbl_qty = ctk.CTkLabel(picker_frame, text="0", font=ctk.CTkFont(weight="bold"), width=40)
        lbl_qty.pack(side="left", padx=5)
        
        # Plus Button
        btn_plus = ctk.CTkButton(
            picker_frame, text="+", width=30, height=28, 
            fg_color=["#cbd5e1", "#334155"], 
            text_color=["black", "white"],
            command=lambda: self.adjust_pos_qty(tag, 1)
        )
        btn_plus.pack(side="left")
        
        # Cache labels
        if not hasattr(self, 'qty_pickers'):
            self.qty_pickers = {}
        self.qty_pickers[tag] = lbl_qty
        return picker_frame

    def adjust_pos_qty(self, tag, amount):
        lbl = self.qty_pickers[tag]
        val = int(lbl.cget("text")) + amount
        if val < 0: val = 0
        if val > 99: val = 99
        lbl.configure(text=str(val))
        self.recalculate_pos_total()
        
    def recalculate_pos_total(self):
        qty1 = int(self.qty_pickers["qty1"].cget("text"))
        qty2 = int(self.qty_pickers["qty2"].cget("text"))
        total = (qty1 * 25.0) + (qty2 * 30.0)
        self.pos_total_label.configure(text=f"₱{total:,.2f}")
        
    def refresh_pos_customers(self):
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, full_name FROM customers WHERE is_active = 1")
        rows = cursor.fetchall()
        
        self.pos_customers_data = {}
        dropdown_vals = []
        for r in rows:
            name = r['full_name']
            self.pos_customers_data[name] = r['id']
            dropdown_vals.append(name)
            
        self.pos_customer_dropdown.configure(values=dropdown_vals)
        if dropdown_vals:
            self.pos_customer_dropdown.set(dropdown_vals[0])
            
        conn.close()
        
    def reset_pos_fields(self):
        self.qty_pickers["qty1"].configure(text="0")
        self.qty_pickers["qty2"].configure(text="0")
        self.pos_notes.delete("1.0", "end")
        self.pos_total_label.configure(text="₱0.00")
        
    def process_pos_checkout(self):
        selected_cust = self.pos_customer_dropdown.get()
        if not selected_cust:
            messagebox.showwarning("POS Checkout", "Please select a customer profile.")
            return
            
        customer_id = self.pos_customers_data.get(selected_cust)
        qty1 = int(self.qty_pickers["qty1"].cget("text"))
        qty2 = int(self.qty_pickers["qty2"].cget("text"))
        total = (qty1 * 25.0) + (qty2 * 30.0)
        notes = self.pos_notes.get("1.0", "end").strip()
        delivery_mode = self.pos_delivery_mode.get()
        
        if qty1 == 0 and qty2 == 0:
            messagebox.showwarning("POS Checkout", "Please select at least 1 refill item to checkout.")
            return
            
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Check inventory first
            cursor.execute("SELECT id, stock_quantity, name FROM products")
            products = cursor.fetchall()
            
            p1_stock, p2_stock = 0, 0
            p1_id, p2_id = None, None
            for p in products:
                if 'Round' in p['name']:
                    p1_id = p['id']
                    p1_stock = p['stock_quantity']
                else:
                    p2_id = p['id']
                    p2_stock = p['stock_quantity']
                    
            if qty1 > p1_stock:
                messagebox.showerror("POS Error", f"Insufficient stock for Round Containers. Currently available: {p1_stock} units.")
                conn.close()
                return
            if qty2 > p2_stock:
                messagebox.showerror("POS Error", f"Insufficient stock for Slim Blue Containers. Currently available: {p2_stock} units.")
                conn.close()
                return
                
            # Create Order
            # For POS direct transaction, we set status as 'completed' (or confirmed if dispatched)
            order_status = 'completed' if "Walk-in" in delivery_mode else 'confirmed'
            order_date_str = datetime.now().isoformat()
            
            cursor.execute(
                "INSERT INTO orders (customer_id, total_amount, status, order_date, notes, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (customer_id, total, order_status, order_date_str, notes, order_date_str, order_date_str)
            )
            order_id = cursor.lastrowid
            
            # Create Order Items & Decrement Inventory
            if qty1 > 0:
                cursor.execute(
                    "INSERT INTO order_items (order_id, product_id, quantity, unit_price, subtotal) VALUES (?, ?, ?, 25.00, ?)",
                    (order_id, p1_id, qty1, qty1 * 25.00)
                )
                cursor.execute("UPDATE products SET stock_quantity = stock_quantity - ? WHERE id = ?", (qty1, p1_id))
                
            if qty2 > 0:
                cursor.execute(
                    "INSERT INTO order_items (order_id, product_id, quantity, unit_price, subtotal) VALUES (?, ?, ?, 30.00, ?)",
                    (order_id, p2_id, qty2, qty2 * 30.00)
                )
                cursor.execute("UPDATE products SET stock_quantity = stock_quantity - ? WHERE id = ?", (qty2, p2_id))
                
            # Create Delivery Status Record
            del_status = 'delivered' if "Walk-in" in delivery_mode else 'in_transit'
            driver = None if "Walk-in" in delivery_mode else delivery_mode.split(": ")[1]
            
            cursor.execute(
                "INSERT INTO deliveries (order_id, delivery_date, status, driver_name, notes, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (order_id, order_date_str if del_status == 'delivered' else None, del_status, driver, f"POS Sale: {delivery_mode}", order_date_str, order_date_str)
            )
            
            conn.commit()
            messagebox.showinfo("POS Checkout", f"Transaction processed successfully!\nOrder #{order_id} recorded.")
            self.reset_pos_fields()
            
        except Exception as e:
            conn.rollback()
            messagebox.showerror("Database Transaction Error", f"Failed to record sale: {e}")
        finally:
            conn.close()

    # ==========================================
    # 3. WEB ORDER MONITOR VIEW
    # ==========================================
    def create_monitor_view(self):
        view = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.views["monitor"] = view
        
        # Header
        view.grid_columnconfigure(0, weight=1)
        view.grid_rowconfigure(1, weight=1)
        
        header_frame = ctk.CTkFrame(view, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        
        lbl_mon = ctk.CTkLabel(header_frame, text="Incoming Web Order Monitor", font=ctk.CTkFont(size=18, weight="bold"))
        lbl_mon.pack(side="left")
        
        btn_refresh_mon = ctk.CTkButton(header_frame, text="🔄 Reload Orders", width=120, command=self.refresh_monitor_data)
        btn_refresh_mon.pack(side="right")
        
        # Order Monitor Grid layout
        monitor_main = ctk.CTkFrame(view)
        monitor_main.grid(row=1, column=0, sticky="nsew", pady=10)
        
        # Split: Left order list, Right order details pane
        monitor_main.grid_columnconfigure(0, weight=1)
        monitor_main.grid_columnconfigure(1, weight=1)
        monitor_main.grid_rowconfigure(0, weight=1)
        
        # Tree list of active orders
        list_box = ctk.CTkFrame(monitor_main, fg_color="#131c2e", border_width=1, border_color="#1e293b")
        list_box.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
        
        self.mon_tree = self.create_custom_tree(
            list_box, 
            ["Order #", "Customer", "Amount", "Status"],
            [60, 150, 100, 100]
        )
        self.mon_tree.pack(fill="both", expand=True)
        self.mon_tree.bind("<<TreeviewSelect>>", self.on_monitor_order_select)
        
        # Details & Action Panel (Right)
        self.details_panel = ctk.CTkFrame(monitor_main, fg_color="#131c2e", border_width=1, border_color="#1e293b")
        self.details_panel.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)
        
        self.lbl_details_title = ctk.CTkLabel(self.details_panel, text="Order Details", font=ctk.CTkFont(size=15, weight="bold"))
        self.lbl_details_title.pack(anchor="w", padx=20, pady=15)
        
        # Data box
        self.mon_details_text = ctk.CTkTextbox(self.details_panel, height=250, font=ctk.CTkFont(family="Consolas", size=12))
        self.mon_details_text.pack(fill="x", padx=20, pady=5)
        self.mon_details_text.configure(state="disabled")
        
        # Driver assignment
        drv_lbl = ctk.CTkLabel(self.details_panel, text="Assign Driver (for Delivery):", font=ctk.CTkFont(size=11, weight="bold"), text_color="gray")
        drv_lbl.pack(anchor="w", padx=20, pady=(15, 2))
        
        self.mon_driver_combobox = ctk.CTkComboBox(self.details_panel, values=["Carlos", "Miguel", "Ramon"], state="readonly")
        self.mon_driver_combobox.pack(fill="x", padx=20, pady=(2, 15))
        self.mon_driver_combobox.set("Carlos")
        
        # Action buttons
        btn_frame = ctk.CTkFrame(self.details_panel, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=10)
        
        self.btn_mon_confirm = ctk.CTkButton(
            btn_frame, text="Confirm Order", fg_color="#3b82f6", hover_color="#2563eb", width=120,
            command=self.confirm_web_order
        )
        self.btn_mon_confirm.pack(side="left", expand=True, padx=2)
        
        self.btn_mon_dispatch = ctk.CTkButton(
            btn_frame, text="Dispatch Delivery", fg_color="#8b5cf6", hover_color="#7c3aed", width=120,
            command=self.dispatch_web_order
        )
        self.btn_mon_dispatch.pack(side="left", expand=True, padx=2)
        
        self.btn_mon_complete = ctk.CTkButton(
            btn_frame, text="Mark Delivered", fg_color="#10b981", hover_color="#059669", width=120,
            command=self.complete_web_order
        )
        self.btn_mon_complete.pack(side="left", expand=True, padx=2)
        
        self.selected_mon_order_id = None
        self.disable_monitor_actions()
        
    def disable_monitor_actions(self):
        self.btn_mon_confirm.configure(state="disabled")
        self.btn_mon_dispatch.configure(state="disabled")
        self.btn_mon_complete.configure(state="disabled")
        
    def refresh_monitor_data(self):
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        # Load only non-completed and non-cancelled orders
        cursor.execute("""
            SELECT o.id, c.full_name, o.total_amount, o.status
            FROM orders o
            JOIN customers c ON o.customer_id = c.id
            WHERE o.status IN ('pending', 'confirmed')
            ORDER BY o.id DESC
        """)
        rows = cursor.fetchall()
        
        # Clear list
        for item in self.mon_tree.get_children():
            self.mon_tree.delete(item)
            
        for r in rows:
            self.mon_tree.insert(
                "", "end", 
                values=(f"#{r['id']}", r['full_name'], f"₱{r['total_amount']:.2f}", r['status'].upper())
            )
            
        conn.close()
        self.selected_mon_order_id = None
        self.mon_details_text.configure(state="normal")
        self.mon_details_text.delete("1.0", "end")
        self.mon_details_text.insert("1.0", "Select an order from the list to view details...")
        self.mon_details_text.configure(state="disabled")
        self.disable_monitor_actions()
        
    def on_monitor_order_select(self, event):
        selected_items = self.mon_tree.selection()
        if not selected_items:
            return
            
        item_vals = self.mon_tree.item(selected_items[0])['values']
        order_id = int(str(item_vals[0]).replace('#', ''))
        self.selected_mon_order_id = order_id
        
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        # Get order details
        cursor.execute("""
            SELECT o.id, c.full_name, c.phone, c.address, o.total_amount, o.status, o.order_date, o.notes, d.status as delivery_status, d.driver_name
            FROM orders o
            JOIN customers c ON o.customer_id = c.id
            LEFT JOIN deliveries d ON o.id = d.order_id
            WHERE o.id = ?
        """, (order_id,))
        order = cursor.fetchone()
        
        # Get items list
        cursor.execute("""
            SELECT p.name, oi.quantity, oi.unit_price, oi.subtotal
            FROM order_items oi
            JOIN products p ON oi.product_id = p.id
            WHERE oi.order_id = ?
        """, (order_id,))
        items = cursor.fetchall()
        
        conn.close()
        
        # Display details in details box
        self.mon_details_text.configure(state="normal")
        self.mon_details_text.delete("1.0", "end")
        
        details = (
            f"ORDER NUMBER:  #{order['id']}\n"
            f"STATUS:        {order['status'].upper()}\n"
            f"ORDER DATE:    {order['order_date']}\n"
            f"----------------------------------------\n"
            f"CUSTOMER:      {order['full_name']}\n"
            f"PHONE:         {order['phone']}\n"
            f"ADDRESS:       {order['address']}\n"
            f"NOTES:         {order['notes'] or 'None'}\n"
            f"----------------------------------------\n"
            f"ORDERED ITEMS:\n"
        )
        
        for item in items:
            p_name = item['name'].split(' (')[0]
            details += f" - {item['quantity']}x {p_name} @ ₱{item['unit_price']:.2f} (₱{item['subtotal']:.2f})\n"
            
        details += f"----------------------------------------\n"
        details += f"DELIVERY STATUS: {str(order['delivery_status']).upper()}\n"
        details += f"ASSIGNED DRIVER: {order['driver_name'] or 'None'}\n"
        details += f"----------------------------------------\n"
        details += f"GRAND TOTAL:     ₱{order['total_amount']:.2f}\n"
        
        self.mon_details_text.insert("1.0", details)
        self.mon_details_text.configure(state="disabled")
        
        # Enable actions based on status
        status = order['status']
        self.disable_monitor_actions()
        
        if status == 'pending':
            self.btn_mon_confirm.configure(state="normal")
        elif status == 'confirmed':
            del_status = order['delivery_status']
            if del_status != 'in_transit':
                self.btn_mon_dispatch.configure(state="normal")
            else:
                self.btn_mon_complete.configure(state="normal")
                
    def confirm_web_order(self):
        if not self.selected_mon_order_id: return
        
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Shift order status to confirmed
            now_str = datetime.now().isoformat()
            cursor.execute(
                "UPDATE orders SET status = 'confirmed', updated_at = ? WHERE id = ?",
                (now_str, self.selected_mon_order_id)
            )
            cursor.execute(
                "UPDATE deliveries SET status = 'pending', updated_at = ? WHERE order_id = ?",
                (now_str, self.selected_mon_order_id)
            )
            conn.commit()
            messagebox.showinfo("Order Monitor", f"Order #{self.selected_mon_order_id} confirmed successfully!")
            self.refresh_monitor_data()
        except Exception as e:
            conn.rollback()
            messagebox.showerror("Error", f"Failed to confirm order: {e}")
        finally:
            conn.close()
            
    def dispatch_web_order(self):
        if not self.selected_mon_order_id: return
        driver = self.mon_driver_combobox.get()
        
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Check inventory: decrement on dispatch
            cursor.execute("SELECT product_id, quantity FROM order_items WHERE order_id = ?", (self.selected_mon_order_id,))
            items = cursor.fetchall()
            
            # Verify stock exists before committing
            for item in items:
                cursor.execute("SELECT stock_quantity, name FROM products WHERE id = ?", (item['product_id'],))
                prod = cursor.fetchone()
                if prod['stock_quantity'] < item['quantity']:
                    messagebox.showerror("Inventory Error", f"Insufficient stock for {prod['name']}. Cannot dispatch order.")
                    conn.close()
                    return
                    
            # Decrement stock and update delivery driver
            now_str = datetime.now().isoformat()
            for item in items:
                cursor.execute(
                    "UPDATE products SET stock_quantity = stock_quantity - ? WHERE id = ?",
                    (item['quantity'], item['product_id'])
                )
                
            cursor.execute(
                "UPDATE deliveries SET status = 'in_transit', driver_name = ?, updated_at = ? WHERE order_id = ?",
                (driver, now_str, self.selected_mon_order_id)
            )
            conn.commit()
            messagebox.showinfo("Order Monitor", f"Order #{self.selected_mon_order_id} dispatched with Driver {driver}!")
            self.refresh_monitor_data()
        except Exception as e:
            conn.rollback()
            messagebox.showerror("Error", f"Failed to dispatch order: {e}")
        finally:
            conn.close()
            
    def complete_web_order(self):
        if not self.selected_mon_order_id: return
        
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            now_str = datetime.now().isoformat()
            cursor.execute(
                "UPDATE orders SET status = 'completed', updated_at = ? WHERE id = ?",
                (now_str, self.selected_mon_order_id)
            )
            cursor.execute(
                "UPDATE deliveries SET status = 'delivered', delivery_date = ?, updated_at = ? WHERE order_id = ?",
                (now_str, now_str, self.selected_mon_order_id)
            )
            conn.commit()
            messagebox.showinfo("Order Monitor", f"Order #{self.selected_mon_order_id} marked as completed and delivered!")
            self.refresh_monitor_data()
        except Exception as e:
            conn.rollback()
            messagebox.showerror("Error", f"Failed to complete order: {e}")
        finally:
            conn.close()

    # ==========================================
    # 4. TRANSACTION HISTORY VIEW
    # ==========================================
    def create_history_view(self):
        view = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.views["history"] = view
        
        # Layout
        view.grid_columnconfigure(0, weight=1)
        view.grid_rowconfigure(1, weight=1)
        
        # Filters toolbar
        toolbar = ctk.CTkFrame(view, fg_color="#131c2e", border_width=1, border_color="#1e293b")
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        
        lbl_search = ctk.CTkLabel(toolbar, text="Search Customer Name:", font=ctk.CTkFont(size=11, weight="bold"))
        lbl_search.pack(side="left", padx=15, pady=10)
        
        self.hist_search_entry = ctk.CTkEntry(toolbar, width=180, placeholder_text="Enter name...")
        self.hist_search_entry.pack(side="left", padx=5, pady=10)
        self.hist_search_entry.bind("<KeyRelease>", lambda e: self.refresh_history_data())
        
        lbl_status = ctk.CTkLabel(toolbar, text="Status Filter:", font=ctk.CTkFont(size=11, weight="bold"))
        lbl_status.pack(side="left", padx=15, pady=10)
        
        self.hist_status_filter = ctk.CTkComboBox(
            toolbar, width=120, values=["ALL", "Completed", "Confirmed", "Pending", "Cancelled"], state="readonly",
            command=lambda v: self.refresh_history_data()
        )
        self.hist_status_filter.pack(side="left", padx=5, pady=10)
        self.hist_status_filter.set("ALL")
        
        # History table container
        table_container = ctk.CTkFrame(view, fg_color="#131c2e", border_width=1, border_color="#1e293b")
        table_container.grid(row=1, column=0, sticky="nsew", pady=10)
        
        self.hist_tree = self.create_custom_tree(
            table_container,
            ["Order ID", "Customer Name", "Total cost", "Status", "Order Date", "Notes"],
            [80, 180, 100, 100, 150, 300]
        )
        self.hist_tree.pack(fill="both", expand=True)
        
    def refresh_history_data(self):
        query_str = self.hist_search_entry.get().strip()
        status_val = self.hist_status_filter.get()
        
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        sql = """
            SELECT o.id, c.full_name, o.total_amount, o.status, o.order_date, o.notes
            FROM orders o
            JOIN customers c ON o.customer_id = c.id
            WHERE c.full_name LIKE ?
        """
        params = [f"%{query_str}%"]
        
        if status_val != "ALL":
            sql += " AND o.status = ?"
            params.append(status_val.lower())
            
        sql += " ORDER BY o.order_date DESC"
        
        cursor.execute(sql, tuple(params))
        rows = cursor.fetchall()
        
        # Clear tree
        for item in self.hist_tree.get_children():
            self.hist_tree.delete(item)
            
        for r in rows:
            try:
                dt = datetime.fromisoformat(r['order_date'].replace('Z', '+00:00'))
                dt_str = dt.strftime('%Y-%m-%d %H:%M')
            except ValueError:
                dt_str = r['order_date'][:16]
                
            self.hist_tree.insert(
                "", "end",
                values=(
                    f"#{r['id']}",
                    r['full_name'],
                    f"₱{r['total_amount']:.2f}",
                    r['status'].capitalize(),
                    dt_str,
                    r['notes'] or ''
                )
            )
            
        conn.close()

    # ==========================================
    # 5. AI PREDICTIONS VIEW
    # ==========================================
    def create_ai_view(self):
        view = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.views["ai"] = view
        
        view.grid_columnconfigure(0, weight=1)
        view.grid_columnconfigure(1, weight=1)
        view.grid_rowconfigure(0, weight=1)
        
        # Left Panel: Customer Refill Predictions
        refill_panel = ctk.CTkFrame(view, fg_color="#131c2e", border_width=1, border_color="#1e293b")
        refill_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=10)
        
        lbl_ai_c = ctk.CTkLabel(refill_panel, text="AI Customer Refill Scheduler", font=ctk.CTkFont(size=16, weight="bold"))
        lbl_ai_c.pack(anchor="w", padx=15, pady=15)
        
        lbl_ai_c_desc = ctk.CTkLabel(
            refill_panel, 
            text="Predicts customer refills based on their historic ordering intervals and flags who is due.",
            font=ctk.CTkFont(size=11), text_color="gray"
        )
        lbl_ai_c_desc.pack(anchor="w", padx=15, pady=(0, 10))
        
        # Refill Table
        self.refill_tree = self.create_custom_tree(
            refill_panel,
            ["Customer", "Last Refill", "Est. Refill", "Cycle (Days)", "Status"],
            [120, 90, 90, 80, 80]
        )
        self.refill_tree.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        self.refill_tree.bind("<<TreeviewSelect>>", self.on_refill_customer_select)
        
        # Right Panel: 7-Day Demand Forecasting Chart
        self.forecast_panel = ctk.CTkFrame(view, fg_color="#131c2e", border_width=1, border_color="#1e293b")
        self.forecast_panel.grid(row=0, column=1, sticky="nsew", padx=(10, 0), pady=10)
        
        lbl_ai_f = ctk.CTkLabel(self.forecast_panel, text="7-Day Weather-Integrated Demand Forecast", font=ctk.CTkFont(size=16, weight="bold"))
        lbl_ai_f.pack(anchor="w", padx=15, pady=15)
        
        self.forecast_canvas_frame = ctk.CTkFrame(self.forecast_panel, fg_color="transparent")
        self.forecast_canvas_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        
    def refresh_ai_data(self):
        # 1. Load customer refill predictions
        refills = predict_customer_refills(self.db_path)
        
        # Clear tree
        for item in self.refill_tree.get_children():
            self.refill_tree.delete(item)
            
        for r in refills:
            self.refill_tree.insert(
                "", "end",
                values=(
                    r['name'],
                    r['last_order_date'],
                    r['predicted_refill_date'],
                    f"{r['avg_interval']} days",
                    r['status']
                )
            )
            
        # 2. Draw 7-Day Demand Forecast Chart
        forecasts = forecast_water_demand(self.db_path)
        self.draw_forecast_chart(forecasts)
        
    def draw_forecast_chart(self, forecasts):
        # Clear existing widgets inside canvas frame
        for child in self.forecast_canvas_frame.winfo_children():
            child.destroy()
            
        if not forecasts:
            lbl_err = ctk.CTkLabel(self.forecast_canvas_frame, text="Not enough data to project forecast.")
            lbl_err.pack()
            return
            
        # Parse data
        dates = [f["date"][-5:] for f in forecasts]  # MM-DD format
        demands = [f["predicted_demand"] for f in forecasts]
        temps = [f["max_temp"] for f in forecasts]
        
        # Create matplotlib figure
        fig = Figure(figsize=(5, 4), dpi=100, facecolor="#131c2e")
        ax1 = fig.add_subplot(111)
        ax1.set_facecolor("#131c2e")
        
        # Hide top and right spines
        ax1.spines['top'].set_visible(False)
        ax1.spines['right'].set_visible(False)
        ax1.spines['left'].set_color('#cbd5e1')
        ax1.spines['bottom'].set_color('#cbd5e1')
        
        # Plot demand line
        line1 = ax1.plot(dates, demands, color='#3b82f6', marker='o', linewidth=2.5, label='Gallons Demand')
        ax1.set_ylabel('Predicted Demand (Containers)', color='#3b82f6', fontweight='bold')
        ax1.tick_params(axis='y', labelcolor='#3b82f6', colors='#cbd5e1')
        ax1.tick_params(axis='x', colors='#cbd5e1')
        
        # Create twin axis for weather temperature
        ax2 = ax1.twinx()
        ax2.spines['top'].set_visible(False)
        ax2.spines['left'].set_visible(False)
        ax2.spines['right'].set_color('#ef4444')
        ax2.spines['bottom'].set_color('#cbd5e1')
        
        line2 = ax2.plot(dates, temps, color='#ef4444', marker='x', linestyle='--', linewidth=1.5, label='Max Temp (°C)')
        ax2.set_ylabel('Max Temp (°C)', color='#ef4444', fontweight='bold')
        ax2.tick_params(axis='y', labelcolor='#ef4444', colors='#cbd5e1')
        
        # Add grid lines
        ax1.grid(True, color='#ffffff', alpha=0.05, linestyle=':')
        
        # Combine labels for legend
        lines = line1 + line2
        labels = [l.get_label() for l in lines]
        ax1.legend(lines, labels, loc='upper left', facecolor='#131c2e', edgecolor='none', labelcolor='white')
        
        fig.tight_layout()
        
        # Embed canvas
        canvas = FigureCanvasTkAgg(fig, master=self.forecast_canvas_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
        
    def on_refill_customer_select(self, event):
        selected_items = self.refill_tree.selection()
        if not selected_items: return
        
        vals = self.refill_tree.item(selected_items[0])['values']
        name = vals[0]
        status = vals[4]
        
        if status in ['Due Now', 'Due Soon']:
            # Alert user/operator that they can make a callback
            reply = messagebox.askyesno(
                "AI Dispatch Suggestion", 
                f"Customer {name} is flagged as '{status}' (Estimated next refill date: {vals[2]}).\n\n"
                f"Would you like to initiate a new POS Sales order for this customer?"
            )
            if reply:
                self.show_pos()
                self.pos_customer_dropdown.set(name)

    # ==========================================
    # UTILITIES
    # ==========================================
    def create_custom_tree(self, parent, columns, widths):
        # Set ttk style for dark theme treeview
        style = ttk.Style()
        style.theme_use("clam")
        
        style.configure(
            "Treeview",
            background="#131c2e",
            foreground="#f1f5f9",
            rowheight=30,
            fieldbackground="#131c2e",
            borderwidth=0
        )
        style.map(
            "Treeview",
            background=[("selected", "#3b82f6")],
            foreground=[("selected", "#ffffff")]
        )
        
        style.configure(
            "Treeview.Heading",
            background="#0d1321",
            foreground="#cbd5e1",
            font=("Outfit", 9, "bold"),
            borderwidth=0
        )
        
        # Tree component
        tree = ttk.Treeview(parent, columns=columns, show="headings", selectmode="browse")
        
        for i, col in enumerate(columns):
            tree.heading(col, text=col)
            tree.column(col, width=widths[i], anchor="w")
            
        return tree

if __name__ == "__main__":
    app = WaterStationApp()
    app.mainloop()
