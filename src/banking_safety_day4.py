"""
Day 4: Banking-Specific Safety Features
Enhanced safety measures for banking app automation
"""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
import hashlib
import re

class BankingSafetyManager:
    def __init__(self, config_path=None):
        self.logger = logging.getLogger(__name__)
        self.config_path = config_path or Path("banking_safety_config.json")
        self.safety_rules = self.load_safety_rules()
        self.audit_log = []
        
    def load_safety_rules(self):
        """Load banking safety rules from configuration"""
        default_rules = {
            "forbidden_elements": {
                "resource_ids": [
                    "password", "pin", "cvv", "otp", "token", "biometric",
                    "transfer_amount", "account_number", "routing_number",
                    "confirm_payment", "execute_transfer", "submit_transaction"
                ],
                "text_patterns": [
                    r"transfer.*\$?\d+", r"pay.*\$?\d+", r"send.*\$?\d+",
                    r"confirm.*transaction", r"execute.*payment",
                    r"enter.*password", r"enter.*pin"
                ],
                "class_names": [
                    "PasswordEditText", "PinEditText", "SecureEditText"
                ]
            },
            "restricted_actions": [
                "tap_transfer_button", "enter_amount", "confirm_transaction",
                "submit_payment", "authenticate_biometric"
            ],
            "safe_navigation": [
                "menu", "settings", "help", "about", "back", "home",
                "profile_view", "statement_view", "contact_info"
            ],
            "compliance_requirements": {
                "max_session_duration": 1800,  # 30 minutes
                "required_confirmations": 3,
                "audit_all_actions": True,
                "screenshot_sensitive_screens": False,
                "log_retention_days": 90
            },
            "alert_thresholds": {
                "high_risk_elements_per_screen": 5,
                "forbidden_actions_per_session": 0,
                "session_duration_warning": 1200  # 20 minutes
            }
        }
        
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    loaded_rules = json.load(f)
                # Merge with defaults
                default_rules.update(loaded_rules)
                self.logger.info("Safety rules loaded from configuration")
            else:
                # Save default rules
                self.save_safety_rules(default_rules)
                self.logger.info("Default safety rules created")
        except Exception as e:
            self.logger.error(f"Failed to load safety rules: {e}")
        
        return default_rules
    
    def save_safety_rules(self, rules):
        """Save safety rules to configuration file"""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(rules, f, indent=4)
        except Exception as e:
            self.logger.error(f"Failed to save safety rules: {e}")
    
    def validate_element_safety(self, element_info):
        """
        Comprehensive safety validation for banking elements
        
        Args:
            element_info: Dictionary containing element information
            
        Returns:
            dict: Safety validation result
        """
        validation_result = {
            'is_safe': True,
            'safety_level': 'SAFE',
            'violations': [],
            'warnings': [],
            'recommendations': [],
            'requires_manual_review': False
        }
        
        try:
            # Check forbidden resource IDs
            resource_id = element_info.get('resource_id', '').lower()
            for forbidden_id in self.safety_rules['forbidden_elements']['resource_ids']:
                if forbidden_id in resource_id:
                    validation_result['is_safe'] = False
                    validation_result['safety_level'] = 'FORBIDDEN'
                    validation_result['violations'].append(f"Forbidden resource ID pattern: {forbidden_id}")
            
            # Check forbidden text patterns
            element_text = ' '.join([
                element_info.get('text', ''),
                element_info.get('content_desc', ''),
                resource_id
            ]).lower()
            
            for pattern in self.safety_rules['forbidden_elements']['text_patterns']:
                if re.search(pattern, element_text):
                    validation_result['is_safe'] = False
                    validation_result['safety_level'] = 'FORBIDDEN'
                    validation_result['violations'].append(f"Forbidden text pattern: {pattern}")
            
            # Check forbidden class names
            class_name = element_info.get('class_name', '')
            for forbidden_class in self.safety_rules['forbidden_elements']['class_names']:
                if forbidden_class.lower() in class_name.lower():
                    validation_result['is_safe'] = False
                    validation_result['safety_level'] = 'FORBIDDEN'
                    validation_result['violations'].append(f"Forbidden class name: {forbidden_class}")
            
            # Check for banking-specific risks
            banking_risks = self._assess_banking_risks(element_info)
            if banking_risks['risk_level'] == 'HIGH':
                validation_result['safety_level'] = 'HIGH_RISK'
                validation_result['warnings'].extend(banking_risks['warnings'])
                validation_result['requires_manual_review'] = True
            
            # Generate recommendations
            validation_result['recommendations'] = self._generate_safety_recommendations(element_info, validation_result)
            
            # Log validation
            self._log_safety_validation(element_info, validation_result)
            
        except Exception as e:
            self.logger.error(f"Safety validation failed: {e}")
            validation_result['is_safe'] = False
            validation_result['safety_level'] = 'ERROR'
            validation_result['violations'].append(f"Validation error: {str(e)}")
        
        return validation_result
    
    def _assess_banking_risks(self, element_info):
        """Assess banking-specific risks"""
        risks = {
            'risk_level': 'LOW',
            'warnings': [],
            'factors': []
        }
        
        # Financial transaction indicators
        financial_keywords = [
            'amount', 'balance', 'transfer', 'payment', 'deposit', 
            'withdraw', 'currency', 'dollar', 'euro', 'account'
        ]
        
        element_text = ' '.join([
            element_info.get('resource_id', ''),
            element_info.get('text', ''),
            element_info.get('content_desc', '')
        ]).lower()
        
        financial_matches = [kw for kw in financial_keywords if kw in element_text]
        if financial_matches:
            risks['risk_level'] = 'MEDIUM'
            risks['warnings'].append(f"Financial keywords detected: {', '.join(financial_matches)}")
            risks['factors'].append('financial_content')
        
        # Authentication elements
        auth_keywords = ['password', 'pin', 'biometric', 'fingerprint', 'face', 'token']
        auth_matches = [kw for kw in auth_keywords if kw in element_text]
        if auth_matches:
            risks['risk_level'] = 'HIGH'
            risks['warnings'].append(f"Authentication elements: {', '.join(auth_matches)}")
            risks['factors'].append('authentication_required')
        
        # Transaction confirmation elements
        confirm_keywords = ['confirm', 'execute', 'submit', 'authorize', 'approve']
        confirm_matches = [kw for kw in confirm_keywords if kw in element_text]
        if confirm_matches and element_info.get('clickable'):
            risks['risk_level'] = 'HIGH'
            risks['warnings'].append(f"Transaction confirmation detected: {', '.join(confirm_matches)}")
            risks['factors'].append('transaction_confirmation')
        
        # Password/sensitive input fields
        if element_info.get('password') or 'password' in element_info.get('class_name', '').lower():
            risks['risk_level'] = 'HIGH'
            risks['warnings'].append("Sensitive input field detected")
            risks['factors'].append('sensitive_input')
        
        return risks
    
    def _generate_safety_recommendations(self, element_info, validation_result):
        """Generate safety recommendations"""
        recommendations = []
        
        if not validation_result['is_safe']:
            recommendations.append("🚫 DO NOT AUTOMATE: Element violates banking safety rules")
            recommendations.append("📝 Document why automation is needed for this element")
            recommendations.append("👥 Requires approval from compliance team")
        
        elif validation_result['safety_level'] == 'HIGH_RISK':
            recommendations.append("⚠️ HIGH RISK: Use extreme caution")
            recommendations.append("🔍 Manual review required before automation")
            recommendations.append("📊 Monitor closely during test execution")
            recommendations.append("🔒 Use test accounts only - never production data")
        
        elif validation_result['requires_manual_review']:
            recommendations.append("👀 Manual review recommended")
            recommendations.append("📋 Verify with business team before automating")
        
        # Locator recommendations
        locators = element_info.get('locators', {})
        if not locators.get('resource_id'):
            recommendations.append("⚠️ No stable resource-id found - automation may be brittle")
        
        if element_info.get('clickable') and validation_result['is_safe']:
            recommendations.append("✅ Safe for navigation automation")
        
        return recommendations
    
    def _log_safety_validation(self, element_info, validation_result):
        """Log safety validation for audit trail"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'element_id': element_info.get('resource_id', 'unknown'),
            'element_text': element_info.get('text', ''),
            'safety_level': validation_result['safety_level'],
            'is_safe': validation_result['is_safe'],
            'violations': validation_result['violations'],
            'warnings': validation_result['warnings']
        }
        
        self.audit_log.append(log_entry)
        
        # Keep audit log size manageable
        if len(self.audit_log) > 1000:
            self.audit_log = self.audit_log[-500:]  # Keep last 500 entries
    
    def validate_test_action(self, action_type, element_info, additional_context=None):
        """
        Validate if a test action is safe to perform
        
        Args:
            action_type: Type of action (tap, type, swipe, etc.)
            element_info: Information about target element
            additional_context: Additional context for the action
            
        Returns:
            dict: Action validation result
        """
        validation = {
            'allowed': True,
            'risk_level': 'LOW',
            'warnings': [],
            'required_confirmations': [],
            'audit_required': False
        }
        
        try:
            # Check if action is in restricted list
            if action_type in self.safety_rules['restricted_actions']:
                validation['allowed'] = False
                validation['risk_level'] = 'FORBIDDEN'
                validation['warnings'].append(f"Action '{action_type}' is in restricted actions list")
                return validation
            
            # Validate the target element
            element_validation = self.validate_element_safety(element_info)
            
            if not element_validation['is_safe']:
                validation['allowed'] = False
                validation['risk_level'] = 'FORBIDDEN'
                validation['warnings'].append("Target element violates safety rules")
                validation['warnings'].extend(element_validation['violations'])
                return validation
            
            # Special validation for different action types
            if action_type == 'type' and element_info.get('password'):
                validation['allowed'] = False
                validation['risk_level'] = 'FORBIDDEN'
                validation['warnings'].append("Typing in password fields is forbidden")
            
            elif action_type == 'tap':
                # Check if tapping financial/transaction elements
                element_text = element_info.get('text', '').lower()
                if any(word in element_text for word in ['confirm', 'execute', 'submit', 'transfer', 'pay']):
                    validation['allowed'] = False
                    validation['risk_level'] = 'HIGH'
                    validation['warnings'].append("Tapping transaction confirmation elements is high risk")
            
            # Add audit requirement for all actions on sensitive elements
            if element_validation['safety_level'] in ['HIGH_RISK', 'MEDIUM_RISK']:
                validation['audit_required'] = True
                validation['required_confirmations'].append("Confirm this action is necessary for the test")
            
            # Log the action validation
            self._log_action_validation(action_type, element_info, validation)
            
        except Exception as e:
            self.logger.error(f"Action validation failed: {e}")
            validation['allowed'] = False
            validation['risk_level'] = 'ERROR'
            validation['warnings'].append(f"Validation error: {str(e)}")
        
        return validation
    
    def _log_action_validation(self, action_type, element_info, validation):
        """Log action validation for audit"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'action_type': action_type,
            'element_id': element_info.get('resource_id', 'unknown'),
            'element_text': element_info.get('text', ''),
            'allowed': validation['allowed'],
            'risk_level': validation['risk_level'],
            'warnings': validation['warnings']
        }
        
        self.audit_log.append(log_entry)
    
    def generate_safety_report(self, scan_results):
        """Generate comprehensive safety report for a screen scan"""
        report = {
            'scan_summary': {
                'timestamp': datetime.now().isoformat(),
                'app_name': scan_results.get('app_name', 'Unknown'),
                'screen_name': scan_results.get('screen_name', 'Unknown'),
                'total_elements': len(scan_results.get('elements', [])),
                'scan_duration': scan_results.get('scan_duration', 0)
            },
            'safety_analysis': {
                'total_violations': 0,
                'high_risk_elements': 0,
                'forbidden_elements': 0,
                'safe_elements': 0,
                'requires_review': 0
            },
            'compliance_status': 'COMPLIANT',
            'recommendations': [],
            'audit_trail': self.audit_log[-50:],  # Last 50 entries
            'detailed_findings': []
        }
        
        try:
            elements = scan_results.get('elements', [])
            
            for element in elements:
                # Validate each element
                validation = self.validate_element_safety(element)
                
                # Update counters
                if not validation['is_safe']:
                    report['safety_analysis']['total_violations'] += 1
                    report['safety_analysis']['forbidden_elements'] += 1
                    report['compliance_status'] = 'NON_COMPLIANT'
                elif validation['safety_level'] == 'HIGH_RISK':
                    report['safety_analysis']['high_risk_elements'] += 1
                elif validation['requires_manual_review']:
                    report['safety_analysis']['requires_review'] += 1
                else:
                    report['safety_analysis']['safe_elements'] += 1
                
                # Add to detailed findings
                finding = {
                    'element_id': element.get('resource_id', 'unknown'),
                    'element_text': element.get('text', ''),
                    'safety_level': validation['safety_level'],
                    'violations': validation['violations'],
                    'warnings': validation['warnings'],
                    'recommendations': validation['recommendations']
                }
                report['detailed_findings'].append(finding)
            
            # Generate overall recommendations
            if report['safety_analysis']['forbidden_elements'] > 0:
                report['recommendations'].append(
                    f"🚫 {report['safety_analysis']['forbidden_elements']} forbidden elements detected - do not automate"
                )
            
            if report['safety_analysis']['high_risk_elements'] > 0:
                report['recommendations'].append(
                    f"⚠️ {report['safety_analysis']['high_risk_elements']} high-risk elements require manual review"
                )
            
            if report['safety_analysis']['safe_elements'] > 0:
                report['recommendations'].append(
                    f"✅ {report['safety_analysis']['safe_elements']} elements are safe for automation"
                )
            
            # Compliance check
            total_risky = (report['safety_analysis']['forbidden_elements'] + 
                          report['safety_analysis']['high_risk_elements'])
            
            if total_risky == 0:
                report['compliance_status'] = 'FULLY_COMPLIANT'
            elif total_risky <= 2:
                report['compliance_status'] = 'CONDITIONALLY_COMPLIANT'
            else:
                report['compliance_status'] = 'NON_COMPLIANT'
                
        except Exception as e:
            self.logger.error(f"Safety report generation failed: {e}")
            report['error'] = str(e)
        
        return report
    
    def get_audit_trail(self, limit=100):
        """Get recent audit trail entries"""
        return self.audit_log[-limit:] if self.audit_log else []
    
    def clear_audit_trail(self):
        """Clear audit trail (use with caution)"""
        self.audit_log.clear()
        self.logger.info("Audit trail cleared")
    
    def export_safety_config(self, export_path):
        """Export current safety configuration"""
        try:
            with open(export_path, 'w') as f:
                json.dump(self.safety_rules, f, indent=4)
            self.logger.info(f"Safety configuration exported to {export_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to export safety config: {e}")
            return False
    
    def import_safety_config(self, import_path):
        """Import safety configuration"""
        try:
            with open(import_path, 'r') as f:
                imported_rules = json.load(f)
            
            # Validate imported rules have required structure
            required_keys = ['forbidden_elements', 'restricted_actions', 'safe_navigation']
            if all(key in imported_rules for key in required_keys):
                self.safety_rules = imported_rules
                self.save_safety_rules(imported_rules)
                self.logger.info(f"Safety configuration imported from {import_path}")
                return True
            else:
                self.logger.error("Invalid safety configuration format")
                return False
        except Exception as e:
            self.logger.error(f"Failed to import safety config: {e}")
            return False

# Utility functions for integration
def validate_banking_element(element_info, config_path=None):
    """
    Quick validation function for banking elements
    
    Args:
        element_info: Element information dictionary
        config_path: Optional path to safety configuration
        
    Returns:
        dict: Validation result
    """
    safety_manager = BankingSafetyManager(config_path)
    return safety_manager.validate_element_safety(element_info)

def create_default_safety_config(output_path):
    """Create default safety configuration file"""
    safety_manager = BankingSafetyManager()
    safety_manager.save_safety_rules(safety_manager.safety_rules)
    return True

if __name__ == "__main__":
    # Test the safety manager
    logging.basicConfig(level=logging.INFO)
    
    safety_manager = BankingSafetyManager()
    
    # Test element validation
    test_element = {
        'resource_id': 'ch.bsct.ebanking.mobile:id/password_field',
        'text': 'Enter Password',
        'class_name': 'android.widget.EditText',
        'password': True,
        'clickable': True
    }
    
    validation = safety_manager.validate_element_safety(test_element)
    print(f"Test validation result: {validation}")
    
    # Test action validation
    action_validation = safety_manager.validate_test_action('type', test_element)
    print(f"Action validation result: {action_validation}")