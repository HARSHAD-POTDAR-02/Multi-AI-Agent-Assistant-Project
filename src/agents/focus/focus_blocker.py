import subprocess
import os
import psutil
import ctypes
import sys
import time
import threading
from typing import List

class FocusBlocker:
    def __init__(self):
        self.blocked_websites = [
            "youtube.com", "facebook.com", "twitter.com", "instagram.com",
            "reddit.com", "tiktok.com", "netflix.com", "twitch.tv"
        ]
        self.blocked_apps = [
            "steam.exe", "discord.exe", "spotify.exe", "telegram.exe",
            "whatsapp.exe", "games.exe", "netflix.exe"
        ]
        self.is_blocking = False
        self.block_thread = None
        self.hosts_file = r"C:\Windows\System32\drivers\etc\hosts"
        self.backup_file = r"C:\Windows\System32\drivers\etc\hosts.backup"

    def is_admin(self):
        """Check if running with admin privileges"""
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False

    def enable_focus_mode_with_elevation(self):
        """Enable focus mode with automatic elevation"""
        results = []
        
        # Method 1: Try direct website blocking
        if self.is_admin():
            try:
                self._block_websites_direct()
                results.append(f"✅ {len(self.blocked_websites)} websites blocked")
            except Exception as e:
                results.append(f"❌ Direct blocking failed: {str(e)}")
        else:
            # Method 2: Auto-elevate and block immediately
            try:
                success = self._auto_elevate_and_block()
                if success:
                    results.append(f"✅ {len(self.blocked_websites)} websites blocked (auto-elevated)")
                else:
                    results.append("❌ Auto-elevation failed")
            except Exception as e:
                results.append(f"❌ Auto-elevation error: {str(e)}")
        
        # Method 3: Start app monitoring
        try:
            self.is_blocking = True
            self.block_thread = threading.Thread(target=self._continuous_blocking, daemon=True)
            self.block_thread.start()
            results.append("✅ App monitoring started")
        except Exception as e:
            results.append(f"❌ App monitoring failed: {str(e)}")
        
        # Method 4: Close existing apps
        try:
            closed_apps = self._close_distracting_apps()
            if closed_apps:
                results.append(f"✅ Closed: {', '.join(closed_apps)}")
            else:
                results.append("ℹ️ No distracting apps found")
        except Exception as e:
            results.append(f"❌ App closing failed: {str(e)}")
        
        # Method 5: Enable Focus Assist
        try:
            self._enable_focus_assist()
            results.append("✅ Focus Assist enabled")
        except Exception as e:
            results.append(f"❌ Focus Assist failed: {str(e)}")
        
        return "Focus mode activated:\n" + "\n".join(results)

    def _block_websites_direct(self):
        """Direct website blocking with multiple methods"""
        success_methods = []
        
        # Method 1: Try firewall blocking first (most effective)
        try:
            self._firewall_block_sites()
            success_methods.append("firewall")
        except Exception as e:
            print(f"Firewall blocking failed: {e}")
        
        # Method 2: Fallback to hosts file
        try:
            self._block_websites_hosts()
            success_methods.append("hosts")
        except Exception as e:
            print(f"Hosts blocking failed: {e}")
        
        if not success_methods:
            raise Exception("All blocking methods failed")
        
        return success_methods
    
    def _firewall_block_sites(self):
        """Block sites using Windows Firewall (most effective)"""
        for site in self.blocked_websites:
            # Block outbound connections to the site
            subprocess.run([
                "netsh", "advfirewall", "firewall", "add", "rule",
                f"name=FocusBlock_{site}", "dir=out", "action=block", 
                "protocol=any", f"remoteip={site}", "enable=yes"
            ], capture_output=True, check=True)
    
    def _block_websites_hosts(self):
        """Fallback: Block sites via hosts file"""
        # Backup original hosts file
        if not os.path.exists(self.backup_file):
            with open(self.hosts_file, 'r', encoding='utf-8') as original:
                with open(self.backup_file, 'w', encoding='utf-8') as backup:
                    backup.write(original.read())
        
        # Add blocked sites
        with open(self.hosts_file, 'a', encoding='utf-8') as f:
            f.write('\n# Focus mode blocks - AUTO GENERATED\n')
            for site in self.blocked_websites:
                f.write(f'127.0.0.1 {site}\n')
                f.write(f'127.0.0.1 www.{site}\n')
                f.write(f'127.0.0.1 m.{site}\n')
        
        # Flush DNS cache
        subprocess.run(['ipconfig', '/flushdns'], capture_output=True)

    def _auto_elevate_and_block(self):
        """Block websites using batch script with elevation"""
        try:
            # Create batch script for elevation
            batch_script = f'''@echo off
echo Blocking websites for focus mode...

REM Backup hosts file
if not exist "C:\\Windows\\System32\\drivers\\etc\\hosts.backup" (
    copy "C:\\Windows\\System32\\drivers\\etc\\hosts" "C:\\Windows\\System32\\drivers\\etc\\hosts.backup"
)

REM Add blocked sites
echo. >> "C:\\Windows\\System32\\drivers\\etc\\hosts"
echo # Focus mode blocks - AUTO GENERATED >> "C:\\Windows\\System32\\drivers\\etc\\hosts"
'''
            
            for site in self.blocked_websites:
                batch_script += f'echo 127.0.0.1 {site} >> "C:\\Windows\\System32\\drivers\\etc\\hosts"\n'
                batch_script += f'echo 127.0.0.1 www.{site} >> "C:\\Windows\\System32\\drivers\\etc\\hosts"\n'
            
            batch_script += '''\nREM Flush DNS\nipconfig /flushdns >nul 2>&1\n\necho SUCCESS: Websites blocked!\ntimeout /t 2 >nul\n'''
            
            # Write batch file
            batch_path = "focus_block_temp.bat"
            with open(batch_path, 'w') as f:
                f.write(batch_script)
            
            # Execute with elevation
            result = subprocess.run([
                'powershell', '-Command',
                f'Start-Process "{batch_path}" -Verb RunAs -Wait'
            ], capture_output=True, timeout=15)
            
            # Clean up
            try:
                os.remove(batch_path)
            except:
                pass
            
            return result.returncode == 0
        except Exception as e:
            print(f"Auto-elevation error: {e}")
            return False

    def _create_blocking_batch(self):
        """Create a batch file for manual admin execution"""
        try:
            batch_content = f'''@echo off
echo Creating website blocks...
echo.

REM Backup hosts file
if not exist "{self.backup_file}" (
    copy "{self.hosts_file}" "{self.backup_file}"
    echo Hosts file backed up
)

REM Add blocked sites
echo. >> "{self.hosts_file}"
echo # Focus mode blocks - AUTO GENERATED >> "{self.hosts_file}"
'''
            
            for site in self.blocked_websites:
                batch_content += f'echo 127.0.0.1 {site} >> "{self.hosts_file}"\n'
                batch_content += f'echo 127.0.0.1 www.{site} >> "{self.hosts_file}"\n'
            
            batch_content += f'''
REM Flush DNS
ipconfig /flushdns >nul 2>&1

echo.
echo SUCCESS: {len(self.blocked_websites)} websites blocked!
echo Press any key to close...
pause >nul
'''
            
            # Try multiple desktop paths
            possible_paths = [
                os.path.join(os.path.expanduser("~"), "OneDrive", "Desktop"),
                os.path.join(os.path.expanduser("~"), "Desktop"),
                os.getcwd()  # Current directory as fallback
            ]
            
            batch_path = None
            for path in possible_paths:
                try:
                    if os.path.exists(path):
                        batch_path = os.path.join(path, "FocusMode_BlockWebsites.bat")
                        break
                except:
                    continue
            
            if not batch_path:
                batch_path = "FocusMode_BlockWebsites.bat"  # Final fallback
            
            with open(batch_path, 'w') as f:
                f.write(batch_content)
            
            return True
        except Exception as e:
            print(f"Batch creation error: {e}")
            return False

    def _continuous_blocking(self):
        """Monitor and close distracting apps"""
        while self.is_blocking:
            try:
                for proc in psutil.process_iter(['pid', 'name']):
                    try:
                        if proc.info['name'].lower() in [app.lower() for app in self.blocked_apps]:
                            proc.terminate()
                            print(f"Blocked: {proc.info['name']}")
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                        continue
                time.sleep(3)  # Check every 3 seconds
            except Exception as e:
                print(f"Monitoring error: {e}")
                time.sleep(5)

    def _close_distracting_apps(self):
        """Close currently running distracting apps"""
        closed_apps = []
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if proc.info['name'].lower() in [app.lower() for app in self.blocked_apps]:
                    proc.terminate()
                    closed_apps.append(proc.info['name'])
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        return closed_apps

    def _enable_focus_assist(self):
        """Enable Windows Focus Assist"""
        try:
            # Disable notification sounds
            subprocess.run([
                'reg', 'add',
                'HKCU\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Notifications\\Settings',
                '/v', 'NOC_GLOBAL_SETTING_ALLOW_NOTIFICATION_SOUND',
                '/t', 'REG_DWORD',
                '/d', '0',
                '/f'
            ], capture_output=True)
            
            # Disable toast notifications
            subprocess.run([
                'reg', 'add',
                'HKCU\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\PushNotifications',
                '/v', 'ToastEnabled',
                '/t', 'REG_DWORD',
                '/d', '0',
                '/f'
            ], capture_output=True)
        except Exception as e:
            print(f"Focus Assist error: {e}")

    def disable_focus_mode(self):
        """Disable focus mode with auto-elevation"""
        results = []
        
        # Stop app monitoring
        self.is_blocking = False
        if self.block_thread:
            self.block_thread.join(timeout=2)
        results.append("✅ App monitoring stopped")
        
        # Restore websites
        if self.is_admin():
            try:
                self._restore_hosts_direct()
                results.append("✅ Website blocks removed")
            except Exception as e:
                results.append(f"❌ Direct restore failed: {str(e)}")
        else:
            try:
                success = self._auto_elevate_and_restore()
                if success:
                    results.append("✅ Website blocks removed (auto-elevated)")
                else:
                    results.append("❌ Auto-elevation restore failed")
            except Exception as e:
                results.append(f"❌ Restore error: {str(e)}")
        
        # Restore notifications
        try:
            subprocess.run([
                'reg', 'add',
                'HKCU\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Notifications\\Settings',
                '/v', 'NOC_GLOBAL_SETTING_ALLOW_NOTIFICATION_SOUND',
                '/t', 'REG_DWORD',
                '/d', '1',
                '/f'
            ], capture_output=True)
            results.append("✅ Notifications restored")
        except:
            results.append("⚠️ Notification restore failed")
        
        return "Focus mode deactivated:\n" + "\n".join(results)
    
    def _restore_hosts_direct(self):
        """Direct hosts file restoration (admin required)"""
        # Remove firewall rules
        self._firewall_unblock_sites()
        
        # Restore hosts file
        if os.path.exists(self.backup_file):
            with open(self.backup_file, 'r', encoding='utf-8') as backup:
                with open(self.hosts_file, 'w', encoding='utf-8') as hosts:
                    hosts.write(backup.read())
            os.remove(self.backup_file)
            subprocess.run(['ipconfig', '/flushdns'], capture_output=True)
    
    def _auto_elevate_and_restore(self):
        """Auto-elevate to restore hosts file"""
        try:
            restore_script = f'''@echo off
echo Restoring websites after focus mode...

REM Restore hosts file from backup
if exist "C:\\Windows\\System32\\drivers\\etc\\hosts.backup" (
    copy "C:\\Windows\\System32\\drivers\\etc\\hosts.backup" "C:\\Windows\\System32\\drivers\\etc\\hosts"
    del "C:\\Windows\\System32\\drivers\\etc\\hosts.backup"
    echo Hosts file restored
) else (
    echo No backup found - removing focus blocks manually
    findstr /v "Focus mode" "C:\\Windows\\System32\\drivers\\etc\\hosts" > "C:\\Windows\\System32\\drivers\\etc\\hosts.temp"
    move "C:\\Windows\\System32\\drivers\\etc\\hosts.temp" "C:\\Windows\\System32\\drivers\\etc\\hosts"
)

REM Flush DNS
ipconfig /flushdns >nul 2>&1

echo SUCCESS: Websites unblocked!
timeout /t 2 >nul
'''
            
            restore_path = "focus_restore_temp.bat"
            with open(restore_path, 'w') as f:
                f.write(restore_script)
            
            result = subprocess.run([
                'powershell', '-Command',
                f'Start-Process "{restore_path}" -Verb RunAs -Wait'
            ], capture_output=True, timeout=15)
            
            try:
                os.remove(restore_path)
            except:
                pass
            
            return result.returncode == 0
        except Exception as e:
            print(f"Auto-restore error: {e}")
            return False

    def get_blocked_status(self):
        """Get current blocking status"""
        return {
            "app_blocking_active": self.is_blocking,
            "websites_blocked": os.path.exists(self.backup_file),
            "admin_privileges": self.is_admin(),
            "blocked_sites_count": len(self.blocked_websites),
            "blocked_apps_count": len(self.blocked_apps)
        }

    def _firewall_unblock_sites(self):
        """Remove firewall blocking rules"""
        for site in self.blocked_websites:
            try:
                subprocess.run([
                    "netsh", "advfirewall", "firewall", "delete", "rule",
                    f"name=FocusBlock_{site}"
                ], capture_output=True)
            except:
                continue  # Rule might not exist
    
    def _check_focus_assist(self):
        """Check Focus Assist status"""
        try:
            result = subprocess.run([
                'reg', 'query',
                'HKCU\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Notifications\\Settings',
                '/v', 'NOC_GLOBAL_SETTING_ALLOW_NOTIFICATION_SOUND'
            ], capture_output=True, text=True)
            return "0x0" in result.stdout
        except:
            return False