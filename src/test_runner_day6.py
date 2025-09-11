"""
test_runner_day6.py
Test Runner with Assertion Framework for Banking App Automation
Handles automated clicks, text input, and validations
"""

import logging
import time
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

from appium import webdriver
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

class ActionType(Enum):
    """Test action types"""
    CLICK = "click"
    TYPE = "type"
    CLEAR = "clear"
    WAIT = "wait"
    ASSERT_EXISTS = "assert_exists"
    ASSERT_TEXT = "assert_text"
    ASSERT_ENABLED = "assert_enabled"
    SCREENSHOT = "screenshot"
    SWIPE = "swipe"

class AssertionResult(Enum):
    """Assertion result types"""
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"

@dataclass
class TestStep:
    """Represents a single test step"""
    action: ActionType
    locator_strategy: str  # id, xpath, accessibility_id, class
    locator_value: str
    data: Optional[str] = None
    description: str = ""
    wait_time: int = 2
    is_safe: bool = True
    expected_value: Optional[str] = None
    
class BankingTestRunner:
    def __init__(self, driver, safety_manager=None, screenshots_dir="screenshots"):
        self.driver = driver
        self.safety_manager = safety_manager
        self.screenshots_dir = Path(screenshots_dir)
        self.logger = logging.getLogger(__name__)
        self.wait = WebDriverWait(driver, 10)
        self.test_results = []
        self.current_test = None
        
    def run_test_case(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run a complete test case with multiple steps
        
        Args:
            test_case: Dictionary containing test information and steps
            
        Returns:
            Test execution results with assertions
        """
        self.current_test = test_case.get('name', 'Unknown Test')
        self.logger.info(f"Starting test case: {self.current_test}")
        
        results = {
            'test_name': self.current_test,
            'start_time': datetime.now().isoformat(),
            'steps': [],
            'total_steps': 0,
            'passed_steps': 0,
            'failed_steps': 0,
            'status': 'PASSED',
            'error_message': None
        }
        
        try:
            steps = test_case.get('steps', [])
            results['total_steps'] = len(steps)
            
            for i, step in enumerate(steps, 1):
                self.logger.info(f"Executing step {i}/{len(steps)}: {step.get('description', '')}")
                
                step_result = self.execute_step(step)
                results['steps'].append(step_result)
                
                if step_result['status'] == AssertionResult.PASSED:
                    results['passed_steps'] += 1
                elif step_result['status'] == AssertionResult.FAILED:
                    results['failed_steps'] += 1
                    if test_case.get('stop_on_failure', True):
                        results['status'] = 'FAILED'
                        break
                
                # Wait between steps
                time.sleep(step.get('wait_after', 1))
                
        except Exception as e:
            results['status'] = 'ERROR'
            results['error_message'] = str(e)
            self.logger.error(f"Test case failed with error: {e}")
        
        results['end_time'] = datetime.now().isoformat()
        self.test_results.append(results)
        
        return results
    
    def execute_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single test step"""
        step_result = {
            'description': step.get('description', ''),
            'action': step.get('action'),
            'status': AssertionResult.SKIPPED,
            'message': '',
            'screenshot': None,
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            action = ActionType(step['action'])
            
            # Safety check for banking elements
            if self.safety_manager and not self._is_action_safe(step):
                step_result['status'] = AssertionResult.SKIPPED
                step_result['message'] = "Skipped due to safety rules"
                return step_result
            
            # Find element
            element = self._find_element(
                step['locator_strategy'],
                step['locator_value'],
                step.get('wait_time', 10)
            )
            
            # Execute action based on type
            if action == ActionType.CLICK:
                step_result = self._execute_click(element, step_result)
                
            elif action == ActionType.TYPE:
                step_result = self._execute_type(element, step.get('data', ''), step_result)
                
            elif action == ActionType.CLEAR:
                step_result = self._execute_clear(element, step_result)
                
            elif action == ActionType.ASSERT_EXISTS:
                step_result = self._assert_exists(element, step_result)
                
            elif action == ActionType.ASSERT_TEXT:
                step_result = self._assert_text(element, step.get('expected_value', ''), step_result)
                
            elif action == ActionType.ASSERT_ENABLED:
                step_result = self._assert_enabled(element, step_result)
                
            elif action == ActionType.SCREENSHOT:
                step_result = self._take_screenshot(step_result)
                
            elif action == ActionType.WAIT:
                time.sleep(step.get('data', 2))
                step_result['status'] = AssertionResult.PASSED
                step_result['message'] = f"Waited {step.get('data', 2)} seconds"
                
        except TimeoutException:
            step_result['status'] = AssertionResult.FAILED
            step_result['message'] = f"Element not found: {step.get('locator_value')}"
            self._take_screenshot(step_result, is_failure=True)
            
        except Exception as e:
            step_result['status'] = AssertionResult.ERROR
            step_result['message'] = f"Error: {str(e)}"
            self._take_screenshot(step_result, is_failure=True)
            
        return step_result
    
    def _find_element(self, strategy: str, value: str, wait_time: int = 10):
        """Find element using various strategies"""
        locator = None
        
        if strategy == 'id':
            locator = (AppiumBy.ID, value)
        elif strategy == 'xpath':
            locator = (AppiumBy.XPATH, value)
        elif strategy == 'accessibility_id':
            locator = (AppiumBy.ACCESSIBILITY_ID, value)
        elif strategy == 'class':
            locator = (AppiumBy.CLASS_NAME, value)
        else:
            raise ValueError(f"Unknown locator strategy: {strategy}")
        
        return WebDriverWait(self.driver, wait_time).until(
            EC.presence_of_element_located(locator)
        )
    
    def _execute_click(self, element, step_result):
        """Execute click action"""
        element.click()
        step_result['status'] = AssertionResult.PASSED
        step_result['message'] = "Click successful"
        return step_result
    
    def _execute_type(self, element, text, step_result):
        """Execute type action"""
        # Clear field first
        element.clear()
        # Type text
        element.send_keys(text)
        step_result['status'] = AssertionResult.PASSED
        step_result['message'] = f"Typed text successfully"
        return step_result
    
    def _execute_clear(self, element, step_result):
        """Execute clear action"""
        element.clear()
        step_result['status'] = AssertionResult.PASSED
        step_result['message'] = "Field cleared"
        return step_result
    
    def _assert_exists(self, element, step_result):
        """Assert element exists"""
        if element:
            step_result['status'] = AssertionResult.PASSED
            step_result['message'] = "Element exists"
        else:
            step_result['status'] = AssertionResult.FAILED
            step_result['message'] = "Element does not exist"
        return step_result
    
    def _assert_text(self, element, expected_text, step_result):
        """Assert element text"""
        actual_text = element.text
        if actual_text == expected_text:
            step_result['status'] = AssertionResult.PASSED
            step_result['message'] = f"Text matches: '{expected_text}'"
        else:
            step_result['status'] = AssertionResult.FAILED
            step_result['message'] = f"Text mismatch. Expected: '{expected_text}', Actual: '{actual_text}'"
        return step_result
    
    def _assert_enabled(self, element, step_result):
        """Assert element is enabled"""
        if element.is_enabled():
            step_result['status'] = AssertionResult.PASSED
            step_result['message'] = "Element is enabled"
        else:
            step_result['status'] = AssertionResult.FAILED
            step_result['message'] = "Element is disabled"
        return step_result
    
    def _take_screenshot(self, step_result, is_failure=False):
        """Take screenshot and attach to result"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            prefix = "failure_" if is_failure else "step_"
            filename = f"{prefix}{self.current_test}_{timestamp}.png"
            filepath = self.screenshots_dir / filename
            
            self.driver.save_screenshot(str(filepath))
            step_result['screenshot'] = str(filepath)
            
            if not is_failure:
                step_result['status'] = AssertionResult.PASSED
                step_result['message'] = "Screenshot captured"
                
        except Exception as e:
            self.logger.error(f"Failed to take screenshot: {e}")
            
        return step_result
    
    def _is_action_safe(self, step: Dict) -> bool:
        """Check if action is safe for banking app"""
        # Skip safety check for assertions
        if step['action'].startswith('assert'):
            return True
            
        # Check for forbidden elements
        forbidden_keywords = ['transfer', 'payment', 'send_money', 'confirm_transaction']
        locator_value = step.get('locator_value', '').lower()
        
        for keyword in forbidden_keywords:
            if keyword in locator_value:
                self.logger.warning(f"Blocked unsafe action on: {locator_value}")
                return False
                
        return True

class InLineaLoginTest:
    """Specific test implementation for InLinea banking app login"""
    
    def __init__(self, test_runner: BankingTestRunner):
        self.runner = test_runner
        self.logger = logging.getLogger(__name__)
        
    def create_login_test(self, username: str, password: str) -> Dict:
        """Create login test case for InLinea app"""
        return {
            'name': 'InLinea_Login_Test',
            'description': 'Automated login test for InLinea banking app',
            'stop_on_failure': True,
            'steps': [
                # Step 1: Wait for app to load
                {
                    'action': 'wait',
                    'data': 3,
                    'description': 'Wait for app to load'
                },
                
                # Step 2: Check if OK button exists and click it
                {
                    'action': 'click',
                    'locator_strategy': 'id',
                    'locator_value': 'android:id/button1',  # Common OK button ID
                    'description': 'Click OK button if present',
                    'wait_time': 5
                },
                
                # Alternative OK button locators
                {
                    'action': 'click',
                    'locator_strategy': 'xpath',
                    'locator_value': '//android.widget.Button[@text="OK"]',
                    'description': 'Click OK button by text',
                    'wait_time': 2
                },
                
                # Step 3: Assert login screen is displayed
                {
                    'action': 'assert_exists',
                    'locator_strategy': 'id',
                    'locator_value': 'ch.bsct.ebanking.mobile:id/login_username',
                    'description': 'Verify username field exists',
                    'wait_time': 10
                },
                
                # Step 4: Clear and enter username
                {
                    'action': 'clear',
                    'locator_strategy': 'id',
                    'locator_value': 'ch.bsct.ebanking.mobile:id/login_username',
                    'description': 'Clear username field'
                },
                {
                    'action': 'type',
                    'locator_strategy': 'id',
                    'locator_value': 'ch.bsct.ebanking.mobile:id/login_username',
                    'data': username,
                    'description': f'Enter username: {username}'
                },
                
                # Step 5: Clear and enter password
                {
                    'action': 'clear',
                    'locator_strategy': 'id',
                    'locator_value': 'ch.bsct.ebanking.mobile:id/login_password',
                    'description': 'Clear password field'
                },
                {
                    'action': 'type',
                    'locator_strategy': 'id',
                    'locator_value': 'ch.bsct.ebanking.mobile:id/login_password',
                    'data': password,
                    'description': 'Enter password'
                },
                
                # Step 6: Take screenshot before login
                {
                    'action': 'screenshot',
                    'description': 'Capture login form filled'
                },
                
                # Step 7: Click login button (commented out for safety)
                # {
                #     'action': 'click',
                #     'locator_strategy': 'id',
                #     'locator_value': 'ch.bsct.ebanking.mobile:id/login_button',
                #     'description': 'Click login button'
                # },
                
                # Step 8: Assert login button is enabled
                {
                    'action': 'assert_enabled',
                    'locator_strategy': 'id',
                    'locator_value': 'ch.bsct.ebanking.mobile:id/login_button',
                    'description': 'Verify login button is enabled'
                }
            ]
        }
    
    def run_login_test(self, username: str = "testuser", password: str = "testpass"):
        """Execute the login test"""
        test_case = self.create_login_test(username, password)
        results = self.runner.run_test_case(test_case)
        
        # Print results
        self.logger.info(f"Test completed: {results['status']}")
        self.logger.info(f"Steps passed: {results['passed_steps']}/{results['total_steps']}")
        
        return results

def create_generic_test_for_elements(elements: List[Dict]) -> Dict:
    """
    Create a generic test case from scanned elements
    
    Args:
        elements: List of scanned UI elements
        
    Returns:
        Test case dictionary
    """
    test_case = {
        'name': 'Generic_UI_Test',
        'description': 'Automated test for scanned elements',
        'steps': []
    }
    
    for element in elements:
        # Only interact with safe elements
        if element.get('safety_classification', {}).get('level') == 'SAFE':
            
            # Add assertion for element existence
            if element.get('resource_id'):
                test_case['steps'].append({
                    'action': 'assert_exists',
                    'locator_strategy': 'id',
                    'locator_value': element['resource_id'],
                    'description': f"Verify {element.get('text', 'element')} exists"
                })
            
            # Add click action for clickable elements
            if element.get('clickable') and 'button' in element.get('class_name', '').lower():
                test_case['steps'].append({
                    'action': 'click',
                    'locator_strategy': 'id',
                    'locator_value': element['resource_id'],
                    'description': f"Click {element.get('text', 'button')}"
                })
    
    return test_case

# Integration with main GUI
def integrate_test_runner(driver, safety_manager=None):
    """
    Integrate test runner with the main application
    
    Args:
        driver: Appium WebDriver instance
        safety_manager: Banking safety manager instance
        
    Returns:
        Configured test runner
    """
    runner = BankingTestRunner(driver, safety_manager)
    return runner

if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    # Mock test case for demonstration
    sample_test = {
        'name': 'Sample_Banking_Test',
        'steps': [
            {
                'action': 'wait',
                'data': 2,
                'description': 'Initial wait'
            },
            {
                'action': 'assert_exists',
                'locator_strategy': 'id',
                'locator_value': 'ch.bsct.ebanking.mobile:id/main_menu',
                'description': 'Verify main menu exists'
            }
        ]
    }
    
    print("Test Runner module ready for integration")