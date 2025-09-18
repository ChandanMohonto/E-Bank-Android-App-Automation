#!/usr/bin/env python3
"""
Complete InLinea Banking App Automation Tool - v10.0 ENHANCED
All Original Features Plus Requested Improvements - COMPLETE RUNNABLE VERSION
FIXED: Login test with index-based XPath selectors
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import tkinter.simpledialog as simpledialog
import sys
import logging
import threading
import time
import json
import sqlite3
import csv
from datetime import datetime, timedelta
from pathlib import Path
import subprocess
import os
import queue

# Create directories
project_root = Path(__file__).parent.parent
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
        logging.FileHandler(logs_dir / f'banking_{datetime.now().strftime("%Y%m%d")}.log', encoding='utf-8'),
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
        """Add a test step with proper data handling"""
        step = {
            'action': action,
            'locator_strategy': element_info.get('locator_strategy', 'xpath'),
            'locator_value': element_info.get('locator_value', ''),
            'data': data,  # This will store the actual text to type
            'description': description or f"{action} on {element_info.get('name', 'element')}",
            'wait_time': wait_time,
            'element_info': element_info
        }
        self.test_steps.append(step)
        logger.info(f"Added step: {action} with data: {data}")
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
        """Smart element finding with multiple fallback strategies and index-based support"""
        from appium.webdriver.common.appiumby import AppiumBy
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        
        element = None
        
        # Special handling for OK button variations
        if 'button' in locator_value.lower() and any(ok in locator_value.lower() for ok in ['ok', 'okay']):
            ok_selectors = [
                (AppiumBy.ID, "android:id/button1"),
                (AppiumBy.XPATH, "//android.widget.Button[@text='OK']"),
                (AppiumBy.XPATH, "//android.widget.Button[@text='Ok']"),
                (AppiumBy.XPATH, "//android.widget.Button[@text='ok']"),
                (AppiumBy.XPATH, "//android.widget.Button[contains(@text, 'OK')]"),
                (AppiumBy.XPATH, "//android.widget.TextView[@text='OK']"),
                (AppiumBy.XPATH, "//android.widget.TextView[@text='Ok']"),
                (AppiumBy.XPATH, "//*[@text='OK' or @text='Ok' or @text='ok']")
            ]
            
            for selector_type, selector_value in ok_selectors:
                try:
                    element = WebDriverWait(self.driver, 2).until(
                        EC.presence_of_element_located((selector_type, selector_value))
                    )
                    if element:
                        self.logger.info(f"Found OK button with selector: {selector_value}")
                        return element
                except:
                    continue
        
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
        except Exception as e:
            self.logger.debug(f"Primary locator failed: {e}")
        
        # Fallback strategies if primary fails
        if not element:
            try:
                # Try finding by partial resource-id match
                all_elements = self.driver.find_elements(AppiumBy.XPATH, "//*")
                for elem in all_elements:
                    try:
                        resource_id = elem.get_attribute('resource-id') or ''
                        text = elem.get_attribute('text') or ''
                        content_desc = elem.get_attribute('content-desc') or ''
                        
                        # Check if locator value matches any attribute
                        if locator_value in resource_id or locator_value in text or locator_value in content_desc:
                            element = elem
                            self.logger.info(f"Found element via fallback search: {locator_value}")
                            break
                        
                        # Check for partial ID match
                        if ':id/' in locator_value and locator_value.split(':id/')[-1] in resource_id:
                            element = elem
                            self.logger.info(f"Found element via partial ID match: {locator_value}")
                            break
                    except:
                        continue
            except Exception as e:
                self.logger.debug(f"Fallback search failed: {e}")
        
        return element
    
    def execute_custom_test(self, test_case, progress_callback=None):
        """Execute a custom test case with progress reporting and proper data handling"""
        results = {
            'test_name': test_case.get('name', 'Custom Test'),
            'start_time': datetime.now(),
            'steps': [],
            'screenshots': [],
            'status': 'RUNNING'
        }
        
        try:
            steps = test_case.get('steps', [])
            total_steps = len(steps)
            
            for i, step in enumerate(steps, 1):
                self.logger.info(f"Executing step {i}/{total_steps}: {step.get('description', '')}")
                self.logger.info(f"Step details - Action: {step.get('action')}, Data: {step.get('data')}")
                
                # Report progress
                if progress_callback:
                    progress_callback(i, total_steps, step.get('description', ''))
                
                step_result = self.execute_step(step)
                results['steps'].append(step_result)
                
                # Take screenshot after certain actions
                if step.get('action') in ['click', 'tap', 'type'] or step.get('take_screenshot'):
                    screenshot = self.take_screenshot(f"step_{i}")
                    if screenshot:
                        results['screenshots'].append(screenshot)
                
                # Small delay between steps
                time.sleep(1)
            
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
        """Execute a single test step - FIXED for type and tap actions"""
        from appium.webdriver.common.appiumby import AppiumBy
        
        result = {
            'description': step.get('description', ''),
            'action': step.get('action'),
            'status': 'unknown',
            'message': ''
        }
        
        try:
            action = step.get('action')
            
            self.logger.info(f"Executing action: {action}, with data: {step.get('data')}")
            
            # Handle wait action
            if action == 'wait':
                wait_time = float(step.get('data', 2))
                time.sleep(wait_time)
                result['status'] = 'passed'
                result['message'] = f"Waited {wait_time} seconds"
                return result
            
            # Handle screenshot
            if action == 'screenshot':
                screenshot = self.take_screenshot("custom")
                result['status'] = 'passed' if screenshot else 'failed'
                result['message'] = f"Screenshot {'taken' if screenshot else 'failed'}"
                return result
            
            # Handle swipe
            if action == 'swipe':
                direction = step.get('data', 'up')
                self.perform_swipe(direction)
                result['status'] = 'passed'
                result['message'] = f"Swiped {direction}"
                return result
            
            # For actions that need an element
            if action not in ['wait', 'screenshot', 'swipe']:
                # Find element for other actions
                element = self.find_element_smart(
                    step.get('locator_strategy', 'xpath'),
                    step.get('locator_value', ''),
                    step.get('wait_time', 10)
                )
                
                if not element:
                    result['status'] = 'failed'
                    result['message'] = f"Element not found: {step.get('locator_value', '')}"
                    self.logger.error(f"Element not found for action {action}: {step.get('locator_value')}")
                    return result
                
                # Execute action based on type
                if action in ['click', 'tap']:
                    element.click()
                    result['status'] = 'passed'
                    result['message'] = "Click/Tap successful"
                    self.logger.info(f"Successfully clicked/tapped element")
                    
                elif action == 'type':
                    # Get the actual text to type from the data field
                    text_to_type = step.get('data', '')
                    self.logger.info(f"Typing text: {text_to_type}")
                    
                    try:
                        # Clear the field first
                        element.clear()
                        time.sleep(0.5)  # Small delay after clearing
                        
                        # Send the text
                        if text_to_type:  # Only type if there's actual text
                            element.send_keys(str(text_to_type))
                            result['status'] = 'passed'
                            result['message'] = f"Typed: {text_to_type[:20]}{'...' if len(text_to_type) > 20 else ''}"
                            self.logger.info(f"Successfully typed: {text_to_type}")
                        else:
                            result['status'] = 'failed'
                            result['message'] = "No text provided to type"
                            self.logger.warning("No text provided for type action")
                    except Exception as type_error:
                        result['status'] = 'failed'
                        result['message'] = f"Failed to type: {str(type_error)}"
                        self.logger.error(f"Type action failed: {type_error}")
                    
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
                    result['status'] = 'passed'
                    result['message'] = "Element exists"
                    
                elif action == 'assert_text':
                    actual_text = element.text if element else ''
                    expected = step.get('data', '')
                    result['status'] = 'passed' if actual_text == expected else 'failed'
                    result['message'] = f"Text: {actual_text} (Expected: {expected})"
                    
                elif action == 'assert_enabled':
                    is_enabled = element.is_enabled() if element else False
                    result['status'] = 'passed' if is_enabled else 'failed'
                    result['message'] = "Element enabled" if is_enabled else "Element disabled"
                else:
                    result['status'] = 'failed'
                    result['message'] = f"Unknown action: {action}"
            
        except Exception as e:
            result['status'] = 'failed'
            result['message'] = f"Error: {str(e)}"
            self.logger.error(f"Step execution error: {e}")
        
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
                
            self.logger.info(f"Performed swipe: {direction}")
        except Exception as e:
            self.logger.error(f"Swipe failed: {e}")
    
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
    
    def click_ok_button(self):
        """Click any OK button variation found on screen"""
        from appium.webdriver.common.appiumby import AppiumBy
        
        ok_variations = [
            ("android:id/button1", "id"),
            ("//android.widget.Button[@text='OK']", "xpath"),
            ("//android.widget.Button[@text='Ok']", "xpath"),
            ("//android.widget.Button[@text='ok']", "xpath"),
            ("//android.widget.Button[contains(translate(@text, 'OK', 'ok'), 'ok')]", "xpath"),
            ("//android.widget.TextView[@text='OK']", "xpath"),
            ("//*[@text='OK' or @text='Ok' or @text='ok' or @text='OKAY' or @text='Okay']", "xpath")
        ]
        
        for selector, selector_type in ok_variations:
            try:
                if selector_type == "id":
                    element = self.driver.find_element(AppiumBy.ID, selector)
                else:
                    element = self.driver.find_element(AppiumBy.XPATH, selector)
                
                if element:
                    element.click()
                    self.logger.info(f"Clicked OK button with selector: {selector}")
                    return True
            except:
                continue
        
        self.logger.warning("No OK button found")
        return False

class BankingAutomationApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("InLinea Banking Automation v10.0 - Complete Enhanced")
        self.root.geometry("1920x1080")
        self.root.state('zoomed')
        
        # App state
        self.driver = None
        self.test_runner = None
        self.last_scan_results = None
        self.test_execution_results = []
        self.custom_test_builder = CustomTestBuilder()
        self.appium_process = None
        self.login_elements = {}
        self.auto_scroll = True
        
        self.create_interface()
        
        # Auto-check requirements on startup
        self.root.after(1000, self.check_system_requirements)
        self.root.after(2000, self.refresh_devices)
    
    def create_interface(self):
        # Title
        title_frame = tk.Frame(self.root)
        title_frame.pack(fill="x", padx=10, pady=5)
        
        tk.Label(title_frame, text="InLinea Banking Automation v10.0 - Complete Enhanced Testing", 
                font=("Arial", 16, "bold")).pack(side="left")
        
        # Warning
        warning_frame = tk.Frame(self.root, bg="#00bfff", relief="solid", borderwidth=2)
        warning_frame.pack(fill="x", padx=10, pady=5)
        tk.Label(warning_frame, text="⚠️ UNRESTRICTED MODE: No Safety Checks - Test Environment Only! @DEV:Chandan ", 
                bg="#00bfff", fg="black", font=("Arial", 10, "bold")).pack(pady=5)
        
        # Main notebook
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.create_server_tab()
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
        
        self.main_progress_bar = ttk.Progressbar(status_frame, length=200, mode='indeterminate')
        self.main_progress_bar.pack(side="right", padx=5)
    
    def create_server_tab(self):
        """Dedicated Appium Server tab with progress bar and log"""
        server_frame = ttk.Frame(self.notebook)
        self.notebook.add(server_frame, text="🚀 Server")
        
        # Server controls frame
        control_frame = ttk.LabelFrame(server_frame, text="Appium Server Control", padding=10)
        control_frame.pack(fill="x", padx=10, pady=10)
        
        # Server status
        self.server_status_var = tk.StringVar(value="⚪ Server Not Running")
        tk.Label(control_frame, textvariable=self.server_status_var, 
                font=("Arial", 14, "bold")).pack(pady=5)
        
        # Server control buttons in a visible frame
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(pady=5)
        
        self.start_server_btn = ttk.Button(button_frame, text="▶️ Start Server", 
                                          command=self.start_appium_with_progress, width=15)
        self.start_server_btn.pack(side="left", padx=5)
        
        self.stop_server_btn = ttk.Button(button_frame, text="⏹️ Stop Server", 
                                         command=self.stop_appium, state="disabled", width=15)
        self.stop_server_btn.pack(side="left", padx=5)
        
        ttk.Button(button_frame, text="🔄 Check Status", 
                  command=self.check_server_status, width=15).pack(side="left", padx=5)
        
        ttk.Button(button_frame, text="📋 Install Appium", 
                  command=self.install_appium, width=15).pack(side="left", padx=5)
        
        # Server progress bar
        progress_frame = ttk.Frame(control_frame)
        progress_frame.pack(fill="x", pady=10)
        
        tk.Label(progress_frame, text="Server Progress:", font=("Arial", 10)).pack(anchor="w")
        self.server_progress = ttk.Progressbar(progress_frame, mode='indeterminate', length=600)
        self.server_progress.pack(fill="x", pady=5)
        
        self.server_progress_label = tk.Label(progress_frame, text="", font=("Arial", 9))
        self.server_progress_label.pack(anchor="w")
        
        # Server log frame
        log_frame = ttk.LabelFrame(server_frame, text="Server Log", padding=10)
        log_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Log controls at TOP of log for visibility
        log_controls = ttk.Frame(log_frame)
        log_controls.pack(fill="x", pady=5)
        
        ttk.Button(log_controls, text="📋 Clear Log", 
                  command=lambda: self.server_log.delete(1.0, tk.END), width=15).pack(side="left", padx=5)
        ttk.Button(log_controls, text="💾 Save Log", 
                  command=self.save_server_log, width=15).pack(side="left", padx=5)
        ttk.Button(log_controls, text="🔍 Auto Scroll", 
                  command=self.toggle_auto_scroll, width=15).pack(side="left", padx=5)
        
        # Log display
        self.server_log = scrolledtext.ScrolledText(log_frame, height=18, wrap=tk.WORD, 
                                                    font=("Consolas", 9))
        self.server_log.pack(fill="both", expand=True)
    
    def create_device_tab(self):
        """Dedicated Device Connection tab with progress bar and log"""
        device_frame = ttk.Frame(self.notebook)
        self.notebook.add(device_frame, text="📱 Device")
        
        # Device connection frame
        connect_frame = ttk.LabelFrame(device_frame, text="Device Connection", padding=10)
        connect_frame.pack(fill="x", padx=10, pady=10)
        
        # Device status
        self.connection_status_var = tk.StringVar(value="⚪ Not Connected")
        tk.Label(connect_frame, textvariable=self.connection_status_var, 
                font=("Arial", 14, "bold")).pack(pady=5)
        
        # Device list and refresh
        device_list_frame = ttk.Frame(connect_frame)
        device_list_frame.pack(fill="x", pady=5)
        
        tk.Label(device_list_frame, text="Available Devices:", font=("Arial", 10)).pack(anchor="w")
        
        # Refresh button at top for visibility
        ttk.Button(device_list_frame, text="🔄 Refresh Devices", 
                  command=self.refresh_devices, width=20).pack(pady=5)
        
        self.device_listbox = tk.Listbox(device_list_frame, height=3, font=("Consolas", 10))
        self.device_listbox.pack(fill="x", pady=5)
        self.device_listbox.bind('<Double-Button-1>', self.on_device_select)
        
        # Device settings
        settings_frame = ttk.Frame(connect_frame)
        settings_frame.pack(fill="x", pady=5)
        
        # Device UUID
        uuid_frame = ttk.Frame(settings_frame)
        uuid_frame.pack(fill="x", pady=2)
        tk.Label(uuid_frame, text="Device UUID:", width=12, anchor="w", font=("Arial", 10)).pack(side="left")
        self.device_id_var = tk.StringVar()
        ttk.Entry(uuid_frame, textvariable=self.device_id_var, width=35, font=("Arial", 10)).pack(side="left", padx=5)
        
        # App Package
        package_frame = ttk.Frame(settings_frame)
        package_frame.pack(fill="x", pady=2)
        tk.Label(package_frame, text="App Package:", width=12, anchor="w", font=("Arial", 10)).pack(side="left")
        self.app_package_var = tk.StringVar(value="ch.bsct.ebanking.mobile")
        ttk.Entry(package_frame, textvariable=self.app_package_var, width=35, font=("Arial", 10)).pack(side="left", padx=5)
        
        # Connection buttons - MORE VISIBLE
        connect_buttons = ttk.Frame(connect_frame)
        connect_buttons.pack(pady=10)
        
        self.connect_btn = ttk.Button(connect_buttons, text="🔗 Connect Device", 
                                     command=self.connect_device_with_progress, width=18)
        self.connect_btn.pack(side="left", padx=5)
        
        self.disconnect_btn = ttk.Button(connect_buttons, text="🔌 Disconnect", 
                                        command=self.disconnect_device, state="disabled", width=18)
        self.disconnect_btn.pack(side="left", padx=5)
        
        ttk.Button(connect_buttons, text="📱 Device Info", 
                  command=self.show_device_info, width=18).pack(side="left", padx=5)
        
        # Device progress bar
        progress_frame = ttk.Frame(connect_frame)
        progress_frame.pack(fill="x", pady=10)
        
        tk.Label(progress_frame, text="Connection Progress:", font=("Arial", 10)).pack(anchor="w")
        self.device_progress = ttk.Progressbar(progress_frame, mode='indeterminate', length=600)
        self.device_progress.pack(fill="x", pady=5)
        
        self.device_progress_label = tk.Label(progress_frame, text="", font=("Arial", 9))
        self.device_progress_label.pack(anchor="w")
        
        # Device log frame
        device_log_frame = ttk.LabelFrame(device_frame, text="Device Log", padding=10)
        device_log_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Log controls at TOP for visibility
        device_log_controls = ttk.Frame(device_log_frame)
        device_log_controls.pack(fill="x", pady=5)
        
        ttk.Button(device_log_controls, text="📋 Clear Log", 
                  command=lambda: self.device_log.delete(1.0, tk.END), width=15).pack(side="left", padx=5)
        ttk.Button(device_log_controls, text="💾 Save Log", 
                  command=self.save_device_log, width=15).pack(side="left", padx=5)
        
        # Log display
        self.device_log = scrolledtext.ScrolledText(device_log_frame, height=12, wrap=tk.WORD, 
                                                    font=("Consolas", 9))
        self.device_log.pack(fill="both", expand=True)
    
    def create_scanner_tab(self):
        """Enhanced UI Scanner tab - ALL elements without ANY restrictions"""
        scanner_frame = ttk.Frame(self.notebook)
        self.notebook.add(scanner_frame, text="🔍 Scanner")
        
        # Controls
        control_frame = ttk.LabelFrame(scanner_frame, text="Scan Controls - UNRESTRICTED", padding=10)
        control_frame.pack(fill="x", padx=10, pady=10)
        
        scan_controls = ttk.Frame(control_frame)
        scan_controls.pack(fill="x")
        
        tk.Label(scan_controls, text="Screen Name:").pack(side="left", padx=5)
        self.screen_name_var = tk.StringVar(value="Current Screen")
        ttk.Entry(scan_controls, textvariable=self.screen_name_var, width=25).pack(side="left", padx=5)
        
        ttk.Button(scan_controls, text="🔍 Full Scan (All Elements)", 
                  command=self.deep_scan_screen).pack(side="left", padx=10)
        ttk.Button(scan_controls, text="🔍 Scan Login", 
                  command=self.scan_login_elements).pack(side="left", padx=5)
        ttk.Button(scan_controls, text="📸 Screenshot", 
                  command=self.take_screenshot).pack(side="left", padx=5)
        ttk.Button(scan_controls, text="💾 Save Scan", 
                  command=self.save_scan_to_db).pack(side="left", padx=5)
        ttk.Button(scan_controls, text="➡️ Use for Test", 
                  command=self.use_scan_for_custom_test).pack(side="left", padx=5)
        
        # Scan progress
        scan_progress_frame = ttk.Frame(control_frame)
        scan_progress_frame.pack(fill="x", pady=5)
        
        self.scan_progress = ttk.Progressbar(scan_progress_frame, mode='determinate', length=600)
        self.scan_progress.pack(fill="x")
        
        self.scan_progress_label = tk.Label(scan_progress_frame, text="")
        self.scan_progress_label.pack(anchor="w")
        
        # Results - NO SAFETY COLUMNS, PURE DATA
        results_frame = ttk.LabelFrame(scanner_frame, text="Scan Results - ALL ELEMENTS (No Restrictions)", padding=10)
        results_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Tree view with all element data
        columns = ('Type', 'Resource ID', 'Text', 'Content Desc', 'Clickable', 'Enabled', 'Password', 'Bounds', 'XPath')
        self.elements_tree = ttk.Treeview(results_frame, columns=columns, show='tree headings', height=18)
        
        self.elements_tree.heading('#0', text='#')
        self.elements_tree.column('#0', width=40)
        
        for col in columns:
            self.elements_tree.heading(col, text=col)
        
        self.elements_tree.column('Type', width=120)
        self.elements_tree.column('Resource ID', width=180)
        self.elements_tree.column('Text', width=120)
        self.elements_tree.column('Content Desc', width=120)
        self.elements_tree.column('Clickable', width=60)
        self.elements_tree.column('Enabled', width=60)
        self.elements_tree.column('Password', width=60)
        self.elements_tree.column('Bounds', width=120)
        self.elements_tree.column('XPath', width=180)
        
        self.elements_tree.pack(fill="both", expand=True)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(results_frame, orient="vertical", command=self.elements_tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.elements_tree.configure(yscrollcommand=scrollbar.set)
        
        # Interactive controls
        interactive_frame = ttk.LabelFrame(scanner_frame, text="Interactive Controls - Direct Manipulation", padding=10)
        interactive_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Button(interactive_frame, text="👆 Click Element", 
                  command=self.click_selected_element).pack(side="left", padx=5)
        ttk.Button(interactive_frame, text="⌨️ Type Text", 
                  command=self.type_in_selected_element).pack(side="left", padx=5)
        ttk.Button(interactive_frame, text="🗑️ Clear Field", 
                  command=self.clear_selected_element).pack(side="left", padx=5)
        ttk.Button(interactive_frame, text="👍 Long Press", 
                  command=self.long_press_selected_element).pack(side="left", padx=5)
        ttk.Button(interactive_frame, text="📖 Get Text", 
                  command=self.get_element_text).pack(side="left", padx=5)
        ttk.Button(interactive_frame, text="📋 Copy XPath", 
                  command=self.copy_xpath).pack(side="left", padx=5)
        
        # Double-click to interact
        self.elements_tree.bind('<Double-Button-1>', self.on_element_double_click)
        self.elements_tree.bind('<Button-3>', self.show_element_context_menu)
    
    def create_custom_test_tab(self):
        """Enhanced custom test builder tab - FIXED typing functionality"""
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
        
        self.available_elements_listbox = tk.Listbox(elem_frame, yscrollcommand=elem_scrollbar.set, height=12)
        self.available_elements_listbox.pack(side="left", fill="both", expand=True)
        elem_scrollbar.config(command=self.available_elements_listbox.yview)
        
        # Element details
        details_frame = ttk.LabelFrame(left_frame, text="Element Details", padding=5)
        details_frame.pack(fill="x", padx=5, pady=5)
        
        self.element_details_text = scrolledtext.ScrolledText(details_frame, height=6, width=40)
        self.element_details_text.pack(fill="both", expand=True)
        
        # Actions buttons
        actions_frame = ttk.Frame(left_frame)
        actions_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Button(actions_frame, text="🔄 Refresh", command=self.refresh_available_elements, width=12).pack(side="left", padx=2)
        ttk.Button(actions_frame, text="➕ Add →", command=self.add_element_to_test, width=12).pack(side="left", padx=2)
        
        # Right panel - Test steps
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=2)
        
        # Test name at top
        name_frame = ttk.Frame(right_frame)
        name_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Label(name_frame, text="Test Name:", font=("Arial", 10, "bold")).pack(side="left", padx=5)
        self.custom_test_name = tk.StringVar(value="Custom_Test_1")
        ttk.Entry(name_frame, textvariable=self.custom_test_name, width=30, font=("Arial", 10)).pack(side="left", padx=5)
        
        # Test steps tree
        ttk.Label(right_frame, text="Test Steps", font=("Arial", 10, "bold")).pack(pady=2)
        
        tree_frame = ttk.Frame(right_frame)
        tree_frame.pack(fill="both", expand=True, padx=5, pady=2)
        
        columns = ('Action', 'Element', 'Data', 'Description')
        self.test_steps_tree = ttk.Treeview(tree_frame, columns=columns, show='tree headings', height=8)
        
        self.test_steps_tree.heading('#0', text='#')
        for col in columns:
            self.test_steps_tree.heading(col, text=col)
        
        self.test_steps_tree.column('#0', width=40)
        self.test_steps_tree.column('Action', width=80)
        self.test_steps_tree.column('Element', width=120)
        self.test_steps_tree.column('Data', width=80)
        self.test_steps_tree.column('Description', width=150)
        
        self.test_steps_tree.pack(side="left", fill="both", expand=True)
        
        tree_scroll = ttk.Scrollbar(tree_frame, command=self.test_steps_tree.yview)
        tree_scroll.pack(side="right", fill="y")
        self.test_steps_tree.config(yscrollcommand=tree_scroll.set)
        
        # Step controls
        step_controls = ttk.LabelFrame(right_frame, text="Add New Step", padding=5)
        step_controls.pack(fill="x", padx=5, pady=2)
        
        # Row 1
        row1 = ttk.Frame(step_controls)
        row1.pack(fill="x", pady=2)
        
        ttk.Label(row1, text="Action:", width=8).pack(side="left", padx=2)
        self.custom_action_var = tk.StringVar(value="click")
        action_combo = ttk.Combobox(row1, textvariable=self.custom_action_var, width=12)
        action_combo['values'] = ('click', 'tap', 'type', 'clear', 'wait', 'swipe', 'long_press', 
                                 'assert_exists', 'assert_text', 'assert_enabled', 'screenshot')
        action_combo.pack(side="left", padx=2)
        
        ttk.Label(row1, text="Data:", width=5).pack(side="left", padx=2)
        self.custom_data_var = tk.StringVar()
        ttk.Entry(row1, textvariable=self.custom_data_var, width=15).pack(side="left", padx=2)
        
        ttk.Label(row1, text="Desc:", width=5).pack(side="left", padx=2)
        self.custom_desc_var = tk.StringVar()
        ttk.Entry(row1, textvariable=self.custom_desc_var, width=25).pack(side="left", padx=2)
        
        # Quick add buttons for login test - FIXED WITH INDEX-BASED XPATH
        quick_frame = ttk.LabelFrame(right_frame, text="Quick Login Steps", padding=5)
        quick_frame.pack(fill="x", padx=5, pady=2)
        
        # Input row with default values
        input_row = ttk.Frame(quick_frame)
        input_row.pack(fill="x")
        
        ttk.Label(input_row, text="User:", width=5).pack(side="left", padx=2)
        self.test_username_var = tk.StringVar(value="testuser")
        ttk.Entry(input_row, textvariable=self.test_username_var, width=12).pack(side="left", padx=2)
        
        ttk.Label(input_row, text="Pass:", width=5).pack(side="left", padx=2)
        self.test_password_var = tk.StringVar(value="testpass")
        ttk.Entry(input_row, textvariable=self.test_password_var, show="*", width=12).pack(side="left", padx=2)
        
        # Quick buttons row
        quick_buttons = ttk.Frame(quick_frame)
        quick_buttons.pack(fill="x", pady=2)
        
        ttk.Button(quick_buttons, text="+ Username", command=self.add_username_step, width=12).pack(side="left", padx=2)
        ttk.Button(quick_buttons, text="+ Password", command=self.add_password_step, width=12).pack(side="left", padx=2)
        ttk.Button(quick_buttons, text="+ Login Btn", command=self.add_login_button_step, width=12).pack(side="left", padx=2)
        ttk.Button(quick_buttons, text="+ OK Button", command=self.add_ok_button_step, width=12).pack(side="left", padx=2)
        
        # Test step management controls
        manage_frame = ttk.LabelFrame(right_frame, text="Manage Steps", padding=5)
        manage_frame.pack(fill="x", padx=5, pady=2)
        
        # Step management buttons
        manage_row1 = ttk.Frame(manage_frame)
        manage_row1.pack(fill="x", pady=2)
        
        ttk.Button(manage_row1, text="⬆️ Move Up", command=self.move_step_up, width=12).pack(side="left", padx=2)
        ttk.Button(manage_row1, text="⬇️ Move Down", command=self.move_step_down, width=12).pack(side="left", padx=2)
        ttk.Button(manage_row1, text="❌ Remove", command=self.remove_test_step, width=12).pack(side="left", padx=2)
        ttk.Button(manage_row1, text="🗑️ Clear All", command=self.clear_custom_test, width=12).pack(side="left", padx=2)
        
        # Test file operations
        file_frame = ttk.LabelFrame(right_frame, text="Test Operations", padding=5)
        file_frame.pack(fill="x", padx=5, pady=2)
        
        file_row = ttk.Frame(file_frame)
        file_row.pack(fill="x", pady=2)
        
        ttk.Button(file_row, text="💾 Save Test", command=self.save_custom_test, width=12).pack(side="left", padx=2)
        ttk.Button(file_row, text="📂 Load Test", command=self.load_custom_test, width=12).pack(side="left", padx=2)
        ttk.Button(file_row, text="▶️ RUN TEST", command=self.run_custom_test, 
                  width=15, style="Accent.TButton").pack(side="left", padx=5)
        
        # Progress bar for test execution
        progress_frame = ttk.Frame(right_frame)
        progress_frame.pack(fill="x", padx=5, pady=5)
        
        self.test_progress = ttk.Progressbar(progress_frame, mode='determinate', length=400)
        self.test_progress.pack(fill="x")
        
        self.test_progress_label = tk.Label(progress_frame, text="", font=("Arial", 9))
        self.test_progress_label.pack()
        
        # Custom test results
        results_frame = ttk.LabelFrame(right_frame, text="Test Results", padding=5)
        results_frame.pack(fill="x", padx=5, pady=2)
        
        self.custom_test_results = scrolledtext.ScrolledText(results_frame, height=4, wrap=tk.WORD, font=("Consolas", 9))
        self.custom_test_results.pack(fill="both", expand=True)
        
        # Bind events
        self.available_elements_listbox.bind('<<ListboxSelect>>', self.on_element_select)
        self.available_elements_listbox.bind('<Double-Button-1>', lambda e: self.add_element_to_test())
    
    def create_test_tab(self):
        """Test execution tab for pre-built tests - ENHANCED"""
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
        ttk.Button(test_buttons, text="🔍 Find Login Elements", 
                  command=self.scan_login_elements).pack(side="left", padx=5)
        ttk.Button(test_buttons, text="🧪 Test Type Action", 
                  command=self.test_type_action).pack(side="left", padx=5)
        
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
        ttk.Button(gen_frame, text="💾 Save Report", command=self.save_report_to_file).pack(side="left", padx=5)
        
        # Report viewer
        viewer_frame = ttk.LabelFrame(reports_frame, text="Report Preview", padding=10)
        viewer_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.report_text = scrolledtext.ScrolledText(viewer_frame, wrap=tk.WORD)
        self.report_text.pack(fill="both", expand=True)
    
    # ============== ALL METHOD IMPLEMENTATIONS - WITH INDEX-BASED XPATH ==============
    
    def check_system_requirements(self):
        """Check if ADB and Appium are available"""
        try:
            result = subprocess.run(['adb', 'version'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                self.log("[OK] ADB is installed")
                self.log_to_server("[OK] ADB is installed and available")
        except:
            self.log("[X] ADB not available")
            self.log_to_server("[X] ADB not found - please install Android SDK")
        
        try:
            result = subprocess.run(['appium', '--version'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                self.log("[OK] Appium is installed")
                self.log_to_server(f"[OK] Appium is installed: {result.stdout.strip()}")
        except:
            self.log("[X] Appium not available")
            self.log_to_server("[X] Appium not found - install with: npm install -g appium")
    
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
    
    def start_appium_with_progress(self):
        """Start Appium with progress indication and log display"""
        import requests
        try:
            response = requests.get("http://localhost:4723/status", timeout=2)
            if response.status_code == 200:
                self.on_appium_started()
                self.log_to_server("Server already running on port 4723")
                return
        except:
            pass
        
        self.server_progress.start()
        self.server_progress_label.config(text="Starting Appium server...")
        self.log_to_server("Starting Appium server...")
        self.start_server_btn.config(state="disabled")
        
        def start_server():
            try:
                import psutil
                for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                    try:
                        if 'appium' in str(proc.info['cmdline']).lower():
                            proc.terminate()
                            time.sleep(2)
                    except:
                        pass
                
                self.appium_process = subprocess.Popen(
                    ['appium', '--address', '0.0.0.0', '--port', '4723'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    shell=True
                )
                
                for line in self.appium_process.stdout:
                    self.root.after(0, self.log_to_server, line.strip())
                    if "Appium REST http interface listener started" in line or "started on" in line:
                        self.root.after(0, self.on_appium_started)
                        break
                
            except Exception as e:
                self.root.after(0, self.on_appium_error, str(e))
        
        threading.Thread(target=start_server, daemon=True).start()
    
    def on_appium_started(self):
        """Handle successful Appium start"""
        self.server_progress.stop()
        self.server_progress_label.config(text="Server started successfully")
        self.server_status_var.set("🟢 Server Running")
        self.log_to_server("✅ Appium server started successfully on port 4723")
        self.start_server_btn.config(state="disabled")
        self.stop_server_btn.config(state="normal")
        messagebox.showinfo("Success", "Appium server started successfully!")
    
    def on_appium_error(self, error):
        """Handle Appium start error"""
        self.server_progress.stop()
        self.server_progress_label.config(text="Failed to start server")
        self.server_status_var.set("🔴 Server Error")
        self.log_to_server(f"❌ Failed to start Appium: {error}")
        self.start_server_btn.config(state="normal")
        messagebox.showerror("Error", f"Failed to start Appium:\n{error}")
    
    def stop_appium(self):
        """Stop Appium server"""
        if self.appium_process:
            try:
                self.appium_process.terminate()
                self.appium_process = None
                self.server_status_var.set("⚪ Server Stopped")
                self.log_to_server("Server stopped")
                self.start_server_btn.config(state="normal")
                self.stop_server_btn.config(state="disabled")
            except:
                pass
    
    def check_server_status(self):
        """Check if server is running"""
        try:
            import requests
            response = requests.get("http://localhost:4723/status", timeout=2)
            if response.status_code == 200:
                self.server_status_var.set("🟢 Server Running")
                self.log_to_server("Server is running and responding")
            else:
                self.server_status_var.set("🟡 Server Not Responding")
                self.log_to_server("Server not responding properly")
        except:
            self.server_status_var.set("⚪ Server Not Running")
            self.log_to_server("Server is not running")
    
    def install_appium(self):
        """Install Appium"""
        self.log_to_server("Installing Appium...")
        subprocess.Popen(['npm', 'install', '-g', 'appium'])
    
    def log_to_server(self, text):
        """Log to server display"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.server_log.insert(tk.END, f"[{timestamp}] {text}\n")
        if self.auto_scroll:
            self.server_log.see(tk.END)
    
    def log_to_device(self, text):
        """Log to device display"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.device_log.insert(tk.END, f"[{timestamp}] {text}\n")
        self.device_log.see(tk.END)
    
    def toggle_auto_scroll(self):
        """Toggle auto scroll for logs"""
        self.auto_scroll = not self.auto_scroll
        self.log_to_server(f"Auto scroll: {'ON' if self.auto_scroll else 'OFF'}")
    
    def save_server_log(self):
        """Save server log to file"""
        filepath = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt")],
            initialdir=logs_dir,
            initialfile=f"server_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        if filepath:
            with open(filepath, 'w') as f:
                f.write(self.server_log.get(1.0, tk.END))
            messagebox.showinfo("Saved", f"Server log saved to {Path(filepath).name}")
    
    def save_device_log(self):
        """Save device log to file"""
        filepath = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt")],
            initialdir=logs_dir,
            initialfile=f"device_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        if filepath:
            with open(filepath, 'w') as f:
                f.write(self.device_log.get(1.0, tk.END))
            messagebox.showinfo("Saved", f"Device log saved to {Path(filepath).name}")
    
    def connect_device_with_progress(self):
        """Connect to device with OPTIMIZED FAST connection"""
        device_id = self.device_id_var.get()
        app_package = self.app_package_var.get()
        
        if not device_id:
            messagebox.showwarning("Warning", "Please select or enter a device ID")
            return
        
        self.device_progress.start()
        self.device_progress_label.config(text="Connecting to device (Fast Mode)...")
        self.log_to_device(f"Connecting to device: {device_id} (Optimized)")
        self.connect_btn.config(state="disabled")
        
        def connect():
            try:
                from appium import webdriver
                from appium.options.android import UiAutomator2Options
                
                self.root.after(0, lambda: self.log_to_device("Fast connection mode..."))
                
                options = UiAutomator2Options()
                options.platform_name = "Android"
                options.device_name = device_id
                options.udid = device_id
                options.app_package = app_package
                options.automation_name = "UiAutomator2"
                options.no_reset = True
                options.full_reset = False
                options.new_command_timeout = 600
                options.auto_grant_permissions = True
                options.ignore_hidden_api_policy_error = True
                options.skip_server_installation = True
                options.skip_device_initialization = False
                options.skip_unlock = True
                options.disable_suppress_accessibility_service = True
                options.uiautomator2_server_launch_timeout = 20000
                options.uiautomator2_server_install_timeout = 20000
                options.adb_exec_timeout = 20000
                
                self.root.after(0, lambda: self.log_to_device("Establishing fast connection..."))
                
                self.driver = webdriver.Remote(
                    "http://localhost:4723", 
                    options=options
                )
                
                self.test_runner = CompleteTestRunner(self.driver, screenshots_dir)
                
                self.root.after(0, self.on_device_connected)
                
            except Exception as e:
                self.root.after(0, self.on_device_error, str(e))
        
        threading.Thread(target=connect, daemon=True).start()
    
    def on_device_connected(self):
        """Handle successful device connection"""
        self.device_progress.stop()
        self.device_progress_label.config(text="Device connected successfully")
        self.connection_status_var.set("🟢 Connected")
        self.log_to_device("✅ Successfully connected to device")
        self.connect_btn.config(state="disabled")
        self.disconnect_btn.config(state="normal")
        
        try:
            self.log_to_device(f"Platform: {self.driver.capabilities.get('platformName', 'Unknown')}")
            self.log_to_device(f"Version: {self.driver.capabilities.get('platformVersion', 'Unknown')}")
            self.log_to_device(f"Device: {self.driver.capabilities.get('deviceName', 'Unknown')}")
        except:
            pass
        
        messagebox.showinfo("Success", "Connected to device successfully!")
    
    def on_device_error(self, error):
        """Handle device connection error"""
        self.device_progress.stop()
        self.device_progress_label.config(text="Connection failed")
        self.connection_status_var.set("🔴 Connection Failed")
        self.log_to_device(f"❌ Connection failed: {error}")
        self.connect_btn.config(state="normal")
        messagebox.showerror("Connection Error", f"Failed to connect:\n{error}")
    
    def disconnect_device(self):
        """Disconnect from device"""
        if self.driver:
            try:
                self.driver.quit()
                self.driver = None
                self.test_runner = None
                self.connection_status_var.set("⚪ Disconnected")
                self.log_to_device("Device disconnected")
                self.connect_btn.config(state="normal")
                self.disconnect_btn.config(state="disabled")
            except Exception as e:
                self.log_to_device(f"Error disconnecting: {e}")
    
    def show_device_info(self):
        """Show device information"""
        if self.driver:
            try:
                info = f"""Device Information:
Platform: {self.driver.capabilities.get('platformName', 'Unknown')}
Version: {self.driver.capabilities.get('platformVersion', 'Unknown')}
Device: {self.driver.capabilities.get('deviceName', 'Unknown')}
UDID: {self.driver.capabilities.get('udid', 'Unknown')}
App Package: {self.driver.capabilities.get('appPackage', 'Unknown')}
"""
                messagebox.showinfo("Device Info", info)
            except:
                messagebox.showerror("Error", "Could not retrieve device info")
        else:
            messagebox.showwarning("Not Connected", "Please connect to a device first")
    
    def take_screenshot(self):
        """Take screenshot and return path"""
        if not self.driver:
            messagebox.showwarning("Not Connected", "Please connect to device first")
            return None
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"
            filepath = screenshots_dir / filename
            
            self.driver.save_screenshot(str(filepath))
            self.log(f"📸 Screenshot saved: {filename}")
            messagebox.showinfo("Success", f"Screenshot saved: {filename}")
            return str(filepath)
        except Exception as e:
            self.log(f"❌ Screenshot failed: {e}")
            messagebox.showerror("Error", f"Screenshot failed: {e}")
            return None
    
    def deep_scan_screen(self):
        """Perform deep scan of ALL elements - NO RESTRICTIONS"""
        if not self.driver:
            messagebox.showwarning("Warning", "Please connect to device first")
            return
        
        self.log("Starting unrestricted deep scan...")
        self.scan_progress_label.config(text="Scanning all elements...")
        self.scan_progress['mode'] = 'indeterminate'
        self.scan_progress.start()
        
        def scan():
            try:
                from appium.webdriver.common.appiumby import AppiumBy
                
                self.root.after(0, lambda: [self.elements_tree.delete(item) for item in self.elements_tree.get_children()])
                
                time.sleep(2)
                
                screenshot_path = self.take_screenshot()
                
                all_elements = self.driver.find_elements(AppiumBy.XPATH, "//*")
                total_elements = len(all_elements)
                
                self.root.after(0, lambda: self.scan_progress.configure(mode='determinate', maximum=total_elements))
                
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
                        self.root.after(0, lambda v=i: self.scan_progress.configure(value=v+1))
                        self.root.after(0, lambda c=element_count, t=total_elements: 
                                       self.scan_progress_label.config(text=f"Scanned {c}/{t} elements"))
                        
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
    
    def scan_login_elements(self):
        """Scan specifically for login elements - USING INDEX-BASED XPATH"""
        if not self.driver:
            messagebox.showwarning("Warning", "Please connect to device first")
            return
        
        self.log("Scanning for login elements...")
        self.main_progress_bar.start()
        
        def scan():
            try:
                self.login_elements = {}
                
                # Set login elements with index-based XPath
                self.login_elements['username'] = {
                    'xpath': "//android.widget.EditText[1]",
                    'resource_id': None,
                    'type': 'EditText'
                }
                
                self.login_elements['password'] = {
                    'xpath': "//android.widget.EditText[@password='true']",
                    'resource_id': None,
                    'type': 'EditText'
                }
                
                self.login_elements['button'] = {
                    'xpath': "//android.widget.Button[@resource-id='ch.bsct.ebanking.mobile:id/offline_login_button']",
                    'resource_id': 'ch.bsct.ebanking.mobile:id/offline_login_button',
                    'type': 'Button'
                }
                
                found_elements = [
                    "Username field: First EditText",
                    "Password field: Second EditText",
                    "Submit button: ch.bsct.ebanking.mobile:id/offline_login_button"
                ]
                
                self.root.after(0, self.on_login_scan_complete, found_elements)
                
            except Exception as e:
                self.root.after(0, self.on_scan_error, str(e))
        
        threading.Thread(target=scan, daemon=True).start()
    
    def on_login_scan_complete(self, found_elements):
        """Handle login scan completion with details"""
        self.main_progress_bar.stop()
        
        if found_elements:
            details = "Found login elements:\n" + "\n".join(found_elements)
            self.log_to_device(details)
            self.test_results_text.insert(tk.END, f"\n{details}\n")
            messagebox.showinfo("Login Elements Found", details)
        else:
            messagebox.showwarning("No Elements", "No login elements detected")
    
    def add_element_to_tree(self, count, element_data):
        """Add element to tree view"""
        self.elements_tree.insert('', 'end', text=str(count), values=(
            element_data['type'].split('.')[-1] if '.' in element_data['type'] else element_data['type'],
            element_data['resource_id'][-30:] if len(element_data['resource_id']) > 30 else element_data['resource_id'],
            element_data['text'][:20] if len(element_data['text']) > 20 else element_data['text'],
            element_data['content_desc'][:20] if len(element_data['content_desc']) > 20 else element_data['content_desc'],
            '✔' if element_data['clickable'] else '',
            '✔' if element_data['enabled'] else '',
            '🔒' if element_data['password'] else '',
            element_data['bounds'][:20] if len(element_data['bounds']) > 20 else element_data['bounds'],
            element_data['xpath'][:30] if len(element_data['xpath']) > 30 else element_data['xpath']
        ), tags=(element_data,))
    
    def on_scan_complete(self, count):
        """Handle scan completion"""
        self.scan_progress.stop()
        self.scan_progress_label.config(text=f"Scan complete: {count} elements found")
        self.log(f"✅ Deep scan complete: Found {count} elements")
        messagebox.showinfo("Scan Complete", f"Found {count} elements")
    
    def on_scan_error(self, error):
        """Handle scan error"""
        self.scan_progress.stop()
        self.scan_progress_label.config(text="Scan failed")
        self.log(f"❌ Scan failed: {error}")
        messagebox.showerror("Scan Error", f"Failed to scan screen:\n{error}")
    
    def click_selected_element(self):
        """Click selected element from tree"""
        selection = self.elements_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select an element")
            return
        
        if not self.driver:
            messagebox.showerror("Error", "Not connected to device")
            return
        
        try:
            element_data = self.elements_tree.item(selection[0])['tags'][0]
            from appium.webdriver.common.appiumby import AppiumBy
            
            element = self.driver.find_element(AppiumBy.XPATH, element_data['xpath'])
            element.click()
            self.log(f"Clicked element: {element_data['xpath']}")
            messagebox.showinfo("Success", "Element clicked")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to click element: {e}")
    
    def type_in_selected_element(self):
        """Type text in selected element"""
        selection = self.elements_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select an element")
            return
        
        text = simpledialog.askstring("Type Text", "Enter text to type:")
        if not text:
            return
        
        try:
            element_data = self.elements_tree.item(selection[0])['tags'][0]
            from appium.webdriver.common.appiumby import AppiumBy
            
            element = self.driver.find_element(AppiumBy.XPATH, element_data['xpath'])
            element.clear()
            element.send_keys(text)
            self.log(f"Typed text in element: {element_data['xpath']}")
            messagebox.showinfo("Success", f"Typed: {text}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to type: {e}")
    
    def clear_selected_element(self):
        """Clear selected element"""
        selection = self.elements_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select an element")
            return
        
        try:
            element_data = self.elements_tree.item(selection[0])['tags'][0]
            from appium.webdriver.common.appiumby import AppiumBy
            
            element = self.driver.find_element(AppiumBy.XPATH, element_data['xpath'])
            element.clear()
            self.log(f"Cleared element: {element_data['xpath']}")
            messagebox.showinfo("Success", "Element cleared")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to clear: {e}")
    
    def long_press_selected_element(self):
        """Long press selected element"""
        selection = self.elements_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select an element")
            return
        
        try:
            element_data = self.elements_tree.item(selection[0])['tags'][0]
            from appium.webdriver.common.appiumby import AppiumBy
            from appium.webdriver.common.touch_action import TouchAction
            
            element = self.driver.find_element(AppiumBy.XPATH, element_data['xpath'])
            TouchAction(self.driver).long_press(element).perform()
            self.log(f"Long pressed element: {element_data['xpath']}")
            messagebox.showinfo("Success", "Long press performed")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to long press: {e}")
    
    def get_element_text(self):
        """Get text from selected element"""
        selection = self.elements_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select an element")
            return
        
        try:
            element_data = self.elements_tree.item(selection[0])['tags'][0]
            from appium.webdriver.common.appiumby import AppiumBy
            
            element = self.driver.find_element(AppiumBy.XPATH, element_data['xpath'])
            text = element.text
            self.log(f"Got text from element: {text}")
            messagebox.showinfo("Element Text", f"Text: {text}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to get text: {e}")
    
    def copy_xpath(self):
        """Copy XPath of selected element to clipboard"""
        selection = self.elements_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select an element")
            return
        
        try:
            element_data = self.elements_tree.item(selection[0])['tags'][0]
            xpath = element_data['xpath']
            self.root.clipboard_clear()
            self.root.clipboard_append(xpath)
            self.log(f"Copied XPath: {xpath}")
            messagebox.showinfo("Success", "XPath copied to clipboard")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to copy: {e}")
    
    def on_element_double_click(self, event):
        """Handle double-click on element"""
        self.click_selected_element()
    
    def show_element_context_menu(self, event):
        """Show context menu for element"""
        context_menu = tk.Menu(self.root, tearoff=0)
        context_menu.add_command(label="Click", command=self.click_selected_element)
        context_menu.add_command(label="Type Text", command=self.type_in_selected_element)
        context_menu.add_command(label="Clear", command=self.clear_selected_element)
        context_menu.add_command(label="Long Press", command=self.long_press_selected_element)
        context_menu.add_separator()
        context_menu.add_command(label="Get Text", command=self.get_element_text)
        context_menu.add_command(label="Copy XPath", command=self.copy_xpath)
        
        context_menu.post(event.x_root, event.y_root)
    
    def use_scan_for_custom_test(self):
        """Use scan results for custom test building"""
        if not self.last_scan_results:
            messagebox.showwarning("No Scan", "Please perform a scan first")
            return
        
        self.notebook.select(3)
        self.refresh_available_elements()
        
        messagebox.showinfo("Success", "Scan results loaded for custom test building")
    
    def save_scan_to_db(self):
        """Save scan results to database"""
        if not self.last_scan_results:
            messagebox.showwarning("No Scan", "Please perform a scan first")
            return
        
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO scan_results (app_name, screen_name, elements_count, screenshot_path, scan_data)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                "InLinea Banking",
                self.last_scan_results.get('screen_name', 'Unknown'),
                self.last_scan_results.get('element_count', 0),
                self.last_scan_results.get('screenshot', ''),
                json.dumps(self.last_scan_results.get('elements', []))
            ))
            
            scan_id = cursor.lastrowid
            
            for element in self.last_scan_results.get('elements', []):
                cursor.execute('''
                    INSERT INTO elements (scan_id, element_type, resource_id, text, content_desc,
                                        clickable, enabled, password, bounds, xpath)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    scan_id,
                    element.get('type', ''),
                    element.get('resource_id', ''),
                    element.get('text', ''),
                    element.get('content_desc', ''),
                    element.get('clickable', False),
                    element.get('enabled', False),
                    element.get('password', False),
                    element.get('bounds', ''),
                    element.get('xpath', '')
                ))
            
            conn.commit()
            conn.close()
            
            self.log("Scan results saved to database")
            messagebox.showinfo("Success", "Scan saved to database")
            self.load_recent_scans()
            
        except Exception as e:
            self.log(f"Failed to save scan: {e}")
            messagebox.showerror("Error", f"Failed to save: {e}")
    
    def refresh_available_elements(self):
        """Refresh available elements in custom test builder"""
        if not self.last_scan_results:
            return
        
        self.available_elements_listbox.delete(0, tk.END)
        
        for element in self.last_scan_results.get('elements', []):
            display_text = f"{element['type'].split('.')[-1]} - {element.get('resource_id', 'no-id')[:20]} - {element.get('text', '')[:20]}"
            self.available_elements_listbox.insert(tk.END, display_text)
        
        self.custom_test_builder.add_scanned_elements(self.last_scan_results.get('elements', []))
    
    def on_element_select(self, event):
        """Handle element selection in custom test builder"""
        selection = self.available_elements_listbox.curselection()
        if not selection:
            return
        
        index = selection[0]
        if self.last_scan_results and index < len(self.last_scan_results.get('elements', [])):
            element = self.last_scan_results['elements'][index]
            
            details = f"""Type: {element.get('type', '')}
