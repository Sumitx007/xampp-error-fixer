hahah = r"""

              ____   _   _  __  __  ___  _____ 
             / ___| | | | ||  \/  ||_ _||_   _|
             \___ \ | | | || |\/| | | |   | |  
              ___) || |_| || |  | | | |   | |  
             |____/  \___/ |_|  |_||___|  |_|  
                                   
        https://github.com/sumitx007/xampp-error-fixer
"""
print(hahah)
import os
import shutil
import subprocess
import time
import ctypes
import re

# Configuration
FOLDERS_TO_DELETE = ["mysql", "performance_schema", "test", "phpmyadmin"]
FILES_TO_KEEP = ["ibdata1"]

def is_admin():
    """Check if script is running as administrator"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def find_xampp_path():
    """Find XAMPP installation path"""
    for drive in ["C:\\", "D:\\", "E:\\", "F:\\"]:
        xampp_path = os.path.join(drive, "xampp")
        if os.path.exists(os.path.join(xampp_path, "xampp-control.exe")):
            return xampp_path
    return None

def stop_all_xampp():
    """Stop all XAMPP processes completely"""
    processes = ["httpd.exe", "mysqld.exe", "xampp-control.exe"]
    
    for process in processes:
        try:
            subprocess.run(['taskkill', '/F', '/IM', process], 
                         capture_output=True, check=False)
        except:
            pass
    
    time.sleep(3)

def is_process_running(process_name):
    """Check if a specific process is running"""
    result = subprocess.run(['tasklist', '/FI', f'IMAGENAME eq {process_name}'],
                          capture_output=True, text=True)
    return process_name in result.stdout

def get_port_usage(port):
    """Get what process is using a specific port"""
    try:
        result = subprocess.run(['netstat', '-ano'], capture_output=True, text=True)
        for line in result.stdout.split('\n'):
            if f':{port}' in line and 'LISTENING' in line:
                # Extract PID from the line
                parts = line.split()
                if len(parts) >= 5:
                    pid = parts[-1]
                    # Get process name from PID
                    tasklist_result = subprocess.run(['tasklist', '/FI', f'PID eq {pid}'], 
                                                   capture_output=True, text=True)
                    for task_line in tasklist_result.stdout.split('\n'):
                        if pid in task_line:
                            process_name = task_line.split()[0]
                            return {'process': process_name, 'pid': pid}
        return None
    except:
        return None

def get_apache_listen_ports(httpd_conf_path):
    """Get actual ports Apache is configured to listen on"""
    ports = set()
    if os.path.exists(httpd_conf_path):
        try:
            with open(httpd_conf_path, 'r') as f:
                for line in f:
                    # Remove comments after #
                    line = line.split('#')[0].strip()
                    if line.lower().startswith("listen"):
                        # Extract port number from Listen line
                        # Match either 'Listen 80' or 'Listen 0.0.0.0:8080' or 'Listen [::]:443'
                        match = re.search(r'Listen\s+(?:\S+:)?(\d{2,5})', line, re.IGNORECASE)
                        if match:
                            ports.add(int(match.group(1)))
        except Exception as e:
            print(f"⚠️ Error parsing httpd.conf: {e}")
    return list(ports) if ports else [80, 443]  # Default fallback

def find_available_port(start_port, avoid_ports=None):
    """Find an available port starting from start_port"""
    if avoid_ports is None:
        avoid_ports = []
    
    for port in range(start_port, start_port + 100):
        if port not in avoid_ports and not get_port_usage(port):
            return port
    return start_port  # Fallback

def diagnose_mysql(xampp_path):
    """Diagnose MySQL issues with clean output"""
    print("🔍 Checking MySQL...")
    
    mysql_exe = os.path.join(xampp_path, "mysql", "bin", "mysqld.exe")
    mysql_ini = os.path.join(xampp_path, "mysql", "bin", "my.ini")
    
    if not os.path.exists(mysql_exe):
        return {"status": "error", "issue": "MySQL executable not found"}
    
    # Try to start MySQL with suppressed output
    try:
        # Redirect all MySQL output to devnull to keep console clean
        with open(os.devnull, 'w') as devnull:
            process = subprocess.Popen([mysql_exe, f"--defaults-file={mysql_ini}", "--standalone"],
                                     cwd=os.path.dirname(mysql_exe),
                                     stdout=devnull, 
                                     stderr=devnull)
        time.sleep(5)
        
        if is_process_running("mysqld.exe"):
            # Test stability
            for i in range(3):
                time.sleep(3)
                if not is_process_running("mysqld.exe"):
                    # MySQL crashed - has the error
                    return {"status": "error", "issue": "MySQL stops unexpectedly"}
            
            # MySQL is stable
            subprocess.run(['taskkill', '/F', '/IM', 'mysqld.exe'], 
                         capture_output=True, check=False)
            return {"status": "ok", "issue": None}
        else:
            return {"status": "error", "issue": "MySQL fails to start"}
            
    except Exception as e:
        return {"status": "error", "issue": f"MySQL startup error: {str(e)}"}

def test_services(xampp_path):
    """Test if services start properly after fixes - with clean output"""
    print("\n🧪 Testing services...")
    
    mysql_exe = os.path.join(xampp_path, "mysql", "bin", "mysqld.exe")
    mysql_ini = os.path.join(xampp_path, "mysql", "bin", "my.ini")
    apache_exe = os.path.join(xampp_path, "apache", "bin", "httpd.exe")
    
    results = {"mysql": False, "apache": False}
    
    # Test MySQL with suppressed output
    try:
        with open(os.devnull, 'w') as devnull:
            subprocess.Popen([mysql_exe, f"--defaults-file={mysql_ini}", "--standalone"],
                           cwd=os.path.dirname(mysql_exe),
                           stdout=devnull, 
                           stderr=devnull)
        time.sleep(5)
        if is_process_running("mysqld.exe"):
            print("✅ MySQL: Working")
            results["mysql"] = True
        else:
            print("❌ MySQL: Failed to start")
    except:
        print("❌ MySQL: Error during startup")
    
    # Test Apache with suppressed output
    try:
        with open(os.devnull, 'w') as devnull:
            subprocess.Popen([apache_exe], 
                           cwd=os.path.dirname(apache_exe),
                           stdout=devnull, 
                           stderr=devnull)
        time.sleep(3)
        if is_process_running("httpd.exe"):
            print("✅ Apache: Working")
            results["apache"] = True
        else:
            print("❌ Apache: Failed to start")
    except:
        print("❌ Apache: Error during startup")
    
    return results
def diagnose_apache(xampp_path):
    """Diagnose Apache issues with intelligent port detection"""
    print("🔍 Checking Apache...")
    
    apache_exe = os.path.join(xampp_path, "apache", "bin", "httpd.exe")
    
    if not os.path.exists(apache_exe):
        return {"status": "error", "issue": "Apache executable not found", "conflicts": [], "configured_ports": []}
    
    # Get the actual ports Apache is configured to use
    httpd_conf_path = os.path.join(xampp_path, "apache", "conf", "httpd.conf")
    apache_ports = get_apache_listen_ports(httpd_conf_path)
    
    print(f"📋 Apache is configured to use ports: {', '.join(map(str, apache_ports))}")
    
    # Check port conflicts ONLY for the ports Apache is actually configured to use
    conflicts = []
    for port in apache_ports:
        port_info = get_port_usage(port)
        if port_info and port_info['process'].lower() != 'httpd.exe':
            conflicts.append({
                'port': port,
                'process': port_info['process'],
                'pid': port_info['pid']
            })
            print(f"⚠️ Port {port} conflict: {port_info['process']} (PID: {port_info['pid']})")
    
    if conflicts:
        return {
            "status": "error", 
            "issue": "Port conflicts detected on Apache's configured ports", 
            "conflicts": conflicts,
            "configured_ports": apache_ports
        }
    
    # Try to start Apache
    try:
        process = subprocess.Popen([apache_exe], cwd=os.path.dirname(apache_exe))
        time.sleep(3)
        
        if is_process_running("httpd.exe"):
            subprocess.run(['taskkill', '/F', '/IM', 'httpd.exe'], capture_output=True)
            return {
                "status": "ok", 
                "issue": None, 
                "conflicts": [],
                "configured_ports": apache_ports
            }
        else:
            return {
                "status": "error", 
                "issue": "Apache fails to start", 
                "conflicts": [],
                "configured_ports": apache_ports
            }
            
    except Exception as e:
        return {
            "status": "error", 
            "issue": f"Apache startup error: {str(e)}", 
            "conflicts": [],
            "configured_ports": apache_ports
        }

def get_user_choice(question, options):
    """Get user choice from multiple options"""
    while True:
        try:
            print(f"\n{question}")
            for i, option in enumerate(options, 1):
                print(f"{i}. {option}")
            
            choice = input(f"\nYour choice (1-{len(options)}): ").strip()
            if choice.isdigit() and 1 <= int(choice) <= len(options):
                return int(choice) - 1
            else:
                print("Please enter a valid number")
        except KeyboardInterrupt:
            print("\n❌ Operation cancelled")
            return -1

def get_yes_no(question):
    """Get yes/no input from user"""
    while True:
        try:
            answer = input(f"{question} (y/n): ").strip().lower()
            if answer in ['y', 'yes']:
                return True
            elif answer in ['n', 'no']:
                return False
            else:
                print("Please enter 'y' or 'n'")
        except KeyboardInterrupt:
            print("\n❌ Operation cancelled")
            return False

def fix_mysql(xampp_path):
    """Fix MySQL stopped unexpectedly error"""
    print("\n🔧 Fixing MySQL...")
    
    data_path = os.path.join(xampp_path, "mysql", "data")
    backup_path = os.path.join(xampp_path, "mysql", "backup")
    
    # Create backup
    print("📦 Creating backup...")
    parent_dir = os.path.dirname(data_path)
    old_data_path = os.path.join(parent_dir, "Old-data")
    
    try:
        if os.path.exists(old_data_path):
            if get_yes_no("Old backup exists. Replace it?"):
                shutil.rmtree(old_data_path)
            else:
                import datetime
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                old_data_path = os.path.join(parent_dir, f"backup_{timestamp}")
        
        shutil.copytree(data_path, old_data_path)
        print(f"✅ Backup created: {os.path.basename(old_data_path)}")
        
        # Clean data folder
        print("🧹 Cleaning data folder...")
        for item in os.listdir(data_path):
            full_path = os.path.join(data_path, item)
            
            if os.path.isdir(full_path) and item in FOLDERS_TO_DELETE:
                shutil.rmtree(full_path, ignore_errors=True)
                print(f"🗑️ Removed folder: {item}")
            elif os.path.isfile(full_path) and item not in FILES_TO_KEEP:
                try:
                    os.remove(full_path)
                    print(f"🗑️ Removed file: {item}")
                except:
                    pass
        
        # Restore from backup
        print("📂 Restoring from backup...")
        for item in os.listdir(backup_path):
            if item in FILES_TO_KEEP:
                continue
                
            src = os.path.join(backup_path, item)
            dst = os.path.join(data_path, item)
            
            if os.path.isdir(src):
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dst)
        
        print("✅ MySQL fix completed")
        return True
        
    except Exception as e:
        print(f"❌ MySQL fix failed: {e}")
        return False

def fix_apache_ports(xampp_path, conflicts, configured_ports):
    """Handle Apache port conflicts with intelligent port management"""
    print(f"\n🔧 Apache Port Conflict Detected!")
    
    # Show conflicts with better formatting
    print(f"\nApache is configured to use ports: {', '.join(map(str, configured_ports))}")
    print("Conflicts found:")
    for conflict in conflicts:
        print(f"  Port {conflict['port']}: occupied by {conflict['process']} (PID: {conflict['pid']})")
    
    # User choice
    options = [
        "Stop conflicting services (Recommended)",
        "Change Apache to use different available ports",
        "Skip Apache fix"
    ]
    
    choice = get_user_choice("How would you like to resolve this?", options)
    
    if choice == 0:  # Stop conflicting services
        print("\n🛑 Stopping conflicting services...")
        success = True
        for conflict in conflicts:
            try:
                subprocess.run(['taskkill', '/F', '/PID', conflict['pid']], check=True)
                print(f"✅ Stopped {conflict['process']} (was using port {conflict['port']})")
            except:
                print(f"⚠️ Could not stop {conflict['process']} on port {conflict['port']}")
                success = False
        
        if success:
            print("✅ All port conflicts resolved")
            return True
        else:
            print("⚠️ Some conflicts remain - Apache may still have issues")
            return False
            
    elif choice == 1:  # Change ports
        print("\n🔧 Finding available ports and updating Apache configuration...")
        try:
            httpd_conf = os.path.join(xampp_path, "apache", "conf", "httpd.conf")
            if not os.path.exists(httpd_conf):
                print("❌ Apache config file not found")
                return False
            
            # Read current config
            with open(httpd_conf, 'r') as f:
                content = f.read()
            
            # Create port mapping (old port -> new available port)
            port_mapping = {}
            used_ports = []
            
            for old_port in configured_ports:
                # Find available port based on common port ranges
                if old_port in [80, 8080]:  # HTTP ports
                    new_port = find_available_port(8080, used_ports)
                elif old_port in [443, 8443]:  # HTTPS ports
                    new_port = find_available_port(8443, used_ports)
                else:  # Other ports
                    new_port = find_available_port(old_port + 1000, used_ports)
                
                port_mapping[old_port] = new_port
                used_ports.append(new_port)
            
            # Update Listen directives
            for old_port, new_port in port_mapping.items():
                # Replace Listen directives (handle various formats)
                content = re.sub(rf'^Listen\s+{old_port}$', f'Listen {new_port}', content, flags=re.MULTILINE)
                content = re.sub(rf'^Listen\s+\*:{old_port}$', f'Listen *:{new_port}', content, flags=re.MULTILINE)
                content = re.sub(rf'^Listen\s+0\.0\.0\.0:{old_port}$', f'Listen 0.0.0.0:{new_port}', content, flags=re.MULTILINE)
            
            # Write updated config
            with open(httpd_conf, 'w') as f:
                f.write(content)
            
            # Show results
            print("✅ Apache ports updated:")
            for old_port, new_port in port_mapping.items():
                print(f"   {old_port} → {new_port}")
            
            # Show access URLs
            http_ports = [new_port for old_port, new_port in port_mapping.items() if old_port in [80, 8080]]
            if http_ports:
                print(f"💡 Access your sites at: http://localhost:{http_ports[0]}")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to change ports: {e}")
            return False
            
    else:  # Skip
        print("⏭️ Apache fix skipped")
        return False

def test_services(xampp_path):
    """Test if services start properly after fixes"""
    print("\n🧪 Testing services...")
    
    mysql_exe = os.path.join(xampp_path, "mysql", "bin", "mysqld.exe")
    mysql_ini = os.path.join(xampp_path, "mysql", "bin", "my.ini")
    apache_exe = os.path.join(xampp_path, "apache", "bin", "httpd.exe")
    
    results = {"mysql": False, "apache": False}
    
    # Test MySQL
    try:
        subprocess.Popen([mysql_exe, f"--defaults-file={mysql_ini}", "--standalone"],
                        cwd=os.path.dirname(mysql_exe))
        time.sleep(5)
        if is_process_running("mysqld.exe"):
            print("✅ MySQL: Working")
            results["mysql"] = True
        else:
            print("❌ MySQL: Failed to start")
    except:
        print("❌ MySQL: Error during startup")
    
    # Test Apache
    try:
        subprocess.Popen([apache_exe], cwd=os.path.dirname(apache_exe))
        time.sleep(3)
        if is_process_running("httpd.exe"):
            print("✅ Apache: Working")
            results["apache"] = True
        else:
            print("❌ Apache: Failed to start")
    except:
        print("❌ Apache: Error during startup")
    
    return results
def revert_apache_ports_to_default(xampp_path):
    """Ask to revert Apache ports to default (80/443) only if they are free and we can actually do it"""
    # Get current Apache configuration
    httpd_conf_path = os.path.join(xampp_path, "apache", "conf", "httpd.conf")
    current_ports = get_apache_listen_ports(httpd_conf_path)
    
    # Check if Apache is already using default ports
    if 80 in current_ports and (443 in current_ports or len(current_ports) == 1):
        return False  # Already using default ports
    
    # Check if default ports are available
    conflict_80 = get_port_usage(80)
    conflict_443 = get_port_usage(443)

    if conflict_80 or conflict_443:
        return False  # Default ports still occupied, silently skip

    # Only ask if we have non-default ports AND we can actually revert them
    non_default_ports = [p for p in current_ports if p not in [80, 443]]
    if not non_default_ports:
        return False  # No non-default ports to revert
    
    # Ask user if they want to revert
    if not get_yes_no(f"\n💡 Default ports (80/443) are now free. Revert Apache from current ports {non_default_ports} to default ports?"):
        print("⏭️ Reverting skipped by user.")
        return False

    try:
        httpd_conf = os.path.join(xampp_path, "apache", "conf", "httpd.conf")
        if not os.path.exists(httpd_conf):
            print("❌ Apache config file not found")
            return False
            
        with open(httpd_conf, 'r') as f:
            content = f.read()

        # Smart port reverting - handle ANY non-default port
        changes_made = False
        
        # For each non-default port, decide what to revert it to
        for current_port in non_default_ports:
            target_port = None
            
            # If we only have one port and it's not 443, make it port 80
            if len(current_ports) == 1:
                target_port = 80
            # If we have multiple ports, try to be smart about HTTP vs HTTPS
            elif current_port > 8000:  # Likely HTTP alternative
                target_port = 80
            elif current_port > 4000:  # Likely HTTPS alternative  
                target_port = 443
            else:
                target_port = 80  # Default to HTTP
            
            # Make sure we don't create duplicate Listen directives
            if target_port in current_ports:
                continue
                
            # Replace all variations of Listen directives for this port
            patterns = [
                rf'^Listen\s+{current_port}$',
                rf'^Listen\s+\*:{current_port}$', 
                rf'^Listen\s+0\.0\.0\.0:{current_port}$',
                rf'^Listen\s+\[::\]:{current_port}$'
            ]
            
            for pattern in patterns:
                old_content = content
                content = re.sub(pattern, f'Listen {target_port}', content, flags=re.MULTILINE)
                if content != old_content:
                    changes_made = True
                    print(f"✅ Reverted port {current_port} → {target_port}")

        # Write the updated config
        if changes_made:
            with open(httpd_conf, 'w') as f:
                f.write(content)
            
            print("💡 Access your sites at: http://localhost")
            return True
        else:
            print("⚠️ No port changes were made")
            return False
            
    except Exception as e:
        print(f"❌ Failed to revert ports: {e}")
        return False

def main():
    """Main execution function"""
    print("=== XAMPP Fixer ===\n")
    
    # Check admin privileges
    if not is_admin():
        print("❌ Administrator privileges required")
        print("💡 Right-click script and 'Run as administrator'")
        input("Press Enter to exit...")
        return
    
    # Find XAMPP
    xampp_path = find_xampp_path()
    if not xampp_path:
        print("❌ XAMPP not found on drives C:, D:, E:, F:")
        input("Press Enter to exit...")
        return
    
    print(f"🔍 XAMPP found at: {xampp_path}")
    
    # Clean start
    print("\n🛑 Stopping any running XAMPP services...")
    stop_all_xampp()
    
    # Auto-diagnosis
    print("\n=== Auto-Diagnosis ===")
    mysql_diagnosis = diagnose_mysql(xampp_path)
    apache_diagnosis = diagnose_apache(xampp_path)
    
    # Report results
    print("\n📋 Diagnosis Results:")
    
    mysql_ok = mysql_diagnosis["status"] == "ok"
    apache_ok = apache_diagnosis["status"] == "ok"
    
    if mysql_ok:
        print("✅ MySQL: Working fine")
    else:
        print(f"❌ MySQL: {mysql_diagnosis['issue']}")
    
    if apache_ok:
        print("✅ Apache: Working fine")
    else:
        print(f"❌ Apache: {apache_diagnosis['issue']}")
    
    # Apply fixes
    if not mysql_ok or not apache_ok:
        print("\n=== Applying Fixes ===")
        
        # Fix MySQL - Handle both "fails to start" and "stops unexpectedly"
        if not mysql_ok:
            mysql_issue = mysql_diagnosis['issue']
            if mysql_issue == "MySQL stops unexpectedly" or mysql_issue == "MySQL fails to start":
                if get_yes_no("Fix MySQL database issue? This will restore your databases"):
                    fix_mysql(xampp_path)
                else:
                    print("⏭️ MySQL fix skipped")
            else:
                print(f"⚠️ MySQL issue ({mysql_issue}) - manual intervention may be needed")
        
        # Fix Apache with intelligent port management
        if not apache_ok and 'conflicts' in apache_diagnosis:
            if apache_diagnosis['conflicts']:
                fix_apache_ports(xampp_path, apache_diagnosis['conflicts'], apache_diagnosis['configured_ports'])
            elif apache_diagnosis['issue'] == "Apache fails to start":
                print("⚠️ Apache fails to start - this may require manual configuration check")
        
        # Test final results
        print("\n=== Final Testing ===")
        stop_all_xampp()  # Clean slate for testing
        time.sleep(2)
        results = test_services(xampp_path)
        
        # Clean shutdown
        print("\n=== Cleanup ===")
        stop_all_xampp()
        print("✅ All services stopped for clean state")
        
        # Success summary
        if results["mysql"] and results["apache"]:
            print("\n🎉 SUCCESS! Both MySQL and Apache are now working!")
            print("💡 You can now start them from XAMPP Control Panel")
        elif results["mysql"]:
            print("\n✅ MySQL is working! Apache may need manual attention.")
        elif results["apache"]:
            print("\n✅ Apache is working! MySQL may need manual attention.")
        else:
            print("\n⚠️ Some issues may remain. Check XAMPP Control Panel.")
    
    else:
        print("\n🎉 Great! Your XAMPP is already working perfectly!")
        print("✅ No fixes needed")
    
    # Optionally revert Apache to default ports
    revert_apache_ports_to_default(xampp_path)

    # User choice for Control Panel
    if get_yes_no("\n💡 Would you like to open XAMPP Control Panel now?"):
        try:
            xampp_control = os.path.join(xampp_path, "xampp-control.exe")
            subprocess.Popen([xampp_control])
            print("✅ XAMPP Control Panel opened")
        except:
            print("❌ Could not open XAMPP Control Panel")
    
    print("\n🎉 Done! You can now use XAMPP normally.")
    input("Press Enter to exit...")

if __name__ == "__main__":
    main()