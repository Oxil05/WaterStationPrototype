import os
import sqlite3
import threading
import bcrypt
from datetime import datetime, timezone
import tkinter as tk
from tkinter import messagebox, ttk
from PIL import Image
import customtkinter as ctk
import pandas as pd
import numpy as np

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

import sys

# Helper to resolve bundled asset resources under PyInstaller _MEIPASS
def get_resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

# Resolve external mutable DB location
try:
    is_frozen = getattr(sys, 'frozen', False)
    if is_frozen:
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
except Exception:
    base_dir = os.path.abspath(".")

DB_PATH = os.path.join(base_dir, 'instance', 'water_station.db')
LOGO_PATH = get_resource_path(os.path.join('assets', 'logo.jpg'))
HERO_PATH = get_resource_path(os.path.join('assets', 'login_hero.jpg'))

class WaterStationApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("AquaFlow - Mineral Water Station POS & AI Console")
        self.geometry("1100x680")
        self.minsize(1050, 650)
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
        self.current_user = None
        self.qty_pickers = {}
        
        # Load business images
        self.load_visual_assets()
        
        # Display the login/security screen initially
        self.show_login_screen()
        
    def load_visual_assets(self):
        """Loads branding logo and welcome illustration using Pillow."""
        self.logo_img = None
        self.hero_img = None
        
        try:
            if os.path.exists(LOGO_PATH):
                self.logo_img = ctk.CTkImage(
                    light_image=Image.open(LOGO_PATH), 
                    dark_image=Image.open(LOGO_PATH), 
                    size=(70, 70)
                )
            if os.path.exists(HERO_PATH):
                self.hero_img = ctk.CTkImage(
                    light_image=Image.open(HERO_PATH), 
                    dark_image=Image.open(HERO_PATH), 
                    size=(460, 640)
                )
        except Exception as e:
            print(f"Error loading visual assets: {e}")

    def get_db_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # ==========================================
    # LOGIN / SECURITY INTERFACE
    # ==========================================
    def show_login_screen(self):
        """Creates and packs a full-screen, dual-pane security lock screen."""
        self.login_frame = ctk.CTkFrame(self, fg_color="#090d16", corner_radius=0)
        self.login_frame.pack(fill="both", expand=True)
        
        # Container Grid
        self.login_frame.grid_columnconfigure(0, weight=1) # Left pane: Visual graphic
        self.login_frame.grid_columnconfigure(1, weight=1) # Right pane: Login form
        self.login_frame.grid_rowconfigure(0, weight=1)
        
        # --- LEFT PANE: Welcoming Brand Banner ---
        left_pane = ctk.CTkFrame(self.login_frame, fg_color="#0d1321", corner_radius=0)
        left_pane.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        if self.hero_img:
            # Display vertical illustration image
            hero_label = ctk.CTkLabel(left_pane, image=self.hero_img, text="")
            hero_label.pack(fill="both", expand=True)
            
            # overlay greeting card (floating over graphic)
            overlay = ctk.CTkFrame(left_pane, fg_color="#0b0f19", corner_radius=12)
            overlay.place(relx=0.5, rely=0.8, anchor="center", relwidth=0.85)
            
            title_lbl = ctk.CTkLabel(
                overlay, text="AquaFlow Control", 
                font=ctk.CTkFont(family="Outfit", size=20, weight="bold"), 
                text_color="#06b6d4"
            )
            title_lbl.pack(pady=(12, 4))
            
            sub_lbl = ctk.CTkLabel(
                overlay, text="Bancal Water Station Console • Meycauayan", 
                font=ctk.CTkFont(size=11), text_color="gray"
            )
            sub_lbl.pack(pady=(0, 12))
        else:
            # Fallback if graphic fails to load
            fallback_label = ctk.CTkLabel(
                left_pane, text="💦 AquaFlow", 
                font=ctk.CTkFont(family="Outfit", size=32, weight="bold"), 
                text_color="#3b82f6"
            )
            fallback_label.pack(expand=True)
            
        # --- RIGHT PANE: Security Form ---
        right_pane = ctk.CTkFrame(self.login_frame, fg_color="transparent")
        right_pane.grid(row=0, column=1, sticky="nsew")
        
        # Form Container (Centered vertically)
        form_container = ctk.CTkFrame(right_pane, width=380, height=440, fg_color="#131c2e", border_width=1, border_color="#1e293b", corner_radius=16)
        form_container.place(relx=0.5, rely=0.5, anchor="center")
        
        # Display Droplet Logo Icon
        if self.logo_img:
            logo_lbl = ctk.CTkLabel(form_container, image=self.logo_img, text="")
            logo_lbl.pack(pady=(25, 5))
        else:
            logo_lbl = ctk.CTkLabel(form_container, text="🔹", font=ctk.CTkFont(size=30))
            logo_lbl.pack(pady=(25, 5))
            
        brand_lbl = ctk.CTkLabel(
            form_container, text="AQUAFLOW STATION", 
            font=ctk.CTkFont(family="Outfit", size=18, weight="bold"), 
            text_color="white"
        )
        brand_lbl.pack(pady=(0, 2))
        
        subtitle_lbl = ctk.CTkLabel(form_container, text="Security Authenticator", font=ctk.CTkFont(size=11), text_color="gray")
        subtitle_lbl.pack(pady=(0, 20))
        
        # Inputs
        self.login_user_entry = ctk.CTkEntry(form_container, placeholder_text="Username", width=280, height=42)
        self.login_user_entry.pack(pady=8)
        
        self.login_pass_entry = ctk.CTkEntry(form_container, placeholder_text="Security Password", show="*", width=280, height=42)
        self.login_pass_entry.pack(pady=8)
        
        # Toggle password visibility
        self.show_pass_var = tk.BooleanVar(value=False)
        self.cb_show_pass = ctk.CTkCheckBox(
            form_container, text="Reveal password", font=ctk.CTkFont(size=11), 
            variable=self.show_pass_var, command=self.toggle_password_view
        )
        self.cb_show_pass.pack(anchor="w", padx=52, pady=5)
        
        # Action button
        btn_login = ctk.CTkButton(
            form_container, text="Authenticate & Enter", font=ctk.CTkFont(family="Outfit", size=13, weight="bold"),
            fg_color="#3b82f6", hover_color="#2563eb", height=42, width=280,
            command=self.process_login
        )
        btn_login.pack(pady=(15, 10))
        
        # Error Label
        self.login_error_lbl = ctk.CTkLabel(form_container, text="", font=ctk.CTkFont(size=12), text_color="#ef4444")
        self.login_error_lbl.pack()
        
    def toggle_password_view(self):
        if self.show_pass_var.get():
            self.login_pass_entry.configure(show="")
        else:
            self.login_pass_entry.configure(show="*")
            
    def process_login(self):
        """Authenticates user credentials against the database using bcrypt."""
        username = self.login_user_entry.get().strip()
        password = self.login_pass_entry.get()
        
        if not username or not password:
            self.login_error_lbl.configure(text="❌ Fields cannot be empty.")
            return
            
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Query user
            cursor.execute("SELECT id, username, password_hash, role FROM users WHERE username = ?", (username,))
            user = cursor.fetchone()
            
            if user:
                # Check password with bcrypt
                pw_bytes = password.encode('utf-8')
                hash_bytes = user['password_hash'].encode('utf-8')
                
                if bcrypt.checkpw(pw_bytes, hash_bytes):
                    # Authentication Success
                    self.current_user = {
                        'id': user['id'],
                        'username': user['username'],
                        'role': user['role'].upper()
                    }
                    
                    # Destroy login frame and build main interface
                    self.login_frame.pack_forget()
                    self.login_frame.destroy()
                    
                    self.create_main_interface()
                    self.show_dashboard()
                else:
                    self.login_error_lbl.configure(text="❌ Invalid username or password.")
            else:
                self.login_error_lbl.configure(text="❌ Invalid username or password.")
                
        except Exception as e:
            self.login_error_lbl.configure(text=f"❌ Database error: {str(e)[:30]}")
        finally:
            conn.close()

    def process_logout(self):
        """Cleans up active session and returns to login screen."""
        if messagebox.askyesno("Log Out", "Are you sure you want to log out from the console?"):
            self.sidebar_frame.pack_forget()
            self.sidebar_frame.destroy()
            self.main_container.pack_forget()
            self.main_container.destroy()
            self.current_user = None
            
            self.show_login_screen()



    # ==========================================
    # MAIN LAYOUT INITIALIZATION
    # ==========================================
    def create_main_interface(self):
        """Creates the primary app frame, sidebar navigation, and headers."""
        # Setup modern grid column configurations
        self.grid_columnconfigure(0, weight=0) # Sidebar
        self.grid_columnconfigure(1, weight=1) # Main View
        self.grid_rowconfigure(0, weight=1)
        
        # --- SIDEBAR PANEL ---
        self.sidebar_frame = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color="#0d1321")
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(6, weight=1)
        
        # Brand title
        self.brand_label = ctk.CTkLabel(
            self.sidebar_frame, 
            text="AquaFlow POS", 
            font=ctk.CTkFont(family="Outfit", size=20, weight="bold")
        )
        self.brand_label.grid(row=0, column=0, padx=20, pady=(20, 4))
        
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
        
        self.btn_prices = ctk.CTkButton(
            self.sidebar_frame, text="Price Settings", anchor="w", command=self.show_prices
        )
        self.btn_prices.grid(row=7, column=0, padx=20, pady=5, sticky="ew")
        
        # Bottom controls: User profile & Logout
        self.btn_logout = ctk.CTkButton(
            self.sidebar_frame, text="🔓 Sign Out", anchor="w", 
            fg_color="transparent", text_color="#ef4444", border_width=1, border_color="#ef4444",
            hover_color="#271b1d", command=self.process_logout
        )
        self.btn_logout.grid(row=8, column=0, padx=20, pady=15, sticky="ew")
        
        # --- MAIN VIEW CONTAINER ---
        self.main_container = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_container.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(0, weight=1)
        
        # Setup views dict
        self.views = {}
        self.create_dashboard_view()
        self.create_pos_view()
        self.create_monitor_view()
        self.create_history_view()
        self.create_ai_view()
        self.create_prices_view()
        

        
    def select_sidebar_button(self, active_button):
        buttons = [self.btn_dashboard, self.btn_pos, self.btn_monitor, self.btn_history, self.btn_ai, self.btn_prices]
        for btn in buttons:
            if btn == active_button:
                btn.configure(fg_color="#3b82f6", text_color="white")
            else:
                btn.configure(fg_color="transparent", text_color="#cbd5e1")
                
    def show_view(self, name):
        for view_name, view_frame in self.views.items():
            if view_name == name:
                view_frame.grid(row=0, column=0, sticky="nsew")
            else:
                view_frame.grid_forget()

    # ==========================================
    # NAVIGATION HANDLERS (SYNCHRONOUS WITH CURSOR LOADER)
    # ==========================================
    def show_dashboard(self):
        self.select_sidebar_button(self.btn_dashboard)
        self.configure(cursor="watch")
        self.update_idletasks()
        
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # Today's Revenue
            today_str = datetime.now().strftime('%Y-%m-%d')
            cursor.execute(
                "SELECT SUM(total_amount) FROM orders WHERE status IN ('completed', 'confirmed') AND DATE(order_date) = DATE(?)",
                (today_str,)
            )
            todays_rev = cursor.fetchone()[0] or 0.0
            
            # Pending Web Orders count
            cursor.execute("SELECT COUNT(*) FROM orders WHERE status = 'pending'")
            pending_count = cursor.fetchone()[0]
            
            # Stock levels & low warnings
            cursor.execute("SELECT id, name, stock_quantity FROM products")
            products = cursor.fetchall()
            
            # Recent registered transactions
            cursor.execute("""
                SELECT o.id, c.full_name, o.total_amount, o.status, o.order_date
                FROM orders o
                JOIN customers c ON o.customer_id = c.id
                ORDER BY o.order_date DESC
                LIMIT 6
            """)
            recent_txs = cursor.fetchall()
            conn.close()
            
            # Live Weather forecast
            weather = get_weather_forecast()
            
            # Update UI
            self.kpi_rev_val.configure(text=f"₱{todays_rev:,.2f}")
            self.kpi_orders_val.configure(text=str(pending_count))
            
            # Update Weather panel
            self.dash_weather_temp.configure(text=f"{weather['current_temp']}°C")
            self.dash_weather_desc.configure(text=weather['current_condition'])
            
            if weather['current_temp'] >= 32.5:
                self.dash_weather_tips.configure(
                    text="⚠️ Heatwave condition: AI predicts a spike in drinking water demand. Keep inventory topped up!",
                    text_color="#ffa726"
                )
            else:
                self.dash_weather_tips.configure(
                    text="ℹ️ Normal temperatures. Customer refills are proceeding on standard schedules.",
                    text_color="gray"
                )
                
            # Update stock meters & warnings
            low_stock = 0
            for p in products:
                qty = p['stock_quantity']
                if qty < 50:
                    low_stock += 1
                if 'Round' in p['name']:
                    self.dash_stock_round_lbl.configure(text=f"Round Blue: {qty}/500 units")
                    prog = max(0.0, min(float(qty) / 500.0, 1.0))
                    self.dash_stock_round_progress.set(prog)
                    self.dash_stock_round_progress.configure(
                        progress_color="#ef4444" if prog < 0.15 else ("#f59e0b" if prog < 0.4 else "#06b6d4")
                    )
                else:
                    self.dash_stock_slim_lbl.configure(text=f"Slim Blue: {qty}/300 units")
                    prog = max(0.0, min(float(qty) / 300.0, 1.0))
                    self.dash_stock_slim_progress.set(prog)
                    self.dash_stock_slim_progress.configure(
                        progress_color="#ef4444" if prog < 0.15 else ("#f59e0b" if prog < 0.4 else "#3b82f6")
                    )
                    
            if low_stock > 0:
                self.kpi_stock_val.configure(text=f"{low_stock} WARNINGS", text_color="#ef4444")
            else:
                self.kpi_stock_val.configure(text="HEALTHY", text_color="#10b981")
                
            # Populate recent transactions tree
            for item in self.dash_tree.get_children():
                self.dash_tree.delete(item)
            for tx in recent_txs:
                try:
                    dt = datetime.fromisoformat(tx['order_date'].replace('Z', '+00:00'))
                    dt_str = dt.strftime('%b %d, %H:%M')
                except ValueError:
                    dt_str = tx['order_date'][:16]
                self.dash_tree.insert(
                    "", "end", 
                    values=(f"#{tx['id']}", tx['full_name'], f"₱{tx['total_amount']:.2f}", tx['status'].capitalize(), dt_str)
                )
                
            self.show_view("dashboard")
        except Exception as e:
            messagebox.showerror("Dashboard Error", f"Failed to load dashboard data: {e}")
        finally:
            self.configure(cursor="")

    def show_pos(self):
        self.select_sidebar_button(self.btn_pos)
        self.configure(cursor="watch")
        self.update_idletasks()
        
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id, full_name FROM customers WHERE is_active = 1")
            data = cursor.fetchall()
            conn.close()
            
            self.pos_customers_data = {}
            dropdown_vals = []
            for r in data:
                name = r['full_name']
                self.pos_customers_data[name] = r['id']
                dropdown_vals.append(name)
                
            self.pos_customer_dropdown.configure(values=dropdown_vals)
            if dropdown_vals:
                self.pos_customer_dropdown.set(dropdown_vals[0])
                self.on_pos_customer_change(dropdown_vals[0])
            else:
                self.reset_pos_fields()
            
            self.show_view("pos")
        except Exception as e:
            messagebox.showerror("POS Error", f"Failed to sync customer profiles: {e}")
        finally:
            self.configure(cursor="")

    def on_pos_customer_change(self, customer_name):
        if not customer_name:
            self.pos_active_price_round = 25.0
            self.pos_active_price_slim = 30.0
            return
            
        customer_id = self.pos_customers_data.get(customer_name)
        if not customer_id:
            self.pos_active_price_round = 25.0
            self.pos_active_price_slim = 30.0
            return
            
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT custom_price_round, custom_price_slim FROM customers WHERE id = ?", (customer_id,))
            row = cursor.fetchone()
            conn.close()
            
            p_round = row['custom_price_round'] if (row and row['custom_price_round'] is not None) else 25.0
            p_slim = row['custom_price_slim'] if (row and row['custom_price_slim'] is not None) else 30.0
            
            self.pos_active_price_round = p_round
            self.pos_active_price_slim = p_slim
            
            r_custom = " [Custom]" if (row and row['custom_price_round'] is not None) else ""
            s_custom = " [Custom]" if (row and row['custom_price_slim'] is not None) else ""
            self.prod1_name.configure(text=f"5-Gallon Round Blue Container Refill (₱{p_round:.2f}){r_custom}")
            self.prod2_name.configure(text=f"5-Gallon Slim Blue Container Refill (₱{p_slim:.2f}){s_custom}")
            
            self.recalculate_pos_total()
        except Exception as e:
            print("Failed to fetch customer custom rates:", e)

    def show_monitor(self):
        self.select_sidebar_button(self.btn_monitor)
        self.configure(cursor="watch")
        self.update_idletasks()
        
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT o.id, c.full_name, o.total_amount, o.status
                FROM orders o
                JOIN customers c ON o.customer_id = c.id
                WHERE o.status IN ('pending', 'confirmed')
                ORDER BY o.id DESC
            """)
            data = cursor.fetchall()
            conn.close()
            
            for item in self.mon_tree.get_children():
                self.mon_tree.delete(item)
            for r in data:
                self.mon_tree.insert(
                    "", "end", 
                    values=(f"#{r['id']}", r['full_name'], f"₱{r['total_amount']:.2f}", r['status'].upper())
                )
            self.selected_mon_order_id = None
            self.mon_details_text.configure(state="normal")
            self.mon_details_text.delete("1.0", "end")
            self.mon_details_text.insert("1.0", "Select a web order from the list to display details...")
            self.mon_details_text.configure(state="disabled")
            self.disable_monitor_actions()
            
            self.show_view("monitor")
        except Exception as e:
            messagebox.showerror("Monitor Error", f"Failed to poll web order queue: {e}")
        finally:
            self.configure(cursor="")

    def show_history(self):
        self.select_sidebar_button(self.btn_history)
        self.configure(cursor="watch")
        self.update_idletasks()
        try:
            self.refresh_history_data()
            self.show_view("history")
        finally:
            self.configure(cursor="")

    def show_ai(self):
        self.select_sidebar_button(self.btn_ai)
        self.configure(cursor="watch")
        self.update_idletasks()
        
        try:
            # Run customer refill interval cycles
            refills = predict_customer_refills(self.db_path)
            # Train model and run 7-day water demand forecasting
            forecasts = forecast_water_demand(self.db_path)
            
            # Populate refills tree
            for item in self.refill_tree.get_children():
                self.refill_tree.delete(item)
            for r in refills:
                self.refill_tree.insert(
                    "", "end",
                    values=(r['name'], r['last_order_date'], r['predicted_refill_date'], f"{r['avg_interval']} days", r['status'])
                )
            # Plot regression demand curve
            self.draw_forecast_chart(forecasts)
            
            self.show_view("ai")
        except Exception as e:
            messagebox.showerror("AI Error", f"Failed to calculate AI predictions: {e}")
        finally:
            self.configure(cursor="")

    def show_prices(self):
        self.select_sidebar_button(self.btn_prices)
        self.configure(cursor="watch")
        self.update_idletasks()
        
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id, full_name, custom_price_round, custom_price_slim FROM customers WHERE is_active = 1")
            customers = cursor.fetchall()
            conn.close()
            
            # Clear old elements
            for child in self.prices_list_frame.winfo_children():
                child.destroy()
                
            for c in customers:
                c_id = c['id']
                c_name = c['full_name']
                c_round = c['custom_price_round']
                c_slim = c['custom_price_slim']
                
                # Card item
                card = ctk.CTkFrame(self.prices_list_frame, fg_color="#1a2233", border_width=1, border_color="#2b3a55", height=110)
                card.pack(fill="x", pady=10, padx=5)
                
                # Customer name label
                lbl_name = ctk.CTkLabel(card, text=c_name, font=ctk.CTkFont(family="Outfit", size=14, weight="bold"))
                lbl_name.pack(side="left", padx=20, pady=20)
                
                # Input controls container (Pack to the right)
                input_frame = ctk.CTkFrame(card, fg_color="transparent")
                input_frame.pack(side="right", padx=20, pady=15)
                
                # Round pricing input
                r_lbl = ctk.CTkLabel(input_frame, text="Round (₱):", font=ctk.CTkFont(size=11))
                r_lbl.pack(side="left", padx=(10, 2))
                entry_round = ctk.CTkEntry(input_frame, width=70, placeholder_text="25.00")
                if c_round is not None:
                    entry_round.insert(0, f"{c_round:.2f}")
                entry_round.pack(side="left", padx=5)
                
                # Slim pricing input
                s_lbl = ctk.CTkLabel(input_frame, text="Slim (₱):", font=ctk.CTkFont(size=11))
                s_lbl.pack(side="left", padx=(15, 2))
                entry_slim = ctk.CTkEntry(input_frame, width=70, placeholder_text="30.00")
                if c_slim is not None:
                    entry_slim.insert(0, f"{c_slim:.2f}")
                entry_slim.pack(side="left", padx=5)
                
                btn_save = ctk.CTkButton(
                    input_frame, text="Save Rates", width=90, fg_color="#10b981", hover_color="#059669",
                    font=ctk.CTkFont(family="Outfit", weight="bold"),
                    command=lambda cid=c_id, er=entry_round, es=entry_slim: self.update_customer_price_rates(cid, er, es)
                )
                btn_save.pack(side="left", padx=(15, 5))
                
            self.show_view("prices")
        except Exception as e:
            messagebox.showerror("Pricing Error", f"Failed to load customers: {e}")
        finally:
            self.configure(cursor="")
            
    def update_customer_price_rates(self, customer_id, entry_round, entry_slim):
        r_val = entry_round.get().strip()
        s_val = entry_slim.get().strip()
        
        try:
            new_round = float(r_val) if r_val else None
            if new_round is not None and not (20.0 <= new_round <= 30.0):
                messagebox.showwarning("Pricing Control", "Round container price must be between ₱20.00 and ₱30.00.")
                return
        except ValueError:
            messagebox.showwarning("Pricing Control", "Please enter a valid round price decimal number.")
            return
            
        try:
            new_slim = float(s_val) if s_val else None
            if new_slim is not None and not (20.0 <= new_slim <= 30.0):
                messagebox.showwarning("Pricing Control", "Slim container price must be between ₱20.00 and ₱30.00.")
                return
        except ValueError:
            messagebox.showwarning("Pricing Control", "Please enter a valid slim price decimal number.")
            return
            
        conn = self.get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE customers SET custom_price_round = ?, custom_price_slim = ? WHERE id = ?", (new_round, new_slim, customer_id))
            conn.commit()
            messagebox.showinfo("Pricing Settings", "Customer custom prices updated successfully!")
            self.show_prices() # Refresh
        except Exception as e:
            conn.rollback()
            messagebox.showerror("Database Error", f"Failed to save customer prices: {e}")
        finally:
            conn.close()

    def create_dashboard_view(self):
        view = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.views["dashboard"] = view
        
        header = ctk.CTkLabel(view, text="Operator Command Dashboard", font=ctk.CTkFont(family="Outfit", size=22, weight="bold"))
        header.pack(anchor="w", pady=(0, 20))
        
        # KPI Frame Container
        kpi_frame = ctk.CTkFrame(view, fg_color="transparent")
        kpi_frame.pack(fill="x", pady=(0, 20))
        
        # Revenue Card
        self.kpi_rev = ctk.CTkFrame(kpi_frame, width=220, height=100, fg_color="#131c2e", border_width=1, border_color="#1e293b")
        self.kpi_rev.pack(side="left", expand=True, fill="both", padx=5)
        self.kpi_rev_lbl = ctk.CTkLabel(self.kpi_rev, text="TODAY'S REVENUE", font=ctk.CTkFont(family="Outfit", size=10, weight="bold"), text_color="gray")
        self.kpi_rev_lbl.pack(anchor="w", padx=15, pady=(15, 0))
        self.kpi_rev_val = ctk.CTkLabel(self.kpi_rev, text="₱0.00", font=ctk.CTkFont(family="Outfit", size=24, weight="bold"), text_color="#10b981")
        self.kpi_rev_val.pack(anchor="w", padx=15, pady=(5, 15))
        
        # Pending Card
        self.kpi_orders = ctk.CTkFrame(kpi_frame, width=220, height=100, fg_color="#131c2e", border_width=1, border_color="#1e293b")
        self.kpi_orders.pack(side="left", expand=True, fill="both", padx=5)
        self.kpi_orders_lbl = ctk.CTkLabel(self.kpi_orders, text="PENDING WEB ORDERS", font=ctk.CTkFont(family="Outfit", size=10, weight="bold"), text_color="gray")
        self.kpi_orders_lbl.pack(anchor="w", padx=15, pady=(15, 0))
        self.kpi_orders_val = ctk.CTkLabel(self.kpi_orders, text="0", font=ctk.CTkFont(family="Outfit", size=24, weight="bold"), text_color="#3b82f6")
        self.kpi_orders_val.pack(anchor="w", padx=15, pady=(5, 15))
        
        # Stock Status Card
        self.kpi_stock = ctk.CTkFrame(kpi_frame, width=220, height=100, fg_color="#131c2e", border_width=1, border_color="#1e293b")
        self.kpi_stock.pack(side="left", expand=True, fill="both", padx=5)
        self.kpi_stock_lbl = ctk.CTkLabel(self.kpi_stock, text="LOW INVENTORY ALERTS", font=ctk.CTkFont(family="Outfit", size=10, weight="bold"), text_color="gray")
        self.kpi_stock_lbl.pack(anchor="w", padx=15, pady=(15, 0))
        self.kpi_stock_val = ctk.CTkLabel(self.kpi_stock, text="HEALTHY", font=ctk.CTkFont(family="Outfit", size=24, weight="bold"), text_color="#10b981")
        self.kpi_stock_val.pack(anchor="w", padx=15, pady=(5, 15))
        
        split_frame = ctk.CTkFrame(view, fg_color="transparent")
        split_frame.pack(fill="both", expand=True)
        
        # Weather & Stock levels box (Left)
        weather_box = ctk.CTkFrame(split_frame, width=300, fg_color="#131c2e", border_width=1, border_color="#1e293b")
        weather_box.pack(side="left", fill="both", expand=False, padx=(0, 10))
        
        w_lbl = ctk.CTkLabel(weather_box, text="LIVE WEATHER (MEYCAUAYAN)", font=ctk.CTkFont(family="Outfit", size=11, weight="bold"), text_color="gray")
        w_lbl.pack(anchor="w", padx=15, pady=(15, 10))
        
        self.dash_weather_temp = ctk.CTkLabel(weather_box, text="--°C", font=ctk.CTkFont(family="Outfit", size=36, weight="bold"))
        self.dash_weather_temp.pack(anchor="w", padx=15, pady=5)
        
        self.dash_weather_desc = ctk.CTkLabel(weather_box, text="Fetching...", font=ctk.CTkFont(family="Plus Jakarta Sans", size=14, weight="bold"), text_color="gray")
        self.dash_weather_desc.pack(anchor="w", padx=15, pady=5)
        
        self.dash_weather_tips = ctk.CTkLabel(
            weather_box, text="AI is loading weather features...", 
            font=ctk.CTkFont(size=10), text_color="gray", wraplength=200, justify="left"
        )
        self.dash_weather_tips.pack(anchor="w", padx=15, pady=(10, 15))
        
        # Stock Progress Bars
        stock_header = ctk.CTkLabel(weather_box, text="CURRENT STOCK LEVELS", font=ctk.CTkFont(family="Outfit", size=11, weight="bold"), text_color="gray")
        stock_header.pack(anchor="w", padx=15, pady=(15, 5))
        
        self.dash_stock_round_lbl = ctk.CTkLabel(weather_box, text="Round Blue: --/500 units", font=ctk.CTkFont(size=11, weight="bold"))
        self.dash_stock_round_lbl.pack(anchor="w", padx=15, pady=(5, 2))
        self.dash_stock_round_progress = ctk.CTkProgressBar(weather_box, width=260, height=8)
        self.dash_stock_round_progress.pack(anchor="w", padx=15, pady=(0, 10))
        
        self.dash_stock_slim_lbl = ctk.CTkLabel(weather_box, text="Slim Blue: --/300 units", font=ctk.CTkFont(size=11, weight="bold"))
        self.dash_stock_slim_lbl.pack(anchor="w", padx=15, pady=(5, 2))
        self.dash_stock_slim_progress = ctk.CTkProgressBar(weather_box, width=260, height=8)
        self.dash_stock_slim_progress.pack(anchor="w", padx=15, pady=(0, 15))
        
        # Recent Completed Transactions (Right)
        sales_box = ctk.CTkFrame(split_frame, fg_color="#131c2e", border_width=1, border_color="#1e293b")
        sales_box.pack(side="right", fill="both", expand=True, padx=(10, 0))
        
        sales_lbl = ctk.CTkLabel(sales_box, text="RECENT REGISTERED TRANSACTIONS", font=ctk.CTkFont(family="Outfit", size=11, weight="bold"), text_color="gray")
        sales_lbl.pack(anchor="w", padx=15, pady=(15, 10))
        
        self.dash_tree = self.create_custom_tree(
            sales_box, 
            ["Order #", "Recipient", "Total Cost", "Order Status", "Date"],
            [60, 150, 100, 100, 150]
        )
        self.dash_tree.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        
    def create_pos_view(self):
        view = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.views["pos"] = view
        
        view.grid_columnconfigure(0, weight=2)
        view.grid_columnconfigure(1, weight=1)
        
        # Inputs Panel
        left_panel = ctk.CTkFrame(view, fg_color="#131c2e", border_width=1, border_color="#1e293b")
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=10)
        
        lbl_pos_title = ctk.CTkLabel(left_panel, text="New Sales Transaction", font=ctk.CTkFont(family="Outfit", size=18, weight="bold"))
        lbl_pos_title.pack(anchor="w", padx=20, pady=20)
        
        ct_lbl = ctk.CTkLabel(left_panel, text="Select Customer Profile:", font=ctk.CTkFont(family="Outfit", size=11, weight="bold"), text_color="gray")
        ct_lbl.pack(anchor="w", padx=20, pady=(0, 5))
        
        self.pos_customer_dropdown = ctk.CTkComboBox(left_panel, width=350, state="readonly", command=self.on_pos_customer_change)
        self.pos_customer_dropdown.pack(anchor="w", padx=20, pady=(0, 20))
        
        # Round container quantity row
        prod1_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        prod1_frame.pack(fill="x", padx=20, pady=10)
        self.prod1_name = ctk.CTkLabel(prod1_frame, text="5-Gallon Round Blue Container Refill (₱25.00)", font=ctk.CTkFont(size=13, weight="bold"))
        self.prod1_name.pack(side="left")
        self.prod1_qty = self.create_qty_picker(prod1_frame, "qty1")
        
        # Slim container quantity row
        prod2_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        prod2_frame.pack(fill="x", padx=20, pady=10)
        self.prod2_name = ctk.CTkLabel(prod2_frame, text="5-Gallon Slim Blue Container Refill (₱30.00)", font=ctk.CTkFont(size=13, weight="bold"))
        self.prod2_name.pack(side="left")
        self.prod2_qty = self.create_qty_picker(prod2_frame, "qty2")
        
        notes_lbl = ctk.CTkLabel(left_panel, text="Optional Sales Notes / Driver Info:", font=ctk.CTkFont(family="Outfit", size=11, weight="bold"), text_color="gray")
        notes_lbl.pack(anchor="w", padx=20, pady=(15, 5))
        self.pos_notes = ctk.CTkTextbox(left_panel, height=80, width=400)
        self.pos_notes.pack(anchor="w", padx=20, pady=(0, 20))
        
        # Checkout Frame (Right)
        right_panel = ctk.CTkFrame(view, fg_color="#131c2e", border_width=1, border_color="#1e293b")
        right_panel.grid(row=0, column=1, sticky="nsew", padx=(10, 0), pady=10)
        
        lbl_summary_title = ctk.CTkLabel(right_panel, text="Checkout Summary", font=ctk.CTkFont(family="Outfit", size=18, weight="bold"))
        lbl_summary_title.pack(anchor="w", padx=20, pady=20)
        
        total_frame = ctk.CTkFrame(right_panel, fg_color="#1a2233", border_width=1, border_color="#2b3a55")
        total_frame.pack(fill="x", padx=20, pady=10)
        
        t_lbl = ctk.CTkLabel(total_frame, text="TOTAL AMOUNT DUE", font=ctk.CTkFont(family="Outfit", size=10, weight="bold"), text_color="gray")
        t_lbl.pack(anchor="w", padx=15, pady=(15, 0))
        self.pos_total_label = ctk.CTkLabel(total_frame, text="₱0.00", font=ctk.CTkFont(family="Outfit", size=30, weight="bold"), text_color="#3b82f6")
        self.pos_total_label.pack(anchor="w", padx=15, pady=(5, 15))
        
        drv_lbl = ctk.CTkLabel(right_panel, text="Delivery / Walk-in Mode:", font=ctk.CTkFont(family="Outfit", size=11, weight="bold"), text_color="gray")
        drv_lbl.pack(anchor="w", padx=20, pady=(10, 5))
        self.pos_delivery_mode = ctk.CTkComboBox(
            right_panel, 
            values=["Over-the-Counter (Walk-in)", "Delivery: Carlos", "Delivery: Miguel", "Delivery: Ramon"],
            state="readonly"
        )
        self.pos_delivery_mode.set("Over-the-Counter (Walk-in)")
        self.pos_delivery_mode.pack(fill="x", padx=20, pady=(0, 20))
        
        self.btn_checkout = ctk.CTkButton(
            right_panel, text="Process POS Sale", fg_color="#10b981", hover_color="#059669", height=45,
            font=ctk.CTkFont(family="Outfit", weight="bold"), command=self.process_pos_checkout
        )
        self.btn_checkout.pack(fill="x", padx=20, pady=10)
        
        self.btn_reset_pos = ctk.CTkButton(
            right_panel, text="Clear Form", fg_color="transparent", border_width=1, border_color="gray",
            command=self.reset_pos_fields
        )
        self.btn_reset_pos.pack(fill="x", padx=20, pady=5)
        
    def create_qty_picker(self, parent, tag):
        picker_frame = ctk.CTkFrame(parent, fg_color="transparent")
        picker_frame.pack(side="right")
        
        btn_minus = ctk.CTkButton(
            picker_frame, text="-", width=30, height=28, 
            fg_color="#334155", text_color="white",
            command=lambda: self.adjust_pos_qty(tag, -1)
        )
        btn_minus.pack(side="left")
        
        lbl_qty = ctk.CTkLabel(picker_frame, text="0", font=ctk.CTkFont(weight="bold"), width=40)
        lbl_qty.pack(side="left", padx=5)
        
        btn_plus = ctk.CTkButton(
            picker_frame, text="+", width=30, height=28, 
            fg_color="#334155", text_color="white",
            command=lambda: self.adjust_pos_qty(tag, 1)
        )
        btn_plus.pack(side="left")
        
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
        p_round = getattr(self, 'pos_active_price_round', 25.0)
        p_slim = getattr(self, 'pos_active_price_slim', 30.0)
        total = (qty1 * p_round) + (qty2 * p_slim)
        self.pos_total_label.configure(text=f"₱{total:,.2f}")
        
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
        p_round = getattr(self, 'pos_active_price_round', 25.0)
        p_slim = getattr(self, 'pos_active_price_slim', 30.0)
        total = (qty1 * p_round) + (qty2 * p_slim)
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
                    "INSERT INTO order_items (order_id, product_id, quantity, unit_price, subtotal) VALUES (?, ?, ?, ?, ?)",
                    (order_id, p1_id, qty1, p_round, qty1 * p_round)
                )
                cursor.execute("UPDATE products SET stock_quantity = stock_quantity - ? WHERE id = ?", (qty1, p1_id))
                
            if qty2 > 0:
                cursor.execute(
                    "INSERT INTO order_items (order_id, product_id, quantity, unit_price, subtotal) VALUES (?, ?, ?, ?, ?)",
                    (order_id, p2_id, qty2, p_slim, qty2 * p_slim)
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

    def create_monitor_view(self):
        view = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.views["monitor"] = view
        
        view.grid_columnconfigure(0, weight=1)
        view.grid_rowconfigure(1, weight=1)
        
        header_frame = ctk.CTkFrame(view, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        
        lbl_mon = ctk.CTkLabel(header_frame, text="Incoming Web Order Monitor", font=ctk.CTkFont(family="Outfit", size=18, weight="bold"))
        lbl_mon.pack(side="left")
        
        btn_refresh_mon = ctk.CTkButton(header_frame, text="🔄 Reload Queue", width=120, command=self.show_monitor)
        btn_refresh_mon.pack(side="right")
        
        monitor_main = ctk.CTkFrame(view, fg_color="transparent")
        monitor_main.grid(row=1, column=0, sticky="nsew", pady=10)
        monitor_main.grid_columnconfigure(0, weight=1)
        monitor_main.grid_columnconfigure(1, weight=1)
        monitor_main.grid_rowconfigure(0, weight=1)
        
        # Order list (Left)
        list_box = ctk.CTkFrame(monitor_main, fg_color="#131c2e", border_width=1, border_color="#1e293b")
        list_box.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
        
        self.mon_tree = self.create_custom_tree(
            list_box, 
            ["Order #", "Customer", "Amount", "Status"],
            [60, 150, 100, 100]
        )
        self.mon_tree.pack(fill="both", expand=True)
        self.mon_tree.bind("<<TreeviewSelect>>", self.on_monitor_order_select)
        
        # Details Pane (Right)
        self.details_panel = ctk.CTkFrame(monitor_main, fg_color="#131c2e", border_width=1, border_color="#1e293b")
        self.details_panel.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)
        
        self.lbl_details_title = ctk.CTkLabel(self.details_panel, text="Order details", font=ctk.CTkFont(family="Outfit", size=15, weight="bold"))
        self.lbl_details_title.pack(anchor="w", padx=20, pady=15)
        
        self.mon_details_text = ctk.CTkTextbox(self.details_panel, height=250, font=ctk.CTkFont(family="Consolas", size=12))
        self.mon_details_text.pack(fill="x", padx=20, pady=5)
        self.mon_details_text.configure(state="disabled")
        
        drv_lbl = ctk.CTkLabel(self.details_panel, text="Assign Driver (for Delivery):", font=ctk.CTkFont(family="Outfit", size=11, weight="bold"), text_color="gray")
        drv_lbl.pack(anchor="w", padx=20, pady=(15, 2))
        self.mon_driver_combobox = ctk.CTkComboBox(self.details_panel, values=["Carlos", "Miguel", "Ramon"], state="readonly")
        self.mon_driver_combobox.pack(fill="x", padx=20, pady=(2, 15))
        self.mon_driver_combobox.set("Carlos")
        
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
        
    def on_monitor_order_select(self, event):
        selected_items = self.mon_tree.selection()
        if not selected_items: return
        
        item_vals = self.mon_tree.item(selected_items[0])['values']
        order_id = int(str(item_vals[0]).replace('#', ''))
        self.selected_mon_order_id = order_id
        
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT o.id, c.full_name, c.phone, c.address, o.total_amount, o.status, o.order_date, o.notes, d.status as delivery_status, d.driver_name
            FROM orders o
            JOIN customers c ON o.customer_id = c.id
            LEFT JOIN deliveries d ON o.id = d.order_id
            WHERE o.id = ?
        """, (order_id,))
        order = cursor.fetchone()
        
        cursor.execute("""
            SELECT p.name, oi.quantity, oi.unit_price, oi.subtotal
            FROM order_items oi
            JOIN products p ON oi.product_id = p.id
            WHERE oi.order_id = ?
        """, (order_id,))
        items = cursor.fetchall()
        
        conn.close()
        
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
            now_str = datetime.now().isoformat()
            cursor.execute("UPDATE orders SET status = 'confirmed', updated_at = ? WHERE id = ?", (now_str, self.selected_mon_order_id))
            cursor.execute("UPDATE deliveries SET status = 'pending', updated_at = ? WHERE order_id = ?", (now_str, self.selected_mon_order_id))
            conn.commit()
            messagebox.showinfo("Order Monitor", f"Order #{self.selected_mon_order_id} confirmed!")
            self.show_monitor()
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
            cursor.execute("SELECT product_id, quantity FROM order_items WHERE order_id = ?", (self.selected_mon_order_id,))
            items = cursor.fetchall()
            for item in items:
                cursor.execute("SELECT stock_quantity, name FROM products WHERE id = ?", (item['product_id'],))
                prod = cursor.fetchone()
                if prod['stock_quantity'] < item['quantity']:
                    messagebox.showerror("Inventory Error", f"Insufficient stock for {prod['name']}.")
                    conn.close()
                    return
            now_str = datetime.now().isoformat()
            for item in items:
                cursor.execute("UPDATE products SET stock_quantity = stock_quantity - ? WHERE id = ?", (item['quantity'], item['product_id']))
            cursor.execute("UPDATE deliveries SET status = 'in_transit', driver_name = ?, updated_at = ? WHERE order_id = ?", (driver, now_str, self.selected_mon_order_id))
            conn.commit()
            messagebox.showinfo("Order Monitor", f"Order #{self.selected_mon_order_id} dispatched with Driver {driver}!")
            self.show_monitor()
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
            cursor.execute("UPDATE orders SET status = 'completed', updated_at = ? WHERE id = ?", (now_str, self.selected_mon_order_id))
            cursor.execute("UPDATE deliveries SET status = 'delivered', delivery_date = ?, updated_at = ? WHERE order_id = ?", (now_str, now_str, self.selected_mon_order_id))
            conn.commit()
            messagebox.showinfo("Order Monitor", f"Order #{self.selected_mon_order_id} marked as delivered!")
            self.show_monitor()
        except Exception as e:
            conn.rollback()
            messagebox.showerror("Error", f"Failed to complete order: {e}")
        finally:
            conn.close()

    def create_history_view(self):
        view = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.views["history"] = view
        
        view.grid_columnconfigure(0, weight=1)
        view.grid_rowconfigure(1, weight=1)
        view.grid_rowconfigure(2, weight=0)
        
        toolbar = ctk.CTkFrame(view, fg_color="#131c2e", border_width=1, border_color="#1e293b")
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        
        lbl_search = ctk.CTkLabel(toolbar, text="Search Customer Name:", font=ctk.CTkFont(family="Outfit", size=11, weight="bold"))
        lbl_search.pack(side="left", padx=15, pady=10)
        
        self.hist_search_entry = ctk.CTkEntry(toolbar, width=180, placeholder_text="Enter name...")
        self.hist_search_entry.pack(side="left", padx=5, pady=10)
        self.hist_search_entry.bind("<KeyRelease>", lambda e: self.refresh_history_data())
        
        lbl_status = ctk.CTkLabel(toolbar, text="Status Filter:", font=ctk.CTkFont(family="Outfit", size=11, weight="bold"))
        lbl_status.pack(side="left", padx=15, pady=10)
        
        self.hist_status_filter = ctk.CTkComboBox(
            toolbar, width=120, values=["ALL", "Completed", "Confirmed", "Pending", "Cancelled"], state="readonly",
            command=lambda v: self.refresh_history_data()
        )
        self.hist_status_filter.pack(side="left", padx=5, pady=10)
        self.hist_status_filter.set("ALL")
        
        table_container = ctk.CTkFrame(view, fg_color="#131c2e", border_width=1, border_color="#1e293b")
        table_container.grid(row=1, column=0, sticky="nsew", pady=10)
        
        self.hist_tree = self.create_custom_tree(
            table_container,
            ["Order ID", "Customer Name", "Total cost", "Status", "Order Date", "Notes"],
            [80, 180, 100, 100, 150, 300]
        )
        self.hist_tree.pack(fill="both", expand=True)
        
        # Report generator toolbar card
        report_panel = ctk.CTkFrame(view, fg_color="#131c2e", border_width=1, border_color="#1e293b")
        report_panel.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        
        lbl_rep_title = ctk.CTkLabel(report_panel, text="Financial Report Console:", font=ctk.CTkFont(family="Outfit", size=12, weight="bold"))
        lbl_rep_title.pack(side="left", padx=20, pady=15)
        
        lbl_rep_range = ctk.CTkLabel(report_panel, text="Range:", font=ctk.CTkFont(size=11))
        lbl_rep_range.pack(side="left", padx=(10, 5), pady=15)
        
        self.report_range_filter = ctk.CTkComboBox(
            report_panel, width=130, values=["All Time", "Today", "Yesterday", "Last 7 Days", "Last 30 Days", "This Month", "This Year"], state="readonly"
        )
        self.report_range_filter.pack(side="left", padx=5, pady=15)
        self.report_range_filter.set("Last 30 Days")
        
        btn_csv = ctk.CTkButton(
            report_panel, text="Export CSV Spreadsheet", width=170, fg_color="#3b82f6", hover_color="#2563eb",
            font=ctk.CTkFont(family="Outfit", weight="bold"),
            command=lambda: self.export_sales_report("csv")
        )
        btn_csv.pack(side="left", padx=15, pady=15)
        
        btn_html = ctk.CTkButton(
            report_panel, text="Print HTML Report (PDF)", width=170, fg_color="#10b981", hover_color="#059669",
            font=ctk.CTkFont(family="Outfit", weight="bold"),
            command=lambda: self.export_sales_report("html")
        )
        btn_html.pack(side="left", padx=5, pady=15)
        
    def refresh_history_data(self):
        # Transaction history loader run on main thread since it responds to live key entry events (fast query)
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
                values=(f"#{r['id']}", r['full_name'], f"₱{r['total_amount']:.2f}", r['status'].capitalize(), dt_str, r['notes'] or '')
            )
        conn.close()

    def export_sales_report(self, format_type):
        from datetime import timedelta
        import csv
        import webbrowser
        
        # Fetch data
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT o.id, c.full_name, o.total_amount, o.status, o.order_date, o.notes
                FROM orders o
                JOIN customers c ON o.customer_id = c.id
                ORDER BY o.order_date DESC
            """)
            orders = cursor.fetchall()
            
            cursor.execute("""
                SELECT oi.order_id, p.name, oi.quantity, oi.unit_price, oi.subtotal
                FROM order_items oi
                JOIN products p ON oi.product_id = p.id
            """)
            order_items = cursor.fetchall()
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to retrieve transaction records:\n{e}")
            conn.close()
            return
        finally:
            conn.close()
            
        # Group order items
        items_by_order = {}
        for item in order_items:
            oid = item['order_id']
            if oid not in items_by_order:
                items_by_order[oid] = []
            items_by_order[oid].append(item)
            
        # Filter ranges
        range_val = self.report_range_filter.get()
        now = datetime.now()
        filtered_records = []
        
        for o in orders:
            try:
                dt_str = o['order_date'].replace('Z', '+00:00')
                dt = datetime.fromisoformat(dt_str)
            except ValueError:
                try:
                    dt = datetime.strptime(o['order_date'][:19], '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    try:
                        dt = datetime.strptime(o['order_date'][:10], '%Y-%m-%d')
                    except ValueError:
                        continue
            
            is_match = False
            if range_val == "All Time":
                is_match = True
            elif range_val == "Today":
                is_match = dt.date() == now.date()
            elif range_val == "Yesterday":
                is_match = dt.date() == (now - timedelta(days=1)).date()
            elif range_val == "Last 7 Days":
                is_match = dt.date() >= (now - timedelta(days=7)).date()
            elif range_val == "Last 30 Days":
                is_match = dt.date() >= (now - timedelta(days=30)).date()
            elif range_val == "This Month":
                is_match = dt.year == now.year and dt.month == now.month
            elif range_val == "This Year":
                is_match = dt.year == now.year
                
            if is_match:
                filtered_records.append((o, dt))
                
        if not filtered_records:
            messagebox.showinfo("Export Console", f"No transaction records found for the range: '{range_val}'.")
            return
            
        # Calculate stats
        total_revenue = 0.0
        total_orders = len(filtered_records)
        completed = 0
        confirmed = 0
        pending = 0
        cancelled = 0
        round_sold = 0
        slim_sold = 0
        
        for o, dt in filtered_records:
            status = o['status'].lower()
            if status == 'completed':
                completed += 1
                total_revenue += o['total_amount']
            elif status == 'confirmed':
                confirmed += 1
                total_revenue += o['total_amount']
            elif status == 'pending':
                pending += 1
            elif status == 'cancelled':
                cancelled += 1
                
            oid = o['id']
            if oid in items_by_order:
                for item in items_by_order[oid]:
                    pname = item['name']
                    qty = item['quantity']
                    if 'Round' in pname:
                        round_sold += qty
                    elif 'Slim' in pname:
                        slim_sold += qty
                        
        avg_value = total_revenue / (completed + confirmed) if (completed + confirmed) > 0 else 0.0
        
        # Create directory
        os.makedirs("exports", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename_base = f"sales_report_{range_val.lower().replace(' ', '_')}_{timestamp}"
        
        if format_type == "csv":
            filepath = os.path.join("exports", f"{filename_base}.csv")
            try:
                with open(filepath, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(["AquaFlow Mineral Water Station - Financial Sales Report"])
                    writer.writerow(["Report Filter Range", range_val])
                    writer.writerow(["Generated At", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
                    writer.writerow([])
                    writer.writerow(["METRICS SUMMARY"])
                    writer.writerow(["Total Realized Revenue", f"PHP {total_revenue:.2f}"])
                    writer.writerow(["Total Order Entries Count", total_orders])
                    writer.writerow(["Completed Refills", completed])
                    writer.writerow(["Confirmed Refills", confirmed])
                    writer.writerow(["Pending Refills", pending])
                    writer.writerow(["Cancelled Refills", cancelled])
                    writer.writerow(["Average Ticket Size (Completed/Confirmed)", f"PHP {avg_value:.2f}"])
                    writer.writerow(["Round Refills Sold (Units)", round_sold])
                    writer.writerow(["Slim Refills Sold (Units)", slim_sold])
                    writer.writerow([])
                    writer.writerow(["DETAILED TRANSACTION LOGS"])
                    writer.writerow(["Order ID", "Customer Name", "Order Date", "Status", "Total Amount", "Notes", "Round Refills (Qty)", "Slim Refills (Qty)"])
                    
                    for o, dt in filtered_records:
                        oid = o['id']
                        r_qty, s_qty = 0, 0
                        if oid in items_by_order:
                            for item in items_by_order[oid]:
                                if 'Round' in item['name']:
                                    r_qty = item['quantity']
                                elif 'Slim' in item['name']:
                                    s_qty = item['quantity']
                        writer.writerow([
                            f"#{oid}",
                            o['full_name'],
                            dt.strftime("%Y-%m-%d %H:%M"),
                            o['status'].upper(),
                            f"{o['total_amount']:.2f}",
                            o['notes'] or "",
                            r_qty,
                            s_qty
                        ])
                messagebox.showinfo("Export Successful", f"Spreadsheet CSV report saved successfully to:\n\n{os.path.abspath(filepath)}")
            except Exception as e:
                messagebox.showerror("Export Failure", f"Failed to write CSV file:\n{e}")
                
        elif format_type == "html":
            filepath = os.path.join("exports", f"{filename_base}.html")
            
            table_rows_html = ""
            for o, dt in filtered_records:
                oid = o['id']
                r_qty, s_qty = 0, 0
                if oid in items_by_order:
                    for item in items_by_order[oid]:
                        if 'Round' in item['name']:
                            r_qty = item['quantity']
                        elif 'Slim' in item['name']:
                            s_qty = item['quantity']
                table_rows_html += f"""
                <tr>
                    <td><strong>#{oid}</strong></td>
                    <td>{o['full_name']}</td>
                    <td>{dt.strftime('%b %d, %Y %H:%M')}</td>
                    <td><span class="status-badge status-{o['status'].lower()}">{o['status'].upper()}</span></td>
                    <td class="text-right"><strong>₱{o['total_amount']:.2f}</strong></td>
                    <td>{r_qty} / {s_qty}</td>
                    <td><span class="notes-text">{o['notes'] or '-'}</span></td>
                </tr>
                """
                
            html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AquaFlow Sales Report - {range_val}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700;800&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-color: #030712;
            --bg-card: rgba(17, 24, 39, 0.7);
            --border-color: #1e293b;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --accent-blue: #06b6d4;
            --accent-green: #10b981;
            --accent-red: #ef4444;
            --accent-orange: #f59e0b;
        }}
        
        body {{
            background-color: var(--bg-color);
            color: var(--text-primary);
            font-family: 'Plus Jakarta Sans', sans-serif;
            margin: 0;
            padding: 3rem 2rem;
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 1000px;
            margin: 0 auto;
        }}
        
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 2rem;
            margin-bottom: 2.5rem;
        }}
        
        .brand {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        
        .brand-icon {{
            color: var(--accent-blue);
            font-size: 2.5rem;
            font-weight: 800;
        }}
        
        .brand-text {{
            font-family: 'Outfit', sans-serif;
            font-size: 1.8rem;
            font-weight: 800;
            letter-spacing: -0.5px;
        }}
        
        .report-meta {{
            text-align: right;
        }}
        
        .report-title {{
            font-family: 'Outfit', sans-serif;
            font-size: 1.4rem;
            font-weight: 700;
            margin: 0 0 6px 0;
            color: var(--accent-blue);
            text-transform: uppercase;
        }}
        
        .report-subtitle {{
            font-size: 0.85rem;
            color: var(--text-secondary);
            margin: 0;
        }}
        
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 1.5rem;
            margin-bottom: 3rem;
        }}
        
        .metric-card {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 1.5rem;
            text-align: center;
        }}
        
        .metric-label {{
            font-size: 0.75rem;
            font-weight: 700;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
        }}
        
        .metric-value {{
            font-family: 'Outfit', sans-serif;
            font-size: 1.6rem;
            font-weight: 800;
            color: var(--text-primary);
        }}
        
        .metric-value.highlight {{
            color: var(--accent-green);
        }}
        
        h2 {{
            font-family: 'Outfit', sans-serif;
            font-size: 1.25rem;
            font-weight: 700;
            margin-bottom: 1.25rem;
            border-left: 4px solid var(--accent-blue);
            padding-left: 10px;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 3rem;
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            overflow: hidden;
        }}
        
        th {{
            background: rgba(255, 255, 255, 0.02);
            color: var(--text-primary);
            font-family: 'Outfit', sans-serif;
            font-size: 0.85rem;
            font-weight: 700;
            text-transform: uppercase;
            text-align: left;
            padding: 14px 18px;
            border-bottom: 1px solid var(--border-color);
        }}
        
        td {{
            padding: 14px 18px;
            font-size: 0.9rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.02);
            color: #cbd5e1;
        }}
        
        tr:hover td {{
            background: rgba(255, 255, 255, 0.01);
        }}
        
        .text-right {{
            text-align: right;
        }}
        
        .status-badge {{
            font-size: 0.72rem;
            font-weight: 800;
            padding: 4px 8px;
            border-radius: 4px;
            letter-spacing: 0.3px;
        }}
        
        .status-completed {{
            background: rgba(16, 185, 129, 0.1);
            color: var(--accent-green);
            border: 1px solid rgba(16, 185, 129, 0.2);
        }}
        
        .status-confirmed {{
            background: rgba(6, 182, 212, 0.1);
            color: var(--accent-blue);
            border: 1px solid rgba(6, 182, 212, 0.2);
        }}
        
        .status-pending {{
            background: rgba(245, 158, 11, 0.1);
            color: var(--accent-orange);
            border: 1px solid rgba(245, 158, 11, 0.2);
        }}
        
        .status-cancelled {{
            background: rgba(239, 68, 68, 0.1);
            color: var(--accent-red);
            border: 1px solid rgba(239, 68, 68, 0.2);
        }}
        
        .notes-text {{
            font-size: 0.82rem;
            color: var(--text-secondary);
            font-style: italic;
        }}
        
        .footer {{
            margin-top: 5rem;
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
            font-size: 0.85rem;
            color: var(--text-secondary);
        }}
        
        .signature-line {{
            width: 220px;
            border-top: 1px solid var(--text-secondary);
            margin-top: 3.5rem;
            text-align: center;
            padding-top: 8px;
        }}
        
        @media print {{
            body {{
                background-color: #fff;
                color: #000;
                padding: 0;
            }}
            :root {{
                --bg-color: #fff;
                --text-primary: #000;
                --text-secondary: #475569;
                --border-color: #cbd5e1;
                --bg-card: transparent;
            }}
            .metric-card {{
                border: 1px solid #94a3b8;
            }}
            table {{
                border: 1px solid #94a3b8;
            }}
            th {{
                border-bottom: 1px solid #94a3b8;
                color: #000;
            }}
            td {{
                color: #000;
                border-bottom: 1px solid #e2e8f0;
            }}
            .status-badge {{
                border: none;
                padding: 0;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="brand">
                <span class="brand-icon">💧</span>
                <div class="brand-text">AquaFlow Station</div>
            </div>
            <div class="report-meta">
                <h1 class="report-title">Financial Sales Report</h1>
                <p class="report-subtitle">Filter Range: <strong>{range_val}</strong></p>
                <p class="report-subtitle" style="font-size:0.75rem; margin-top:4px;">Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
            </div>
        </div>
        
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-label">Realized Revenue</div>
                <div class="metric-value highlight">₱{total_revenue:,.2f}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Refill Orders</div>
                <div class="metric-value">{total_orders}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Round Refills</div>
                <div class="metric-value">{round_sold} units</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Slim Refills</div>
                <div class="metric-value">{slim_sold} units</div>
            </div>
        </div>
        
        <h2>Detailed Transaction Logs</h2>
        <table>
            <thead>
                <tr>
                    <th>Order</th>
                    <th>Customer</th>
                    <th>Date</th>
                    <th>Status</th>
                    <th class="text-right">Amount</th>
                    <th>Refills (R/S)</th>
                    <th>Delivery Notes</th>
                </tr>
            </thead>
            <tbody>
                {table_rows_html}
            </tbody>
        </table>
        
        <div class="footer">
            <div>
                <p>Location: Bancal, Meycauayan, Bulacan</p>
                <p style="font-size:0.75rem; margin-top:4px;">Document generated securely via AquaFlow POS Engine.</p>
            </div>
            <div>
                <div class="signature-line">
                    Station Manager / Operator
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(html_content)
                messagebox.showinfo("Report Exported", f"HTML report page saved successfully to:\n\n{os.path.abspath(filepath)}\n\nOpening print dashboard in default web browser...")
                webbrowser.open(f"file:///{os.path.abspath(filepath)}")
            except Exception as e:
                messagebox.showerror("Export Failure", f"Failed to write HTML file:\n{e}")

    def create_ai_view(self):
        view = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.views["ai"] = view
        
        view.grid_columnconfigure(0, weight=1)
        view.grid_columnconfigure(1, weight=1)
        view.grid_rowconfigure(0, weight=1)
        
        # Predictions list (Left)
        refill_panel = ctk.CTkFrame(view, fg_color="#131c2e", border_width=1, border_color="#1e293b")
        refill_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=10)
        
        lbl_ai_c = ctk.CTkLabel(refill_panel, text="AI Customer Refill Scheduler", font=ctk.CTkFont(family="Outfit", size=16, weight="bold"))
        lbl_ai_c.pack(anchor="w", padx=15, pady=15)
        
        lbl_ai_c_desc = ctk.CTkLabel(
            refill_panel, text="Monitors ordering cycle intervals to predict when customer refills are due.",
            font=ctk.CTkFont(size=11), text_color="gray"
        )
        lbl_ai_c_desc.pack(anchor="w", padx=15, pady=(0, 10))
        
        self.refill_tree = self.create_custom_tree(
            refill_panel,
            ["Customer", "Last Refill", "Est. Refill", "Cycle (Days)", "Status"],
            [120, 90, 90, 80, 80]
        )
        self.refill_tree.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        self.refill_tree.bind("<<TreeviewSelect>>", self.on_refill_customer_select)
        
        # Forecast panel (Right)
        self.forecast_panel = ctk.CTkFrame(view, fg_color="#131c2e", border_width=1, border_color="#1e293b")
        self.forecast_panel.grid(row=0, column=1, sticky="nsew", padx=(10, 0), pady=10)
        
        lbl_ai_f = ctk.CTkLabel(self.forecast_panel, text="7-Day Weather-Integrated Demand Forecast", font=ctk.CTkFont(family="Outfit", size=16, weight="bold"))
        lbl_ai_f.pack(anchor="w", padx=15, pady=15)
        
        self.forecast_canvas_frame = ctk.CTkFrame(self.forecast_panel, fg_color="transparent")
        self.forecast_canvas_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        
    def create_prices_view(self):
        view = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.views["prices"] = view
        
        # Header
        header = ctk.CTkLabel(view, text="Pricing Settings Manager", font=ctk.CTkFont(family="Outfit", size=22, weight="bold"))
        header.pack(anchor="w", pady=(0, 10))
        
        # Description
        desc = ctk.CTkLabel(
            view, 
            text="Modify container refill rates for individual customers. Prices must be configured within the bounds of ₱20.00 to ₱30.00.",
            font=ctk.CTkFont(size=12),
            text_color="gray",
            justify="left"
        )
        desc.pack(anchor="w", pady=(0, 20))
        
        # Prices Container Panel
        self.prices_list_frame = ctk.CTkScrollableFrame(view, fg_color="#131c2e", border_width=1, border_color="#1e293b", width=600, height=350)
        self.prices_list_frame.pack(anchor="w", fill="both", expand=True, pady=10)
        
    def draw_forecast_chart(self, forecasts):
        for child in self.forecast_canvas_frame.winfo_children():
            child.destroy()
        if not forecasts:
            lbl_err = ctk.CTkLabel(self.forecast_canvas_frame, text="Not enough historical data to generate forecast graph.")
            lbl_err.pack()
            return
            
        dates = [f["date"][-5:] for f in forecasts]
        demands = [f["predicted_demand"] for f in forecasts]
        temps = [f["max_temp"] for f in forecasts]
        
        # Create styled matplotlib plot
        fig = Figure(figsize=(5, 4), dpi=100, facecolor="#131c2e")
        ax1 = fig.add_subplot(111)
        ax1.set_facecolor("#131c2e")
        
        ax1.spines['top'].set_visible(False)
        ax1.spines['right'].set_visible(False)
        ax1.spines['left'].set_color('#cbd5e1')
        ax1.spines['bottom'].set_color('#cbd5e1')
        
        line1 = ax1.plot(dates, demands, color='#06b6d4', marker='o', linewidth=2.5, label='Gallons Demand')
        ax1.set_ylabel('Forecast Demand (Containers)', color='#06b6d4', fontweight='bold')
        ax1.tick_params(axis='y', labelcolor='#06b6d4', colors='#cbd5e1')
        ax1.tick_params(axis='x', colors='#cbd5e1')
        
        ax2 = ax1.twinx()
        ax2.spines['top'].set_visible(False)
        ax2.spines['left'].set_visible(False)
        ax2.spines['right'].set_color('#ef4444')
        ax2.spines['bottom'].set_color('#cbd5e1')
        
        line2 = ax2.plot(dates, temps, color='#ef4444', marker='x', linestyle='--', linewidth=1.5, label='Max Temp (°C)')
        ax2.set_ylabel('Max Temp (°C)', color='#ef4444', fontweight='bold')
        ax2.tick_params(axis='y', labelcolor='#ef4444', colors='#cbd5e1')
        
        ax1.grid(True, color='#ffffff', alpha=0.05, linestyle=':')
        
        lines = line1 + line2
        labels = [l.get_label() for l in lines]
        ax1.legend(lines, labels, loc='upper left', facecolor='#131c2e', edgecolor='none', labelcolor='white')
        fig.tight_layout()
        
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
            reply = messagebox.askyesno(
                "AI Dispatch Suggestion", 
                f"Customer {name} is flagged as '{status}' (Next refill date: {vals[2]}).\n\n"
                f"Would you like to initiate a new POS Sales order for this customer?"
            )
            if reply:
                self.show_pos()
                self.pos_customer_dropdown.set(name)

    def create_custom_tree(self, parent, columns, widths):
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
        
        tree = ttk.Treeview(parent, columns=columns, show="headings", selectmode="browse")
        for i, col in enumerate(columns):
            tree.heading(col, text=col)
            tree.column(col, width=widths[i], anchor="w")
        return tree

if __name__ == "__main__":
    app = WaterStationApp()
    app.mainloop()
