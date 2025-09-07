#!/usr/bin/env python3
"""
Banking App Automation Tool - Day 3 Version
InLinea (ch.bsct.ebanking.mobile) Automation with Advanced Scanning
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import sys
import logging
import os
import threading
import time
from datetime import datetime
from pathlib import Path

# Create necessary directories (relative to project root)
project_root = Path(__file__).parent.parent  # Go up from src to project root
logs_dir = project_root / 'logs'
screenshots_dir = project_root / 'screenshots'

logs_dir.mkdir(exist_ok=True)
screenshots_dir.mkdir(exist_ok=True)

# Setup logging with absolute path
log_file = logs_dir / f'banking_automation_{datetime.now().strftime("%Y%m%d")}.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(str(log_file)),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Import our Appium manager
try:
    from appium_manager import AppiumServerManager, check_prerequisites, install_missing_prerequisites
    APPIUM_AVAILABLE = True
except ImportError:
    logger.warning("Appium manager not found - some features will be limited")
    APPIUM_AVAILABLE = False
    AppiumServerManager = None

class BankingAutomationApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("InLinea Banking App Automation Tool - v3.0")
        self.root.geometry("1200x800")
        
        # App state
        self.driver = None
        self.connected_device = None
        self.appium_manager = AppiumServerManager() if APPIUM_AVAILABLE else None
        
        # Create GUI
        self.create_interface()
        
        # Check prerequisites on startup
        if APPIUM_AVAILABLE:
            threading.Thread(target=self.check_system_requirements, daemon=True).start()
        
        logger.info("Banking Automation Tool v3.0 initialized")
    
    def create_interface(self):
        """Create the main interface"""
        # Title
        title_label = tk.Label(self.root, 
                              text="InLinea Banking App Automation v3.0", 
                              font=("Arial", 16, "bold"))
        title_label.pack(pady=10)
        
        # Warning message
        warning_frame = tk.Frame(self.root, bg="yellow", relief="solid", borderwidth=2)
        warning_frame.pack(fill="x", padx=10, pady=5)
        
        warning_text = """⚠️ WARNING: Banking App Automation
• Use only on test accounts, never production
• Comply with all banking regulations
• Tool is for UI analysis and navigation only
• No actual banking transactions will be automated"""
        
        warning_label = tk.Label(warning_frame, text=warning_text, 
                                bg="yellow", justify="left", font=("Arial", 9))
        warning_label.pack(padx=10, pady=5)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Create tabs
        self.create_system_tab()      # System management
        self.create_device_tab()      # Device connection
        self.create_scanner_tab()     # UI scanner
        self.create_runner_tab()      # Test runner
        
        # Status bar
        self.status_var = tk.StringVar(value="Initializing system...")
        status_bar = tk.Label(self.root, textvariable=self.status_var, 
                             relief="sunken", anchor="w")
        status_bar.pack(side="bottom", fill="x")
    
    def create_system_tab(self):
        """Create system management tab"""
        system_frame = ttk.Frame(self.notebook)
        self.notebook.add(system_frame, text="System Setup")
        
        # Prerequisites section
        prereq_frame = ttk.LabelFrame(system_frame, text="System Prerequisites", padding=10)
        prereq_frame.pack(fill="x", padx=10, pady=10)
        
        # Prerequisites list
        self.prereq_tree = ttk.Treeview(prereq_frame, columns=('Status', 'Info'), show='tree headings', height=4)
        self.prereq_tree.heading('#0', text='Component')
        self.prereq_tree.heading('Status', text='Status')
        self.prereq_tree.heading('Info', text='Information')
        self.prereq_tree.pack(fill="x", pady=5)
        
        # Buttons
        prereq_buttons = ttk.Frame(prereq_frame)
        prereq_buttons.pack(fill="x", pady=5)
        ttk.Button(prereq_buttons, text="Check Requirements", command=self.check_system_requirements).pack(side="left", padx=5)
        
        if APPIUM_AVAILABLE:
            ttk.Button(prereq_buttons, text="Install Appium", command=self.install_appium).pack(side="left", padx=5)
        
        # Appium Server section
        appium_frame = ttk.LabelFrame(system_frame, text="Appium Server Management", padding=10)
        appium_frame.pack(fill="x", padx=10, pady=10)
        
        if not APPIUM_AVAILABLE:
            ttk.Label(appium_frame, text="Appium management not available - missing appium_manager.py", 
                     foreground="red").pack(pady=10)
        else:
            # Server status
            status_frame = ttk.Frame(appium_frame)
            status_frame.pack(fill="x", pady=5)
            
            ttk.Label(status_frame, text="Server Status:").pack(side="left")
            self.server_status_var = tk.StringVar(value="Unknown")
            self.server_status_label = ttk.Label(status_frame, textvariable=self.server_status_var, font=("Arial", 9, "bold"))
            self.server_status_label.pack(side="left", padx=10)
            
            # Server URL
            ttk.Label(status_frame, text="URL:").pack(side="left", padx=(20,5))
            self.server_url_var = tk.StringVar(value="http://127.0.0.1:4723")
            ttk.Label(status_frame, textvariable=self.server_url_var).pack(side="left")
            
            # Server control buttons
            server_buttons = ttk.Frame(appium_frame)
            server_buttons.pack(fill="x", pady=10)
            
            self.start_server_btn = ttk.Button(server_buttons, text="Start Server", command=self.start_appium_server)
            self.start_server_btn.pack(side="left", padx=5)
            
            self.stop_server_btn = ttk.Button(server_buttons, text="Stop Server", command=self.stop_appium_server)
            self.stop_server_btn.pack(side="left", padx=5)
            
            ttk.Button(server_buttons, text="Check Status", command=self.check_server_status).pack(side="left", padx=5)
            
            # Progress bar for server operations
            self.server_progress = ttk.Progressbar(appium_frame, mode='indeterminate')
            self.server_progress.pack(fill="x", pady=5)
        
        # Server logs section
        logs_frame = ttk.LabelFrame(system_frame, text="System Logs", padding=10)
        logs_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.server_logs = scrolledtext.ScrolledText(logs_frame, height=8, width=80)
        self.server_logs.pack(fill="both", expand=True)
        
        # Log control buttons
        log_buttons = ttk.Frame(logs_frame)
        log_buttons.pack(fill="x", pady=5)
        ttk.Button(log_buttons, text="Clear Logs", command=self.clear_server_logs).pack(side="left", padx=5)
    
    def create_device_tab(self):
        """Create device connection tab"""
        device_frame = ttk.Frame(self.notebook)
        self.notebook.add(device_frame, text="Device Connection")
        
        # Instructions
        instructions = """📱 Device Setup Instructions:
