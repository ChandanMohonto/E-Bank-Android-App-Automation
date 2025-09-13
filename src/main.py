#!/usr/bin/env python3
"""
Complete InLinea Banking App Automation Tool - v9.0 UNRESTRICTED
All Features Including Custom Test Builder - NO SAFETY CHECKS
FOR TESTING PURPOSES ONLY
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import sys
import logging
import threading
import time
import json
import sqlite3
import csv
from datetime import datetime
from pathlib import Path
import subprocess
import os
import queue

# Create directories
project_root = Path(__file__).parent
logs_dir = project_root / 'logs'
screenshots_dir = project_root / 'screenshots' 
exports_dir = project_root / 'exports'
reports_dir = project_root / 'reports'
custom_tests_dir = project_root / 'custom_tests'
db_dir = project_root / 'database'

for directory in [logs_dir, screenshots_dir, exports_dir, reports_dir, custom_tests_dir, db_dir]:
    directory.mkdir(exist_ok=True)

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(logs_dir / f'banking_{datetime.now().strftime("%Y%m%d")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Database setup
DB_PATH = db_dir / 'banking_automation.db'

def init_database():
    """Initialize database with all required tables"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scan_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            app_name TEXT,
            screen_name TEXT,
            elements_count INTEGER,
            screenshot_path TEXT,
            scan_data TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS test_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            test_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            test_name TEXT,
            status TEXT,
            passed_steps INTEGER,
            failed_steps INTEGER,
            total_steps INTEGER,
            duration REAL,
            screenshot_paths TEXT,
            result_data TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS elements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_id INTEGER,
            element_type TEXT,
            resource_id TEXT,
            text TEXT,
            content_desc TEXT,
            clickable BOOLEAN,
            enabled BOOLEAN,
            password BOOLEAN,
            bounds TEXT,
            xpath TEXT,
            FOREIGN KEY (scan_id) REFERENCES scan_results(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS custom_tests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            test_name TEXT UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            steps TEXT,
            description TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

# Initialize database
init_database()

class CustomTestBuilder:
    """Helper class for building custom tests from scanned elements"""
    
    def __init__(self):
        self.test_steps = []
        self.scanned_elements = []
        
    def add_scanned_elements(self, elements):
        """Add scanned elements for test building"""
        self.scanned_elements = elements
        
    def add_step(self, action, element_info, data=None, description="", wait_time=5):
        """Add a test step"""
        step = {
            'action': action,
            'locator_strategy': element_info.get('locator_strategy', 'xpath'),
            'locator_value': element_info.get('locator_value', ''),
            'data': data,
            'description': description or f"{action} on {element_info.get('name', 'element')}",
            'wait_time': wait_time,
            'element_info': element_info
        }
        self.test_steps.append(step)
        return step
        
    def remove_step(self, index):
        """Remove a test step"""
        if 0 <= index < len(self.test_steps):
            del self.test_steps[index]
            
    def move_step_up(self, index):
        """Move step up in order"""
        if 0 < index < len(self.test_steps):
            self.test_steps[index], self.test_steps[index-1] = self.test_steps[index-1], self.test_steps[index]
            
    def move_step_down(self, index):
        """Move step down in order"""
        if 0 <= index < len(self.test_steps) - 1:
            self.test_steps[index], self.test_steps[index+1] = self.test_steps[index+1], self.test_steps[index]
            
    def clear_steps(self):
        """Clear all test steps"""
        self.test_steps = []
        
    def build_test_case(self, name="Custom Test"):
        """Build test case from steps"""
        return {
            'name': name,
            'description': f"Custom test created at {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            'stop_on_failure': False,
            'steps': self.test_steps.copy()
        }
        
    def save_test(self, filepath):
        """Save test to JSON file"""
        test_case = self.build_test_case()
        with open(filepath, 'w') as f:
            json.dump(test_case, f, indent=2)
            
    def load_test(self, filepath):
        """Load test from JSON file"""
        with open(filepath, 'r') as f:
            test_case = json.load(f)
            self.test_steps = test_case.get('steps', [])
            return test_case

class CompleteTestRunner:
    """Test runner that executes all types of tests without restrictions"""
    
    def __init__(self, driver, screenshots_dir):
        self.driver = driver
        self.screenshots_dir = Path(screenshots_dir)
        self.logger = logging.getLogger(__name__)
        
    def find_element_smart(self, locator_type, locator_value, timeout=10):
        """Smart element finding with multiple fallback strategies"""
        from appium.webdriver.common.appiumby import AppiumBy
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        
        element = None
        
        # Try primary locator
        try:
            if locator_type == 'id':
                element = WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((AppiumBy.ID, locator_value))
                )
            elif locator_type == 'xpath':
                element = WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((AppiumBy.XPATH, locator_value))
                )
            elif locator_type == 'accessibility_id':
                element = WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((AppiumBy.ACCESSIBILITY_ID, locator_value))
                )
            elif locator_type == 'class':
                element = WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((AppiumBy.CLASS_NAME, locator_value))
                )
        except:
            pass
        
        # Fallback strategies
        if not element:
            try:
                all_elements = self.driver.find_elements(AppiumBy.XPATH, "//*")
                for elem in all_elements:
                    try:
                        if locator_value in str(elem.get_attribute('resource-id') or ''):
                            element = elem
                            break
                        if locator_value in str(elem.get_attribute('text') or ''):
                            element = elem
                            break
                    except:
                        continue
            except:
                pass
        
        return element
    
    def execute_custom_test(self, test_case):
        """Execute a custom test case"""
        results = {
            'test_name': test_case.get('name', 'Custom Test'),
            'start_time': datetime.now(),
            'steps': [],
            'screenshots': [],
            'status': 'RUNNING'
        }
        
        try:
            steps = test_case.get('steps', [])
            
            for i, step in enumerate(steps, 1):
                self.logger.info(f"Executing step {i}: {step.get('description', '')}")
                
                step_result = self.execute_step(step)
                results['steps'].append(step_result)
                
                # Take screenshot after each step if needed
                if step.get('action') == 'screenshot' or step.get('take_screenshot'):
                    screenshot = self.take_screenshot(f"step_{i}")
                    results['screenshots'].append(screenshot)
                
                time.sleep(1)  # Small delay between steps
            
            # Determine overall status
            failed_count = sum(1 for s in results['steps'] if s['status'] == 'failed')
            if failed_count == 0:
                results['status'] = 'PASSED'
            elif failed_count < len(results['steps']):
                results['status'] = 'PARTIAL'
            else:
                results['status'] = 'FAILED'
            
        except Exception as e:
            self.logger.error(f"Custom test error: {e}")
            results['status'] = 'ERROR'
            results['error'] = str(e)
        
        results['end_time'] = datetime.now()
        results['duration'] = (results['end_time'] - results['start_time']).total_seconds()
        
        return results
    
    def execute_step(self, step):
        """Execute a single test step - NO RESTRICTIONS"""
        from appium.webdriver.common.appiumby import AppiumBy
        
        result = {
            'description': step.get('description', ''),
            'action': step.get('action'),
            'status': 'unknown',
            'message': ''
        }
        
        try:
            action = step.get('action')
            
            # Handle wait action
            if action == 'wait':
                time.sleep(step.get('data', 2))
                result['status'] = 'passed'
                result['message'] = f"Waited {step.get('data', 2)} seconds"
                return result
            
            # Handle screenshot
            if action == 'screenshot':
                screenshot = self.take_screenshot("custom")
                result['status'] = 'passed'
                result['message'] = f"Screenshot taken: {Path(screenshot).name}"
                return result
            
            # Handle swipe
            if action == 'swipe':
                direction = step.get('data', 'up')
                self.perform_swipe(direction)
                result['status'] = 'passed'
                result['message'] = f"Swiped {direction}"
                return result
            
            # Find element for other actions
            element = self.find_element_smart(
                step.get('locator_strategy', 'xpath'),
                step.get('locator_value', ''),
                step.get('wait_time', 10)
            )
            
            if not element and action not in ['wait', 'screenshot', 'swipe']:
                result['status'] = 'failed'
                result['message'] = f"Element not found: {step.get('locator_value', '')}"
                return result
            
            # Execute action - NO RESTRICTIONS
            if action == 'click' or action == 'tap':
                element.click()
                result['status'] = 'passed'
                result['message'] = "Click/Tap successful"
                
            elif action == 'type':
                element.clear()
                element.send_keys(step.get('data', ''))
                result['status'] = 'passed'
                result['message'] = f"Typed: {step.get('data', '')[:20]}..."
                
            elif action == 'clear':
                element.clear()
                result['status'] = 'passed'
                result['message'] = "Field cleared"
                
            elif action == 'long_press':
                from appium.webdriver.common.touch_action import TouchAction
                TouchAction(self.driver).long_press(element).perform()
                result['status'] = 'passed'
                result['message'] = "Long press successful"
                
            elif action == 'assert_exists':
                result['status'] = 'passed' if element else 'failed'
                result['message'] = "Element exists" if element else "Element not found"
                
            elif action == 'assert_text':
                actual_text = element.text if element else ''
                expected = step.get('data', '')
                result['status'] = 'passed' if actual_text == expected else 'failed'
                result['message'] = f"Text: {actual_text}"
                
            elif action == 'assert_enabled':
                is_enabled = element.is_enabled() if element else False
                result['status'] = 'passed' if is_enabled else 'failed'
                result['message'] = "Element enabled" if is_enabled else "Element disabled"
                
        except Exception as e:
            result['status'] = 'failed'
            result['message'] = f"Error: {str(e)}"
        
        return result
    
    def perform_swipe(self, direction='up'):
        """Perform swipe action"""
        try:
            size = self.driver.get_window_size()
            width = size['width']
            height = size['height']
            
            if direction == 'up':
                self.driver.swipe(width/2, height*0.8, width/2, height*0.2, 500)
            elif direction == 'down':
                self.driver.swipe(width/2, height*0.2, width/2, height*0.8, 500)
            elif direction == 'left':
                self.driver.swipe(width*0.8, height/2, width*0.2, height/2, 500)
            elif direction == 'right':
                self.driver.swipe(width*0.2, height/2, width*0.8, height/2, 500)
        except:
            pass
    
    def execute_ok_button_test(self):
        """Test for handling OK button dialogs"""
        results = {
            'test_name': 'OK Button Test',
            'start_time': datetime.now(),
            'steps': [],
            'status': 'RUNNING'
        }
        
        try:
            # Try multiple strategies to find OK button
            ok_strategies = [
                ('id', 'android:id/button1'),
                ('xpath', "//android.widget.Button[@text='OK']"),
                ('xpath', "//android.widget.Button[contains(@text,'OK')]"),
                ('xpath', "//android.widget.TextView[@text='OK']"),
                ('xpath', "//*[@text='OK']"),
            ]
            
            found = False
            for strat_type, strat_value in ok_strategies:
                element = self.find_element_smart(strat_type, strat_value, timeout=3)
                if element:
                    element.click()
                    results['steps'].append({'step': f'Clicked OK button using {strat_type}', 'status': 'passed'})
                    found = True
                    break
            
            if not found:
                results['steps'].append({'step': 'No OK button found', 'status': 'info'})
            
            results['status'] = 'PASSED' if found else 'NO_ACTION'
            
        except Exception as e:
            results['status'] = 'ERROR'
            results['error'] = str(e)
        
        results['end_time'] = datetime.now()
        results['duration'] = (results['end_time'] - results['start_time']).total_seconds()
        
        return results
    
    def execute_login_test(self, username, password):
        """Execute complete login test with validation"""
        results = {
            'test_name': 'InLinea Login Test',
            'start_time': datetime.now(),
            'steps': [],
            'screenshots': [],
            'status': 'RUNNING'
        }
        
        try:
            # Step 1: Wait for app
            self.logger.info("Step 1: Waiting for app to load")
            time.sleep(3)
            results['steps'].append({'step': 'Wait for app', 'status': 'passed'})
            
            # Step 2: Handle OK button if present
            ok_result = self.execute_ok_button_test()
            if ok_result['status'] != 'ERROR':
                results['steps'].append({'step': 'OK button check', 'status': 'passed'})
            
            # Step 3: Take initial screenshot
            screenshot1 = self.take_screenshot("01_initial")
            results['screenshots'].append(screenshot1)
            results['steps'].append({'step': 'Initial screenshot', 'status': 'passed'})
            
            # Step 4: Find and fill username field
            self.logger.info("Step 4: Finding username field")
            username_element = None
            
            strategies = [
                ('xpath', "//android.widget.EditText[@text='User number']"),
                ('xpath', "//android.widget.EditText[contains(@text,'User')]"),
                ('xpath', "//android.widget.EditText[1]"),
                ('xpath', "//*[@class='android.widget.EditText'][1]"),
                ('xpath', "//android.widget.EditText[not(@password='true')][1]"),
            ]
            
            for strat_type, strat_value in strategies:
                username_element = self.find_element_smart(strat_type, strat_value, timeout=5)
                if username_element:
                    self.logger.info(f"Found username field with: {strat_value}")
                    break
            
            if username_element:
                username_element.clear()
                username_element.send_keys(username)
                results['steps'].append({'step': f'Enter username: {username}', 'status': 'passed'})
                self.logger.info(f"Username entered: {username}")
            else:
                results['steps'].append({'step': 'Find username field', 'status': 'failed'})
                self.logger.error("Username field not found")
            
            # Step 5: Find and fill password field
            time.sleep(1)
            self.logger.info("Step 5: Finding password field")
            password_element = None
            
            strategies = [
                ('xpath', "//android.widget.EditText[@password='true']"),
                ('xpath', "//android.widget.EditText[@text='Password']"),
                ('xpath', "//android.widget.EditText[contains(@text,'Password')]"),
                ('xpath', "//android.widget.EditText[2]"),
                ('xpath', "//*[@class='android.widget.EditText'][2]"),
                ('xpath', "//android.widget.EditText[last()]"),
            ]
            
            for strat_type, strat_value in strategies:
                password_element = self.find_element_smart(strat_type, strat_value, timeout=5)
                if password_element:
                    self.logger.info(f"Found password field with: {strat_value}")
                    break
            
            if password_element:
                password_element.clear()
                password_element.send_keys(password)
                results['steps'].append({'step': 'Enter password', 'status': 'passed'})
                self.logger.info("Password entered")
            else:
                results['steps'].append({'step': 'Find password field', 'status': 'failed'})
                self.logger.error("Password field not found")
            
            # Step 6: Take screenshot after filling
            time.sleep(1)
            screenshot2 = self.take_screenshot("02_filled_form")
            results['screenshots'].append(screenshot2)
            results['steps'].append({'step': 'Screenshot after filling', 'status': 'passed'})
            
            # Step 7: Find and click login button
            self.logger.info("Step 7: Finding and clicking login button")
            login_button = None
            
            button_strategies = [
                ('xpath', "//android.widget.Button[contains(@text,'Submit')]"),
                ('xpath', "//android.widget.Button[contains(@text,'Submit')]"),
                ('xpath', "//android.widget.TextView[contains(@text,'Submit')]"),
                ('xpath', "//*[@clickable='true'][contains(@text,'Submit')]"),
                ('xpath', "//android.widget.Button"),
            ]
            
            for strat_type, strat_value in button_strategies:
                login_button = self.find_element_smart(strat_type, strat_value, timeout=3)
                if login_button:
                    self.logger.info(f"Found login button with: {strat_value}")
                    login_button.click()
                    results['steps'].append({'step': 'Clicked login button', 'status': 'passed'})
                    break
            
            if not login_button:
                results['steps'].append({'step': 'Login button not found or clicked', 'status': 'warning'})
            
            # Step 8: Wait and check for login result
            time.sleep(3)
            
            # Check if login was successful by looking for error messages or success indicators
            login_success = self.verify_login_success()
            
            if login_success:
                results['steps'].append({'step': 'Login verification', 'status': 'passed'})
                results['status'] = 'PASSED'
            else:
                results['steps'].append({'step': 'Login verification', 'status': 'failed'})
                results['status'] = 'FAILED'
                self.logger.error("Login failed - incorrect credentials or other error")
            
            # Step 9: Final screenshot
            screenshot3 = self.take_screenshot("03_final")
            results['screenshots'].append(screenshot3)
            
        except Exception as e:
            self.logger.error(f"Test execution error: {e}")
            results['status'] = 'ERROR'
            results['error'] = str(e)
        
        results['end_time'] = datetime.now()
        results['duration'] = (results['end_time'] - results['start_time']).total_seconds()
        
        return results
    
    def verify_login_success(self):
        """Verify if login was successful"""
        try:
            # Check for common error indicators
            error_indicators = [
                "//android.widget.TextView[contains(@text,'Invalid')]",
                "//android.widget.TextView[contains(@text,'Incorrect')]",
                "//android.widget.TextView[contains(@text,'Wrong')]",
                "//android.widget.TextView[contains(@text,'Failed')]",
                "//*[contains(@text,'Error')]",
            ]
            
            for xpath in error_indicators:
                error_element = self.find_element_smart('xpath', xpath, timeout=2)
                if error_element:
                    self.logger.info(f"Found error indicator: {error_element.text}")
                    return False
            
            # Check for success indicators
            success_indicators = [
                "//android.widget.TextView[contains(@text,'Welcome')]",
                "//android.widget.TextView[contains(@text,'Dashboard')]",
                "//android.widget.TextView[contains(@text,'Account')]",
                "//android.widget.TextView[contains(@text,'Balance')]",
            ]
            
            for xpath in success_indicators:
                success_element = self.find_element_smart('xpath', xpath, timeout=2)
                if success_element:
                    self.logger.info(f"Found success indicator: {success_element.text}")
                    return True
            
            # If no clear indicators, assume failure for wrong credentials
            return False
            
        except:
            return False
    
    def take_screenshot(self, name):
        """Take screenshot and return path"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{name}_{timestamp}.png"
        filepath = self.screenshots_dir / filename
        
        try:
            self.driver.save_screenshot(str(filepath))
            self.logger.info(f"Screenshot saved: {filename}")
            return str(filepath)
        except Exception as e:
            self.logger.error(f"Screenshot failed: {e}")
            return None

class BankingAutomationApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("InLinea Banking Automation v9.0 - Unrestricted Edition")
        self.root.geometry("1700x1000")
        
        # App state
        self.driver = None
        self.test_runner = None
        self.last_scan_results = None
        self.test_execution_results = []
        self.custom_test_builder = CustomTestBuilder()
        self.appium_process = None
        self.server_log_queue = queue.Queue()
        
        self.create_interface()
        
        # Auto-check requirements on startup
        self.root.after(1000, self.check_system_requirements)
        self.root.after(2000, self.refresh_devices)
    
    def create_interface(self):
        # Title
        title_frame = tk.Frame(self.root)
        title_frame.pack(fill="x", padx=10, pady=5)
        
        tk.Label(title_frame, text="InLinea Banking Automation v9.0 - Unrestricted Testing", 
                font=("Arial", 16, "bold")).pack(side="left")
        
        # Warning
        warning_frame = tk.Frame(self.root, bg="red", relief="solid", borderwidth=2)
        warning_frame.pack(fill="x", padx=10, pady=5)
        tk.Label(warning_frame, text="⚠️ UNRESTRICTED MODE: No Safety Checks - Test Environment Only!", 
                bg="red", fg="white", font=("Arial", 10, "bold")).pack(pady=5)
        
        # Main notebook
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.create_device_tab()
        self.create_scanner_tab()
        self.create_custom_test_tab()
        self.create_test_tab()
        self.create_database_tab()
        self.create_reports_tab()
        
        # Status bar with progress
        status_frame = tk.Frame(self.root)
        status_frame.pack(side="bottom", fill="x")
        
        self.status_var = tk.StringVar(value="Ready")
        status_bar = tk.Label(status_frame, textvariable=self.status_var, relief="sunken", anchor="w")
        status_bar.pack(side="left", fill="x", expand=True)
        
        self.progress_bar = ttk.Progressbar(status_frame, length=200, mode='indeterminate')
        self.progress_bar.pack(side="right", padx=5)
    
    def create_device_tab(self):
        """Device connection tab with server console"""
        device_frame = ttk.Frame(self.notebook)
        self.notebook.add(device_frame, text="📱 Device & Server")
        
        # Split into two panes
        paned = ttk.PanedWindow(device_frame, orient=tk.HORIZONTAL)
        paned.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Left pane - Device controls
        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=1)
        
        # Connection settings
        settings_frame = ttk.LabelFrame(left_frame, text="Connection Settings", padding=10)
        settings_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Label(settings_frame, text="Device ID:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.device_id_var = tk.StringVar()
        ttk.Entry(settings_frame, textvariable=self.device_id_var, width=40).grid(row=0, column=1, padx=5, pady=5)
        
        tk.Label(settings_frame, text="App Package:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.app_package_var = tk.StringVar(value="ch.bsct.ebanking.mobile")
        ttk.Entry(settings_frame, textvariable=self.app_package_var, width=40).grid(row=1, column=1, padx=5, pady=5)
        
        # Control buttons
        control_frame = ttk.Frame(settings_frame)
        control_frame.grid(row=2, column=0, columnspan=2, pady=10)
        
        ttk.Button(control_frame, text="🔄 Refresh Devices", command=self.refresh_devices).pack(side="left", padx=5)
        ttk.Button(control_frame, text="🚀 Start Appium", command=self.start_appium_with_progress).pack(side="left", padx=5)
        self.connect_btn = ttk.Button(control_frame, text="🔗 Connect Device", command=self.connect_device_with_progress)
        self.connect_btn.pack(side="left", padx=5)
        ttk.Button(control_frame, text="🔌 Disconnect", command=self.disconnect_device).pack(side="left", padx=5)
        ttk.Button(control_frame, text="🛑 Stop Appium", command=self.stop_appium).pack(side="left", padx=5)
        
        # Device list
        list_frame = ttk.LabelFrame(left_frame, text="Available Devices", padding=10)
        list_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.device_listbox = tk.Listbox(list_frame, height=10)
        self.device_listbox.pack(fill="both", expand=True)
        self.device_listbox.bind('<Double-Button-1>', self.on_device_select)
        
        # Status
        self.connection_status_var = tk.StringVar(value="❌ Not Connected")
        tk.Label(left_frame, textvariable=self.connection_status_var, 
                font=("Arial", 12, "bold")).pack(pady=10)
        
        # Right pane - Server console
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=1)
        
        console_frame = ttk.LabelFrame(right_frame, text="Appium Server Console", padding=10)
        console_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Console output
        self.server_console = scrolledtext.ScrolledText(console_frame, height=20, bg="black", fg="green", 
                                                        font=("Consolas", 9))
        self.server_console.pack(fill="both", expand=True)
        
        # Console controls
        console_controls = ttk.Frame(console_frame)
        console_controls.pack(fill="x", pady=5)
        
        ttk.Button(console_controls, text="Clear", command=lambda: self.server_console.delete(1.0, tk.END)).pack(side="left", padx=5)
        ttk.Button(console_controls, text="Auto-scroll", command=lambda: self.server_console.see(tk.END)).pack(side="left", padx=5)
    
    def create_scanner_tab(self):
        """Enhanced UI Scanner tab"""
        scanner_frame = ttk.Frame(self.notebook)
        self.notebook.add(scanner_frame, text="🔍 Enhanced Scanner")
        
        # Controls
        control_frame = ttk.LabelFrame(scanner_frame, text="Scan Controls", padding=10)
        control_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Label(control_frame, text="Screen Name:").pack(side="left", padx=5)
        self.screen_name_var = tk.StringVar(value="Login Screen")
        ttk.Entry(control_frame, textvariable=self.screen_name_var, width=30).pack(side="left", padx=5)
        
        ttk.Button(control_frame, text="🔍 Deep Scan", command=self.deep_scan_screen).pack(side="left", padx=10)
        ttk.Button(control_frame, text="📸 Screenshot", command=self.take_screenshot).pack(side="left", padx=5)
        ttk.Button(control_frame, text="➡️ Use for Custom Test", command=self.use_scan_for_custom_test).pack(side="left", padx=5)
        ttk.Button(control_frame, text="💾 Save to DB", command=self.save_scan_to_db).pack(side="left", padx=5)
        ttk.Button(control_frame, text="🎯 Interactive Mode", command=self.toggle_interactive_mode).pack(side="left", padx=5)
        
        # Results with enhanced columns
        results_frame = ttk.LabelFrame(scanner_frame, text="Scan Results - All Elements", padding=10)
        results_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        columns = ('Type', 'Resource ID', 'Text', 'Content Desc', 'Clickable', 'Enabled', 'Bounds', 'XPath')
        self.elements_tree = ttk.Treeview(results_frame, columns=columns, show='tree headings', height=20)
        
        self.elements_tree.heading('#0', text='#')
        self.elements_tree.heading('Type', text='Type')
        self.elements_tree.heading('Resource ID', text='Resource ID')
        self.elements_tree.heading('Text', text='Text')
        self.elements_tree.heading('Content Desc', text='Content Desc')
        self.elements_tree.heading('Clickable', text='Click')
        self.elements_tree.heading('Enabled', text='Enabled')
        self.elements_tree.heading('Bounds', text='Bounds')
        self.elements_tree.heading('XPath', text='XPath')
        
        self.elements_tree.column('#0', width=50)
        self.elements_tree.column('Type', width=150)
        self.elements_tree.column('Resource ID', width=200)
        self.elements_tree.column('Text', width=150)
        self.elements_tree.column('Content Desc', width=150)
        self.elements_tree.column('Clickable', width=60)
        self.elements_tree.column('Enabled', width=60)
        self.elements_tree.column('Bounds', width=150)
        self.elements_tree.column('XPath', width=200)
        
        self.elements_tree.pack(fill="both", expand=True)
        
        # Add context menu for element interaction
        self.elements_tree.bind('<Button-3>', self.show_element_context_menu)
        
        scrollbar = ttk.Scrollbar(results_frame, orient="vertical", command=self.elements_tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.elements_tree.configure(yscrollcommand=scrollbar.set)
        
        # Interactive controls
        self.interactive_frame = ttk.LabelFrame(scanner_frame, text="Interactive Controls", padding=10)
        
        ttk.Button(self.interactive_frame, text="Click Selected", command=self.click_selected_element).pack(side="left", padx=5)
        ttk.Button(self.interactive_frame, text="Type Text", command=self.type_in_selected_element).pack(side="left", padx=5)
        ttk.Button(self.interactive_frame, text="Clear Field", command=self.clear_selected_element).pack(side="left", padx=5)
        ttk.Button(self.interactive_frame, text="Long Press", command=self.long_press_selected_element).pack(side="left", padx=5)
        ttk.Button(self.interactive_frame, text="Get Text", command=self.get_element_text).pack(side="left", padx=5)
    
    def create_custom_test_tab(self):
        """Enhanced custom test builder tab"""
        custom_frame = ttk.Frame(self.notebook)
        self.notebook.add(custom_frame, text="🛠️ Custom Test Builder")
        
        # Main paned window
        paned = ttk.PanedWindow(custom_frame, orient=tk.HORIZONTAL)
        paned.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Left panel - Available elements
        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=1)
        
        ttk.Label(left_frame, text="Available Elements (from last scan)", font=("Arial", 10, "bold")).pack(pady=5)
        
        # Elements listbox
        elem_frame = ttk.Frame(left_frame)
        elem_frame.pack(fill="both", expand=True, padx=5)
        
        elem_scrollbar = ttk.Scrollbar(elem_frame)
        elem_scrollbar.pack(side="right", fill="y")
        
        self.available_elements_listbox = tk.Listbox(elem_frame, yscrollcommand=elem_scrollbar.set, height=15)
        self.available_elements_listbox.pack(side="left", fill="both", expand=True)
        elem_scrollbar.config(command=self.available_elements_listbox.yview)
        
        # Element details
        details_frame = ttk.LabelFrame(left_frame, text="Element Details", padding=5)
        details_frame.pack(fill="x", padx=5, pady=5)
        
        self.element_details_text = scrolledtext.ScrolledText(details_frame, height=8, width=40)
        self.element_details_text.pack(fill="both", expand=True)
        
        # Actions buttons
        actions_frame = ttk.Frame(left_frame)
        actions_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Button(actions_frame, text="🔄 Refresh from Scan", command=self.refresh_available_elements).pack(side="left", padx=2)
        ttk.Button(actions_frame, text="➕ Add to Test →", command=self.add_element_to_test).pack(side="left", padx=2)
        
        # Right panel - Test steps
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=2)
        
        ttk.Label(right_frame, text="Custom Test Steps", font=("Arial", 10, "bold")).pack(pady=5)
        
        # Test name
        name_frame = ttk.Frame(right_frame)
        name_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Label(name_frame, text="Test Name:").pack(side="left", padx=5)
        self.custom_test_name = tk.StringVar(value="Custom_Test_1")
        ttk.Entry(name_frame, textvariable=self.custom_test_name, width=30).pack(side="left", padx=5)
        
        # Test steps tree
        columns = ('Action', 'Element', 'Data', 'Description')
        self.test_steps_tree = ttk.Treeview(right_frame, columns=columns, show='tree headings', height=12)
        self.test_steps_tree.heading('#0', text='#')
        self.test_steps_tree.heading('Action', text='Action')
        self.test_steps_tree.heading('Element', text='Element')
        self.test_steps_tree.heading('Data', text='Data')
        self.test_steps_tree.heading('Description', text='Description')
        
        self.test_steps_tree.column('#0', width=40)
        self.test_steps_tree.column('Action', width=100)
        self.test_steps_tree.column('Element', width=150)
        self.test_steps_tree.column('Data', width=100)
        self.test_steps_tree.column('Description', width=200)
        
        self.test_steps_tree.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Step controls - Enhanced actions
        step_controls = ttk.Frame(right_frame)
        step_controls.pack(fill="x", padx=5, pady=5)
        
        ttk.Label(step_controls, text="Action:").grid(row=0, column=0, sticky="w", padx=5)
        self.custom_action_var = tk.StringVar(value="click")
        action_combo = ttk.Combobox(step_controls, textvariable=self.custom_action_var, width=15)
        action_combo['values'] = ('click', 'tap', 'type', 'clear', 'wait', 'swipe', 'long_press', 
                                 'assert_exists', 'assert_text', 'assert_enabled', 'screenshot')
        action_combo.grid(row=0, column=1, padx=5)
        
        ttk.Label(step_controls, text="Data:").grid(row=0, column=2, sticky="w", padx=5)
        self.custom_data_var = tk.StringVar()
        ttk.Entry(step_controls, textvariable=self.custom_data_var, width=20).grid(row=0, column=3, padx=5)
        
        ttk.Label(step_controls, text="Description:").grid(row=1, column=0, sticky="w", padx=5)
        self.custom_desc_var = tk.StringVar()
        ttk.Entry(step_controls, textvariable=self.custom_desc_var, width=50).grid(row=1, column=1, columnspan=3, padx=5, pady=5)
        
        # Test controls
        test_controls = ttk.Frame(right_frame)
        test_controls.pack(fill="x", padx=5, pady=10)
        
        ttk.Button(test_controls, text="⬆️ Move Up", command=self.move_step_up).pack(side="left", padx=2)
        ttk.Button(test_controls, text="⬇️ Move Down", command=self.move_step_down).pack(side="left", padx=2)
        ttk.Button(test_controls, text="❌ Remove Step", command=self.remove_test_step).pack(side="left", padx=2)
        ttk.Button(test_controls, text="🗑️ Clear All", command=self.clear_custom_test).pack(side="left", padx=2)
        
        ttk.Separator(test_controls, orient="vertical").pack(side="left", fill="y", padx=10)
        
        ttk.Button(test_controls, text="💾 Save Test", command=self.save_custom_test).pack(side="left", padx=2)
        ttk.Button(test_controls, text="📁 Load Test", command=self.load_custom_test).pack(side="left", padx=2)
        ttk.Button(test_controls, text="▶️ Run Custom Test", command=self.run_custom_test, 
                  style="Accent.TButton").pack(side="left", padx=10)
        
        # Custom test results
        results_frame = ttk.LabelFrame(right_frame, text="Test Results", padding=5)
        results_frame.pack(fill="x", padx=5, pady=5)
        
        self.custom_test_results = scrolledtext.ScrolledText(results_frame, height=5, wrap=tk.WORD)
        self.custom_test_results.pack(fill="both", expand=True)
        
        # Bind events
        self.available_elements_listbox.bind('<<ListboxSelect>>', self.on_element_select)
        self.available_elements_listbox.bind('<Double-Button-1>', lambda e: self.add_element_to_test())
    
    def create_test_tab(self):
        """Test execution tab for pre-built tests"""
        test_frame = ttk.Frame(self.notebook)
        self.notebook.add(test_frame, text="🧪 Tests")
        
        # Login test
        login_frame = ttk.LabelFrame(test_frame, text="Login Test", padding=10)
        login_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Label(login_frame, text="Username:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.username_var = tk.StringVar(value="testuser")
        ttk.Entry(login_frame, textvariable=self.username_var, width=30).grid(row=0, column=1, padx=5, pady=5)
        
        tk.Label(login_frame, text="Password:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.password_var = tk.StringVar(value="testpass")
        ttk.Entry(login_frame, textvariable=self.password_var, show="*", width=30).grid(row=1, column=1, padx=5, pady=5)
        
        test_buttons = ttk.Frame(login_frame)
        test_buttons.grid(row=2, column=0, columnspan=2, pady=10)
        
        ttk.Button(test_buttons, text="▶️ Run Full Login Test", 
                  command=self.run_login_test).pack(side="left", padx=5)
        ttk.Button(test_buttons, text="🔘 Test OK Button", 
                  command=self.run_ok_button_test).pack(side="left", padx=5)
        
        # Test results
        results_frame = ttk.LabelFrame(test_frame, text="Test Results", padding=10)
        results_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.test_results_text = scrolledtext.ScrolledText(results_frame, height=20, wrap=tk.WORD)
        self.test_results_text.pack(fill="both", expand=True)
    
    def create_database_tab(self):
        """Database tab"""
        db_frame = ttk.Frame(self.notebook)
        self.notebook.add(db_frame, text="🗄️ Database")
        
        # Stats
        stats_frame = ttk.LabelFrame(db_frame, text="Database Statistics", padding=10)
        stats_frame.pack(fill="x", padx=10, pady=10)
        
        self.db_stats_text = scrolledtext.ScrolledText(stats_frame, height=8)
        self.db_stats_text.pack(fill="both", expand=True)
        
        # Controls
        control_frame = ttk.Frame(stats_frame)
        control_frame.pack(fill="x", pady=5)
        
        ttk.Button(control_frame, text="📊 Refresh Stats", command=self.refresh_db_stats).pack(side="left", padx=5)
        ttk.Button(control_frame, text="📁 Export CSV", command=self.export_to_csv).pack(side="left", padx=5)
        ttk.Button(control_frame, text="🧹 Clear Old Data", command=self.clear_old_data).pack(side="left", padx=5)
        
        # Recent scans
        scans_frame = ttk.LabelFrame(db_frame, text="Recent Scans", padding=10)
        scans_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        columns = ('ID', 'Timestamp', 'Screen', 'Elements', 'Screenshot')
        self.scans_tree = ttk.Treeview(scans_frame, columns=columns, show='tree headings', height=10)
        
        for col in columns:
            self.scans_tree.heading(col, text=col)
            self.scans_tree.column(col, width=150)
        
        self.scans_tree.pack(fill="both", expand=True)
        
        self.root.after(3000, self.load_recent_scans)
    
    def create_reports_tab(self):
        """Reports tab"""
        reports_frame = ttk.Frame(self.notebook)
        self.notebook.add(reports_frame, text="📈 Reports")
        
        # Report generation
        gen_frame = ttk.LabelFrame(reports_frame, text="Generate Reports", padding=10)
        gen_frame.pack(fill="x", padx=10, pady=10)
        
        ttk.Button(gen_frame, text="📊 Generate Test Report", command=self.generate_test_report).pack(side="left", padx=5)
        ttk.Button(gen_frame, text="📋 Generate Scan Report", command=self.generate_scan_report).pack(side="left", padx=5)
        ttk.Button(gen_frame, text="📑 Generate Full Report", command=self.generate_full_report).pack(side="left", padx=5)
        
        # Report viewer
        viewer_frame = ttk.LabelFrame(reports_frame, text="Report Preview", padding=10)
        viewer_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.report_text = scrolledtext.ScrolledText(viewer_frame, wrap=tk.WORD)
        self.report_text.pack(fill="both", expand=True)
    
    # Enhanced Methods
    def start_appium_with_progress(self):
        """Start Appium with progress indication"""
        self.progress_bar.start()
        self.log("Starting Appium server...")
        
        def start_server():
            try:
                self.appium_process = subprocess.Popen(
                    ['appium'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    shell=True
                )
                
                # Read output
                for line in self.appium_process.stdout:
                    self.server_log_queue.put(line)
                    self.root.after(0, self.update_server_console, line)
                    if "Appium REST http interface listener started" in line or "started on" in line:
                        self.root.after(0, self.on_appium_started)
                        break
                
            except Exception as e:
                self.root.after(0, self.on_appium_error, str(e))
        
        threading.Thread(target=start_server, daemon=True).start()
    
    def on_appium_started(self):
        """Handle successful Appium start"""
        self.progress_bar.stop()
        self.log("✅ Appium server started successfully")
        self.update_server_console("✅ Server ready on port 4723\n")
    
    def on_appium_error(self, error):
        """Handle Appium start error"""
        self.progress_bar.stop()
        self.log(f"❌ Failed to start Appium: {error}")
        messagebox.showerror("Error", f"Failed to start Appium:\n{error}")
    
    def stop_appium(self):
        """Stop Appium server"""
        if self.appium_process:
            try:
                self.appium_process.terminate()
                self.appium_process = None
                self.log("Appium server stopped")
                self.update_server_console("🛑 Server stopped\n")
            except:
                pass
    
    def update_server_console(self, text):
        """Update server console output"""
        self.server_console.insert(tk.END, text)
        self.server_console.see(tk.END)
    
    def connect_device_with_progress(self):
        """Connect to device with progress indication"""
        device_id = self.device_id_var.get()
        app_package = self.app_package_var.get()
        
        if not device_id:
            messagebox.showwarning("Warning", "Please select or enter a device ID")
            return
        
        self.progress_bar.start()
        self.log(f"Connecting to device: {device_id}")
        
        def connect():
            try:
                from appium import webdriver
                from appium.options.android import UiAutomator2Options
                
                options = UiAutomator2Options()
                options.platform_name = "Android"
                options.device_name = device_id
                options.udid = device_id
                options.app_package = app_package
                options.automation_name = "UiAutomator2"
                options.no_reset = True
                options.full_reset = False
                options.new_command_timeout = 300
                options.auto_grant_permissions = True
                options.ignore_hidden_api_policy_error = True
                
                self.driver = webdriver.Remote("http://localhost:4723", options=options)
                
                # Initialize test runner
                self.test_runner = CompleteTestRunner(self.driver, screenshots_dir)
                
                self.root.after(0, self.on_device_connected)
                
            except Exception as e:
                self.root.after(0, self.on_device_error, str(e))
        
        threading.Thread(target=connect, daemon=True).start()
    
    def on_device_connected(self):
        """Handle successful device connection"""
        self.progress_bar.stop()
        self.connection_status_var.set("✅ Connected")
        self.log("✅ Successfully connected to device")
        messagebox.showinfo("Success", "Connected to device successfully!")
    
    def on_device_error(self, error):
        """Handle device connection error"""
        self.progress_bar.stop()
        self.connection_status_var.set("❌ Connection Failed")
        self.log(f"❌ Connection failed: {error}")
        messagebox.showerror("Connection Error", f"Failed to connect:\n{error}")
    
    def deep_scan_screen(self):
        """Perform deep scan of all elements"""
        if not self.driver:
            messagebox.showwarning("Warning", "Please connect to device first")
            return
        
        self.log("Starting deep screen scan...")
        self.progress_bar.start()
        
        def scan():
            try:
                from appium.webdriver.common.appiumby import AppiumBy
                
                # Clear previous results
                self.root.after(0, lambda: [self.elements_tree.delete(item) for item in self.elements_tree.get_children()])
                
                time.sleep(2)
                
                screenshot_path = self.take_screenshot()
                
                # Get ALL elements without restrictions
                all_elements = self.driver.find_elements(AppiumBy.XPATH, "//*")
                
                elements_data = []
                element_count = 0
                
                for i, elem in enumerate(all_elements):
                    try:
                        elem_type = elem.get_attribute('className') or elem.get_attribute('class') or elem.tag_name or 'Unknown'
                        resource_id = elem.get_attribute('resource-id') or ''
                        text = elem.get_attribute('text') or ''
                        content_desc = elem.get_attribute('content-desc') or ''
                        clickable = elem.get_attribute('clickable') == 'true'
                        enabled = elem.get_attribute('enabled') == 'true'
                        password = elem.get_attribute('password') == 'true'
                        bounds = elem.get_attribute('bounds') or ''
                        
                        # Generate XPath
                        xpath = f"//{elem_type}"
                        if resource_id:
                            xpath += f"[@resource-id='{resource_id}']"
                        elif text:
                            xpath += f"[@text='{text}']"
                        else:
                            xpath += f"[{i+1}]"
                        
                        element_data = {
                            'type': elem_type,
                            'resource_id': resource_id,
                            'text': text,
                            'content_desc': content_desc,
                            'clickable': clickable,
                            'enabled': enabled,
                            'password': password,
                            'bounds': bounds,
                            'xpath': xpath,
                            'index': i
                        }
                        elements_data.append(element_data)
                        
                        element_count += 1
                        self.root.after(0, self.add_element_to_tree, element_count, element_data)
                        
                    except Exception as e:
                        continue
                
                self.last_scan_results = {
                    'timestamp': datetime.now(),
                    'screen_name': self.screen_name_var.get(),
                    'elements': elements_data,
                    'element_count': element_count,
                    'screenshot': screenshot_path
                }
                
                self.root.after(0, self.on_scan_complete, element_count)
                
            except Exception as e:
                self.root.after(0, self.on_scan_error, str(e))
        
        threading.Thread(target=scan, daemon=True).start()
    
    def add_element_to_tree(self, count, element_data):
        """Add element to tree view"""
        self.elements_tree.insert('', 'end', text=str(count), values=(
            element_data['type'].split('.')[-1] if '.' in element_data['type'] else element_data['type'],
            element_data['resource_id'][-30:] if len(element_data['resource_id']) > 30 else element_data['resource_id'],
            element_data['text'][:20] if len(element_data['text']) > 20 else element_data['text'],
            element_data['content_desc'][:20] if len(element_data['content_desc']) > 20 else element_data['content_desc'],
            '✔' if element_data['clickable'] else '',
            '✔' if element_data['enabled'] else '',
            element_data['bounds'][:20] if len(element_data['bounds']) > 20 else element_data['bounds'],
            element_data['xpath'][:30] if len(element_data['xpath']) > 30 else element_data['xpath']
        ), tags=(element_data,))
    
    def on_scan_complete(self, count):
        """Handle scan completion"""
        self.progress_bar.stop()
        self.log(f"✅ Deep scan complete: Found {count} elements")
        messagebox.showinfo("Scan Complete", f"Found {count} elements")
    
    def on_scan_error(self, error):
        """Handle scan error"""
        self.progress_bar.stop()
        self.log(f"❌ Scan failed: {error}")
        messagebox.showerror("Scan Error", f"Failed to scan screen:\n{error}")
    
    def toggle_interactive_mode(self):
        """Toggle interactive mode"""
        if hasattr(self, 'interactive_frame'):
            if self.interactive_frame.winfo_viewable():
                self.interactive_frame.pack_forget()
            else:
                self.interactive_frame.pack(fill="x", padx=10, pady=5)
    
    def show_element_context_menu(self, event):
        """Show context menu for element interaction"""
        item = self.elements_tree.identify('item', event.x, event.y)
        if item:
            self.elements_tree.selection_set(item)
            
            menu = tk.Menu(self.root, tearoff=0)
            menu.add_command(label="Click", command=self.click_selected_element)
            menu.add_command(label="Type Text", command=self.type_in_selected_element)
            menu.add_command(label="Clear", command=self.clear_selected_element)
            menu.add_command(label="Long Press", command=self.long_press_selected_element)
            menu.add_separator()
            menu.add_command(label="Get Text", command=self.get_element_text)
            menu.add_command(label="Get Attributes", command=self.get_element_attributes)
            menu.add_separator()
            menu.add_command(label="Add to Test", command=self.add_selected_to_test)
            
            menu.post(event.x_root, event.y_root)
    
    def click_selected_element(self):
        """Click the selected element"""
        selection = self.elements_tree.selection()
        if selection and self.driver:
            item = selection[0]
            tags = self.elements_tree.item(item)['tags']
            if tags:
                element_data = tags[0]
                try:
                    element = self.test_runner.find_element_smart('xpath', element_data['xpath'], timeout=5)
                    if element:
                        element.click()
                        self.log(f"Clicked element: {element_data.get('text', element_data.get('resource_id', 'Unknown'))}")
                except Exception as e:
                    self.log(f"Failed to click: {e}")
    
    def type_in_selected_element(self):
        """Type text in selected element"""
        selection = self.elements_tree.selection()
        if selection and self.driver:
            text = tk.simpledialog.askstring("Type Text", "Enter text to type:")
            if text:
                item = selection[0]
                tags = self.elements_tree.item(item)['tags']
                if tags:
                    element_data = tags[0]
                    try:
                        element = self.test_runner.find_element_smart('xpath', element_data['xpath'], timeout=5)
                        if element:
                            element.clear()
                            element.send_keys(text)
                            self.log(f"Typed text in element: {element_data.get('resource_id', 'Unknown')}")
                    except Exception as e:
                        self.log(f"Failed to type: {e}")
    
    def clear_selected_element(self):
        """Clear selected element"""
        selection = self.elements_tree.selection()
        if selection and self.driver:
            item = selection[0]
            tags = self.elements_tree.item(item)['tags']
            if tags:
                element_data = tags[0]
                try:
                    element = self.test_runner.find_element_smart('xpath', element_data['xpath'], timeout=5)
                    if element:
                        element.clear()
                        self.log(f"Cleared element: {element_data.get('resource_id', 'Unknown')}")
                except Exception as e:
                    self.log(f"Failed to clear: {e}")
    
    def long_press_selected_element(self):
        """Long press selected element"""
        selection = self.elements_tree.selection()
        if selection and self.driver:
            item = selection[0]
            tags = self.elements_tree.item(item)['tags']
            if tags:
                element_data = tags[0]
                try:
                    from appium.webdriver.common.touch_action import TouchAction
                    element = self.test_runner.find_element_smart('xpath', element_data['xpath'], timeout=5)
                    if element:
                        TouchAction(self.driver).long_press(element).perform()
                        self.log(f"Long pressed element: {element_data.get('resource_id', 'Unknown')}")
                except Exception as e:
                    self.log(f"Failed to long press: {e}")
    
    def get_element_text(self):
        """Get text from selected element"""
        selection = self.elements_tree.selection()
        if selection and self.driver:
            item = selection[0]
            tags = self.elements_tree.item(item)['tags']
            if tags:
                element_data = tags[0]
                try:
                    element = self.test_runner.find_element_smart('xpath', element_data['xpath'], timeout=5)
                    if element:
                        text = element.text
                        messagebox.showinfo("Element Text", f"Text: {text}")
                        self.log(f"Got text: {text}")
                except Exception as e:
                    self.log(f"Failed to get text: {e}")
    
    def get_element_attributes(self):
        """Get all attributes of selected element"""
        selection = self.elements_tree.selection()
        if selection and self.driver:
            item = selection[0]
            tags = self.elements_tree.item(item)['tags']
            if tags:
                element_data = tags[0]
                try:
                    element = self.test_runner.find_element_smart('xpath', element_data['xpath'], timeout=5)
                    if element:
                        attrs = {
                            'text': element.text,
                            'enabled': element.is_enabled(),
                            'displayed': element.is_displayed(),
                            'selected': element.is_selected(),
                            'location': element.location,
                            'size': element.size
                        }
                        messagebox.showinfo("Element Attributes", json.dumps(attrs, indent=2))
                except Exception as e:
                    self.log(f"Failed to get attributes: {e}")
    
    def add_selected_to_test(self):
        """Add selected element to custom test"""
        selection = self.elements_tree.selection()
        if selection:
            item = selection[0]
            tags = self.elements_tree.item(item)['tags']
            if tags:
                element_data = tags[0]
                element_info = {
                    'name': element_data.get('text', '') or element_data.get('resource_id', '').split('/')[-1] or f'Element_{element_data["index"]}',
                    'locator_strategy': 'xpath',
                    'locator_value': element_data['xpath']
                }
                
                action = self.custom_action_var.get()
                data = self.custom_data_var.get() if self.custom_data_var.get() else None
                description = self.custom_desc_var.get()
                
                self.custom_test_builder.add_step(action, element_info, data, description)
                self.update_test_steps_tree()
                self.log(f"Added {action} step for {element_info['name']}")
    
    def run_ok_button_test(self):
        """Run OK button test"""
        if not self.driver or not self.test_runner:
            messagebox.showwarning("Warning", "Please connect to device first")
            return
        
        self.log("Running OK button test...")
        
        def run_test():
            results = self.test_runner.execute_ok_button_test()
            self.root.after(0, self.display_test_results, results)
        
        threading.Thread(target=run_test, daemon=True).start()
    
    # All other existing methods remain the same...
    def check_system_requirements(self):
        """Check if ADB and Appium are available"""
        try:
            result = subprocess.run(['adb', 'version'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                self.log("✅ ADB is installed")
        except:
            self.log("❌ ADB not available")
        
        try:
            result = subprocess.run(['appium', '--version'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                self.log("✅ Appium is installed")
        except:
            self.log("❌ Appium not available")
    
    def refresh_devices(self):
        """Refresh device list"""
        self.device_listbox.delete(0, tk.END)
        
        try:
            result = subprocess.run(['adb', 'devices'], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')[1:]
                for line in lines:
                    if '\tdevice' in line:
                        device_id = line.split('\t')[0]
                        self.device_listbox.insert(tk.END, device_id)
                        self.log(f"Found device: {device_id}")
                
                if self.device_listbox.size() == 0:
                    self.device_listbox.insert(tk.END, "No devices found")
        except Exception as e:
            self.log(f"Error refreshing devices: {e}")
            self.device_listbox.insert(tk.END, "Error: ADB not available")
    
    def on_device_select(self, event):
        """Handle device selection"""
        selection = self.device_listbox.curselection()
        if selection:
            device_id = self.device_listbox.get(selection[0])
            if device_id != "No devices found" and "Error" not in device_id:
                self.device_id_var.set(device_id)
                self.log(f"Selected device: {device_id}")
    
    def disconnect_device(self):
        """Disconnect from device"""
        if self.driver:
            try:
                self.driver.quit()
                self.driver = None
                self.test_runner = None
                self.connection_status_var.set("❌ Disconnected")
                self.log("Device disconnected")
            except Exception as e:
                self.log(f"Error disconnecting: {e}")
    
    def take_screenshot(self):
        """Take screenshot and return path"""
        if not self.driver:
            return None
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"
            filepath = screenshots_dir / filename
            
            self.driver.save_screenshot(str(filepath))
            self.log(f"📸 Screenshot saved: {filename}")
            return str(filepath)
        except Exception as e:
            self.log(f"❌ Screenshot failed: {e}")
            return None
    
    def save_scan_to_db(self):
        """Save scan results to database"""
        if not self.last_scan_results:
            messagebox.showwarning("Warning", "No scan results to save")
            return
        
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO scan_results (app_name, screen_name, elements_count, screenshot_path, scan_data)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                self.app_package_var.get(),
                self.last_scan_results['screen_name'],
                self.last_scan_results['element_count'],
                self.last_scan_results.get('screenshot', ''),
                json.dumps(self.last_scan_results['elements'])
            ))
            
            scan_id = cursor.lastrowid
            
            for elem in self.last_scan_results['elements']:
                cursor.execute('''
                    INSERT INTO elements (scan_id, element_type, resource_id, text, content_desc, 
                                        clickable, enabled, password, bounds, xpath)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    scan_id,
                    elem['type'],
                    elem['resource_id'],
                    elem['text'],
                    elem['content_desc'],
                    elem['clickable'],
                    elem['enabled'],
                    elem['password'],
                    elem['bounds'],
                    elem.get('xpath', '')
                ))
            
            conn.commit()
            conn.close()
            
            self.log(f"✅ Scan saved to database (ID: {scan_id})")
            messagebox.showinfo("Success", f"Scan saved to database\nScan ID: {scan_id}")
            
            self.load_recent_scans()
            self.refresh_db_stats()
            
        except Exception as e:
            self.log(f"❌ Database save failed: {e}")
            messagebox.showerror("Error", f"Failed to save to database:\n{e}")
    
    def run_login_test(self):
        """Run complete login test"""
        if not self.driver:
            messagebox.showwarning("Warning", "Please connect to device first")
            return
        
        if not self.test_runner:
            messagebox.showerror("Error", "Test runner not initialized")
            return
        
        username = self.username_var.get()
        password = self.password_var.get()
        
        if not username or not password:
            messagebox.showwarning("Warning", "Please enter username and password")
            return
        
        self.log("Starting login test...")
        self.test_results_text.delete(1.0, tk.END)
        
        def run_test():
            results = self.test_runner.execute_login_test(username, password)
            self.root.after(0, self.display_test_results, results)
            self.save_test_results_to_db(results)
        
        threading.Thread(target=run_test, daemon=True).start()
    
    def display_test_results(self, results):
        """Display test results in UI"""
        output = f"""