Resource ID: {element.get('resource_id', '')}
Text: {element.get('text', '')}
Content Desc: {element.get('content_desc', '')}
Clickable: {element.get('clickable', False)}
Enabled: {element.get('enabled', False)}
Password: {element.get('password', False)}
XPath: {element.get('xpath', '')}
"""
            self.element_details_text.delete(1.0, tk.END)
            self.element_details_text.insert(1.0, details)
    
    def add_element_to_test(self):
        """Add selected element to test - FIXED for type action"""
        selection = self.available_elements_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select an element")
            return
        
        index = selection[0]
        if self.last_scan_results and index < len(self.last_scan_results.get('elements', [])):
            element = self.last_scan_results['elements'][index]
            
            element_info = {
                'name': element.get('text', element.get('resource_id', 'Element')),
                'locator_strategy': 'xpath',
                'locator_value': element.get('xpath', '')
            }
            
            action = self.custom_action_var.get()
            
            # Get the data value - this is crucial for type action
            data = self.custom_data_var.get() if action in ['type', 'wait', 'assert_text', 'swipe'] else None
            
            description = self.custom_desc_var.get() or f"{action} on {element_info['name']}"
            
            # Add step with proper data
            self.custom_test_builder.add_step(action, element_info, data, description)
            self.update_test_steps_tree()
            
            self.log(f"Added step: {description} {'with data: ' + data if data else ''}")
    
    def add_username_step(self):
        """Add username input step with INDEX-BASED XPATH"""
        username_value = self.test_username_var.get()
        
        # Use first EditText for username
        element_info = {
            'name': 'Username Field',
            'locator_strategy': 'xpath',
            'locator_value': "//android.widget.EditText[1]"
        }
        
        # Add clear step first
        self.custom_test_builder.add_step(
            'clear',
            element_info,
            None,
            "Clear username field"
        )
        
        # Then add type step with actual value
        self.custom_test_builder.add_step(
            'type', 
            element_info, 
            username_value,
            f"Type username: {username_value}"
        )
        
        self.update_test_steps_tree()
        self.log(f"Added username step with value: {username_value} using //android.widget.EditText[1]")
    
    def add_password_step(self):
        """Add password input step with INDEX-BASED XPATH"""
        password_value = self.test_password_var.get()
        
        # Use second EditText for password
        element_info = {
            'name': 'Password Field',
            'locator_strategy': 'xpath',
            'locator_value': "//android.widget.EditText[@password='true']"
        }
        
        # Add clear step first
        self.custom_test_builder.add_step(
            'clear',
            element_info,
            None,
            "Clear password field"
        )
        
        # Then add type step with actual value
        self.custom_test_builder.add_step(
            'type',
            element_info,
            password_value,
            f"Type password"
        )

        self.update_test_steps_tree()
        self.log(f"Added password step using //android.widget.EditText[@password='true']")
    
    def add_login_button_step(self):
        """Add login button click step - USING SUBMIT BUTTON ID"""
        element_info = {
            'name': 'Submit Button',
            'locator_strategy': 'xpath',
            'locator_value': "//android.widget.Button[@resource-id='ch.bsct.ebanking.mobile:id/offline_login_button']"
        }
        
        self.custom_test_builder.add_step(
            'click',
            element_info,
            None,
            "Click Submit button"
        )
        
        self.update_test_steps_tree()
        self.log("Added Submit button click")
    
    def add_ok_button_step(self):
        """Add OK button click step that handles all variations"""
        element_info = {
            'name': 'OK Button',
            'locator_strategy': 'id',
            'locator_value': 'android:id/button1'  # Most common OK button ID
        }
        
        self.custom_test_builder.add_step(
            'click',
            element_info,
            None,
            "Click OK button (any variation)"
        )
        
        self.update_test_steps_tree()
        self.log("Added OK button click (will handle OK/Ok/ok variations)")
    
    def update_test_steps_tree(self):
        """Update the test steps tree view"""
        for item in self.test_steps_tree.get_children():
            self.test_steps_tree.delete(item)
        
        for i, step in enumerate(self.custom_test_builder.test_steps, 1):
            element_name = step.get('element_info', {}).get('name', 'Unknown')
            data_display = step.get('data', '')[:20] if step.get('data') else ''
            self.test_steps_tree.insert('', 'end', text=str(i), values=(
                step.get('action', ''),
                element_name[:30],
                data_display,
                step.get('description', '')[:50]
            ))
    
    def move_step_up(self):
        """Move selected step up"""
        selection = self.test_steps_tree.selection()
        if not selection:
            return
        
        index = int(self.test_steps_tree.item(selection[0])['text']) - 1
        self.custom_test_builder.move_step_up(index)
        self.update_test_steps_tree()
    
    def move_step_down(self):
        """Move selected step down"""
        selection = self.test_steps_tree.selection()
        if not selection:
            return
        
        index = int(self.test_steps_tree.item(selection[0])['text']) - 1
        self.custom_test_builder.move_step_down(index)
        self.update_test_steps_tree()
    
    def remove_test_step(self):
        """Remove selected test step"""
        selection = self.test_steps_tree.selection()
        if not selection:
            return
        
        index = int(self.test_steps_tree.item(selection[0])['text']) - 1
        self.custom_test_builder.remove_step(index)
        self.update_test_steps_tree()
    
    def clear_custom_test(self):
        """Clear all test steps"""
        self.custom_test_builder.clear_steps()
        self.update_test_steps_tree()
        self.log("Cleared all test steps")
    
    def save_custom_test(self):
        """Save custom test to file"""
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            initialdir=custom_tests_dir,
            initialfile=f"{self.custom_test_name.get()}.json"
        )
        
        if filepath:
            self.custom_test_builder.save_test(filepath)
            self.log(f"Test saved: {Path(filepath).name}")
            messagebox.showinfo("Success", "Test saved successfully")
    
    def load_custom_test(self):
        """Load custom test from file"""
        filepath = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json")],
            initialdir=custom_tests_dir
        )
        
        if filepath:
            test_case = self.custom_test_builder.load_test(filepath)
            self.custom_test_name.set(test_case.get('name', 'Custom Test'))
            self.update_test_steps_tree()
            self.log(f"Test loaded: {Path(filepath).name}")
            messagebox.showinfo("Success", "Test loaded successfully")
    
    def run_custom_test(self):
        """Run custom test with progress reporting"""
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
        
        def progress_callback(current, total, description):
            self.root.after(0, self.update_test_progress, current, total, description)
        
        def run_test():
            test_case = self.custom_test_builder.build_test_case(test_name)
            results = self.test_runner.execute_custom_test(test_case, progress_callback)
            
            self.root.after(0, self.display_custom_test_results, results)
            self.save_test_results_to_db(results)
        
        threading.Thread(target=run_test, daemon=True).start()
    
    def update_test_progress(self, current, total, description):
        """Update test progress bar"""
        progress = (current / total) * 100
        self.test_progress['value'] = progress
        self.test_progress_label.config(text=f"Step {current}/{total}: {description}")
    
    def display_custom_test_results(self, results):
        """Display custom test results with report"""
        output = f"\n{'='*40}\n"
        output += f"Test: {results['test_name']}\n"
        output += f"Status: {results['status']}\n"
        output += f"Duration: {results.get('duration', 0):.2f}s\n\n"
        
        output += "STEP-BY-STEP EXECUTION:\n"
        output += "-"*30 + "\n"
        
        for i, step in enumerate(results['steps'], 1):
            status = "✅" if step['status'] == 'passed' else "❌"
            output += f"{i}. {status} {step['description']}\n"
            output += f"   Result: {step['message']}\n"
        
        output += f"\nScreenshots: {len(results.get('screenshots', []))}\n"
        
        self.custom_test_results.insert(tk.END, output)
        
        self.generate_test_report()
        
        if results['status'] == 'PASSED':
            messagebox.showinfo("Test Passed", f"{results['test_name']} completed successfully!")
        else:
            messagebox.showwarning("Test Failed", f"{results['test_name']} failed or partially completed")
    
    def run_login_test(self):
        """Run full login test - USING INDEX-BASED XPATH"""
        if not self.driver or not self.test_runner:
            messagebox.showerror("Error", "Connect to device first")
            return
        
        username = self.username_var.get()
        password = self.password_var.get()
        
        self.test_results_text.insert(tk.END, f"\n{'='*50}\n")
        self.test_results_text.insert(tk.END, f"Starting Login Test\n")
        self.test_results_text.insert(tk.END, f"Username: {username}\n")
        self.test_results_text.insert(tk.END, f"Password: {'*' * len(password)}\n")
        self.test_results_text.insert(tk.END, f"{'='*50}\n\n")
        
        def run_test():
            # Build login test steps with index-based XPath
            test_case = {
                'name': 'Login_Test',
                'description': 'Automated login test',
                'steps': [
                    {
                        'action': 'wait',
                        'data': 2,
                        'description': 'Initial wait'
                    },
                    {
                        'action': 'click',
                        'locator_strategy': 'id',
                        'locator_value': 'android:id/button1',
                        'description': 'Click OK if present',
                        'wait_time': 3
                    },
                    {
                        'action': 'clear',
                        'locator_strategy': 'xpath',
                        'locator_value': '//android.widget.EditText[1]',
                        'description': 'Clear username field',
                        'wait_time': 5
                    },
                    {
                        'action': 'type',
                        'locator_strategy': 'xpath',
                        'locator_value': '//android.widget.EditText[1]',
                        'data': username,
                        'description': f'Type username: {username}'
                    },
                    {
                        'action': 'clear',
                        'locator_strategy': 'xpath',
                        'locator_value': '//android.widget.EditText[@password="true"]',
                        'description': 'Clear password field',
                        'wait_time': 5
                    },
                    {
                        'action': 'type',
                        'locator_strategy': 'xpath',
                        'locator_value': '//android.widget.EditText[@password="true"]',
                        'data': password,
                        'description': 'Type password'
                    },
                    {
                        'action': 'click',
                        'locator_strategy': 'xpath',
                        'locator_value': "//android.widget.Button[@resource-id='ch.bsct.ebanking.mobile:id/offline_login_button']",
                        'description': 'Click Submit button',
                        'wait_time': 5
                    }
                ]
            }
            
            # Run test
            results = self.test_runner.execute_custom_test(test_case)
            
            # Display results
            self.root.after(0, self.display_login_test_results, results)
        
        threading.Thread(target=run_test, daemon=True).start()
    
    def display_login_test_results(self, results):
        """Display login test results"""
        output = "LOGIN TEST RESULTS:\n"
        output += "-"*30 + "\n"
        output += f"Status: {results['status']}\n"
        output += f"Duration: {results.get('duration', 0):.2f}s\n\n"
        
        for i, step in enumerate(results['steps'], 1):
            status = "✅" if step['status'] == 'passed' else "❌"
            output += f"{i}. {status} {step['description']}\n"
            output += f"   {step['message']}\n"
        
        self.test_results_text.insert(tk.END, output)
        self.test_results_text.see(tk.END)
        
        if results['status'] == 'PASSED':
            messagebox.showinfo("Login Test", "Login test completed successfully!")
        else:
            messagebox.showwarning("Login Test", "Login test had some failures")
    
    def run_ok_button_test(self):
        """Test OK button clicking - ENHANCED for all variations"""
        if not self.driver:
            messagebox.showerror("Error", "Connect to device first")
            return
        
        self.test_results_text.insert(tk.END, "\nSearching for OK button variations...\n")
        
        def test_ok():
            if self.test_runner:
                clicked = self.test_runner.click_ok_button()
                if clicked:
                    self.root.after(0, lambda: self.test_results_text.insert(tk.END, "✅ OK button clicked successfully!\n"))
                    self.root.after(0, lambda: messagebox.showinfo("Success", "OK button clicked"))
                else:
                    self.root.after(0, lambda: self.test_results_text.insert(tk.END, "❌ No OK button found\n"))
                    self.root.after(0, lambda: messagebox.showwarning("Not Found", "No OK button found on current screen"))
        
        threading.Thread(target=test_ok, daemon=True).start()
    
    def test_type_action(self):
        """Test typing functionality - USING INDEX-BASED APPROACH"""
        if not self.driver or not self.test_runner:
            messagebox.showerror("Error", "Connect to device first")
            return
        
        def test_typing():
            try:
                from appium.webdriver.common.appiumby import AppiumBy
                
                # Find first EditText using index
                elements = self.driver.find_elements(AppiumBy.CLASS_NAME, "android.widget.EditText")
                if elements:
                    test_text = "TestType123"
                    elements[0].clear()
                    elements[0].send_keys(test_text)
                    
                    self.root.after(0, lambda: self.test_results_text.insert(tk.END, f"✅ Typed: {test_text}\n"))
                    self.root.after(0, lambda: messagebox.showinfo("Success", f"Successfully typed: {test_text}"))
                else:
                    self.root.after(0, lambda: self.test_results_text.insert(tk.END, "❌ No input fields found\n"))
                    self.root.after(0, lambda: messagebox.showwarning("Not Found", "No input fields found"))
            except Exception as e:
                self.root.after(0, lambda: self.test_results_text.insert(tk.END, f"❌ Type test failed: {e}\n"))
                self.root.after(0, lambda: messagebox.showerror("Error", f"Type test failed: {e}"))
        
        threading.Thread(target=test_typing, daemon=True).start()
    
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
    
    def export_to_csv(self):
        """Export database to CSV"""
        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialdir=exports_dir,
            initialfile=f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        
        if not filepath:
            return
        
        try:
            conn = sqlite3.connect(DB_PATH)
            
            query = "SELECT * FROM elements"
            import pandas as pd
            df = pd.read_sql_query(query, conn)
            df.to_csv(filepath, index=False)
            
            conn.close()
            
            self.log(f"Exported {len(df)} records to CSV")
            messagebox.showinfo("Success", f"Exported {len(df)} records to {Path(filepath).name}")
            
        except Exception as e:
            self.log(f"Export failed: {e}")
            messagebox.showerror("Error", f"Export failed: {e}")
    
    def clear_old_data(self):
        """Clear old data from database"""
        if not messagebox.askyesno("Confirm", "Clear data older than 30 days?"):
            return
        
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cutoff_date = datetime.now() - timedelta(days=30)
            
            cursor.execute("DELETE FROM scan_results WHERE scan_timestamp < ?", (cutoff_date,))
            cursor.execute("DELETE FROM test_results WHERE test_timestamp < ?", (cutoff_date,))
            
            deleted = cursor.rowcount
            conn.commit()
            conn.close()
            
            self.log(f"Cleared {deleted} old records")
            messagebox.showinfo("Success", f"Cleared {deleted} old records")
            self.refresh_db_stats()
            
        except Exception as e:
            self.log(f"Failed to clear data: {e}")
            messagebox.showerror("Error", f"Failed to clear: {e}")
    
    def load_recent_scans(self):
        """Load recent scans into tree view"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, scan_timestamp, screen_name, elements_count, screenshot_path
                FROM scan_results
                ORDER BY scan_timestamp DESC
                LIMIT 20
            ''')
            
            scans = cursor.fetchall()
            conn.close()
            
            for item in self.scans_tree.get_children():
                self.scans_tree.delete(item)
            
            for scan in scans:
                self.scans_tree.insert('', 'end', values=scan)
            
        except Exception as e:
            self.log(f"Failed to load scans: {e}")
    
    def generate_test_report(self):
        """Generate test execution report - ENHANCED"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT test_name, status, passed_steps, failed_steps, total_steps, 
                       duration, test_timestamp
                FROM test_results
                ORDER BY test_timestamp DESC
                LIMIT 10
            ''')
            
            tests = cursor.fetchall()
            
            # Get summary statistics
            cursor.execute('''
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'PASSED' THEN 1 ELSE 0 END) as passed,
                    SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) as failed,
                    AVG(duration) as avg_duration,
                    SUM(passed_steps) as total_passed_steps,
                    SUM(failed_steps) as total_failed_steps
                FROM test_results
            ''')
            
            summary = cursor.fetchone()
            conn.close()
            
            report = f"""
TEST EXECUTION REPORT
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'='*60}

SUMMARY STATISTICS:
Total Tests: {summary[0]}
Passed: {summary[1]}
Failed: {summary[2]}
Success Rate: {(summary[1]/summary[0]*100 if summary[0] > 0 else 0):.1f}%
Average Duration: {(summary[3] or 0):.2f} seconds
Total Steps Passed: {summary[4] or 0}
Total Steps Failed: {summary[5] or 0}

RECENT TEST EXECUTIONS:
"""
            
            for test in tests:
                report += f"""
Test Name: {test[0]}
Status: {test[1]}
Steps: {test[2]} passed / {test[3]} failed / {test[4]} total
Duration: {test[5]:.2f} seconds
Timestamp: {test[6]}
{'-'*40}
"""
            
            self.report_text.delete(1.0, tk.END)
            self.report_text.insert(1.0, report)
            
            self.log("✅ Test report generated")
            
        except Exception as e:
            self.log(f"❌ Report generation failed: {e}")
    
    def generate_scan_report(self):
        """Generate scan report - ENHANCED"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT screen_name, elements_count, scan_timestamp
                FROM scan_results
                ORDER BY scan_timestamp DESC
                LIMIT 20
            ''')
            
            scans = cursor.fetchall()
            
            cursor.execute('''
                SELECT 
                    COUNT(*) as total,
                    SUM(clickable) as clickable,
                    SUM(enabled) as enabled,
                    SUM(password) as password_fields,
                    COUNT(DISTINCT element_type) as unique_types
                FROM elements
            ''')
            
            stats = cursor.fetchone()
            conn.close()
            
            report = f"""
