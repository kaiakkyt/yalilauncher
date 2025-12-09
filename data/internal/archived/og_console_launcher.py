# DO NOT USE THIS FILE
# its archived, turned into launcher.pyw :)
# for the modern released version of this code with WAY more features, see the root launcher.pyw

import requests
import json
import os
import sys
import subprocess
import re
import time
from typing import Optional, Dict, List
from tkinter import Tk, filedialog

class MinecraftServerLauncher:
    def __init__(self):
        self.version = None
        self.software = None
        self.download_directory = None
        self.ram_amount = None
        self.supported_versions = [
            "1.8", "1.8.1", "1.8.2", "1.8.3", "1.8.4", "1.8.5", "1.8.6", "1.8.7", "1.8.8", "1.8.9",
            "1.9", "1.9.1", "1.9.2", "1.9.3", "1.9.4",
            "1.10", "1.10.1", "1.10.2",
            "1.11", "1.11.1", "1.11.2",
            "1.12", "1.12.1", "1.12.2",
            "1.13", "1.13.1", "1.13.2",
            "1.14", "1.14.1", "1.14.2", "1.14.3", "1.14.4",
            "1.15", "1.15.1", "1.15.2",
            "1.16", "1.16.1", "1.16.2", "1.16.3", "1.16.4", "1.16.5",
            "1.17", "1.17.1",
            "1.18", "1.18.1", "1.18.2",
            "1.19", "1.19.1", "1.19.2", "1.19.3", "1.19.4",
            "1.20", "1.20.1", "1.20.2", "1.20.3", "1.20.4", "1.20.5", "1.20.6",
            "1.21", "1.21.1", "1.21.2", "1.21.3", "1.21.4", "1.21.5", "1.21.6", "1.21.7", "1.21.8", "1.21.9", "1.21.10"
        ]
        self.supported_software = ["vanilla", "bukkit", "spigot", "paper", "purpur", "folia", "fabric", "forge", "neoforge", "bungeecord", "waterfall", "velocity"]
        
    def get_required_java_version(self, mc_version: str) -> int:
        """Get the required Java version for a Minecraft version"""
        parts = mc_version.split('.')
        major = int(parts[0])
        minor = int(parts[1]) if len(parts) > 1 else 0
        patch = int(parts[2]) if len(parts) > 2 else 0
        
        if major == 1:
            if minor <= 16:
                return 8
            elif minor == 17:
                return 16
            elif minor == 18 or minor == 19:
                return 17
            elif minor == 20:
                if patch <= 4:
                    return 17
                else:
                    return 21
            elif minor >= 21:
                return 21
        
        return 21
        
    def check_java_version(self) -> Optional[int]:
        """Check installed Java version"""
        print("\n[DEBUG] Checking Java installation...")
        try:
            result = subprocess.run(
                ['java', '-version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            output = result.stderr
            
            version_match = re.search(r'version\s+"?(\d+)\.?(\d+)?\.?(\d+)?', output)
            if version_match:
                major = int(version_match.group(1))
                if major == 1:
                    minor = int(version_match.group(2)) if version_match.group(2) else 0
                    java_version = minor
                else:
                    java_version = major
                    
                print(f"[DEBUG] Detected Java {java_version}")
                return java_version
            else:
                print("[WARNING] Could not parse Java version from output")
                return None
                
        except FileNotFoundError:
            print("[ERROR] Java is not installed or not in PATH")
            return None
        except subprocess.TimeoutExpired:
            print("[ERROR] Java version check timed out")
            return None
        except Exception as e:
            print(f"[ERROR] Failed to check Java version: {e}")
            return None
            
    def validate_java_version(self):
        """Validate that the correct Java version is installed"""
        required_java = self.get_required_java_version(self.version)
        installed_java = self.check_java_version()
        
        print(f"\n[INFO] Minecraft {self.version} requires Java {required_java}+")
        
        if installed_java is None:
            print("\n" + "="*50)
            print("   Java Not Found!")
            print("="*50)
            print("\n[ERROR] Java is not installed or not in your PATH")
            print("\nPlease install Java before continuing:")
            print(f"  - For Java {required_java}: https://adoptium.net/")
            print("  - After installation, restart your terminal")
            
            choice = input("\nContinue anyway? (yes/no): ").strip().lower()
            if choice not in ['yes', 'y']:
                print("[INFO] Setup cancelled")
                sys.exit(0)
        elif installed_java < required_java:
            print("\n" + "="*50)
            print("   Java Version Warning!")
            print("="*50)
            print(f"\n[WARNING] You have Java {installed_java}, but Java {required_java}+ is recommended")
            print(f"[WARNING] The server may not start or may have issues")
            print(f"\nDownload Java {required_java}: https://adoptium.net/")
            
            choice = input("\nContinue anyway? (yes/no): ").strip().lower()
            if choice not in ['yes', 'y']:
                print("[INFO] Setup cancelled")
                sys.exit(0)
        else:
            print(f"[SUCCESS] Java {installed_java} is compatible")
        
    def display_versions(self):
        """Display available Minecraft versions"""
        print("\n=== Available Minecraft Versions ===")
        print("Supported range: 1.8 - 1.21.10")
        print("\nPopular versions:")
        print("  1.8.8  - Legacy PvP")
        print("  1.12.2 - Stable modded")
        print("  1.16.5 - Popular modded")
        print("  1.19.4 - Recent stable")
        print("  1.20.1 - Pretty known")
        print("  1.21 - Current popular")
        print("  1.21.10 - Latest version")
        print("\nYou can enter any version between 1.8 and 1.21.10")
        
    def display_software(self):
        """Display available server software"""
        print("\n=== Available Server Software ===")
        print("\nVanilla & Plugin Servers:")
        print("  1. vanilla    - Official Minecraft server")
        print("  2. bukkit     - Classic plugin support (CraftBukkit)")
        print("  3. spigot     - Performance-optimized Bukkit fork")
        print("  4. paper      - High-performance Spigot fork (recommended)")
        print("  5. purpur     - Feature-rich Paper fork")
        print("  6. folia      - Multi-threaded Paper fork (experimental)")
        print("\nModded Servers:")
        print("  7. fabric     - Lightweight modding platform")
        print("  8. forge      - Popular modding platform")
        print("  9. neoforge   - Modern Forge fork (1.20.1+)")
        print("\nProxy Servers:")
        print("  10. bungeecord - Classic proxy server")
        print("  11. waterfall  - Improved BungeeCord fork")
        print("  12. velocity   - Modern, high-performance proxy")
        
    def get_version_input(self) -> str:
        """Get version input from user"""
        self.display_versions()
        while True:
            version = input("\nEnter Minecraft version (e.g., 1.20.1): ").strip()
            if version in self.supported_versions:
                print(f"[DEBUG] Version '{version}' validated successfully")
                return version
            else:
                print(f"[ERROR] Version '{version}' is not supported. Please enter a version between 1.8 and 1.21.10")
                
    def get_software_input(self) -> str:
        """Get software input from user"""
        self.display_software()
        while True:
            software = input("\nEnter server software: ").strip().lower()
            if software in self.supported_software:
                print(f"[DEBUG] Software '{software}' validated successfully")
                return software
            else:
                print(f"[ERROR] Software '{software}' is not supported. Choose from: {', '.join(self.supported_software)}")
                
    def get_directory_input(self) -> str:
        """Get download directory from user"""
        print("\n=== Select Download Directory ===")
        print("Choose how to select your download location:")
        print("1. Use file browser (recommended)")
        print("2. Enter path manually")
        
        while True:
            choice = input("\nEnter choice (1 or 2): ").strip()
            
            if choice == "1":
                print("[DEBUG] Opening Windows file browser...")
                try:
                    root = Tk()
                    root.withdraw()
                    root.attributes('-topmost', True)
                    
                    directory = filedialog.askdirectory(
                        title="Select Download Directory for Server JAR",
                        mustexist=True
                    )
                    root.destroy()
                    
                    if directory:
                        directory = os.path.normpath(directory)
                        print(f"[DEBUG] Selected directory: {directory}")
                        
                        if os.path.exists(directory) and os.path.isdir(directory):
                            if os.access(directory, os.W_OK):
                                print(f"[DEBUG] Directory is writable")
                                return directory
                            else:
                                print(f"[ERROR] Directory is not writable. Please choose another location.")
                                continue
                        else:
                            print(f"[ERROR] Invalid directory. Please try again.")
                            continue
                    else:
                        print("[INFO] No directory selected. Please try again.")
                        continue
                        
                except Exception as e:
                    print(f"[ERROR] Failed to open file browser: {e}")
                    print("[INFO] Falling back to manual entry...")
                    choice = "2"
            
            if choice == "2":
                directory = input("\nEnter full directory path (e.g., C:\\NON-WINDOWS THINGS\\jarholder): ").strip()
                
                directory = directory.strip('"').strip("'")
                
                print(f"[DEBUG] Validating directory: {directory}")
                
                if os.path.exists(directory):
                    if os.path.isdir(directory):
                        if os.access(directory, os.W_OK):
                            print(f"[DEBUG] Directory validated successfully")
                            return directory
                        else:
                            print(f"[ERROR] Directory exists but is not writable. Please check permissions.")
                    else:
                        print(f"[ERROR] Path exists but is not a directory")
                else:
                    create = input(f"[INFO] Directory doesn't exist. Create it? (yes/no): ").strip().lower()
                    if create in ['yes', 'y']:
                        try:
                            os.makedirs(directory, exist_ok=True)
                            print(f"[DEBUG] Directory created successfully: {directory}")
                            return directory
                        except Exception as e:
                            print(f"[ERROR] Failed to create directory: {e}")
                    else:
                        print("[INFO] Please enter a different path")
            else:
                print("[ERROR] Invalid choice. Please enter 1 or 2")
                
    def get_ram_input(self) -> str:
        """Get RAM amount from user"""
        print("\n=== Select RAM Amount ===")
        print("How much RAM do you want to allocate to the server?")
        print("\nRecommended amounts:")
        print("  1G  - Minimal (testing only)")
        print("  2G  - Small server (1-10 players)")
        print("  4G  - Medium server (10-20 players)")
        print("  8G  - Large server (20-50 players)")
        print("  16G - Very large server (50+ players)")
        print("\nYou can enter any amount (e.g., 1G, 2G, 4G, 512M)")
        
        while True:
            ram = input("\nEnter RAM amount (e.g., 4G): ").strip().upper()
            
            if ram and (ram[-1] == 'G' or ram[-1] == 'M'):
                try:
                    amount = ram[:-1]
                    if amount.replace('.', '', 1).isdigit():
                        num = float(amount)
                        if num > 0:
                            print(f"[DEBUG] RAM amount '{ram}' validated successfully")
                            return ram
                        else:
                            print("[ERROR] RAM amount must be greater than 0")
                    else:
                        print("[ERROR] Invalid RAM format")
                except ValueError:
                    print("[ERROR] Invalid RAM amount")
            else:
                print("[ERROR] RAM must end with 'G' (gigabytes) or 'M' (megabytes). Example: 4G, 2048M")
                
    def confirm_selection(self) -> bool:
        """Confirm user's selection"""
        print("\n" + "="*50)
        print(f"Selected Configuration:")
        print(f"  Version: {self.version}")
        print(f"  Software: {self.software}")
        print(f"  RAM: {self.ram_amount}")
        print(f"  Download Directory: {self.download_directory}")
        print("="*50)
        confirmation = input("\nProceed with download? (yes/no): ").strip().lower()
        confirmed = confirmation in ['yes', 'y']
        print(f"[DEBUG] User confirmation: {confirmed}")
        return confirmed
        
    def create_eula_file(self, jar_path: str):
        """Create eula.txt in the same directory as the server JAR"""
        try:
            eula_path = os.path.join(os.path.dirname(jar_path), "eula.txt")
            eula_content = """#By changing the setting below to TRUE you are indicating your agreement to our EULA (https://aka.ms/MinecraftEULA).
#by YaliLauncher :)
eula=TRUE
"""
            with open(eula_path, 'w') as f:
                f.write(eula_content)
            print(f"[DEBUG] Created eula.txt: {eula_path}")
            return eula_path
        except Exception as e:
            print(f"[ERROR] Failed to create eula.txt: {e}")
            return None
            
    def create_start_batch(self, jar_path: str):
        """Create start.bat in the same directory as the server JAR"""
        try:
            batch_path = os.path.join(os.path.dirname(jar_path), "start.bat")
            jar_name = os.path.basename(jar_path)
            
            required_java = self.get_required_java_version(self.version)
            
            batch_content = f"""@echo off
title Minecraft Server - {self.version} {self.software}
echo ================================================
echo    Minecraft Server Launcher
echo ================================================
echo Version: {self.version}
echo Software: {self.software}
echo RAM: {self.ram_amount}
echo Required Java: {required_java}+
echo ================================================
echo.
echo Checking Java version...
java -version
echo.
echo Starting server...
echo.
java -Xmx{self.ram_amount} -Xms{self.ram_amount} -jar "{jar_name}" nogui
echo.
echo ================================================
echo Server stopped!
echo ================================================
pause
"""
            with open(batch_path, 'w') as f:
                f.write(batch_content)
            print(f"[DEBUG] Created start.bat: {batch_path}")
            return batch_path
        except Exception as e:
            print(f"[ERROR] Failed to create start.bat: {e}")
            return None
        
    def download_vanilla(self) -> Optional[str]:
        """Download vanilla server jar from Mojang"""
        print(f"\n[DEBUG] Attempting to download Vanilla {self.version}")
        print("[DEBUG] Fetching version manifest from Mojang...")
        
        try:
            manifest_url = "https://launchermeta.mojang.com/mc/game/version_manifest.json"
            print(f"[DEBUG] Requesting: {manifest_url}")
            response = requests.get(manifest_url, timeout=10)
            response.raise_for_status()
            print("[DEBUG] Version manifest downloaded successfully")
            
            manifest = response.json()
            version_info = None
            
            for version in manifest['versions']:
                if version['id'] == self.version:
                    version_info = version
                    break
                    
            if not version_info:
                print(f"[ERROR] Version {self.version} not found in Mojang manifest")
                return None
                
            print(f"[DEBUG] Found version info: {version_info['url']}")
            
            print("[DEBUG] Fetching version details...")
            version_response = requests.get(version_info['url'], timeout=10)
            version_response.raise_for_status()
            version_data = version_response.json()
            
            if 'downloads' not in version_data or 'server' not in version_data['downloads']:
                print(f"[ERROR] No server download available for version {self.version}")
                return None
                
            server_url = version_data['downloads']['server']['url']
            server_size = version_data['downloads']['server']['size']
            
            print(f"[DEBUG] Server JAR URL: {server_url}")
            print(f"[DEBUG] Server JAR size: {server_size} bytes ({server_size / 1024 / 1024:.2f} MB)")
            
            filename = os.path.join(self.download_directory, f"server-{self.version}-vanilla.jar")
            print(f"[DEBUG] Downloading to: {filename}")
            
            jar_response = requests.get(server_url, stream=True, timeout=30)
            jar_response.raise_for_status()
            
            total_size = int(jar_response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(filename, 'wb') as f:
                for chunk in jar_response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            print(f"\r[DEBUG] Download progress: {percent:.1f}% ({downloaded}/{total_size} bytes)", end='')
                            
            print(f"\n[SUCCESS] Downloaded vanilla server: {filename}")
            return filename
            
        except requests.RequestException as e:
            print(f"[ERROR] Network error while downloading vanilla: {e}")
            return None
        except Exception as e:
            print(f"[ERROR] Unexpected error downloading vanilla: {e}")
            return None
            
    def download_paper(self) -> Optional[str]:
        """Download Paper server jar from PaperMC API"""
        print(f"\n[DEBUG] Attempting to download Paper {self.version}")
        print("[DEBUG] Querying PaperMC API...")
        
        try:
            api_url = f"https://api.papermc.io/v2/projects/paper/versions/{self.version}"
            print(f"[DEBUG] Requesting: {api_url}")
            response = requests.get(api_url, timeout=10)
            
            if response.status_code == 404:
                print(f"[ERROR] Paper doesn't support version {self.version}")
                return None
                
            response.raise_for_status()
            version_data = response.json()
            
            builds = version_data.get('builds', [])
            if not builds:
                print(f"[ERROR] No builds available for Paper {self.version}")
                return None
                
            latest_build = builds[-1]
            print(f"[DEBUG] Latest build: {latest_build}")
            
            download_url = f"https://api.papermc.io/v2/projects/paper/versions/{self.version}/builds/{latest_build}/downloads/paper-{self.version}-{latest_build}.jar"
            print(f"[DEBUG] Download URL: {download_url}")
            
            filename = os.path.join(self.download_directory, f"server-{self.version}-paper.jar")
            print(f"[DEBUG] Downloading to: {filename}")
            
            jar_response = requests.get(download_url, stream=True, timeout=30)
            jar_response.raise_for_status()
            
            total_size = int(jar_response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(filename, 'wb') as f:
                for chunk in jar_response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            print(f"\r[DEBUG] Download progress: {percent:.1f}% ({downloaded}/{total_size} bytes)", end='')
                            
            print(f"\n[SUCCESS] Downloaded Paper server: {filename}")
            return filename
            
        except requests.RequestException as e:
            print(f"[ERROR] Network error while downloading Paper: {e}")
            return None
        except Exception as e:
            print(f"[ERROR] Unexpected error downloading Paper: {e}")
            return None
            
    def download_purpur(self) -> Optional[str]:
        """Download Purpur server jar from PurpurMC API"""
        print(f"\n[DEBUG] Attempting to download Purpur {self.version}")
        print("[DEBUG] Querying PurpurMC API...")
        
        try:
            api_url = f"https://api.purpurmc.org/v2/purpur/{self.version}"
            print(f"[DEBUG] Requesting: {api_url}")
            response = requests.get(api_url, timeout=10)
            
            if response.status_code == 404:
                print(f"[ERROR] Purpur doesn't support version {self.version}")
                return None
                
            response.raise_for_status()
            version_data = response.json()
            
            builds = version_data.get('builds', {}).get('all', [])
            if not builds:
                print(f"[ERROR] No builds available for Purpur {self.version}")
                return None
                
            latest_build = builds[-1]
            print(f"[DEBUG] Latest build: {latest_build}")
            
            download_url = f"https://api.purpurmc.org/v2/purpur/{self.version}/{latest_build}/download"
            print(f"[DEBUG] Download URL: {download_url}")
            
            filename = os.path.join(self.download_directory, f"server-{self.version}-purpur.jar")
            print(f"[DEBUG] Downloading to: {filename}")
            
            jar_response = requests.get(download_url, stream=True, timeout=30)
            jar_response.raise_for_status()
            
            total_size = int(jar_response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(filename, 'wb') as f:
                for chunk in jar_response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            print(f"\r[DEBUG] Download progress: {percent:.1f}% ({downloaded}/{total_size} bytes)", end='')
                            
            print(f"\n[SUCCESS] Downloaded Purpur server: {filename}")
            return filename
            
        except requests.RequestException as e:
            print(f"[ERROR] Network error while downloading Purpur: {e}")
            return None
        except Exception as e:
            print(f"[ERROR] Unexpected error downloading Purpur: {e}")
            return None
            
    def download_fabric(self) -> Optional[str]:
        """Download Fabric server jar from Fabric API"""
        print(f"\n[DEBUG] Attempting to download Fabric {self.version}")
        print("[DEBUG] Querying Fabric Meta API...")
        
        try:
            loader_url = "https://meta.fabricmc.net/v2/versions/loader"
            print(f"[DEBUG] Requesting loader info: {loader_url}")
            loader_response = requests.get(loader_url, timeout=10)
            loader_response.raise_for_status()
            loaders = loader_response.json()
            
            if not loaders:
                print("[ERROR] No Fabric loader versions available")
                return None
                
            latest_loader = loaders[0]['version']
            print(f"[DEBUG] Latest Fabric loader: {latest_loader}")
            
            installer_url = "https://meta.fabricmc.net/v2/versions/installer"
            print(f"[DEBUG] Requesting installer info: {installer_url}")
            installer_response = requests.get(installer_url, timeout=10)
            installer_response.raise_for_status()
            installers = installer_response.json()
            
            if not installers:
                print("[ERROR] No Fabric installer versions available")
                return None
                
            latest_installer = installers[0]['version']
            print(f"[DEBUG] Latest Fabric installer: {latest_installer}")
            
            download_url = f"https://meta.fabricmc.net/v2/versions/loader/{self.version}/{latest_loader}/{latest_installer}/server/jar"
            print(f"[DEBUG] Download URL: {download_url}")
            
            filename = os.path.join(self.download_directory, f"server-{self.version}-fabric.jar")
            print(f"[DEBUG] Downloading to: {filename}")
            
            jar_response = requests.get(download_url, stream=True, timeout=30)
            
            if jar_response.status_code == 404:
                print(f"[ERROR] Fabric doesn't support version {self.version}")
                return None
                
            jar_response.raise_for_status()
            
            total_size = int(jar_response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(filename, 'wb') as f:
                for chunk in jar_response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            print(f"\r[DEBUG] Download progress: {percent:.1f}% ({downloaded}/{total_size} bytes)", end='')
                            
            print(f"\n[SUCCESS] Downloaded Fabric server: {filename}")
            return filename
            
        except requests.RequestException as e:
            print(f"[ERROR] Network error while downloading Fabric: {e}")
            return None
        except Exception as e:
            print(f"[ERROR] Unexpected error downloading Fabric: {e}")
            return None
            
    def download_forge(self) -> Optional[str]:
        """Provide instructions for Forge (requires installer)"""
        print(f"\n[INFO] Forge requires running an installer")
        print("[DEBUG] Forge must be installed using their official installer")
        print("\n=== Manual Installation Instructions ===")
        print(f"1. Go to: https://files.minecraftforge.net/net/minecraftforge/forge/index_{self.version}.html")
        print(f"2. Download the 'Installer' for version {self.version}")
        print(f"3. Run the installer and select 'Install server'")
        print(f"4. Choose installation directory: {self.download_directory}")
        print("5. The server files will be created in that directory")
        print("\n[INFO] After installation, you'll need to run the forge server jar")
        print("\n[NOTE] Forge cannot be automatically downloaded - requires interactive installer")
        return "MANUAL_BUILD_REQUIRED"
        
    def download_neoforge(self) -> Optional[str]:
        """Download NeoForge server jar"""
        print(f"\n[DEBUG] Attempting to download NeoForge {self.version}")
        print("[DEBUG] Querying NeoForge API...")
        print("[INFO] NeoForge supports Minecraft 1.20.1 and newer")
        
        try:
            parts = self.version.split('.')
            minor = int(parts[1]) if len(parts) > 1 else 0
            patch = int(parts[2]) if len(parts) > 2 else 0
            
            if minor < 20 or (minor == 20 and patch == 0):
                print(f"[ERROR] NeoForge doesn't support version {self.version}")
                print("[INFO] NeoForge only supports Minecraft 1.20.1 and newer")
                return None
            
            neoforge_major = str(minor)
            print(f"[DEBUG] Looking for NeoForge {neoforge_major}.x versions for Minecraft {self.version}")
            
            api_url = f"https://maven.neoforged.net/api/maven/versions/releases/net/neoforged/neoforge"
            print(f"[DEBUG] Requesting: {api_url}")
            response = requests.get(api_url, timeout=10)
            response.raise_for_status()
            
            versions_data = response.json()
            versions = versions_data.get('versions', [])
            
            if not versions:
                print("[ERROR] No NeoForge versions available")
                return None
            
            compatible_versions = []
            for version in versions:
                if '-beta' in version:
                    continue
                if version.startswith(f"{neoforge_major}."):
                    compatible_versions.append(version)
            
            if not compatible_versions:
                print(f"[ERROR] No stable NeoForge build found for Minecraft {self.version}")
                print(f"[DEBUG] Searched for versions starting with {neoforge_major}.")
                return None
            
            compatible_version = compatible_versions[-1]
            print(f"[DEBUG] Found NeoForge version: {compatible_version}")
            
            download_url = f"https://maven.neoforged.net/releases/net/neoforged/neoforge/{compatible_version}/neoforge-{compatible_version}-installer.jar"
            print(f"[DEBUG] Download URL: {download_url}")
            
            filename = os.path.join(self.download_directory, f"neoforge-{compatible_version}-installer.jar")
            print(f"[DEBUG] Downloading to: {filename}")
            
            jar_response = requests.get(download_url, stream=True, timeout=30)
            
            if jar_response.status_code == 404:
                print(f"[ERROR] NeoForge installer not found")
                return None
            
            jar_response.raise_for_status()
            
            total_size = int(jar_response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(filename, 'wb') as f:
                for chunk in jar_response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            print(f"\r[DEBUG] Download progress: {percent:.1f}% ({downloaded}/{total_size} bytes)", end='')
            
            print(f"\n[SUCCESS] Downloaded NeoForge installer: {filename}")
            print(f"\n[INFO] To install NeoForge server:")
            print(f"1. Run: java -jar {os.path.basename(filename)} --installServer")
            print(f"2. The server jar will be created in the same directory")
            return filename
            
        except requests.RequestException as e:
            print(f"[ERROR] Network error while downloading NeoForge: {e}")
            return None
        except Exception as e:
            print(f"[ERROR] Unexpected error downloading NeoForge: {e}")
            return None
            
    def download_bungeecord(self) -> Optional[str]:
        """Download BungeeCord proxy jar"""
        print(f"\n[DEBUG] Attempting to download BungeeCord (latest)")
        print("[DEBUG] BungeeCord is version-independent (works with all MC versions)")
        
        try:
            download_url = "https://ci.md-5.net/job/BungeeCord/lastSuccessfulBuild/artifact/bootstrap/target/BungeeCord.jar"
            print(f"[DEBUG] Download URL: {download_url}")
            
            filename = os.path.join(self.download_directory, "BungeeCord.jar")
            print(f"[DEBUG] Downloading to: {filename}")
            
            jar_response = requests.get(download_url, stream=True, timeout=30)
            jar_response.raise_for_status()
            
            total_size = int(jar_response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(filename, 'wb') as f:
                for chunk in jar_response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            print(f"\r[DEBUG] Download progress: {percent:.1f}% ({downloaded}/{total_size} bytes)", end='')
            
            print(f"\n[SUCCESS] Downloaded BungeeCord: {filename}")
            return filename
            
        except requests.RequestException as e:
            print(f"[ERROR] Network error while downloading BungeeCord: {e}")
            return None
        except Exception as e:
            print(f"[ERROR] Unexpected error downloading BungeeCord: {e}")
            return None
            
    def download_waterfall(self) -> Optional[str]:
        """Download Waterfall proxy jar from PaperMC API"""
        print(f"\n[DEBUG] Attempting to download Waterfall (latest)")
        print("[DEBUG] Waterfall is version-independent (improved BungeeCord)")
        
        try:
            api_url = "https://api.papermc.io/v2/projects/waterfall"
            print(f"[DEBUG] Requesting: {api_url}")
            response = requests.get(api_url, timeout=10)
            response.raise_for_status()
            
            project_data = response.json()
            versions = project_data.get('versions', [])
            
            if not versions:
                print("[ERROR] No Waterfall versions available")
                return None
            
            latest_version = versions[-1]
            print(f"[DEBUG] Latest Waterfall version: {latest_version}")
            
            version_url = f"https://api.papermc.io/v2/projects/waterfall/versions/{latest_version}"
            print(f"[DEBUG] Requesting: {version_url}")
            version_response = requests.get(version_url, timeout=10)
            version_response.raise_for_status()
            
            version_data = version_response.json()
            builds = version_data.get('builds', [])
            
            if not builds:
                print(f"[ERROR] No builds available for Waterfall {latest_version}")
                return None
            
            latest_build = builds[-1]
            print(f"[DEBUG] Latest build: {latest_build}")
            
            download_url = f"https://api.papermc.io/v2/projects/waterfall/versions/{latest_version}/builds/{latest_build}/downloads/waterfall-{latest_version}-{latest_build}.jar"
            print(f"[DEBUG] Download URL: {download_url}")
            
            filename = os.path.join(self.download_directory, f"waterfall-{latest_version}-{latest_build}.jar")
            print(f"[DEBUG] Downloading to: {filename}")
            
            jar_response = requests.get(download_url, stream=True, timeout=30)
            jar_response.raise_for_status()
            
            total_size = int(jar_response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(filename, 'wb') as f:
                for chunk in jar_response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            print(f"\r[DEBUG] Download progress: {percent:.1f}% ({downloaded}/{total_size} bytes)", end='')
            
            print(f"\n[SUCCESS] Downloaded Waterfall: {filename}")
            return filename
            
        except requests.RequestException as e:
            print(f"[ERROR] Network error while downloading Waterfall: {e}")
            return None
        except Exception as e:
            print(f"[ERROR] Unexpected error downloading Waterfall: {e}")
            return None
            
    def download_velocity(self) -> Optional[str]:
        """Download Velocity proxy jar from PaperMC API"""
        print(f"\n[DEBUG] Attempting to download Velocity (latest)")
        print("[DEBUG] Velocity is version-independent (modern proxy)")
        
        try:
            api_url = "https://api.papermc.io/v2/projects/velocity"
            print(f"[DEBUG] Requesting: {api_url}")
            response = requests.get(api_url, timeout=10)
            response.raise_for_status()
            
            project_data = response.json()
            versions = project_data.get('versions', [])
            
            if not versions:
                print("[ERROR] No Velocity versions available")
                return None
            
            latest_version = versions[-1]
            print(f"[DEBUG] Latest Velocity version: {latest_version}")
            
            version_url = f"https://api.papermc.io/v2/projects/velocity/versions/{latest_version}"
            print(f"[DEBUG] Requesting: {version_url}")
            version_response = requests.get(version_url, timeout=10)
            version_response.raise_for_status()
            
            version_data = version_response.json()
            builds = version_data.get('builds', [])
            
            if not builds:
                print(f"[ERROR] No builds available for Velocity {latest_version}")
                return None
            
            latest_build = builds[-1]
            print(f"[DEBUG] Latest build: {latest_build}")
            
            download_url = f"https://api.papermc.io/v2/projects/velocity/versions/{latest_version}/builds/{latest_build}/downloads/velocity-{latest_version}-{latest_build}.jar"
            print(f"[DEBUG] Download URL: {download_url}")
            
            filename = os.path.join(self.download_directory, f"velocity-{latest_version}-{latest_build}.jar")
            print(f"[DEBUG] Downloading to: {filename}")
            
            jar_response = requests.get(download_url, stream=True, timeout=30)
            jar_response.raise_for_status()
            
            total_size = int(jar_response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(filename, 'wb') as f:
                for chunk in jar_response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            print(f"\r[DEBUG] Download progress: {percent:.1f}% ({downloaded}/{total_size} bytes)", end='')
            
            print(f"\n[SUCCESS] Downloaded Velocity: {filename}")
            return filename
            
        except requests.RequestException as e:
            print(f"[ERROR] Network error while downloading Velocity: {e}")
            return None
        except Exception as e:
            print(f"[ERROR] Unexpected error downloading Velocity: {e}")
            return None
            
    def download_spigot_buildtools(self) -> Optional[str]:
        """Provide instructions for Spigot/Bukkit (requires BuildTools)"""
        print(f"\n[INFO] Spigot and Bukkit require BuildTools to compile")
        print("[DEBUG] These servers must be built locally due to DMCA restrictions")
        print("\n=== Manual Build Instructions ===")
        print("1. Download BuildTools.jar from: https://hub.spigotmc.org/jenkins/job/BuildTools/lastSuccessfulBuild/artifact/target/BuildTools.jar")
        print(f"2. Place BuildTools.jar in: {self.download_directory}")
        print(f"3. Open a terminal in that directory and run: java -jar BuildTools.jar --rev {self.version}")
        print("4. The compiled JAR will be in the same directory")
        print("\n[INFO] This process may take 10-30 minutes depending on your system")
        print("\n[NOTE] Spigot/Bukkit cannot be automatically downloaded due to DMCA restrictions")
        return "MANUAL_BUILD_REQUIRED"
        
    def download_folia(self) -> Optional[str]:
        """Download Folia server jar from PaperMC API"""
        print(f"\n[DEBUG] Attempting to download Folia {self.version}")
        print("[DEBUG] Querying PaperMC API for Folia...")
        print("[WARNING] Folia is experimental and only supports 1.18+")
        
        try:
            api_url = f"https://api.papermc.io/v2/projects/folia/versions/{self.version}"
            print(f"[DEBUG] Requesting: {api_url}")
            response = requests.get(api_url, timeout=10)
            
            if response.status_code == 404:
                print(f"[ERROR] Folia doesn't support version {self.version}")
                print("[INFO] Folia only supports Minecraft 1.18 and newer")
                return None
                
            response.raise_for_status()
            version_data = response.json()
            
            builds = version_data.get('builds', [])
            if not builds:
                print(f"[ERROR] No builds available for Folia {self.version}")
                return None
                
            latest_build = builds[-1]
            print(f"[DEBUG] Latest build: {latest_build}")
            
            download_url = f"https://api.papermc.io/v2/projects/folia/versions/{self.version}/builds/{latest_build}/downloads/folia-{self.version}-{latest_build}.jar"
            print(f"[DEBUG] Download URL: {download_url}")
            
            filename = os.path.join(self.download_directory, f"server-{self.version}-folia.jar")
            print(f"[DEBUG] Downloading to: {filename}")
            
            jar_response = requests.get(download_url, stream=True, timeout=30)
            jar_response.raise_for_status()
            
            total_size = int(jar_response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(filename, 'wb') as f:
                for chunk in jar_response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            print(f"\r[DEBUG] Download progress: {percent:.1f}% ({downloaded}/{total_size} bytes)", end='')
                            
            print(f"\n[SUCCESS] Downloaded Folia server: {filename}")
            return filename
            
        except requests.RequestException as e:
            print(f"[ERROR] Network error while downloading Folia: {e}")
            return None
        except Exception as e:
            print(f"[ERROR] Unexpected error downloading Folia: {e}")
            return None
            
    def download_server(self) -> Optional[str]:
        """Route to appropriate download method based on software"""
        print(f"\n[DEBUG] Starting download process for {self.software} {self.version}")
        
        if self.software == "vanilla":
            return self.download_vanilla()
        elif self.software == "paper":
            return self.download_paper()
        elif self.software == "purpur":
            return self.download_purpur()
        elif self.software == "fabric":
            return self.download_fabric()
        elif self.software == "forge":
            return self.download_forge()
        elif self.software == "neoforge":
            return self.download_neoforge()
        elif self.software == "bungeecord":
            return self.download_bungeecord()
        elif self.software == "waterfall":
            return self.download_waterfall()
        elif self.software == "velocity":
            return self.download_velocity()
        elif self.software == "folia":
            return self.download_folia()
        elif self.software in ["spigot", "bukkit"]:
            return self.download_spigot_buildtools()
        else:
            print(f"[ERROR] Unknown software type: {self.software}")
            return None
            
    def run(self):
        """Main application loop"""
        try:
            print("="*50)
            print("   Minecraft Server Launcher")
            print("="*50)
            print("[DEBUG] Application started")
            
            self.version = self.get_version_input()
            self.software = self.get_software_input()
            self.download_directory = self.get_directory_input()
            self.ram_amount = self.get_ram_input()
            
            self.validate_java_version()
            
            if not self.confirm_selection():
                print("\n[INFO] Operation cancelled by user")
                self._countdown_exit(0)
                return
                
            result = self.download_server()
            if result:
                if result == "MANUAL_BUILD_REQUIRED":
                    print("\n" + "="*50)
                    print("   Manual Build Required")
                    print("="*50)
                    print("\nPlease follow the instructions above to build your server.")
                    print(f"Build location: {self.download_directory}")
                else:
                    print("\n" + "="*50)
                    print("   Download Complete!")
                    print("="*50)
                    print(f"\nServer JAR: {result}")
                    
                    print("\n[INFO] Creating server files...")
                    eula_file = self.create_eula_file(result)
                    batch_file = self.create_start_batch(result)
                    
                    print("\n" + "="*50)
                    print("   Setup Complete!")
                    print("="*50)
                    print(f"\nFiles created:")
                    print(f"  - Server JAR: {os.path.basename(result)}")
                    if eula_file:
                        print(f"  - EULA: eula.txt (already accepted)")
                    if batch_file:
                        print(f"  - Launcher: start.bat")
                        
                    print(f"\nLocation: {os.path.dirname(result)}")
                    print("\nTo start your server:")
                    print("1. Double-click start.bat")
                    print("   OR")
                    print(f"2. Run: java -Xmx{self.ram_amount} -Xms{self.ram_amount} -jar {os.path.basename(result)} nogui")
                    print("\n3. Configure server.properties as needed")
            else:
                print("\n[ERROR] Failed to download server JAR")
                print("[INFO] Please check the debug messages above for details")
                self._countdown_exit(1)
                
        except KeyboardInterrupt:
            print("\n\n[INFO] Operation cancelled by user (Ctrl+C)")
            self._countdown_exit(0)
        except Exception as e:
            print(f"\n[FATAL ERROR] Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            self._countdown_exit(1)
    
    def _countdown_exit(self, exit_code=0):
        """Display countdown before exiting"""
        print("\n[INFO] Closing in 15 seconds...")
        try:
            for i in range(15, 0, -1):
                print(f"\r[INFO] Closing in {i} seconds... (Press Ctrl+C to close immediately)", end='', flush=True)
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[INFO] Closing immediately...")
        sys.exit(exit_code)

if __name__ == "__main__":
    launcher = MinecraftServerLauncher()
    launcher.run()
