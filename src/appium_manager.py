"""
Appium Server Manager
Handles starting/stopping Appium server and checking status
"""

import subprocess
import time
import threading
import logging
import requests
import psutil
from pathlib import Path

class AppiumServerManager:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.server_process = None
        self.server_port = 4723
        self.server_host = "127.0.0.1"
        self.server_url = f"http://{self.server_host}:{self.server_port}"
        self.is_running = False
        
    def check_node_installed(self):
        """Check if Node.js is installed"""
        try:
            result = subprocess.run(['node', '--version'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                version = result.stdout.strip()
                self.logger.info(f"Node.js found: {version}")
                return True, version
            else:
                return False, "Node.js not found"
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False, "Node.js not installed"
    
    def check_appium_installed(self):
        """Check if Appium is installed globally"""
        # Try multiple command variations for Windows compatibility
        commands_to_try = ['appium', 'appium.cmd', 'appium.exe']
        
        for cmd in commands_to_try:
            try:
                result = subprocess.run([cmd, '--version'], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    version_output = result.stdout.strip()
                    # Clean up version output (remove warnings and get actual version)
                    version_lines = [line.strip() for line in version_output.split('\n') if line.strip()]
                    
                    # Look for version number in the output
                    actual_version = None
                    for line in version_lines:
                        if line and not line.startswith('WARN') and not line.startswith('['):
                            # Try to extract version number
                            import re
                            version_match = re.search(r'(\d+\.\d+\.\d+)', line)
                            if version_match:
                                actual_version = version_match.group(1)
                                break
                    
                    if not actual_version:
                        # Fallback to last non-warning line
                        for line in reversed(version_lines):
                            if not line.startswith('WARN') and not line.startswith('['):
                                actual_version = line
                                break
                    
                    if not actual_version:
                        actual_version = "3.0.1"  # Default assumption if we can't parse
                    
                    self.logger.info(f"Appium found with command '{cmd}': {actual_version}")
                    return True, actual_version
                else:
                    self.logger.debug(f"Command '{cmd}' failed with return code {result.returncode}")
            except subprocess.TimeoutExpired:
                self.logger.debug(f"Command '{cmd}' timed out")
                continue
            except FileNotFoundError:
                self.logger.debug(f"Command '{cmd}' not found")
                continue
            except Exception as e:
                self.logger.debug(f"Command '{cmd}' failed with exception: {e}")
                continue
        
        # If direct commands fail, try checking if server is already running
        if self.check_server_running():
            self.logger.info("Appium server is running, assuming Appium is installed")
            return True, "3.0.1 (server running)"
        
        return False, "Appium not installed"
    
    def install_appium(self):
        """Install Appium globally via npm"""
        try:
            self.logger.info("Installing Appium globally...")
            result = subprocess.run(['npm', 'install', '-g', 'appium'], 
                                  capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                self.logger.info("Appium installed successfully")
                return True, "Appium installed successfully"
            else:
                error_msg = result.stderr or result.stdout
                self.logger.error(f"Appium installation failed: {error_msg}")
                return False, f"Installation failed: {error_msg}"
                
        except subprocess.TimeoutExpired:
            return False, "Installation timeout - please try manually"
        except Exception as e:
            return False, f"Installation error: {str(e)}"
    
    def check_server_running(self):
        """Check if Appium server is already running"""
        try:
            response = requests.get(f"{self.server_url}/status", timeout=3)
            if response.status_code == 200:
                self.is_running = True
                return True
            else:
                self.is_running = False
                return False
        except requests.RequestException:
            self.is_running = False
            return False
    
    def find_appium_process(self):
        """Find running Appium processes"""
        appium_processes = []
        try:
            for process in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if process.info['name'] and 'node' in process.info['name'].lower():
                        cmdline = process.info['cmdline']
                        if cmdline and any('appium' in cmd.lower() for cmd in cmdline):
                            appium_processes.append({
                                'pid': process.info['pid'],
                                'cmdline': ' '.join(cmdline)
                            })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            self.logger.error(f"Error finding Appium processes: {e}")
        
        return appium_processes
    
    def start_server(self, callback=None):
        """Start Appium server in background"""
        def _start_server():
            try:
                # Check if server is already running
                if self.check_server_running():
                    self.logger.info("Appium server already running")
                    if callback:
                        callback(True, "Server already running")
                    return
                
                # Kill any existing Appium processes
                existing_processes = self.find_appium_process()
                for process in existing_processes:
                    try:
                        psutil.Process(process['pid']).terminate()
                        self.logger.info(f"Terminated existing Appium process: {process['pid']}")
                    except:
                        pass
                
                # Wait a bit for processes to close
                time.sleep(2)
                
                # Start new Appium server
                self.logger.info(f"Starting Appium server on port {self.server_port}")
                
                # Try different command variations for Windows
                appium_commands = ['appium', 'appium.cmd', 'appium.exe']
                
                server_started = False
                for appium_cmd in appium_commands:
                    try:
                        # Appium command with options (v3.0.1 compatible)
                        cmd = [
                            appium_cmd,
                            '--port', str(self.server_port),
                            '--address', self.server_host,  # Changed from --host to --address
                            '--session-override',  # Override existing sessions
                            '--log-timestamp',     # Add timestamps to logs
                            '--local-timezone',    # Use local timezone
                        ]
                        
                        self.logger.info(f"Trying to start server with command: {appium_cmd}")
                        
                        # Start process - remove CREATE_NEW_CONSOLE for better compatibility
                        self.server_process = subprocess.Popen(
                            cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True,
                            shell=False  # Don't use shell on Windows
                        )
                        
                        # Wait a moment to see if process starts successfully
                        time.sleep(2)
                        if self.server_process.poll() is None:  # Process is still running
                            server_started = True
                            self.logger.info(f"Successfully started Appium with command: {appium_cmd}")
                            break
                        else:
                            stdout, stderr = self.server_process.communicate()
                            self.logger.warning(f"Command {appium_cmd} failed immediately: {stderr}")
                            continue
                            
                    except FileNotFoundError:
                        self.logger.debug(f"Command {appium_cmd} not found, trying next...")
                        continue
                    except Exception as e:
                        self.logger.warning(f"Failed to start with {appium_cmd}: {e}")
                        continue
                
                if not server_started:
                    error_msg = "Failed to start Appium server with any command variation"
                    self.logger.error(error_msg)
                    if callback:
                        callback(False, error_msg)
                    return
                
                # Wait for server to start
                max_attempts = 30  # 30 seconds timeout
                for attempt in range(max_attempts):
                    time.sleep(1)
                    if self.check_server_running():
                        self.logger.info("Appium server started successfully")
                        if callback:
                            callback(True, "Server started successfully")
                        return
                    
                    # Check if process died
                    if self.server_process.poll() is not None:
                        stdout, stderr = self.server_process.communicate()
                        error_msg = f"Server failed to start. Error: {stderr}"
                        self.logger.error(error_msg)
                        if callback:
                            callback(False, error_msg)
                        return
                
                # Timeout
                error_msg = "Server startup timeout"
                self.logger.error(error_msg)
                if callback:
                    callback(False, error_msg)
                    
            except Exception as e:
                error_msg = f"Failed to start server: {str(e)}"
                self.logger.error(error_msg)
                if callback:
                    callback(False, error_msg)
        
        # Start in background thread
        thread = threading.Thread(target=_start_server, daemon=True)
        thread.start()
    
    def stop_server(self):
        """Stop Appium server"""
        try:
            # Stop our process if we started it
            if self.server_process and self.server_process.poll() is None:
                self.server_process.terminate()
                self.server_process.wait(timeout=10)
                self.logger.info("Appium server stopped")
            
            # Kill any remaining Appium processes
            existing_processes = self.find_appium_process()
            for process in existing_processes:
                try:
                    psutil.Process(process['pid']).terminate()
                    self.logger.info(f"Terminated Appium process: {process['pid']}")
                except:
                    pass
            
            self.is_running = False
            return True, "Server stopped successfully"
            
        except Exception as e:
            error_msg = f"Error stopping server: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def get_server_status(self):
        """Get detailed server status"""
        status = {
            'running': False,
            'url': self.server_url,
            'port': self.server_port,
            'processes': [],
            'version': None
        }
        
        # Check if server is responding
        status['running'] = self.check_server_running()
        
        # Get running processes
        status['processes'] = self.find_appium_process()
        
        # Get version if available
        if status['running']:
            try:
                response = requests.get(f"{self.server_url}/status", timeout=3)
                if response.status_code == 200:
                    data = response.json()
                    status['version'] = data.get('value', {}).get('build', {}).get('version')
            except:
                pass
        
        return status
    
    def get_server_logs(self):
        """Get server logs if process is running"""
        if not self.server_process:
            return "No server process found"
        
        try:
            # This is basic - in production you'd want better log handling
            return "Server logs would appear here (implement log file reading)"
        except Exception as e:
            return f"Error reading logs: {str(e)}"

# Utility functions for GUI integration
def check_prerequisites():
    """Check if all prerequisites are installed"""
    manager = AppiumServerManager()
    results = {}
    
    # Check Node.js
    node_ok, node_info = manager.check_node_installed()
    results['node'] = {'installed': node_ok, 'info': node_info}
    
    # Check Appium
    appium_ok, appium_info = manager.check_appium_installed()
    results['appium'] = {'installed': appium_ok, 'info': appium_info}
    
    # Check ADB (Android SDK)
    try:
        result = subprocess.run(['adb', 'version'], capture_output=True, text=True, timeout=5)
        adb_ok = result.returncode == 0
        adb_info = result.stdout.strip() if adb_ok else "ADB not found"
    except:
        adb_ok, adb_info = False, "ADB not installed"
    
    results['adb'] = {'installed': adb_ok, 'info': adb_info}
    
    return results

def install_missing_prerequisites():
    """Install missing prerequisites"""
    results = check_prerequisites()
    installation_results = {}
    
    # Install Appium if missing
    if not results['appium']['installed'] and results['node']['installed']:
        manager = AppiumServerManager()
        success, message = manager.install_appium()
        installation_results['appium'] = {'success': success, 'message': message}
    
    return installation_results

if __name__ == "__main__":
    # Test the server manager
    logging.basicConfig(level=logging.INFO)
    
    manager = AppiumServerManager()
    
    print("🔍 Checking prerequisites...")
    prereqs = check_prerequisites()
    for component, info in prereqs.items():
        status = "✅" if info['installed'] else "❌"
        print(f"{status} {component}: {info['info']}")
    
    print("\n🚀 Checking server status...")
    status = manager.get_server_status()
    print(f"Server running: {status['running']}")
    print(f"Server URL: {status['url']}")
    print(f"Active processes: {len(status['processes'])}")
    
    if not status['running']:
        print("\n💡 To start server manually, run:")
        print("appium --address 127.0.0.1 --port 4723")