╔════════════════════════════════════════════╗
║         LOGIN TEST RESULTS                 ║
╚════════════════════════════════════════════╝

Test Name: {results['test_name']}
Status: {results['status']}
Duration: {results.get('duration', 0):.2f} seconds

Steps Executed:
"""
        
        for i, step in enumerate(results['steps'], 1):
            status_icon = "✅" if step['status'] == 'passed' else "❌" if step['status'] == 'failed' else "⭕"
            output += f"{i}. {status_icon} {step['step']}\n"
        
        output += f"\nScreenshots Captured: {len(results.get('screenshots', []))}\n"
        
        for i, screenshot in enumerate(results.get('screenshots', []), 1):
            if screenshot:
                output += f"  {i}. {Path(screenshot).name}\n"
        
        if results.get('error'):
            output += f"\n❌ Error: {results['error']}\n"
        
        output += "\n" + "="*50 + "\n"
        
        self.test_results_text.insert(tk.END, output)
        self.log(f"Test completed: {results['status']}")
        
        if results['status'] == 'PASSED':
            messagebox.showinfo("Test Passed", "Login test completed successfully!")
        elif results['status'] == 'PARTIAL':
            messagebox.showwarning("Test Partial", "Login test partially completed")
        else:
            messagebox.showerror("Test Failed", "Login test failed - check credentials")
    
    def save_test_results_to_db(self, results):
        """Save test results to database"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO test_results (test_name, status, passed_steps, failed_steps, 
                                        total_steps, duration, screenshot_paths, result_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                results['test_name'],
                results['status'],
                sum(1 for s in results['steps'] if s.get('status') == 'passed'),
                sum(1 for s in results['steps'] if s.get('status') == 'failed'),
                len(results['steps']),
                results.get('duration', 0),
                json.dumps(results.get('screenshots', [])),
                json.dumps(results)
            ))
            
            conn.commit()
            conn.close()
            
            self.log("Test results saved to database")
            
        except Exception as e:
            self.log(f"Failed to save test results: {e}")
    
    # Custom Test Methods
    def refresh_available_elements(self):
        """Refresh available elements from last scan"""
        self.available_elements_listbox.delete(0, tk.END)
        
        if self.last_scan_results:
            elements = self.last_scan_results.get('elements', [])
            self.custom_test_builder.add_scanned_elements(elements)
            
            for i, element in enumerate(elements):
                # Create display name
                name = element.get('text', '')[:20] or element.get('resource_id', '').split('/')[-1][:20] or f'Element_{i+1}'
                elem_type = element.get('type', '').split('.')[-1] if '.' in element.get('type', '') else element.get('type', '')
                display = f"{name} [{elem_type}]"
                
                self.available_elements_listbox.insert(tk.END, display)
            
            self.log(f"Loaded {len(elements)} elements for custom test")
        else:
            messagebox.showinfo("No Elements", "Please scan a screen first to get available elements")
    
    def on_element_select(self, event):
        """Handle element selection in custom test builder"""
        selection = self.available_elements_listbox.curselection()
        if selection:
            index = selection[0]
            elements = self.custom_test_builder.scanned_elements
            
            if index < len(elements):
                element = elements[index]
                
                # Display element details
                details = f"""Resource ID: {element.get('resource_id', 'N/A')}
Text: {element.get('text', 'N/A')}
Type: {element.get('type', 'N/A')}
Clickable: {element.get('clickable', False)}
Enabled: {element.get('enabled', False)}
Bounds: {element.get('bounds', 'N/A')}
XPath: {element.get('xpath', 'N/A')}"""
                
                self.element_details_text.delete(1.0, tk.END)
                self.element_details_text.insert(1.0, details)
    
    def add_element_to_test(self):
        """Add selected element to custom test"""
        selection = self.available_elements_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select an element first")
            return
        
        index = selection[0]
        elements = self.custom_test_builder.scanned_elements
        
        if index >= len(elements):
            return
        
        element = elements[index]
        
        # Prepare element info for test step
        element_info = {
            'name': element.get('text', '') or element.get('resource_id', '').split('/')[-1] or f'Element_{index+1}',
            'locator_strategy': 'xpath',
            'locator_value': element.get('xpath', f"//*[{index+1}]")
        }
        
        # Get action and data
        action = self.custom_action_var.get()
        data = self.custom_data_var.get() if self.custom_data_var.get() else None
        description = self.custom_desc_var.get()
        
        # Add step
        self.custom_test_builder.add_step(action, element_info, data, description)
        
        # Update tree
        self.update_test_steps_tree()
        
        self.log(f"Added {action} step for {element_info['name']}")
    
    def update_test_steps_tree(self):
        """Update the test steps tree view"""
        # Clear tree
        for item in self.test_steps_tree.get_children():
            self.test_steps_tree.delete(item)
        
        # Add steps
        for i, step in enumerate(self.custom_test_builder.test_steps, 1):
            element_name = step.get('element_info', {}).get('name', 'Unknown')
            self.test_steps_tree.insert('', 'end', text=str(i), values=(
                step.get('action', ''),
                element_name[:30],
                step.get('data', '')[:20] if step.get('data') else '',
                step.get('description', '')[:50]
            ))
    
    def move_step_up(self):
        """Move selected test step up"""
        selection = self.test_steps_tree.selection()
        if selection:
            item = selection[0]
            index = self.test_steps_tree.index(item)
            self.custom_test_builder.move_step_up(index)
            self.update_test_steps_tree()
    
    def move_step_down(self):
        """Move selected test step down"""
        selection = self.test_steps_tree.selection()
        if selection:
            item = selection[0]
            index = self.test_steps_tree.index(item)
            self.custom_test_builder.move_step_down(index)
            self.update_test_steps_tree()
    
    def remove_test_step(self):
        """Remove selected test step"""
        selection = self.test_steps_tree.selection()
        if selection:
            item = selection[0]
            index = self.test_steps_tree.index(item)
            self.custom_test_builder.remove_step(index)
            self.update_test_steps_tree()
    
    def clear_custom_test(self):
        """Clear all custom test steps"""
        if messagebox.askyesno("Clear Test", "Remove all test steps?"):
            self.custom_test_builder.clear_steps()
            self.update_test_steps_tree()
    
    def save_custom_test(self):
        """Save custom test to file and database"""
        test_name = self.custom_test_name.get()
        
        # Save to file
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            initialdir=custom_tests_dir,
            initialfile=f"{test_name}.json"
        )
        
        if filepath:
            try:
                self.custom_test_builder.save_test(filepath)
                
                # Also save to database
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO custom_tests (test_name, steps, description)
                    VALUES (?, ?, ?)
                ''', (
                    test_name,
                    json.dumps(self.custom_test_builder.test_steps),
                    f"Custom test saved at {datetime.now()}"
                ))
                
                conn.commit()
                conn.close()
                
                messagebox.showinfo("Saved", f"Test saved to {Path(filepath).name}")
                self.log(f"Custom test saved: {test_name}")
                
            except Exception as e:
                messagebox.showerror("Save Error", str(e))
    
    def load_custom_test(self):
        """Load custom test from file"""
        filepath = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json")],
            initialdir=custom_tests_dir
        )
        
        if filepath:
            try:
                test_case = self.custom_test_builder.load_test(filepath)
                self.custom_test_name.set(test_case.get('name', 'Loaded_Test'))
                self.update_test_steps_tree()
                messagebox.showinfo("Loaded", f"Test loaded: {test_case.get('name')}")
                self.log(f"Custom test loaded from {Path(filepath).name}")
            except Exception as e:
                messagebox.showerror("Load Error", str(e))
    
    def run_custom_test(self):
        """Run the custom test"""
        if not self.driver:
            messagebox.showerror("Error", "Connect to device first")
            return
        
        if not self.test_runner:
            messagebox.showerror("Error", "Test runner not initialized")
            return
        
        if not self.custom_test_builder.test_steps:
            messagebox.showwarning("No Steps", "Please add test steps first")
            return
        
        test_name = self.custom_test_name.get()
        
        self.log(f"Running custom test: {test_name}")
        self.custom_test_results.delete(1.0, tk.END)
        self.custom_test_results.insert(tk.END, f"Running {test_name}...\n")
        
        # Run test in thread
        def run_test():
            test_case = self.custom_test_builder.build_test_case(test_name)
            results = self.test_runner.execute_custom_test(test_case)
            
            # Display results
            self.root.after(0, self.display_custom_test_results, results)
            
            # Save to database
            self.save_test_results_to_db(results)
        
        threading.Thread(target=run_test, daemon=True).start()
    
    def display_custom_test_results(self, results):
        """Display custom test results"""
        output = f"\n{'='*40}\n"
        output += f"Test: {results['test_name']}\n"
        output += f"Status: {results['status']}\n"
        output += f"Duration: {results.get('duration', 0):.2f}s\n\n"
        
        for i, step in enumerate(results['steps'], 1):
            status = "✅" if step['status'] == 'passed' else "❌"
            output += f"{i}. {status} {step['description']}\n"
        
        output += f"\nScreenshots: {len(results.get('screenshots', []))}\n"
        
        self.custom_test_results.insert(tk.END, output)
        
        # Show notification
        if results['status'] == 'PASSED':
            messagebox.showinfo("Test Passed", f"{results['test_name']} completed successfully!")
        else:
            messagebox.showwarning("Test Failed", f"{results['test_name']} failed or partially completed")
    
    def use_scan_for_custom_test(self):
        """Use last scan results for custom test building"""
        if not self.last_scan_results:
            messagebox.showwarning("No Scan", "Please scan a screen first")
            return
        
        self.refresh_available_elements()
        self.notebook.select(2)  # Switch to Custom Test Builder tab
        messagebox.showinfo("Elements Loaded", f"Loaded {len(self.last_scan_results.get('elements', []))} elements for custom test building")
    
    def refresh_db_stats(self):
        """Refresh database statistics"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM scan_results")
            scan_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM test_results")
            test_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM elements")
            element_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM custom_tests")
            custom_test_count = cursor.fetchone()[0]
            
            db_size = Path(DB_PATH).stat().st_size / 1024
            
            conn.close()
            
            stats_text = f"""
📊 DATABASE STATISTICS
{'='*40}

Total Scans: {scan_count}
Total Tests: {test_count}
Custom Tests Saved: {custom_test_count}
Total Elements: {element_count}
Database Size: {db_size:.2f} KB

Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
            
            self.db_stats_text.delete(1.0, tk.END)
            self.db_stats_text.insert(1.0, stats_text)
            
        except Exception as e:
            self.log(f"Failed to refresh stats: {e}")
    
    def load_recent_scans(self):
        """Load recent scans from database"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, scan_timestamp, screen_name, elements_count, screenshot_path
                FROM scan_results
                ORDER BY scan_timestamp DESC
                LIMIT 10
            ''')
            
            scans = cursor.fetchall()
            conn.close()
            
            for item in self.scans_tree.get_children():
                self.scans_tree.delete(item)
            
            for scan in scans:
                self.scans_tree.insert('', 'end', values=scan)
            
        except Exception as e:
            self.log(f"Failed to load scans: {e}")
    
    def export_to_csv(self):
        """Export database to CSV"""
        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialdir=exports_dir
        )
        
        if not filepath:
            return
        
        try:
            conn = sqlite3.connect(DB_PATH)
            
            query = "SELECT * FROM elements"
            cursor = conn.cursor()
            cursor.execute(query)
            
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([desc[0] for desc in cursor.description])
                writer.writerows(cursor.fetchall())
            
            conn.close()
            
            self.log(f"✅ Exported to {Path(filepath).name}")
            messagebox.showinfo("Success", f"Data exported to:\n{filepath}")
            
        except Exception as e:
            self.log(f"❌ Export failed: {e}")
            messagebox.showerror("Error", f"Export failed:\n{e}")
    
    def clear_old_data(self):
        """Clear old data from database"""
        if messagebox.askyesno("Confirm", "Clear all database data?"):
            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                
                cursor.execute("DELETE FROM elements")
                cursor.execute("DELETE FROM scan_results")
                cursor.execute("DELETE FROM test_results")
                cursor.execute("DELETE FROM custom_tests")
                
                conn.commit()
                conn.close()
                
                self.log("✅ Database cleared")
                messagebox.showinfo("Success", "Database cleared successfully")
                
                self.refresh_db_stats()
                self.load_recent_scans()
                
            except Exception as e:
                self.log(f"❌ Failed to clear database: {e}")
                messagebox.showerror("Error", f"Failed to clear database:\n{e}")
    
    def generate_test_report(self):
        """Generate test execution report"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT test_name, status, passed_steps, failed_steps, total_steps, 
                       duration, test_timestamp
                FROM test_results
                ORDER BY test_timestamp DESC
            ''')
            
            tests = cursor.fetchall()
            conn.close()
            
            html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Test Execution Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
        .passed {{ color: green; font-weight: bold; }}
        .failed {{ color: red; font-weight: bold; }}
    </style>
</head>
<body>
    <h1>Test Execution Report</h1>
    <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    
    <table>
        <tr>
            <th>Test Name</th>
            <th>Status</th>
            <th>Passed</th>
            <th>Failed</th>
            <th>Total</th>
            <th>Duration (s)</th>
            <th>Timestamp</th>
        </tr>
"""
            
            for test in tests:
                status_class = 'passed' if test[1] == 'PASSED' else 'failed'
                html += f"""
        <tr>
            <td>{test[0]}</td>
            <td class="{status_class}">{test[1]}</td>
            <td>{test[2]}</td>
            <td>{test[3]}</td>
            <td>{test[4]}</td>
            <td>{test[5]:.2f}</td>
            <td>{test[6]}</td>
        </tr>
"""
            
            html += """
    </table>
</body>
</html>
"""
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = reports_dir / f"test_report_{timestamp}.html"
            
            with open(report_path, 'w') as f:
                f.write(html)
            
            self.log(f"✅ Test report generated: {report_path.name}")
            
            self.report_text.delete(1.0, tk.END)
            self.report_text.insert(1.0, f"Test Report Generated\n{'='*50}\n\n")
            self.report_text.insert(tk.END, f"Total Tests: {len(tests)}\n")
            self.report_text.insert(tk.END, f"Report saved to: {report_path}\n")
            
            if messagebox.askyesno("Report Generated", "Open report in browser?"):
                import webbrowser
                webbrowser.open(f"file://{report_path.absolute()}")
            
        except Exception as e:
            self.log(f"❌ Report generation failed: {e}")
            messagebox.showerror("Error", f"Failed to generate report:\n{e}")
    
    def generate_scan_report(self):
        """Generate scan report"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT screen_name, elements_count, scan_timestamp
                FROM scan_results
                ORDER BY scan_timestamp DESC
            ''')
            
            scans = cursor.fetchall()
            conn.close()
            
            report = f"Scan Report\n{'='*50}\n\n"
            report += f"Total Scans: {len(scans)}\n\n"
            
            for scan in scans[:10]:
                report += f"Screen: {scan[0]}\n"
                report += f"Elements: {scan[1]}\n"
                report += f"Time: {scan[2]}\n"
                report += "-"*30 + "\n"
            
            self.report_text.delete(1.0, tk.END)
            self.report_text.insert(1.0, report)
            
            self.log("✅ Scan report generated")
            
        except Exception as e:
            self.log(f"❌ Scan report failed: {e}")
    
    def generate_full_report(self):
        """Generate comprehensive report"""
        self.generate_test_report()
    
    def log(self, message):
        """Log message to status and file"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        self.status_var.set(log_message)
        logger.info(message)
    
    def run(self):
        """Run the application"""
        self.log("Application started - v9.0 Unrestricted")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()
    
    def on_closing(self):
        """Handle window closing"""
        if self.driver:
            self.disconnect_device()
        if self.appium_process:
            self.stop_appium()
        self.root.destroy()

def main():
    """Main entry point"""
    print("="*60)
    print("InLinea Banking Automation v9.0 - Unrestricted Edition")
    print("Complete with Enhanced Features - NO SAFETY CHECKS")
    print("FOR TESTING ENVIRONMENT ONLY")
    print("="*60)
    
    app = BankingAutomationApp()
    app.run()

if __name__ == "__main__":
    main()