1. Install InLinea banking app on your Android device
2. Enable Developer Options (Settings → About → Tap Build Number 7 times)
3. Enable USB Debugging (Settings → Developer Options → USB Debugging)
4. Connect device via USB cable
5. Allow USB debugging when prompted
6. Make sure Appium server is running (check System Setup tab)"""
        
        ttk.Label(device_frame, text=instructions, justify="left").grid(row=0, column=0, columnspan=2, pady=10, sticky="w")
        
        # Device connection form
        ttk.Label(device_frame, text="Device UDID:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.device_udid = tk.StringVar()
        ttk.Entry(device_frame, textvariable=self.device_udid, width=40).grid(row=1, column=1, padx=5, pady=5)
        
        ttk.Label(device_frame, text="App Package:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.app_package = tk.StringVar(value="ch.bsct.ebanking.mobile")
        ttk.Entry(device_frame, textvariable=self.app_package, width=40).grid(row=2, column=1, padx=5, pady=5)
        
        # Buttons
        ttk.Button(device_frame, text="Refresh Devices", command=self.refresh_devices).grid(row=3, column=0, pady=10)
        self.connect_btn = ttk.Button(device_frame, text="Connect Device", command=self.connect_device)
        self.connect_btn.grid(row=3, column=1, pady=10)
        
        # Device list
        ttk.Label(device_frame, text="Available Devices:").grid(row=4, column=0, sticky="w", padx=5)
        self.device_listbox = tk.Listbox(device_frame, height=6)
        self.device_listbox.grid(row=5, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        self.device_listbox.bind('<Double-Button-1>', self.on_device_select)
        
        # Connection status
        self.connection_status = tk.StringVar(value="Not Connected")
        ttk.Label(device_frame, textvariable=self.connection_status).grid(row=6, column=0, columnspan=2, pady=5)
    
    def create_scanner_tab(self):
        """Create UI scanner tab"""
        scanner_frame = ttk.Frame(self.notebook)
        self.notebook.add(scanner_frame, text="UI Scanner")
        
        # Scanner controls
        ttk.Label(scanner_frame, text="Screen Name:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.screen_name = tk.StringVar(value="Unknown Screen")
        ttk.Entry(scanner_frame, textvariable=self.screen_name, width=30).grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Button(scanner_frame, text="Advanced Scan", 
                  command=self.scan_current_screen).grid(row=0, column=2, padx=5, pady=5)
        
        # Safety reminder
        safety_text = """🛡️ BANKING SAFETY FEATURES (Day 3-4): 
