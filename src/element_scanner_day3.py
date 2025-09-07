"""
Day 3: Real UI Element Scanner
Advanced element detection and banking-specific safety classification
"""

import time
import logging
from pathlib import Path
from datetime import datetime
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import xml.etree.ElementTree as ET
import re

class BankingElementScanner:
    def __init__(self, driver, screenshots_dir):
        self.driver = driver
        self.screenshots_dir = Path(screenshots_dir)
        self.logger = logging.getLogger(__name__)
        self.wait = WebDriverWait(driver, 10)
        
        # Banking-specific element patterns
        self.banking_patterns = {
            'HIGH_RISK': [
                'transfer', 'send', 'pay', 'withdraw', 'deposit', 'confirm', 'authorize', 
                'submit', 'execute', 'password', 'pin', 'cvv', 'otp', 'token', 'biometric',
                'fingerprint', 'face', 'transaction', 'amount', 'balance', 'account'
            ],
            'MEDIUM_RISK': [
                'login', 'sign', 'authenticate', 'verify', 'profile', 'settings', 
                'statement', 'history', 'details', 'information', 'search'
            ],
            'LOW_RISK': [
                'menu', 'home', 'back', 'close', 'help', 'about', 'contact', 'support',
                'news', 'notification', 'language', 'theme', 'version'
            ]
        }
    
    def scan_current_screen(self, app_name="Unknown App", screen_name="Unknown Screen"):
        """
        Perform comprehensive scan of current screen
        
        Returns:
            dict: Scan results with elements, metadata, and safety classifications
        """
        scan_start_time = time.time()
        
        scan_results = {
            'app_name': app_name,
            'screen_name': screen_name,
            'scan_timestamp': datetime.now().isoformat(),
            'scan_duration': 0,
            'elements': [],
            'metadata': {},
            'statistics': {},
            'warnings': []
        }
        
        try:
            # Capture screen metadata
            scan_results['metadata'] = self._capture_screen_metadata()
            
            # Take screenshot
            screenshot_path = self._take_screenshot(app_name, screen_name)
            scan_results['metadata']['screenshot_path'] = str(screenshot_path)
            
            # Get page source for detailed analysis
            page_source = self.driver.page_source
            scan_results['metadata']['page_source_length'] = len(page_source)
            
            # Method 1: Find all interactive elements
            interactive_elements = self._find_interactive_elements()
            
            # Method 2: Parse XML hierarchy for comprehensive detection
            xml_elements = self._parse_xml_hierarchy(page_source)
            
            # Method 3: Find elements by common banking patterns
            pattern_elements = self._find_elements_by_patterns()
            
            # Combine and deduplicate elements
            all_elements = self._merge_and_deduplicate(
                interactive_elements, xml_elements, pattern_elements
            )
            
            # Process each element
            processed_elements = []
            for element_data in all_elements:
                processed_element = self._process_element(element_data)
                if processed_element:
                    processed_elements.append(processed_element)
            
            scan_results['elements'] = processed_elements
            
            # Generate statistics
            scan_results['statistics'] = self._generate_statistics(processed_elements)
            
            # Add banking-specific warnings
            scan_results['warnings'] = self._generate_banking_warnings(processed_elements)
            
            scan_results['scan_duration'] = round(time.time() - scan_start_time, 2)
            
            self.logger.info(f"Screen scan completed: {len(processed_elements)} elements found in {scan_results['scan_duration']}s")
            
        except Exception as e:
            error_msg = f"Screen scanning failed: {str(e)}"
            self.logger.error(error_msg)
            scan_results['error'] = error_msg
            scan_results['scan_duration'] = round(time.time() - scan_start_time, 2)
        
        return scan_results
    
    def _capture_screen_metadata(self):
        """Capture screen and app metadata"""
        metadata = {
            'device_info': {},
            'app_info': {},
            'screen_info': {}
        }
        
        try:
            # Device information
            metadata['device_info'] = {
                'platform_name': self.driver.capabilities.get('platformName', 'Unknown'),
                'platform_version': self.driver.capabilities.get('platformVersion', 'Unknown'),
                'device_name': self.driver.capabilities.get('deviceName', 'Unknown'),
                'device_udid': self.driver.capabilities.get('udid', 'Unknown'),
            }
            
            # App information
            metadata['app_info'] = {
                'app_package': self.driver.capabilities.get('appPackage', 'Unknown'),
                'app_activity': self.driver.capabilities.get('appActivity', 'Unknown'),
                'automation_name': self.driver.capabilities.get('automationName', 'Unknown'),
            }
            
            # Current screen information
            try:
                metadata['screen_info']['current_activity'] = self.driver.current_activity
            except:
                metadata['screen_info']['current_activity'] = 'Unknown'
                
            try:
                metadata['screen_info']['current_package'] = self.driver.current_package
            except:
                metadata['screen_info']['current_package'] = 'Unknown'
            
            # Screen dimensions
            try:
                window_size = self.driver.get_window_size()
                metadata['screen_info']['window_size'] = window_size
            except:
                metadata['screen_info']['window_size'] = {'width': 0, 'height': 0}
            
        except Exception as e:
            self.logger.warning(f"Failed to capture metadata: {e}")
            
        return metadata
    
    def _take_screenshot(self, app_name, screen_name):
        """Take and save screenshot"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_app_name = re.sub(r'[^\w\-_\.]', '_', app_name)
        safe_screen_name = re.sub(r'[^\w\-_\.]', '_', screen_name)
        
        screenshot_filename = f"{safe_app_name}_{safe_screen_name}_{timestamp}.png"
        screenshot_path = self.screenshots_dir / screenshot_filename
        
        try:
            self.driver.save_screenshot(str(screenshot_path))
            self.logger.info(f"Screenshot saved: {screenshot_filename}")
        except Exception as e:
            self.logger.error(f"Failed to save screenshot: {e}")
            screenshot_path = None
            
        return screenshot_path
    
    def _find_interactive_elements(self):
        """Find all interactive elements (clickable, editable)"""
        elements = []
        
        try:
            # Find clickable elements
            clickable_elements = self.driver.find_elements(AppiumBy.XPATH, "//*[@clickable='true']")
            for elem in clickable_elements:
                elements.append(('interactive', elem, 'clickable'))
            
            # Find input elements
            input_elements = self.driver.find_elements(AppiumBy.XPATH, "//android.widget.EditText")
            for elem in input_elements:
                elements.append(('interactive', elem, 'input'))
            
            # Find buttons
            button_elements = self.driver.find_elements(AppiumBy.XPATH, "//android.widget.Button")
            for elem in button_elements:
                elements.append(('interactive', elem, 'button'))
                
        except Exception as e:
            self.logger.warning(f"Failed to find interactive elements: {e}")
            
        return elements
    
    def _parse_xml_hierarchy(self, page_source):
        """Parse XML page source for comprehensive element detection"""
        elements = []
        
        try:
            # Parse XML
            root = ET.fromstring(page_source)
            
            # Recursively find all elements with useful attributes
            def traverse_element(xml_elem, path=""):
                current_path = f"{path}/{xml_elem.tag}" if path else xml_elem.tag
                
                # Check if element has useful attributes
                if self._has_useful_attributes(xml_elem.attrib):
                    elements.append(('xml', xml_elem, current_path))
                
                # Traverse children
                for child in xml_elem:
                    traverse_element(child, current_path)
            
            traverse_element(root)
            
        except Exception as e:
            self.logger.warning(f"Failed to parse XML hierarchy: {e}")
            
        return elements
    
    def _find_elements_by_patterns(self):
        """Find elements using banking-specific patterns"""
        elements = []
        
        banking_xpaths = [
            # Common banking element patterns
            "//*[contains(@resource-id, 'login')]",
            "//*[contains(@resource-id, 'password')]",
            "//*[contains(@resource-id, 'username')]",
            "//*[contains(@resource-id, 'pin')]",
            "//*[contains(@resource-id, 'balance')]",
            "//*[contains(@resource-id, 'account')]",
            "//*[contains(@resource-id, 'transfer')]",
            "//*[contains(@resource-id, 'payment')]",
            "//*[contains(@resource-id, 'menu')]",
            "//*[contains(@resource-id, 'settings')]",
            "//*[contains(@resource-id, 'help')]",
            "//*[contains(@text, 'Login')]",
            "//*[contains(@text, 'Menu')]",
            "//*[contains(@text, 'Settings')]",
            "//*[contains(@text, 'Help')]",
            "//*[contains(@text, 'Transfer')]",
            "//*[contains(@content-desc, 'menu')]",
            "//*[contains(@content-desc, 'settings')]",
            "//*[contains(@content-desc, 'help')]",
        ]
        
        for xpath in banking_xpaths:
            try:
                found_elements = self.driver.find_elements(AppiumBy.XPATH, xpath)
                for elem in found_elements:
                    elements.append(('pattern', elem, xpath))
            except:
                continue
                
        return elements
    
    def _has_useful_attributes(self, attrib):
        """Check if XML element has useful attributes for automation"""
        useful_attrs = ['resource-id', 'text', 'content-desc', 'clickable', 'class']
        
        # Has resource-id
        if attrib.get('resource-id'):
            return True
            
        # Has text content
        if attrib.get('text') and len(attrib.get('text').strip()) > 0:
            return True
            
        # Has content description
        if attrib.get('content-desc') and len(attrib.get('content-desc').strip()) > 0:
            return True
            
        # Is clickable
        if attrib.get('clickable') == 'true':
            return True
            
        return False
    
    def _merge_and_deduplicate(self, *element_lists):
        """Merge element lists and remove duplicates"""
        seen_elements = set()
        merged_elements = []
        
        for element_list in element_lists:
            for source, element, extra_info in element_list:
                try:
                    # Create unique identifier for element
                    bounds = element.get_attribute('bounds') if hasattr(element, 'get_attribute') else element.attrib.get('bounds', '')
                    resource_id = element.get_attribute('resource-id') if hasattr(element, 'get_attribute') else element.attrib.get('resource-id', '')
                    text = element.get_attribute('text') if hasattr(element, 'get_attribute') else element.attrib.get('text', '')
                    
                    element_id = f"{bounds}_{resource_id}_{text}"
                    
                    if element_id not in seen_elements:
                        seen_elements.add(element_id)
                        merged_elements.append((source, element, extra_info))
                        
                except Exception as e:
                    self.logger.debug(f"Error processing element in deduplication: {e}")
                    continue
        
        return merged_elements
    
    def _process_element(self, element_data):
        """Process individual element and extract all useful information"""
        source, element, extra_info = element_data
        
        try:
            # Handle different element types (WebDriver element vs XML element)
            if hasattr(element, 'get_attribute'):
                # WebDriver element
                element_info = {
                    'detection_source': source,
                    'detection_info': extra_info,
                    'class_name': element.tag_name,
                    'resource_id': element.get_attribute('resource-id') or '',
                    'text': element.get_attribute('text') or '',
                    'content_desc': element.get_attribute('content-desc') or '',
                    'bounds': element.get_attribute('bounds') or '',
                    'clickable': element.get_attribute('clickable') == 'true',
                    'enabled': element.get_attribute('enabled') == 'true',
                    'displayed': element.is_displayed() if hasattr(element, 'is_displayed') else True,
                    'checkable': element.get_attribute('checkable') == 'true',
                    'checked': element.get_attribute('checked') == 'true',
                    'focusable': element.get_attribute('focusable') == 'true',
                    'focused': element.get_attribute('focused') == 'true',
                    'password': element.get_attribute('password') == 'true',
                    'scrollable': element.get_attribute('scrollable') == 'true',
                    'long_clickable': element.get_attribute('long-clickable') == 'true',
                }
            else:
                # XML element
                attrib = element.attrib
                element_info = {
                    'detection_source': source,
                    'detection_info': extra_info,
                    'class_name': element.tag,
                    'resource_id': attrib.get('resource-id', ''),
                    'text': attrib.get('text', ''),
                    'content_desc': attrib.get('content-desc', ''),
                    'bounds': attrib.get('bounds', ''),
                    'clickable': attrib.get('clickable') == 'true',
                    'enabled': attrib.get('enabled') == 'true',
                    'displayed': attrib.get('displayed') != 'false',
                    'checkable': attrib.get('checkable') == 'true',
                    'checked': attrib.get('checked') == 'true',
                    'focusable': attrib.get('focusable') == 'true',
                    'focused': attrib.get('focused') == 'true',
                    'password': attrib.get('password') == 'true',
                    'scrollable': attrib.get('scrollable') == 'true',
                    'long_clickable': attrib.get('long-clickable') == 'true',
                }
            
            # Generate locators
            element_info['locators'] = self._generate_locators(element_info)
            
            # Safety classification
            element_info['safety_classification'] = self._classify_element_safety(element_info)
            
            # Element categorization
            element_info['category'] = self._categorize_element(element_info)
            
            # Automation recommendations
            element_info['automation_notes'] = self._generate_automation_notes(element_info)
            
            return element_info
            
        except Exception as e:
            self.logger.warning(f"Failed to process element: {e}")
            return None
    
    def _generate_locators(self, element_info):
        """Generate multiple locator strategies for the element"""
        locators = {}
        
        # Resource ID locator (preferred)
        if element_info['resource_id']:
            locators['resource_id'] = element_info['resource_id']
            locators['xpath_resource_id'] = f"//*[@resource-id='{element_info['resource_id']}']"
        
        # Text locator
        if element_info['text']:
            locators['text'] = element_info['text']
            locators['xpath_text'] = f"//*[@text='{element_info['text']}']"
        
        # Content description locator
        if element_info['content_desc']:
            locators['accessibility_id'] = element_info['content_desc']
            locators['xpath_content_desc'] = f"//*[@content-desc='{element_info['content_desc']}']"
        
        # Class name locator
        if element_info['class_name']:
            locators['class_name'] = element_info['class_name']
        
        # Bounds-based locator (for tap coordinates)
        if element_info['bounds']:
            locators['bounds'] = element_info['bounds']
        
        # Combined locator strategies
        combined_locators = []
        if element_info['resource_id'] and element_info['text']:
            combined_locators.append(f"//*[@resource-id='{element_info['resource_id']}' and @text='{element_info['text']}']")
        if element_info['class_name'] and element_info['text']:
            combined_locators.append(f"//{element_info['class_name']}[@text='{element_info['text']}']")
        
        if combined_locators:
            locators['xpath_combined'] = combined_locators
        
        # Recommended locator
        if 'resource_id' in locators:
            locators['recommended'] = 'resource_id'
        elif 'accessibility_id' in locators:
            locators['recommended'] = 'accessibility_id'
        elif 'text' in locators:
            locators['recommended'] = 'text'
        else:
            locators['recommended'] = 'class_name'
        
        return locators
    
    def _classify_element_safety(self, element_info):
        """Classify element safety for banking automation"""
        
        # Combine all text for analysis
        all_text = ' '.join([
            element_info.get('resource_id', ''),
            element_info.get('text', ''),
            element_info.get('content_desc', ''),
            element_info.get('class_name', '')
        ]).lower()
        
        # Check for high-risk patterns
        for pattern in self.banking_patterns['HIGH_RISK']:
            if pattern in all_text:
                return {
                    'level': 'HIGH_RISK',
                    'reason': f'Contains high-risk pattern: {pattern}',
                    'color': 'red',
                    'automation_allowed': False
                }
        
        # Check for medium-risk patterns
        for pattern in self.banking_patterns['MEDIUM_RISK']:
            if pattern in all_text:
                return {
                    'level': 'MEDIUM_RISK',
                    'reason': f'Contains medium-risk pattern: {pattern}',
                    'color': 'orange',
                    'automation_allowed': True,
                    'requires_caution': True
                }
        
        # Check for low-risk patterns
        for pattern in self.banking_patterns['LOW_RISK']:
            if pattern in all_text:
                return {
                    'level': 'LOW_RISK',
                    'reason': f'Contains low-risk pattern: {pattern}',
                    'color': 'green',
                    'automation_allowed': True
                }
        
        # Password fields are always high risk
        if element_info.get('password'):
            return {
                'level': 'HIGH_RISK',
                'reason': 'Password input field',
                'color': 'red',
                'automation_allowed': False
            }
        
        # Default classification
        if element_info.get('clickable') or 'EditText' in element_info.get('class_name', ''):
            return {
                'level': 'UNKNOWN',
                'reason': 'Interactive element - requires manual review',
                'color': 'gray',
                'automation_allowed': True,
                'requires_review': True
            }
        else:
            return {
                'level': 'SAFE',
                'reason': 'Non-interactive element',
                'color': 'blue',
                'automation_allowed': True
            }
    
    def _categorize_element(self, element_info):
        """Categorize element by function"""
        class_name = element_info.get('class_name', '').lower()
        
        if 'button' in class_name:
            return 'button'
        elif 'edittext' in class_name:
            return 'input'
        elif 'textview' in class_name:
            return 'text'
        elif 'imageview' in class_name or 'imagebutton' in class_name:
            return 'image'
        elif 'checkbox' in class_name:
            return 'checkbox'
        elif 'radiobutton' in class_name:
            return 'radio'
        elif 'spinner' in class_name:
            return 'dropdown'
        elif 'listview' in class_name or 'recyclerview' in class_name:
            return 'list'
        elif 'scrollview' in class_name:
            return 'scroll'
        else:
            return 'other'
    
    def _generate_automation_notes(self, element_info):
        """Generate automation recommendations for the element"""
        notes = []
        
        # Safety notes
        safety = element_info.get('safety_classification', {})
        if safety.get('level') == 'HIGH_RISK':
            notes.append("⚠️ HIGH RISK: Do not automate this element in production")
        elif safety.get('level') == 'MEDIUM_RISK':
            notes.append("⚠️ CAUTION: Review carefully before automation")
        
        # Locator recommendations
        locators = element_info.get('locators', {})
        if 'resource_id' in locators:
            notes.append("✅ Has stable resource-id - good for automation")
        elif 'accessibility_id' in locators:
            notes.append("✅ Has accessibility-id - good for automation")
        elif 'text' in locators and element_info.get('text'):
            notes.append("⚠️ Text-based locator - may break if text changes")
        else:
            notes.append("⚠️ No stable locator - consider using bounds/coordinates")
        
        # Interaction notes
        if element_info.get('clickable'):
            notes.append("🖱️ Clickable element")
        if element_info.get('password'):
            notes.append("🔒 Password field - handle with extreme caution")
        if not element_info.get('enabled'):
            notes.append("❌ Element is disabled")
        if not element_info.get('displayed'):
            notes.append("👁️ Element may not be visible")
        
        return notes
    
    def _generate_statistics(self, elements):
        """Generate statistics about scanned elements"""
        stats = {
            'total_elements': len(elements),
            'by_safety_level': {},
            'by_category': {},
            'by_interaction_type': {},
            'automation_summary': {
                'safe_to_automate': 0,
                'requires_caution': 0,
                'high_risk': 0,
                'no_stable_locator': 0
            }
        }
        
        for element in elements:
            # Safety level statistics
            safety_level = element.get('safety_classification', {}).get('level', 'UNKNOWN')
            stats['by_safety_level'][safety_level] = stats['by_safety_level'].get(safety_level, 0) + 1
            
            # Category statistics
            category = element.get('category', 'other')
            stats['by_category'][category] = stats['by_category'].get(category, 0) + 1
            
            # Interaction type
            if element.get('clickable'):
                interaction_type = 'clickable'
            elif 'EditText' in element.get('class_name', ''):
                interaction_type = 'input'
            else:
                interaction_type = 'display'
            
            stats['by_interaction_type'][interaction_type] = stats['by_interaction_type'].get(interaction_type, 0) + 1
            
            # Automation summary
            safety = element.get('safety_classification', {})
            locators = element.get('locators', {})
            
            if safety.get('level') == 'HIGH_RISK':
                stats['automation_summary']['high_risk'] += 1
            elif safety.get('requires_caution'):
                stats['automation_summary']['requires_caution'] += 1
            else:
                stats['automation_summary']['safe_to_automate'] += 1
            
            if not locators.get('resource_id') and not locators.get('accessibility_id'):
                stats['automation_summary']['no_stable_locator'] += 1
        
        return stats
    
    def _generate_banking_warnings(self, elements):
        """Generate banking-specific warnings"""
        warnings = []
        
        # Count high-risk elements
        high_risk_count = sum(1 for e in elements if e.get('safety_classification', {}).get('level') == 'HIGH_RISK')
        if high_risk_count > 0:
            warnings.append(f"⚠️ Found {high_risk_count} high-risk banking elements - avoid automation")
        
        # Check for password fields
        password_fields = sum(1 for e in elements if e.get('password'))
        if password_fields > 0:
            warnings.append(f"🔒 Found {password_fields} password field(s) - never automate these")
        
        # Check for transaction-related elements
        transaction_keywords = ['transfer', 'send', 'pay', 'amount', 'confirm']
        transaction_elements = []
        for element in elements:
            element_text = ' '.join([
                element.get('resource_id', ''),
                element.get('text', ''),
                element.get('content_desc', '')
            ]).lower()
            
            for keyword in transaction_keywords:
                if keyword in element_text:
                    transaction_elements.append(element)
                    break
        
        if transaction_elements:
            warnings.append(f"💰 Found {len(transaction_elements)} transaction-related elements - high compliance risk")
        
        # Check for elements without stable locators
        unstable_locators = sum(1 for e in elements if not e.get('locators', {}).get('resource_id') and not e.get('locators', {}).get('accessibility_id'))
        if unstable_locators > len(elements) * 0.3:  # More than 30%
            warnings.append(f"⚠️ {unstable_locators} elements lack stable locators - automation may be unreliable")
        
        return warnings

# Integration function for main application
def perform_advanced_scan(driver, screenshots_dir, app_name, screen_name):
    """
    Perform advanced element scan and return results
    
    Args:
        driver: Appium WebDriver instance
        screenshots_dir: Path to screenshots directory
        app_name: Name of the app being scanned
        screen_name: Name of the current screen
    
    Returns:
        dict: Comprehensive scan results
    """
    scanner = BankingElementScanner(driver, screenshots_dir)
    return scanner.scan_current_screen(app_name, screen_name)