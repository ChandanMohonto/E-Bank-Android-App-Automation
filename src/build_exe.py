# build_exe.py
"""
Complete build script for Banking Automation Tool
Creates a single executable with all dependencies
"""

import PyInstaller.__main__
import shutil
import os
from pathlib import Path

def build_executable():
    """Build the complete executable package"""
    
    # Clean previous builds
    for dir in ['build', 'dist']:
        if os.path.exists(dir):
            shutil.rmtree(dir)
    
    # PyInstaller arguments
    args = [
        'main.py',
        '--name=BankingAutomation',
        '--onefile',
        '--windowed',
        '--icon=icon.ico' if os.path.exists('icon.ico') else '--icon=NONE',
        
        # Add all Python modules
        '--add-data=appium_manager.py;.',
        '--add-data=banking_safety_day4.py;.',
        '--add-data=database_manager_day5.py;.',
        '--add-data=element_scanner_day3.py;.',
        '--add-data=test_runner_day6.py;.',
        
        # Hidden imports for all dependencies
        '--hidden-import=tkinter',
        '--hidden-import=sqlite3',
        '--hidden-import=pandas',
        '--hidden-import=openpyxl',
        '--hidden-import=appium',
        '--hidden-import=selenium',
        '--hidden-import=requests',
        '--hidden-import=psutil',
        '--hidden-import=xml.etree.ElementTree',
        '--hidden-import=csv',
        '--hidden-import=json',
        '--hidden-import=logging',
        '--hidden-import=threading',
        '--hidden-import=subprocess',
        '--hidden-import=pathlib',
        
        # Collect all data
        '--collect-all=appium',
        '--collect-all=selenium',
        '--collect-all=pandas',
        '--collect-all=openpyxl',
        
        # Exclude unnecessary modules
        '--exclude-module=matplotlib',
        '--exclude-module=numpy',
        '--exclude-module=scipy',
        
        # Output settings
        '--log-level=INFO',
        '--clean',
        '--noconfirm'
    ]
    
    # Run PyInstaller
    PyInstaller.__main__.run(args)
    
    # Create distribution package
    create_distribution_package()

def create_distribution_package():
    """Create complete distribution with sample DB and folders"""
    
    dist_dir = Path('BankingAutomation_Package')
    dist_dir.mkdir(exist_ok=True)
    
    # Copy executable
    shutil.copy('dist/BankingAutomation.exe', dist_dir)
    
    # Create required directories
    for folder in ['logs', 'screenshots', 'exports']:
        (dist_dir / folder).mkdir(exist_ok=True)
    
    # Create sample database with demo data
    create_sample_database(dist_dir / 'sample_tests.db')
    
    # Create README
    create_readme(dist_dir / 'README.txt')
    
    # Create batch file for easy launch
    create_launch_script(dist_dir / 'RunTool.bat')
    
    print(f"Distribution package created in {dist_dir}")

def create_sample_database(db_path):
    """Create sample SQLite database with demo test cases"""
    import sqlite3
    import json
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create tables (same schema as main app)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS test_cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            app_name TEXT,
            status TEXT DEFAULT 'Ready',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS test_steps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            test_case_id INTEGER,
            step_order INTEGER,
            action_type TEXT,
            locator_type TEXT,
            locator_value TEXT,
            input_data TEXT,
            expected_result TEXT,
            FOREIGN KEY (test_case_id) REFERENCES test_cases (id)
        )
    ''')
    
    # Insert demo test cases
    demo_tests = [
        {
            'name': 'Login Test',
            'description': 'Test login functionality',
            'app_name': 'InLinea Banking',
            'steps': [
                ('click', 'xpath', '//android.widget.Button[@text="OK"]', '', 'OK button clicked'),
                ('type', 'id', 'ch.bsct.ebanking.mobile:id/username', 'testuser', 'Username entered'),
                ('type', 'id', 'ch.bsct.ebanking.mobile:id/password', 'testpass', 'Password entered'),
                ('assert_exists', 'id', 'ch.bsct.ebanking.mobile:id/login_button', '', 'Login button exists')
            ]
        },
        {
            'name': 'Navigation Test',
            'description': 'Test main menu navigation',
            'app_name': 'InLinea Banking',
            'steps': [
                ('click', 'id', 'ch.bsct.ebanking.mobile:id/menu_button', '', 'Menu opened'),
                ('assert_exists', 'xpath', '//android.widget.TextView[@text="Settings"]', '', 'Settings option exists'),
                ('screenshot', '', '', '', 'Screenshot captured')
            ]
        }
    ]
    
    for test in demo_tests:
        cursor.execute('''
            INSERT INTO test_cases (name, description, app_name)
            VALUES (?, ?, ?)
        ''', (test['name'], test['description'], test['app_name']))
        
        test_id = cursor.lastrowid
        
        for i, step in enumerate(test['steps'], 1):
            cursor.execute('''
                INSERT INTO test_steps 
                (test_case_id, step_order, action_type, locator_type, locator_value, input_data, expected_result)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (test_id, i, *step))
    
    conn.commit()
    conn.close()

def create_readme(readme_path):
    """Create README file"""
    content = """
Banking Automation Tool v6.0
============================

SYSTEM REQUIREMENTS:
- Windows 10/11 (64-bit)
- 4GB RAM minimum
- Android device with USB debugging enabled
- Appium server (will be checked on startup)

QUICK START:
1. Double-click BankingAutomation.exe or RunTool.bat
2. The tool will check system requirements
3. Start Appium server from System Setup tab
4. Connect your Android device
5. Start scanning and testing!

FEATURES:
✓ UI Element scanning with safety classification
✓ SQLite database storage
✓ CSV/Excel export
✓ Automated test execution
✓ Screenshot capture
✓ Detailed reporting

FILES INCLUDED:
- BankingAutomation.exe - Main executable
- sample_tests.db - Demo test cases
- logs/ - Application logs
- screenshots/ - Test screenshots
- exports/ - CSV/Excel exports

SUPPORT:
Check logs/ folder for troubleshooting
All test reports are saved automatically

WARNING:
Use only on test accounts, never production!
"""
    
    readme_path.write_text(content)

def create_launch_script(script_path):
    """Create batch file for launching"""
    content = """@echo off
echo Starting Banking Automation Tool...
echo.
echo Checking system requirements...
start BankingAutomation.exe
echo.
echo Tool launched. Check the application window.
pause
"""
    script_path.write_text(content)

if __name__ == "__main__":
    build_executable()