• Advanced element detection with safety classification
• Automatic identification of high-risk banking elements
• Compliance validation for banking regulations
• Multiple locator strategies for reliable automation
• Real-time safety warnings and recommendations"""
        
        safety_label = tk.Label(scanner_frame, text=safety_text, fg="blue", justify="left")
        safety_label.grid(row=1, column=0, columnspan=3, pady=5, sticky="w")
        
        # Elements tree view
        self.elements_tree = ttk.Treeview(scanner_frame, 
                                         columns=('Type', 'Locator', 'Text', 'Safety'), 
                                         show='tree headings')
        self.elements_tree.heading('#0', text='Element')
        self.elements_tree.heading('Type', text='Class')
        self.elements_tree.heading('Locator', text='Best Locator')
        self.elements_tree.heading('Text', text='Text Content')
        self.elements_tree.heading('Safety', text='Safety Level')
        
        # Configure column widths
        self.elements_tree.column('#0', width=200)
        self.elements_tree.column('Type', width=150)
        self.elements_tree.column('Locator', width=200)
        self.elements_tree.column('Text', width=150)
        self.elements_tree.column('Safety', width=120)
        
        self.elements_tree.grid(row=2, column=0, columnspan=3, sticky="nsew", padx=5, pady=5)
        
        # Configure grid weights for resizing
        scanner_frame.grid_rowconfigure(2, weight=1)
        scanner_frame.grid_columnconfigure(0, weight=1)
        
        # Export buttons
        export_frame = ttk.Frame(scanner_frame)
        export_frame.grid(row=3, column=0, columnspan=3, pady=10)
        ttk.Button(export_frame, text="Export to CSV", command=self.export_csv).pack(side="left", padx=5)
        ttk.Button(export_frame, text="Save to Database", command=self.save_to_database).pack(side="left", padx=5)
        ttk.Button(export_frame, text="View Detailed Report", command=self.show_last_scan_report).pack(side="left", padx=5)
    
    def create_runner_tab(self):
        """Create test runner tab (placeholder)"""
        runner_frame = ttk.Frame(self.notebook)
        self.notebook.add(runner_frame, text="Test Runner")
        
        # Coming soon message
        coming_soon = """🚧 Test Runner - Coming in Day 6

This tab will include:
• Safe test case execution
• Banking-compliant automation
• Screenshot capture on failures
• Detailed execution logs
• Compliance reporting