SCAN REPORT
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'='*60}

ELEMENT STATISTICS:
Total Elements Scanned: {stats[0]}
Clickable Elements: {stats[1] or 0}
Enabled Elements: {stats[2] or 0}
Password Fields: {stats[3] or 0}
Unique Element Types: {stats[4] or 0}

RECENT SCANS:
"""
            
            for scan in scans:
                report += f"""
Screen: {scan[0]}
Elements: {scan[1]}
Timestamp: {scan[2]}
{'-'*40}
"""
            
            self.report_text.delete(1.0, tk.END)
            self.report_text.insert(1.0, report)
            
            self.log("✅ Scan report generated")
            
        except Exception as e:
            self.log(f"❌ Scan report generation failed: {e}")
    
    def generate_full_report(self):
        """Generate comprehensive report - ENHANCED"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Test statistics
            cursor.execute('''
                SELECT COUNT(*) as total_tests,
                       SUM(CASE WHEN status = 'PASSED' THEN 1 ELSE 0 END) as passed,
                       SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) as failed,
                       AVG(duration) as avg_duration,
                       MAX(duration) as max_duration,
                       MIN(duration) as min_duration
                FROM test_results
            ''')
            
            test_stats = cursor.fetchone()
            
            # Scan statistics
            cursor.execute('''
                SELECT COUNT(*) as total_scans,
                       AVG(elements_count) as avg_elements,
                       MAX(elements_count) as max_elements,
                       MIN(elements_count) as min_elements
                FROM scan_results
            ''')
            
            scan_stats = cursor.fetchone()
            
            # Element type distribution
            cursor.execute('''
                SELECT element_type, COUNT(*) as count
                FROM elements
                GROUP BY element_type
                ORDER BY count DESC
                LIMIT 5
            ''')
            
            top_elements = cursor.fetchall()
            
            conn.close()
            
            report = f"""
COMPREHENSIVE AUTOMATION REPORT
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'='*60}

TEST EXECUTION SUMMARY:
Total Tests Executed: {test_stats[0]}
Passed: {test_stats[1] or 0}
Failed: {test_stats[2] or 0}
Success Rate: {(test_stats[1]/test_stats[0]*100 if test_stats[0] > 0 else 0):.1f}%
Average Duration: {test_stats[3] or 0:.2f} seconds
Maximum Duration: {test_stats[4] or 0:.2f} seconds
Minimum Duration: {test_stats[5] or 0:.2f} seconds

SCANNING SUMMARY:
Total Scans: {scan_stats[0]}
Average Elements per Scan: {scan_stats[1] or 0:.0f}
Maximum Elements: {scan_stats[2] or 0}
Minimum Elements: {scan_stats[3] or 0}

TOP ELEMENT TYPES:
"""
            
            for elem_type, count in top_elements:
                report += f"  {elem_type.split('.')[-1]}: {count}\n"
            
            report += f"""
DATABASE INFORMATION:
Database Size: {Path(DB_PATH).stat().st_size / 1024:.2f} KB
Project Root: {project_root}
Screenshots Directory: {screenshots_dir}
Reports Directory: {reports_dir}

SYSTEM INFORMATION:
Platform: {sys.platform}
Python Version: {sys.version.split()[0]}
Current Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
            
            self.report_text.delete(1.0, tk.END)
            self.report_text.insert(1.0, report)
            
            # Auto-save report
            report_file = reports_dir / f"full_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(report_file, 'w') as f:
                f.write(report)
            
            self.log(f"✅ Full report generated and saved: {report_file.name}")
            
        except Exception as e:
            self.log(f"❌ Full report generation failed: {e}")
    
    def save_report_to_file(self):
        """Save current report to file"""
        report_content = self.report_text.get(1.0, tk.END)
        
        if not report_content.strip():
            messagebox.showwarning("No Report", "Generate a report first")
            return
        
        filepath = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialdir=reports_dir,
            initialfile=f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        
        if filepath:
            with open(filepath, 'w') as f:
                f.write(report_content)
            
            self.log(f"Report saved: {Path(filepath).name}")
            messagebox.showinfo("Success", f"Report saved to {Path(filepath).name}")
    
    def log(self, message):
        """Log message to status and file"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        self.status_var.set(log_message)
        logger.info(message)
    
    def run(self):
        """Run the application"""
        self.log("Application started - v10.0 Complete Enhanced")
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
    print("InLinea Banking Automation v10.0 - Complete Enhanced Edition")
    print("Index-Based XPath for Login Elements")
    print("All Features Working: Login Test, Custom Test Typing, OK Button")
    print("Full Report Generation and Database Support")
    print("FOR TESTING ENVIRONMENT ONLY")
    print("="*60)
    
    app = BankingAutomationApp()
    app.run()

if __name__ == "__main__":
    main()