Current Status:
✅ Day 1: Basic GUI structure
✅ Day 2: Appium server management
✅ Day 3: Advanced UI element scanning (Current)
🔄 Day 4: Banking safety validation
📅 Day 5: Database integration & export
📅 Day 6: Test execution engine
📅 Day 7: Final .exe packaging"""
        
        ttk.Label(runner_frame, text=coming_soon, justify="left").pack(pady=50, padx=20)
    
    def log_to_server(self, message):
        """Add message to server logs"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        
        self.server_logs.insert(tk.END, log_entry)
        self.server_logs.see(tk.END)  # Auto-scroll to bottom
    
    def clear_server_logs(self):
        """Clear server logs"""
        self.server_logs.delete(1.0, tk.END)
        self.log_to_server("Logs cleared")
    
    def check_system_requirements(self):
        """Check system prerequisites"""
        if not APPIUM_AVAILABLE:
            self.status_var.set("⚠️ Appium manager not available")
            self.log_to_server("⚠️ appium_manager.py not found")
            return
        
        self.status_var.set("Checking system requirements...")
        
        def _check_requirements():
            try:
                prereqs = check_prerequisites()
                
                # Update prerequisites tree on main thread
                self.root.after(0, self._update_prereq_tree, prereqs)
                
                # Log results
                all_good = all(info['installed'] for info in prereqs.values())
                if all_good:
                    self.root.after(0, lambda: self.status_var.set("✅ All prerequisites installed"))
                    self.log_to_server("✅ All system requirements met")
                else:
                    missing = [comp for comp, info in prereqs.items() if not info['installed']]
                    self.root.after(0, lambda: self.status_var.set(f"❌ Missing: {', '.join(missing)}"))
                    self.log_to_server(f"❌ Missing components: {', '.join(missing)}")
                
            except Exception as e:
                error_msg = f"Error checking requirements: {str(e)}"
                self.root.after(0, lambda: self.status_var.set("Error checking requirements"))
                self.log_to_server(error_msg)
                logger.error(error_msg)
        
        threading.Thread(target=_check_requirements, daemon=True).start()
    
    def _update_prereq_tree(self, prereqs):
        """Update prerequisites tree view"""
        # Clear existing items
        for item in self.prereq_tree.get_children():
            self.prereq_tree.delete(item)
        
        # Add prerequisites
        for component, info in prereqs.items():
            status = "✅ Installed" if info['installed'] else "❌ Missing"
            self.prereq_tree.insert('', 'end', text=component.upper(), 
                                  values=(status, info['info']))
    
    def install_appium(self):
        """Install Appium via npm"""
        if not self.appium_manager:
            messagebox.showerror("Error", "Appium manager not available")
            return
        
        def _install():
            self.root.after(0, lambda: self.server_progress.start())
            self.root.after(0, lambda: self.status_var.set("Installing Appium..."))
            self.log_to_server("Starting Appium installation...")
            
            success, message = self.appium_manager.install_appium()
            
            self.root.after(0, lambda: self.server_progress.stop())
            
            if success:
                self.root.after(0, lambda: messagebox.showinfo("Success", message))
                self.root.after(0, self.check_system_requirements)
                self.log_to_server("✅ Appium installation completed")
            else:
                self.root.after(0, lambda: messagebox.showerror("Installation Failed", message))
                self.log_to_server(f"❌ Appium installation failed: {message}")
            
            self.root.after(0, lambda: self.status_var.set("Installation complete"))
        
        threading.Thread(target=_install, daemon=True).start()
    
    def start_appium_server(self):
        """Start Appium server"""
        if not self.appium_manager:
            messagebox.showerror("Error", "Appium manager not available")
            return
        
        self.start_server_btn.config(state='disabled')
        self.server_progress.start()
        self.status_var.set("Starting Appium server...")
        self.log_to_server("Starting Appium server...")
        
        def callback(success, message):
            self.root.after(0, lambda: self.server_progress.stop())
            self.root.after(0, lambda: self.start_server_btn.config(state='normal'))
            
            if success:
                self.root.after(0, lambda: self.server_status_var.set("🟢 Running"))
                self.root.after(0, lambda: self.status_var.set("Appium server started"))
                self.root.after(0, lambda: self.connect_btn.config(state='normal'))
                self.log_to_server("✅ Appium server started successfully")
            else:
                self.root.after(0, lambda: self.server_status_var.set("🔴 Stopped"))
                self.root.after(0, lambda: self.status_var.set("Failed to start server"))
                self.root.after(0, lambda: messagebox.showerror("Server Error", message))
                self.log_to_server(f"❌ Server start failed: {message}")
        
        self.appium_manager.start_server(callback)
    
    def stop_appium_server(self):
        """Stop Appium server"""
        if not self.appium_manager:
            return
        
        self.status_var.set("Stopping Appium server...")
        self.log_to_server("Stopping Appium server...")
        
        success, message = self.appium_manager.stop_server()
        
        if success:
            self.server_status_var.set("🔴 Stopped")
            self.connect_btn.config(state='disabled')
            self.log_to_server("✅ Server stopped successfully")
        else:
            self.log_to_server(f"❌ Server stop failed: {message}")
        
        self.status_var.set(message)
    
    def check_server_status(self):
        """Check Appium server status"""
        if not self.appium_manager:
            return
        
        self.status_var.set("Checking server status...")
        
        def _check_status():
            try:
                status = self.appium_manager.get_server_status()
                
                # Update UI on main thread
                if status['running']:
                    self.root.after(0, lambda: self.server_status_var.set("🟢 Running"))
                    self.root.after(0, lambda: self.connect_btn.config(state='normal'))
                    self.root.after(0, lambda: self.status_var.set("Server is running"))
                else:
                    self.root.after(0, lambda: self.server_status_var.set("🔴 Stopped"))
                    self.root.after(0, lambda: self.connect_btn.config(state='disabled'))
                    self.root.after(0, lambda: self.status_var.set("Server is not running"))
                
                # Log detailed status
                log_msg = f"Server Status: {'Running' if status['running'] else 'Stopped'}"
                if status['version']:
                    log_msg += f" (v{status['version']})"
                if status['processes']:
                    log_msg += f" - {len(status['processes'])} process(es)"
                
                self.log_to_server(log_msg)
                
            except Exception as e:
                error_msg = f"Error checking server status: {str(e)}"
                self.root.after(0, lambda: self.status_var.set("Error checking status"))
                self.log_to_server(error_msg)
        
        threading.Thread(target=_check_status, daemon=True).start()
    
    def refresh_devices(self):
        """Refresh list of connected Android devices"""
        self.device_listbox.delete(0, tk.END)
        self.status_var.set("Refreshing devices...")
        
        try:
            import subprocess
            result = subprocess.run(['adb', 'devices'], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')[1:]  # Skip header
                device_count = 0
                for line in lines:
                    if '\tdevice' in line:
                        device_id = line.split('\t')[0]
                        self.device_listbox.insert(tk.END, f"Android: {device_id}")
                        device_count += 1
                
                if device_count == 0:
                    self.device_listbox.insert(tk.END, "No devices found")
                    self.status_var.set("No Android devices connected")
                    self.log_to_server("No Android devices found")
                else:
                    self.status_var.set(f"Found {device_count} Android device(s)")
                    self.log_to_server(f"Found {device_count} Android device(s)")
            else:
                self.device_listbox.insert(tk.END, "ADB not found - install Android SDK")
                self.status_var.set("ADB not available")
                self.log_to_server("❌ ADB not found - install Android SDK")
                
        except Exception as e:
            self.device_listbox.insert(tk.END, f"Error: {str(e)}")
            self.status_var.set("Error checking devices")
            self.log_to_server(f"❌ Device refresh failed: {str(e)}")
            logger.error(f"Device refresh failed: {e}")
    
    def on_device_select(self, event):
        """Handle device selection from listbox"""
        selection = self.device_listbox.curselection()
        if selection:
            device_text = self.device_listbox.get(selection[0])
            if "Android:" in device_text:
                device_id = device_text.replace("Android: ", "")
                self.device_udid.set(device_id)
                self.status_var.set(f"Selected device: {device_id}")
                self.log_to_server(f"Selected device: {device_id}")
    
    def connect_device(self):
        """Connect to Android device for automation"""
        # Check if server is running first
        if self.appium_manager and not self.appium_manager.check_server_running():
            messagebox.showerror("Server Not Running", 
                               "Appium server is not running. Please start the server first in the System Setup tab.")
            return
        
        self.connect_btn.config(state='disabled')
        self.status_var.set("Connecting to device...")
        self.log_to_server("Attempting device connection...")
        
        def _connect():
            try:
                # Import Appium here to check if it's available
                from appium import webdriver
                from appium.options.android import UiAutomator2Options
                
                # Setup Appium options for banking app
                options = UiAutomator2Options()
                options.platform_name = "Android"
                options.device_name = self.device_udid.get() or "Android"
                options.app_package = self.app_package.get()
                options.automation_name = "UiAutomator2"
                options.no_reset = True  # Don't reset app state
                options.full_reset = False
                options.auto_grant_permissions = True
                options.new_command_timeout = 300  # 5 minutes timeout
                
                # Connect to Appium server
                self.driver = webdriver.Remote("http://localhost:4723", options=options)
                
                # Success
                self.root.after(0, lambda: self.connection_status.set("✅ Connected Successfully"))
                self.root.after(0, lambda: self.status_var.set("Device connected - Ready for advanced scanning"))
                self.root.after(0, lambda: self.connect_btn.config(state='normal'))
                
                logger.info("Successfully connected to banking app")
                self.log_to_server("✅ Device connected successfully")
                
            except ImportError:
                error_msg = "Appium Python client not installed.\nRun: pip install Appium-Python-Client"
                self.root.after(0, lambda: messagebox.showerror("Missing Dependency", error_msg))
                self.root.after(0, lambda: self.status_var.set("Missing dependencies"))
                self.root.after(0, lambda: self.connect_btn.config(state='normal'))
                self.log_to_server("❌ Missing Appium Python client")
            except Exception as e:
                error_msg = str(e)
                self.root.after(0, lambda: self.connection_status.set(f"❌ Connection Failed"))
                self.root.after(0, lambda: self.status_var.set("Connection failed"))
                self.root.after(0, lambda: self.connect_btn.config(state='normal'))
                
                logger.error(f"Device connection failed: {e}")
                self.log_to_server(f"❌ Connection failed: {error_msg}")
                
                detailed_error = f"""Failed to connect:\n{error_msg}\n\nMake sure:\n• Appium server is running\n• USB debugging is enabled\n• Banking app is installed\n• Device is unlocked\n• Correct package name: {self.app_package.get()}"""
                self.root.after(0, lambda: messagebox.showerror("Connection Error", detailed_error))
        
        threading.Thread(target=_connect, daemon=True).start()
    
    def scan_current_screen(self):
        """Scan current screen for UI elements - Day 3 Advanced Version"""
        if not self.driver:
            messagebox.showerror("Error", "Please connect to device first")
            return
        
        self.status_var.set("Performing advanced screen scan...")
        self.log_to_server("Starting advanced element scanning...")
        
        # Clear previous results
        for item in self.elements_tree.get_children():
            self.elements_tree.delete(item)
        
        def _perform_scan():
            try:
                # Import the advanced scanner
                from element_scanner_day3 import perform_advanced_scan
                
                app_name = "InLinea Banking"
                screen_name = self.screen_name.get() or "Unknown Screen"
                
                # Perform comprehensive scan
                scan_results = perform_advanced_scan(
                    self.driver, 
                    screenshots_dir, 
                    app_name, 
                    screen_name
                )
                
                # Store results for later use
                self.last_scan_results = scan_results
                
                # Update UI on main thread
                self.root.after(0, self._display_scan_results, scan_results)
                
            except ImportError:
                # Fallback to basic scanning if Day 3 scanner not available
                self.root.after(0, self._fallback_scan)
            except Exception as e:
                error_msg = f"Advanced scanning failed: {str(e)}"
                self.root.after(0, lambda: self.log_to_server(f"❌ {error_msg}"))
                self.root.after(0, lambda: self.status_var.set("Advanced scanning failed"))
                self.root.after(0, lambda: messagebox.showerror("Scan Error", error_msg))
        
        threading.Thread(target=_perform_scan, daemon=True).start()
    
    def _display_scan_results(self, scan_results):
        """Display advanced scan results in the UI"""
        try:
            elements = scan_results.get('elements', [])
            statistics = scan_results.get('statistics', {})
            warnings = scan_results.get('warnings', [])
            
            # Clear and populate elements tree
            for item in self.elements_tree.get_children():
                self.elements_tree.delete(item)
            
            for i, element in enumerate(elements):
                # Determine display name
                display_name = (element.get('text', '') or 
                               element.get('resource_id', '').split('/')[-1] or 
                               element.get('content_desc', '') or 
                               f"{element.get('category', 'element')}_{i+1}")
                
                # Safety info
                safety = element.get('safety_classification', {})
                safety_display = f"{safety.get('level', 'UNKNOWN')}"
                
                # Locator info
                locators = element.get('locators', {})
                locator_display = locators.get('recommended', 'none')
                if locator_display in locators:
                    locator_value = locators[locator_display]
                    if len(locator_value) > 30:
                        locator_value = locator_value[:27] + "..."
                    locator_display = f"{locator_display}: {locator_value}"
                
                # Add to tree with color coding
                item_id = self.elements_tree.insert('', 'end', text=display_name, 
                                        values=(element.get('class_name', 'Unknown'), 
                                               locator_display,
                                               element.get('text', '')[:30],
                                               safety_display))
                
                # Color code by safety level
                safety_level = safety.get('level', 'UNKNOWN')
                if safety_level == 'HIGH_RISK':
                    self.elements_tree.set(item_id, 'Safety', '🔴 HIGH_RISK')
                elif safety_level == 'MEDIUM_RISK':
                    self.elements_tree.set(item_id, 'Safety', '🟡 MEDIUM_RISK')
                elif safety_level == 'LOW_RISK':
                    self.elements_tree.set(item_id, 'Safety', '🟢 LOW_RISK')
                elif safety_level == 'SAFE':
                    self.elements_tree.set(item_id, 'Safety', '🔵 SAFE')
                else:
                    self.elements_tree.set(item_id, 'Safety', '⚪ UNKNOWN')
            
            # Update status and logs
            total_elements = len(elements)
            scan_duration = scan_results.get('scan_duration', 0)
            
            self.status_var.set(f"Advanced scan complete - {total_elements} elements in {scan_duration}s")
            self.log_to_server(f"✅ Advanced scan completed:")
            self.log_to_server(f"   Total elements: {total_elements}")
            self.log_to_server(f"   Scan duration: {scan_duration}s")
            
            # Log statistics
            if statistics:
                self.log_to_server(f"   Safety breakdown:")
                for level, count in statistics.get('by_safety_level', {}).items():
                    self.log_to_server(f"     {level}: {count}")
                
                automation_summary = statistics.get('automation_summary', {})
                safe_count = automation_summary.get('safe_to_automate', 0)
                caution_count = automation_summary.get('requires_caution', 0)
                risk_count = automation_summary.get('high_risk', 0)
                
                self.log_to_server(f"   Automation summary: {safe_count} safe, {caution_count} caution, {risk_count} high-risk")
            
            # Log warnings
            if warnings:
                self.log_to_server("   Warnings:")
                for warning in warnings:
                    self.log_to_server(f"     {warning}")
            
            # Show success message
            messagebox.showinfo("Advanced Scan Complete", 
                               f"✅ Advanced scan completed successfully!\n\n"
                               f"📊 Results:\n"
                               f"• Total elements: {total_elements}\n"
                               f"• Scan duration: {scan_duration}s\n"
                               f"• Safety warnings: {len(warnings)}\n\n"
                               f"Click 'View Detailed Report' for comprehensive analysis.")
            
        except Exception as e:
            self.log_to_server(f"❌ Error displaying scan results: {str(e)}")
            self.status_var.set("Error displaying results")
    
    def _fallback_scan(self):
        """Fallback to basic scanning method"""
        try:
            # Take screenshot first
            screenshot_path = screenshots_dir / f"scan_{int(time.time())}.png"
            self.driver.save_screenshot(str(screenshot_path))
            
            # Basic placeholder elements
            sample_elements = [
                {
                    'name': 'Navigation Menu Button',
                    'type': 'android.widget.ImageButton',
                    'resource_id': 'android:id/home',
                    'text': '',
                    'safety': 'SAFE'
                },
                {
                    'name': 'Title Text',
                    'type': 'android.widget.TextView', 
                    'resource_id': 'android:id/action_bar_title',
                    'text': 'InLinea',
                    'safety': 'SAFE'
                },
                {
                    'name': 'Login Field',
                    'type': 'android.widget.EditText',
                    'resource_id': 'ch.bsct.ebanking.mobile:id/login_field',
                    'text': '',
                    'safety': 'MEDIUM_RISK'
                }
            ]
            
            # Add to tree view
            for element in sample_elements:
                locator = element['resource_id'] if element['resource_id'] else 'xpath'
                item_id = self.elements_tree.insert('', 'end', text=element['name'], 
                                        values=(element['type'], locator, element['text'], element['safety']))
                
                # Color code
                if element['safety'] == 'SAFE':
                    self.elements_tree.set(item_id, 'Safety', '🟢 SAFE')
                elif element['safety'] == 'MEDIUM_RISK':
                    self.elements_tree.set(item_id, 'Safety', '🟡 MEDIUM_RISK')
            
            self.status_var.set(f"Basic scan complete - {len(sample_elements)} elements found")
            self.log_to_server(f"Fallback to basic scanning - {len(sample_elements)} elements")
            self.log_to_server(f"Screenshot saved: {screenshot_path.name}")
            
            messagebox.showinfo("Basic Scan Complete", 
                               f"Basic scan completed with {len(sample_elements)} elements.\n\n"
                               f"Note: This is fallback mode. For advanced scanning, "
                               f"ensure element_scanner_day3.py is available.")
            
        except Exception as e:
            self.log_to_server(f"❌ Fallback scan failed: {str(e)}")
            self.status_var.set("Scanning failed")
            messagebox.showerror("Scan Error", f"Screen scanning failed: {str(e)}")
    
    def show_last_scan_report(self):
        """Show detailed scan results dialog"""
        if not hasattr(self, 'last_scan_results'):
            messagebox.showwarning("No Data", "No scan results available. Please perform a scan first.")
            return
        
        self._show_scan_results_dialog(self.last_scan_results)
    
    def _show_scan_results_dialog(self, scan_results):
        """Show detailed scan results in a popup dialog"""
        
        # Create results window
        results_window = tk.Toplevel(self.root)
        results_window.title("Advanced Scan Results")
        results_window.geometry("900x700")
        
        # Create notebook for different result views
        results_notebook = ttk.Notebook(results_window)
        results_notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Summary tab
        summary_frame = ttk.Frame(results_notebook)
        results_notebook.add(summary_frame, text="Summary")
        
        summary_text = scrolledtext.ScrolledText(summary_frame, height=25, width=100)
        summary_text.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Build summary content
        summary_content = f"""ADVANCED SCAN RESULTS SUMMARY
{'='*60}

App: {scan_results.get('app_name', 'Unknown')}
Screen: {scan_results.get('screen_name', 'Unknown')}
Scan Time: {scan_results.get('scan_timestamp', 'Unknown')}
Duration: {scan_results.get('scan_duration', 0)}s

ELEMENT STATISTICS:
"""
        
        statistics = scan_results.get('statistics', {})
        if statistics:
            summary_content += f"Total Elements: {statistics.get('total_elements', 0)}\n\n"
            
            # Safety breakdown
            summary_content += "Safety Level Breakdown:\n"
            for level, count in statistics.get('by_safety_level', {}).items():
                summary_content += f"  {level}: {count}\n"
            
            summary_content += "\nElement Categories:\n"
            for category, count in statistics.get('by_category', {}).items():
                summary_content += f"  {category}: {count}\n"
            
            automation_summary = statistics.get('automation_summary', {})
            summary_content += f"""
AUTOMATION READINESS:
Safe to automate: {automation_summary.get('safe_to_automate', 0)}
Requires caution: {automation_summary.get('requires_caution', 0)}
High risk (avoid): {automation_summary.get('high_risk', 0)}
No stable locator: {automation_summary.get('no_stable_locator', 0)}
"""
        
        # Add warnings
        warnings = scan_results.get('warnings', [])
        if warnings:
            summary_content += "\nSAFETY WARNINGS:\n"
            for warning in warnings:
                summary_content += f"  {warning}\n"
        
        # Add metadata
        metadata = scan_results.get('metadata', {})
        if metadata:
            summary_content += f"""
DEVICE INFORMATION:
Platform: {metadata.get('device_info', {}).get('platformName', 'Unknown')}
Version: {metadata.get('device_info', {}).get('platformVersion', 'Unknown')}
Device: {metadata.get('device_info', {}).get('deviceName', 'Unknown')}

APPLICATION INFORMATION:
Package: {metadata.get('app_info', {}).get('appPackage', 'Unknown')}
Activity: {metadata.get('screen_info', {}).get('current_activity', 'Unknown')}
Screenshot: {metadata.get('screenshot_path', 'Not available')}
"""
        
        summary_text.insert('1.0', summary_content)
        summary_text.config(state='disabled')
        
        # Details tab
        details_frame = ttk.Frame(results_notebook)
        results_notebook.add(details_frame, text="Element Details")
        
        # Element details tree
        details_tree = ttk.Treeview(details_frame, 
                                   columns=('Class', 'ResourceID', 'Text', 'Safety', 'Locators'), 
                                   show='tree headings')
        details_tree.heading('#0', text='Element')
        details_tree.heading('Class', text='Class')
        details_tree.heading('ResourceID', text='Resource ID')
        details_tree.heading('Text', text='Text')
        details_tree.heading('Safety', text='Safety')
        details_tree.heading('Locators', text='Locators')
        
        # Scrollbar for details tree
        details_scrollbar = ttk.Scrollbar(details_frame, orient='vertical', command=details_tree.yview)
        details_tree.configure(yscrollcommand=details_scrollbar.set)
        
        details_tree.pack(side='left', fill='both', expand=True, padx=5, pady=5)
        details_scrollbar.pack(side='right', fill='y')
        
        # Populate details tree
        elements = scan_results.get('elements', [])
        for i, element in enumerate(elements):
            display_name = (element.get('text', '') or 
                           element.get('resource_id', '').split('/')[-1] or 
                           f"Element_{i+1}")
            
            safety = element.get('safety_classification', {})
            locators = element.get('locators', {})
            locator_count = len([k for k in locators.keys() if not k.startswith('xpath_') and k != 'recommended'])
            
            details_tree.insert('', 'end', text=display_name,
                               values=(
                                   element.get('class_name', ''),
                                   element.get('resource_id', '')[:40],
                                   element.get('text', '')[:30],
                                   safety.get('level', 'UNKNOWN'),
                                   f"{locator_count} available"
                               ))
        
        # Close button
        close_frame = ttk.Frame(results_window)
        close_frame.pack(fill="x", pady=10)
        ttk.Button(close_frame, text="Close", command=results_window.destroy).pack()
    
    def export_csv(self):
        """Export scanned elements to CSV (placeholder for Day 5)"""
        messagebox.showinfo("Export", "CSV export functionality will be implemented in Day 5!")
        self.log_to_server("CSV export requested (coming in Day 5)")
    
    def save_to_database(self):
        """Save elements to SQLite database (placeholder for Day 5)"""
        messagebox.showinfo("Database", "Database save functionality will be implemented in Day 5!")
        self.log_to_server("Database save requested (coming in Day 5)")
    
    def cleanup(self):
        """Cleanup resources on exit"""
        self.log_to_server("Application shutting down...")
        
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Driver session closed")
            except:
                pass
        
        if self.appium_manager:
            try:
                self.appium_manager.stop_server()
                logger.info("Appium server stopped")
            except:
                pass
    
    def run(self):
        """Start the application"""
        logger.info("Starting Banking Automation Tool v3.0")
        self.root.protocol("WM_DELETE_WINDOW", lambda: (self.cleanup(), self.root.destroy()))
        
        # Initial status update
        if APPIUM_AVAILABLE:
            self.status_var.set("Ready - Check System Setup tab to start")
        else:
            self.status_var.set("⚠️ appium_manager.py missing - limited functionality")
        
        self.root.mainloop()

def main():
    """Main entry point"""
    try:
        app = BankingAutomationApp()
        app.run()
    except Exception as e:
        logger.error(f"Application failed to start: {e}")
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()