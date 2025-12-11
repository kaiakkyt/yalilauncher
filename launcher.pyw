import sys
import os
import shutil
import psutil
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                              QHBoxLayout, QLabel, QComboBox, QPushButton, 
                              QTextEdit, QLineEdit, QFileDialog, QProgressBar,
                              QGroupBox, QMessageBox, QSpinBox, QTabWidget,
                              QCheckBox, QScrollArea, QFormLayout, QListWidget,
                              QListWidgetItem, QSlider, QTabBar)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QProcess, QTimer, QEvent, QUrl
from PyQt6.QtGui import QFont, QTextCursor, QKeyEvent, QFontDatabase, QIcon
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput, QSoundEffect
from PyQt6.QtGui import QPainter, QColor, QPen
from collections import deque
import re
try:
    import psutil
    HAS_PSUTIL = True
except Exception:
    psutil = None
    HAS_PSUTIL = False
try:
    import pyqtgraph as pg
    from pyqtgraph import PlotWidget
    HAS_PG = True
except Exception:
    pg = None
    PlotWidget = None
    HAS_PG = False
import requests
import subprocess
import re
import time
import json
import zipfile
from datetime import datetime
import time
import html
from components.net import https as http, downloader, java as temurin

class ScrollableComboBox(QComboBox):
    """QComboBox that limits popup height to maxVisibleItems so it scrolls reliably.

    Override showPopup to set the view's maximum height based on row height
    and the current maxVisibleItems value. This works around platform/style
    behaviours that sometimes ignore setMaxVisibleItems alone.
    """
    def showPopup(self) -> None:
        try:
            super().showPopup()
        except Exception:
            try:
                super().showPopup()
            except Exception:
                return

        try:
            view = self.view()
            max_items = self.maxVisibleItems() if hasattr(self, 'maxVisibleItems') else 8
            try:
                row_h = view.sizeHintForRow(0)
                if not row_h or row_h <= 0:
                    row_h = self.fontMetrics().height() + 4
            except Exception:
                row_h = self.fontMetrics().height() + 4

            try:
                view_max_h = int(row_h * max(1, max_items) + 4)
            except Exception:
                view_max_h = int((self.fontMetrics().height() + 4) * max(1, max_items) + 4)

            padding = 8

            try:
                view.setMaximumHeight(view_max_h)
                view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            except Exception:
                pass

            try:
                popup = view.window()
                screen = QApplication.instance().primaryScreen()
                if screen is None:
                    geom = QApplication.instance().desktop().availableGeometry()
                else:
                    geom = screen.availableGeometry()

                top_left = self.mapToGlobal(self.rect().topLeft())
                bottom_left = self.mapToGlobal(self.rect().bottomLeft())

                desired_h = min(view_max_h + padding, geom.height())

                below_space = geom.bottom() - bottom_left.y()
                above_space = top_left.y() - geom.top()

                if below_space >= desired_h:
                    y = bottom_left.y()
                elif above_space >= desired_h:
                    y = top_left.y() - desired_h
                else:
                    y = max(geom.top(), min(bottom_left.y(), geom.bottom() - desired_h))

                popup_w = popup.width()
                x = bottom_left.x()
                x = max(geom.left(), min(x, geom.right() - popup_w))

                try:
                    popup.move(x, int(y))
                    popup.setMaximumHeight(int(desired_h))
                except Exception:
                    try:
                        popup.resize(popup_w, int(desired_h))
                    except Exception:
                        pass
            except Exception:
                pass
        except Exception:
            pass

def get_base_dir():
    try:
        if getattr(sys, 'frozen', False):
            return getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(sys.argv[0])))
    except Exception:
        pass
    return os.path.dirname(os.path.abspath(sys.argv[0])) if sys.argv and sys.argv[0] else os.getcwd()

class WorldListWidget(QListWidget):
    """QListWidget that accepts world folders via drag & drop and imports them
    into the current server directory.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        md = event.mimeData()
        if md.hasUrls():
            urls = md.urls()
            for u in urls:
                path = u.toLocalFile()
                if os.path.isdir(path):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dragMoveEvent(self, event):
        md = event.mimeData()
        if md.hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        md = event.mimeData()
        if not md.hasUrls():
            event.ignore()
            return

        window = self.window()
        if not hasattr(window, 'server_directory') or not window.server_directory:
            if hasattr(window, 'log'):
                window.log('[WARNING] No server directory selected.')
            event.ignore()
            return

        for url in md.urls():
            src = url.toLocalFile()
            if not src or not os.path.isdir(src):
                continue

            if not hasattr(window, 'is_valid_world'):
                continue
            
            if not window.is_valid_world(src):
                if hasattr(window, 'log'):
                    window.log(f"[WARNING] {os.path.basename(src)} is not a valid Minecraft world (missing level.dat and region folder or not fully initialized)")
                continue

            world_name = os.path.basename(src)
            dest = os.path.join(window.server_directory, world_name)
            
            try:
                if os.path.exists(dest):
                    if hasattr(window, 'log'):
                        window.log(f"[WARNING] World '{world_name}' already exists in server directory")
                    continue
                    
                shutil.copytree(src, dest)
                if hasattr(window, 'log'):
                    window.log(f"[SUCCESS] Imported world: {world_name}")
            except Exception as e:
                if hasattr(window, 'log'):
                    window.log(f"[WARNING] Failed to import {world_name}: {e}")

        try:
            if hasattr(window, 'refresh_worlds_list'):
                window.refresh_worlds_list()
        except Exception:
            pass

class AddonListWidget(QListWidget):
    """QListWidget that accepts .jar files via drag & drop and copies them
    into the current server's addons folder (plugins/mods) using the
    parent `ServerLauncherGUI` methods.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        md = event.mimeData()
        if md.hasUrls():
            urls = md.urls()
            for u in urls:
                if u.toLocalFile().lower().endswith('.jar'):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dragMoveEvent(self, event):
        md = event.mimeData()
        if md.hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        md = event.mimeData()
        if not md.hasUrls():
            event.ignore()
            return

        window = self.window()
        addon_type, addon_folder = (None, None)
        try:
            if hasattr(window, 'get_addon_folder_type'):
                addon_type, addon_folder = window.get_addon_folder_type()
        except Exception:
            addon_folder = None

        if not addon_folder:
            if hasattr(window, 'log'):
                window.log('[WARNING] No server directory selected or no addons folder available.')
            event.ignore()
            return

        for url in md.urls():
            src = url.toLocalFile()
            if not src or not src.lower().endswith('.jar'):
                continue

            dest = os.path.join(addon_folder, os.path.basename(src))
            try:
                os.makedirs(addon_folder, exist_ok=True)
                if os.path.exists(dest):
                    if hasattr(window, 'log'):
                        window.log(f"[WARNING] Skipping {os.path.basename(src)} — already exists in addons folder")
                    continue
                shutil.copy2(src, dest)
                if hasattr(window, 'log'):
                    window.log(f"[SUCCESS] Added {os.path.basename(src)} to {addon_type} folder")
            except Exception as e:
                if hasattr(window, 'log'):
                    window.log(f"[WARNING] Failed to copy {os.path.basename(src)}: {e}")

        try:
            if hasattr(window, 'refresh_addons_list'):
                window.refresh_addons_list()
        except Exception:
            pass


class SimplePlot(QWidget):
    """Very small rolling line plot widget backed by a deque of numeric samples."""
    def __init__(self, parent=None, max_samples=60, color=(63,163,77)):
        super().__init__(parent)
        self.samples = deque(maxlen=max_samples)
        self.setMinimumHeight(80)
        self._color = QColor(*color)

    def add_sample(self, value):
        try:
            self.samples.append(float(value) if value is not None else None)
        except Exception:
            self.samples.append(None)
        self.update()

    def paintEvent(self, ev):
        qp = QPainter(self)
        rect = self.rect()
        qp.fillRect(rect, QColor(40,40,40))
        if not self.samples:
            return
        vals = [v for v in self.samples if v is not None]
        if not vals:
            return
        minv = min(vals)
        maxv = max(vals)
        if minv == maxv:
            minv -= 1
            maxv += 1
        w = rect.width()
        h = rect.height()
        grid_pen = QPen(QColor(70,70,70))
        grid_pen.setStyle(Qt.PenStyle.DashLine)
        qp.setPen(grid_pen)
        for i in range(1,4):
            y = int(h * i / 4)
            qp.drawLine(0, y, w, y)

        step = w / max(1, len(self.samples)-1)
        pen = QPen(self._color)
        pen.setWidth(2)
        qp.setPen(pen)
        pts = []
        for i, v in enumerate(self.samples):
            x = int(i * step)
            if v is None:
                pts.append(None)
                continue
            y = int(h - ((v - minv) / (maxv - minv)) * (h-8) - 4)
            pts.append((x, y))
        last = None
        for p in pts:
            if p is None:
                last = None
                continue
            if last is None:
                last = p
                continue
            qp.drawLine(last[0], last[1], p[0], p[1])
            last = p

        border_pen = QPen(QColor(80,80,80))
        border_pen.setWidth(1)
        qp.setPen(border_pen)
        qp.drawRect(0, 0, w-1, h-1)

        try:
            cur = next((v for v in reversed(self.samples) if v is not None), None)
            if cur is not None:
                txt = f"{cur:.2f}"
                qp.setPen(QColor(200,200,200))
                qp.drawText(w-6-qp.fontMetrics().horizontalAdvance(txt), 14, txt)
        except Exception:
            pass


class DownloadThread(QThread):
    """Background thread for downloading server files"""
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int, str)
    finished_signal = pyqtSignal(bool, str)
    
    def __init__(self, version, software, directory, ram, java_exe: str | None = None):
        super().__init__()
        self.version = version
        self.software = software
        self.directory = directory
        self.ram = ram
        self.java_exe = java_exe
        
    def log(self, message):
        """Send log message to UI"""
        self.log_signal.emit(message)
        
    def run(self):
        """Execute download in background"""
        try:
            self.log(f"\n[INFO] Starting download: {self.software} {self.version}")
            self.log(f"[INFO] Target directory: {self.directory}")
            self.log(f"[INFO] RAM allocation: {self.ram}")
            
            jar_path = None
            if self.software == "Vanilla":
                jar_path = self.download_vanilla()
            elif self.software == "Paper":
                jar_path = self.download_paper()
            elif self.software == "Purpur":
                jar_path = self.download_purpur()
            elif self.software == "Fabric":
                jar_path = self.download_fabric()
            elif self.software == "Folia":
                jar_path = self.download_folia()
            elif self.software == "BungeeCord":
                jar_path = self.download_bungeecord()
            elif self.software == "Waterfall":
                jar_path = self.download_waterfall()
            elif self.software == "Velocity":
                jar_path = self.download_velocity()
            elif self.software == "NeoForge":
                jar_path = self.download_neoforge()
            elif self.software in ["Forge", "Spigot", "Bukkit"]:
                self.finished_signal.emit(False, f"{self.software} requires manual installation")
                return
                
            if jar_path:
                self.log("\n[INFO] Creating server files...")
                self.create_eula_file(jar_path)
                self.create_start_batch(jar_path, getattr(self, 'java_exe', None) or getattr(self, 'java_exe', None))
                self.create_plugin_mods_folder(jar_path)
                self.install_axior_plugin(jar_path)
                self.install_foliaperms_plugin(jar_path)
                self.install_eventron_plugin(jar_path)
                try:
                    self.install_multimedia_plugin(jar_path)
                except Exception:
                    pass
                try:
                    if self.software == 'Fabric':
                        self.install_fabric_api(jar_path)
                except Exception:
                    pass
                self.finished_signal.emit(True, jar_path)
            else:
                self.finished_signal.emit(False, "Download failed")
                
        except Exception as e:
            self.log(f"\n[ERROR] {str(e)}")
            self.finished_signal.emit(False, str(e))
            
    def download_with_progress(self, url, filename):
        """Download file with progress updates"""
        def _progress_cb(downloaded, total):
            try:
                now = time.monotonic()
                if not hasattr(_progress_cb, '_started'):
                    _progress_cb._started = now
                    _progress_cb._last_ts = now
                    _progress_cb._last_bytes = 0
                    _progress_cb._speed = 0.0

                size_mb = downloaded / (1024 * 1024)

                dt = now - getattr(_progress_cb, '_last_ts', now)
                dbytes = downloaded - getattr(_progress_cb, '_last_bytes', 0)
                instant_bps = (dbytes / dt) if dt > 0 else 0.0

                alpha = 0.2
                _progress_cb._speed = (alpha * instant_bps) + ((1 - alpha) * getattr(_progress_cb, '_speed', 0.0))

                _progress_cb._last_ts = now
                _progress_cb._last_bytes = downloaded

                bps = _progress_cb._speed
                if bps >= 1024 * 1024:
                    speed_str = f"{bps / (1024 * 1024):.2f} MB/s"
                elif bps >= 1024:
                    speed_str = f"{bps / 1024:.1f} KB/s"
                else:
                    speed_str = f"{bps:.0f} B/s"

                if total and total > 0:
                    percent = int((downloaded / total) * 100)
                    total_mb = (total / (1024 * 1024))
                    remaining = total - downloaded
                    eta = None
                    if _progress_cb._speed > 0:
                        eta_sec = int(remaining / _progress_cb._speed)
                        mins, secs = divmod(eta_sec, 60)
                        eta = f"ETA {mins:d}:{secs:02d}"
                    text = f"{size_mb:.1f} MB / {total_mb:.1f} MB — {speed_str}"
                    if eta:
                        text += f" — {eta}"
                else:
                    percent = -1
                    text = f"{size_mb:.1f} MB — {speed_str}"

                self.progress_signal.emit(percent, text)
            except Exception:
                pass

        try:
            downloader.download_file(url, filename, progress_cb=_progress_cb)
        except Exception as e:
            raise
                        
    def download_vanilla(self):
        """Download vanilla server"""
        self.log("[INFO] Fetching vanilla server from Mojang...")
        
        manifest_url = "https://launchermeta.mojang.com/mc/game/version_manifest.json"
        manifest = http.get_json(manifest_url, timeout=10)
        version_info = next((v for v in manifest['versions'] if v['id'] == self.version), None)
        
        if not version_info:
            raise Exception(f"Version {self.version} not found")
            
        version_data = http.get_json(version_info['url'], timeout=10)
        
        if 'downloads' not in version_data or 'server' not in version_data['downloads']:
            raise Exception(f"No server download available for {self.version}")
            
        server_url = version_data['downloads']['server']['url']
        filename = os.path.join(self.directory, f"server-{self.version}-vanilla.jar")
        
        self.log(f"[INFO] Downloading to: {os.path.basename(filename)}")
        self.download_with_progress(server_url, filename)
        self.log(f"\n[SUCCESS] Downloaded vanilla server")
        
        return filename
        
    def download_paper(self):
        """Download Paper server"""
        self.log("[INFO] Fetching Paper server from PaperMC...")
        
        api_url = f"https://api.papermc.io/v2/projects/paper/versions/{self.version}"
        version_data = http.get_json(api_url, timeout=10)
        
        builds = version_data.get('builds', [])
        if not builds:
            raise Exception(f"No builds available for Paper {self.version}")
            
        latest_build = builds[-1]
        self.log(f"[INFO] Latest build: {latest_build}")
        
        download_url = f"https://api.papermc.io/v2/projects/paper/versions/{self.version}/builds/{latest_build}/downloads/paper-{self.version}-{latest_build}.jar"
        filename = os.path.join(self.directory, f"server-{self.version}-paper.jar")
        
        self.log(f"[INFO] Downloading to: {os.path.basename(filename)}")
        self.download_with_progress(download_url, filename)
        self.log(f"\n[SUCCESS] Downloaded Paper server")
        
        return filename
        
    def download_purpur(self):
        """Download Purpur server"""
        self.log("[INFO] Fetching Purpur server from PurpurMC...")
        
        api_url = f"https://api.purpurmc.org/v2/purpur/{self.version}"
        version_data = http.get_json(api_url, timeout=10)
        
        builds = version_data.get('builds', {}).get('all', [])
        if not builds:
            raise Exception(f"No builds available for Purpur {self.version}")
            
        latest_build = builds[-1]
        self.log(f"[INFO] Latest build: {latest_build}")
        
        download_url = f"https://api.purpurmc.org/v2/purpur/{self.version}/{latest_build}/download"
        filename = os.path.join(self.directory, f"server-{self.version}-purpur.jar")
        
        self.log(f"[INFO] Downloading to: {os.path.basename(filename)}")
        self.download_with_progress(download_url, filename)
        self.log(f"\n[SUCCESS] Downloaded Purpur server")
        
        return filename
        
    def download_fabric(self):
        """Download Fabric server"""
        self.log("[INFO] Fetching Fabric server from Fabric Meta...")
        
        loaders = http.get_json("https://meta.fabricmc.net/v2/versions/loader", timeout=10)
        
        if not loaders:
            raise Exception("No Fabric loader versions available")
            
        latest_loader = loaders[0]['version']
        self.log(f"[INFO] Fabric loader: {latest_loader}")
        installers = http.get_json("https://meta.fabricmc.net/v2/versions/installer", timeout=10)
        
        if not installers:
            raise Exception("No Fabric installer versions available")
            
        latest_installer = installers[0]['version']
        self.log(f"[INFO] Fabric installer: {latest_installer}")
        
        download_url = f"https://meta.fabricmc.net/v2/versions/loader/{self.version}/{latest_loader}/{latest_installer}/server/jar"
        filename = os.path.join(self.directory, f"server-{self.version}-fabric.jar")
        
        self.log(f"[INFO] Downloading to: {os.path.basename(filename)}")
        
        self.download_with_progress(download_url, filename)
        self.log(f"\n[SUCCESS] Downloaded Fabric server")
        
        return filename
        
    def download_folia(self):
        """Download Folia server"""
        self.log("[INFO] Fetching Folia server from PaperMC...")
        self.log("[WARNING] Folia is experimental (1.18+ only)")
        
        api_url = f"https://api.papermc.io/v2/projects/folia/versions/{self.version}"
        version_data = http.get_json(api_url, timeout=10)
        
        builds = version_data.get('builds', [])
        if not builds:
            raise Exception(f"No builds available for Folia {self.version}")
            
        latest_build = builds[-1]
        self.log(f"[INFO] Latest build: {latest_build}")
        
        download_url = f"https://api.papermc.io/v2/projects/folia/versions/{self.version}/builds/{latest_build}/downloads/folia-{self.version}-{latest_build}.jar"
        filename = os.path.join(self.directory, f"server-{self.version}-folia.jar")
        
        self.log(f"[INFO] Downloading to: {os.path.basename(filename)}")
        self.download_with_progress(download_url, filename)
        self.log(f"\n[SUCCESS] Downloaded Folia server")
        
        return filename
        
    def download_bungeecord(self):
        """Download BungeeCord proxy"""
        self.log("[INFO] Fetching BungeeCord from Jenkins...")
        
        download_url = "https://ci.md-5.net/job/BungeeCord/lastSuccessfulBuild/artifact/bootstrap/target/BungeeCord.jar"
        filename = os.path.join(self.directory, "BungeeCord.jar")
        
        self.log(f"[INFO] Downloading to: {os.path.basename(filename)}")
        self.download_with_progress(download_url, filename)
        self.log(f"\n[SUCCESS] Downloaded BungeeCord")
        
        return filename
        
    def download_waterfall(self):
        """Download Waterfall proxy"""
        self.log("[INFO] Fetching Waterfall from PaperMC...")
        
        api_url = "https://api.papermc.io/v2/projects/waterfall"
        project_data = http.get_json(api_url, timeout=10)
        versions = project_data.get('versions', [])
        
        if not versions:
            raise Exception("No Waterfall versions available")
            
        latest_version = versions[-1]
        self.log(f"[INFO] Waterfall version: {latest_version}")
        
        version_url = f"https://api.papermc.io/v2/projects/waterfall/versions/{latest_version}"
        version_data = http.get_json(version_url, timeout=10)
        builds = version_data.get('builds', [])
        
        if not builds:
            raise Exception(f"No builds available for Waterfall {latest_version}")
            
        latest_build = builds[-1]
        self.log(f"[INFO] Latest build: {latest_build}")
        
        download_url = f"https://api.papermc.io/v2/projects/waterfall/versions/{latest_version}/builds/{latest_build}/downloads/waterfall-{latest_version}-{latest_build}.jar"
        filename = os.path.join(self.directory, f"waterfall-{latest_version}-{latest_build}.jar")
        
        self.log(f"[INFO] Downloading to: {os.path.basename(filename)}")
        self.download_with_progress(download_url, filename)
        self.log(f"\n[SUCCESS] Downloaded Waterfall")
        
        return filename
        
    def download_velocity(self):
        """Download Velocity proxy"""
        self.log("[INFO] Fetching Velocity from PaperMC...")
        
        api_url = "https://api.papermc.io/v2/projects/velocity"
        project_data = http.get_json(api_url, timeout=10)
        versions = project_data.get('versions', [])
        
        if not versions:
            raise Exception("No Velocity versions available")
            
        latest_version = versions[-1]
        self.log(f"[INFO] Velocity version: {latest_version}")
        
        version_url = f"https://api.papermc.io/v2/projects/velocity/versions/{latest_version}"
        version_data = http.get_json(version_url, timeout=10)
        builds = version_data.get('builds', [])
        
        if not builds:
            raise Exception(f"No builds available for Velocity {latest_version}")
            
        latest_build = builds[-1]
        self.log(f"[INFO] Latest build: {latest_build}")
        
        download_url = f"https://api.papermc.io/v2/projects/velocity/versions/{latest_version}/builds/{latest_build}/downloads/velocity-{latest_version}-{latest_build}.jar"
        filename = os.path.join(self.directory, f"velocity-{latest_version}-{latest_build}.jar")
        
        self.log(f"[INFO] Downloading to: {os.path.basename(filename)}")
        self.download_with_progress(download_url, filename)
        self.log(f"\n[SUCCESS] Downloaded Velocity")
        
        return filename
        
    def download_neoforge(self):
        """Download NeoForge installer"""
        self.log("[INFO] Fetching NeoForge from Maven...")
        self.log("[INFO] NeoForge supports Minecraft 1.20.1+")
        
        parts = self.version.split('.')
        minor = int(parts[1]) if len(parts) > 1 else 0
        patch = int(parts[2]) if len(parts) > 2 else 0
        
        if minor < 20 or (minor == 20 and patch == 0):
            raise Exception("NeoForge only supports Minecraft 1.20.1 and newer")
            
        neoforge_major = str(minor)
        self.log(f"[INFO] Looking for NeoForge {neoforge_major}.x versions")
        
        api_url = "https://maven.neoforged.net/api/maven/versions/releases/net/neoforged/neoforge"
        versions_data = http.get_json(api_url, timeout=10)
        versions = versions_data.get('versions', [])
        
        if not versions:
            raise Exception("No NeoForge versions available")
            
        compatible_versions = [v for v in versions if not '-beta' in v and v.startswith(f"{neoforge_major}.")]
        
        if not compatible_versions:
            raise Exception(f"No stable NeoForge build found for Minecraft {self.version}")
            
        compatible_version = compatible_versions[-1]
        self.log(f"[INFO] NeoForge version: {compatible_version}")
        
        download_url = f"https://maven.neoforged.net/releases/net/neoforged/neoforge/{compatible_version}/neoforge-{compatible_version}-installer.jar"
        filename = os.path.join(self.directory, f"neoforge-{compatible_version}-installer.jar")
        
        self.log(f"[INFO] Downloading to: {os.path.basename(filename)}")
        self.download_with_progress(download_url, filename)
        self.log(f"\n[SUCCESS] Downloaded NeoForge installer")
        self.log(f"[INFO] Run: java -jar {os.path.basename(filename)} --installServer")
        
        return filename
        
    def create_eula_file(self, jar_path):
        """Create eula.txt"""
        try:
            eula_path = os.path.join(os.path.dirname(jar_path), "eula.txt")
            with open(eula_path, 'w') as f:
                f.write("#By changing the setting below to TRUE you are indicating your agreement to our EULA (https://aka.ms/MinecraftEULA).\n")
                f.write("#by YaliLauncher :)\n")
                f.write("eula=TRUE\n")
            self.log(f"[SUCCESS] Created eula.txt")
        except Exception as e:
            self.log(f"[WARNING] Failed to create eula.txt: {e}")
            
    def create_start_batch(self, jar_path, java_exe: str | None = None):
        """Create start.bat"""
        try:
            batch_path = os.path.join(os.path.dirname(jar_path), "start.bat")
            jar_name = os.path.basename(jar_path)
            exe = java_exe or getattr(self, 'java_exe', None) or os.environ.get('JAVA_EXEC') or 'java'
            try:
                if exe and os.path.isdir(exe):
                    exe = os.path.join(exe, 'bin', 'java.exe' if sys.platform == 'win32' else 'java')
            except Exception:
                pass

            try:
                if not exe or (not os.path.isabs(exe)) or (isinstance(exe, str) and not os.path.exists(exe)):
                    jh = os.environ.get('JAVA_HOME')
                    if jh:
                        candidate = os.path.join(jh, 'bin', 'java.exe' if sys.platform == 'win32' else 'java')
                        if os.path.exists(candidate):
                            exe = candidate
                    if (not exe or not os.path.exists(exe)) and shutil is not None:
                        try:
                            found = shutil.which(exe) if exe else None
                            if found:
                                exe = found
                        except Exception:
                            pass
            except Exception:
                pass

            if isinstance(exe, str) and (' ' in exe or '\\' in exe or ('\\' in exe)):
                if not (exe.startswith('"') and exe.endswith('"')):
                    exe_quoted = f'"{exe}"'
                else:
                    exe_quoted = exe
            else:
                exe_quoted = exe

            ram_val = f"{self.ram}G" if isinstance(self.ram, int) or (isinstance(self.ram, str) and self.ram.isdigit()) else str(self.ram)

            with open(batch_path, 'w') as f:
                f.write(f"""@echo off
title Minecraft Server - {self.version} {self.software}
echo ================================================
echo    Minecraft Server Launcher
echo ================================================
echo Version: {self.version}
echo Software: {self.software}
echo RAM: {self.ram}
echo ================================================
echo.
echo Starting server...
echo.
{exe_quoted} -Xmx{ram_val} -Xms{ram_val} -jar "{jar_name}" nogui
echo.
echo ================================================
echo Server stopped!
echo ================================================
pause
""")
            self.log(f"[SUCCESS] Created start.bat")
        except Exception as e:
            self.log(f"[WARNING] Failed to create start.bat: {e}")
    
    def create_plugin_mods_folder(self, jar_path):
        """Create plugins or mods folder based on server type"""
        try:
            server_dir = os.path.dirname(jar_path)
            
            if self.software == "Vanilla":
                return
            elif self.software in ["Fabric", "Forge", "NeoForge"]:
                folder_path = os.path.join(server_dir, "mods")
                folder_name = "mods"
            else:
                folder_path = os.path.join(server_dir, "plugins")
                folder_name = "plugins"
            
            os.makedirs(folder_path, exist_ok=True)
            self.log(f"[SUCCESS] Created {folder_name}/ folder")
        except Exception as e:
            self.log(f"[WARNING] Failed to create folder: {e}")
    
    def install_axior_plugin(self, jar_path):
        """Install Axior plugin based on server type"""
        try:
            sw = getattr(self, 'software', None)
            platform_hint = None
            if sw == 'Velocity':
                platform_hint = 'velocity'
            elif sw in ('BungeeCord', 'Waterfall'):
                platform_hint = 'bungeecord'
            elif sw == 'Folia':
                platform_hint = 'folia'
            elif sw in ('Bukkit', 'Spigot', 'Paper', 'Purpur'):
                platform_hint = 'bukkit'

            return self.install_plugin_from_modrinth('axior', jar_path, platform_hint=platform_hint)
        except Exception as e:
            self.log(f"[WARNING] Failed to install Axior plugin: {e}")

    def install_foliaperms_plugin(self, jar_path):
        """Install FoliaPerms plugin for Folia servers (Modrinth)"""
        try:
            if getattr(self, 'software', None) != 'Folia':
                self.log(f"[INFO] FoliaPerms not applicable for {getattr(self, 'software', None)}; skipping")
                return None
            return self.install_plugin_from_modrinth('foliaperms', jar_path)
        except Exception as e:
            self.log(f"[WARNING] Failed to install FoliaPerms plugin: {e}")

    def install_eventron_plugin(self, jar_path):
        """Install Eventron plugin for Bukkit-based servers (Modrinth)"""
        try:
            supported = {"Bukkit", "Spigot", "Paper", "Purpur", "Folia"}
            if getattr(self, 'software', None) not in supported:
                self.log(f"[INFO] Eventron not applicable for {getattr(self, 'software', None)}; skipping")
                return None
            return self.install_plugin_from_modrinth('eventron', jar_path)
        except Exception as e:
            self.log(f"[WARNING] Failed to install Eventron plugin: {e}")

    def install_multimedia_plugin(self, jar_path):
        """Install Multimedia plugin from Modrinth"""
        try:
            supported = {"Bukkit", "Spigot", "Paper", "Purpur", "Folia"}
            if getattr(self, 'software', None) not in supported:
                self.log(f"[INFO] Multimedia plugin not applicable for {getattr(self, 'software', None)}; skipping")
                return None

            return self.install_plugin_from_modrinth('multimedia', jar_path)
        except Exception as e:
            self.log(f"[WARNING] Failed to install Multimedia plugin: {e}")

    def install_fabric_api(self, jar_path):
        """Install Fabric API mod from Modrinth for Fabric servers.

        Chooses the newest Fabric API version compatible with the selected
        Minecraft version and places it into the `mods/` folder.
        """
        try:
            if getattr(self, 'software', None) != 'Fabric':
                self.log(f"[INFO] Fabric API not applicable for {getattr(self, 'software', None)}; skipping")
                return None

            self.log(f"[INFO] Attempting to install Fabric API for game version {self.version}...")
            return self.install_plugin_from_modrinth('fabric-api', jar_path)
        except Exception as e:
            self.log(f"[WARNING] Failed to install Fabric API: {e}")

    def install_plugin_from_modrinth(self, slug: str, jar_path: str, platform_hint: str | None = None):
        """Download the best matching plugin version from Modrinth and place it into the server's plugins/mods folder.

        Returns the destination path on success, or None on failure.
        """
        try:
            server_dir = os.path.dirname(jar_path)
            if self.software in ["Fabric", "NeoForge", "Forge"]:
                dest_folder = os.path.join(server_dir, 'mods')
            else:
                dest_folder = os.path.join(server_dir, 'plugins')

            os.makedirs(dest_folder, exist_ok=True)

            api_url = f"https://api.modrinth.com/v2/project/{slug}/version"
            try:
                versions = http.get_json(api_url, timeout=10)
            except Exception as e:
                self.log(f"[WARNING] Modrinth lookup failed for {slug}: {e}")
                return None

            if not versions:
                self.log(f"[WARNING] No versions returned from Modrinth for {slug}")
                return None

            chosen = None

            if platform_hint:
                ph = platform_hint.lower()
                matches = []
                for v in versions:
                    ver_num = (v.get('version_number') or '').lower()
                    name = (v.get('name') or '').lower()
                    if ver_num.endswith(f"-{ph}") or name.endswith(f"-{ph}"):
                        matches.append(v)

                if matches:
                    for v in matches:
                        gvs = v.get('game_versions', []) or []
                        if self.version in gvs:
                            chosen = v
                            break
                    if not chosen:
                        chosen = matches[0]

            if not chosen:
                for v in versions:
                    gvs = v.get('game_versions', []) or []
                    if self.version in gvs:
                        chosen = v
                        break

            if not chosen:
                chosen = versions[0]

            files = chosen.get('files', [])
            try:
                ver_label = chosen.get('version_number') or chosen.get('name') or '<unknown>'
                self.log(f"[INFO] Modrinth selected version for {slug}: {ver_label} (id: {chosen.get('id')})")
            except Exception:
                pass
            if not files:
                self.log(f"[WARNING] No downloadable files found in selected Modrinth version for {slug}")
                return None

            jar_file = None
            sw = getattr(self, 'software', None)
            if sw in ["Fabric", "NeoForge", "Forge"]:
                preferred_tokens = ['fabric', 'mod', 'mods']
            elif sw in ["Velocity", "BungeeCord", "Waterfall"]:
                preferred_tokens = ['velocity', 'bungee', 'waterfall', 'proxy']
            elif sw == 'Folia':
                preferred_tokens = ['folia']
            else:
                preferred_tokens = ['paper', 'bukkit', 'spigot', 'purpur', 'plugin']

            if platform_hint:
                ph = platform_hint.lower()
                if ph not in preferred_tokens:
                    preferred_tokens.insert(0, ph)

            for f in files:
                fn = (f.get('filename') or '').lower()
                if fn.endswith('.jar') and any(tok in fn for tok in preferred_tokens):
                    jar_file = f
                    break

            if not jar_file and sw not in ["Fabric", "NeoForge", "Forge"]:
                for f in files:
                    fn = (f.get('filename') or '').lower()
                    if fn.endswith('.jar') and ('paper' in fn or 'bukkit' in fn or 'plugin' in fn):
                        jar_file = f
                        break

            if not jar_file:
                for f in files:
                    fn = (f.get('filename') or '').lower()
                    if fn.endswith('.jar'):
                        jar_file = f
                        break

            if not jar_file:
                self.log(f"[WARNING] No jar file available to download for {slug}")
                return None

            file_url = jar_file.get('url') or jar_file.get('download_url')
            if not file_url:
                self.log(f"[WARNING] Selected Modrinth file for {slug} has no download URL")
                return None

            filename = jar_file.get('filename') or os.path.basename(file_url)
            dest_path = os.path.join(dest_folder, filename)

            try:
                self.log(f"[INFO] Modrinth selected file for {slug}: {filename}")
            except Exception:
                pass

            self.log(f"[INFO] Downloading {slug} -> {os.path.basename(dest_path)}")
            try:
                self.download_with_progress(file_url, dest_path)
            except Exception as e:
                self.log(f"[WARNING] Failed to download {slug} file: {e}")
                return None

            self.log(f"[SUCCESS] Installed {slug} to {dest_folder}")
            return dest_path
        except Exception as e:
            self.log(f"[WARNING] install_plugin_from_modrinth({slug}) failed: {e}")
            return None


class TemurinInstallThread(QThread):
    """Background thread to download and install Temurin (Adoptium) JDKs.

    Emits:
    - log_signal(str)
    - progress_signal(int, str)  # percent (or -1) and text
    - finished_signal(bool, str)  # success, message/path
    """
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int, str)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, major: int, dest_dir: str, install_dir: str | None = None, set_java_home: bool = True):
        super().__init__()
        self.major = major
        self.dest_dir = dest_dir
        self.install_dir = install_dir
        self.set_java_home = set_java_home

    def run(self):
        try:
            self.log_signal.emit(f"[INFO] Starting Temurin download/install for Java {self.major}...")

            def _cb(read, total):
                try:
                    if total:
                        pct = int((read / total) * 100)
                    else:
                        pct = -1
                except Exception:
                    pct = -1
                self.progress_signal.emit(pct, f"Downloaded {read} bytes")

            path = temurin.download_temurin(self.major, self.dest_dir, progress_cb=_cb, install=True, install_dir=self.install_dir, set_java_home=self.set_java_home)
            self.log_signal.emit(f"[SUCCESS] Temurin download/install finished: {path}")
            self.finished_signal.emit(True, str(path))
        except Exception as e:
            self.log_signal.emit(f"[ERROR] Temurin install failed: {e}")
            self.finished_signal.emit(False, str(e))


class ServerLauncherGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.download_thread = None
        self.java_version = None
        self.java_check_done = False
        self.server_process = None
        self.server_jar_path = None
        self.server_directory = None
        self.command_history = []
        self.history_index = -1
        self._last_plugin_alert = ""
        self._last_plugin_alert_time = 0.0
        self.ram_samples = deque(maxlen=60)
        self.ram_plot = None
        self.cpu_samples = deque(maxlen=120)
        self.disk_samples = deque(maxlen=120)
        self.net_read_samples = deque(maxlen=120)
        self.net_write_samples = deque(maxlen=120)
        self.cpu_plot = None
        self.disk_plot = None
        self.net_read_plot = None
        self.net_write_plot = None
        self._last_disk_io = None
        self._last_net_io = None
        self.monitor_timer = QTimer(self)
        self.monitor_timer.timeout.connect(self._monitor_tick)
        self.monitor_timer.start(1000)
        self._raw_console_lines = deque(maxlen=2000)
        
        try:
            self.setup_click_sound()
            self.setup_background_music()
        except Exception:
            pass

        self.init_ui()
        try:
            self.load_app_settings()
        except Exception:
            pass
        self.check_java_version_once()

    def setup_click_sound(self):
        app = QApplication.instance()
        self._click_effect = None
        self._click_player = None
        self._click_output = None

        base = get_base_dir()
        candidates = [
            os.path.join(base, 'components/audio/sfx', 'click.wav'),
        ]
        sound_path = None
        for p in candidates:
            if os.path.exists(p):
                sound_path = p
                break

        if sound_path:
            ext = os.path.splitext(sound_path)[1].lower()
            if ext == '.wav':
                try:
                    self._click_effect = QSoundEffect(self)
                    self._click_effect.setSource(QUrl.fromLocalFile(sound_path))
                    self._click_effect.setLoopCount(1)
                    self._click_effect.setVolume(0.35)
                except Exception:
                    self._click_effect = None
            if not self._click_effect:
                self._click_media_source = sound_path
            else:
                self._click_media_source = None
        else:
            self._click_effect = None
            self._click_player = None
            self._click_output = None

        if app:
            app.installEventFilter(self)

    def eventFilter(self, obj, event):
        try:
            if event.type() == QEvent.Type.MouseButtonPress:
                try:
                    if getattr(event, 'button', None) is not None and event.button() != Qt.MouseButton.LeftButton:
                        return super().eventFilter(obj, event)

                    target_widget = None
                    try:
                        if hasattr(event, 'globalPosition'):
                            gp = event.globalPosition().toPoint()
                        else:
                            gp = event.globalPos()
                        target_widget = QApplication.widgetAt(gp)
                    except Exception:
                        target_widget = None

                    if target_widget is None:
                        target_widget = obj

                    if target_widget is not None and self.is_interactive_widget(target_widget):
                        try:
                            self.play_click_sound()
                        except Exception:
                            pass
                except Exception:
                    pass
        except Exception:
            pass
        return super().eventFilter(obj, event)

    def play_click_sound(self):
        """Play the click sound if available."""
        try:
            if getattr(self, '_click_effect', None):
                try:
                    self._click_effect.play()
                    return
                except Exception:
                    pass

            media_src = getattr(self, '_click_media_source', None)
            if media_src:
                try:
                    player = QMediaPlayer(self)
                    output = QAudioOutput(self)
                    player.setAudioOutput(output)
                    try:
                        output.setVolume((self.sfx_slider.value() if hasattr(self, 'sfx_slider') else 35) / 100.0)
                    except Exception:
                        pass
                    player.setSource(QUrl.fromLocalFile(media_src))

                    def _on_status_changed(status):
                        try:
                            if status == QMediaPlayer.MediaStatus.EndOfMedia or status == QMediaPlayer.MediaStatus.InvalidMedia:
                                try:
                                    player.stop()
                                except Exception:
                                    pass
                                try:
                                    player.mediaStatusChanged.disconnect(_on_status_changed)
                                except Exception:
                                    pass
                                QTimer.singleShot(50, lambda: (player.deleteLater(), output.deleteLater()))
                        except Exception:
                            pass

                    try:
                        player.mediaStatusChanged.connect(_on_status_changed)
                    except Exception:
                        pass

                    try:
                        player.play()
                    except Exception:
                        try:
                            player.stop()
                            player.play()
                        except Exception:
                            pass
                except Exception:
                    pass
        except Exception:
            pass

    def is_interactive_widget(self, obj) -> bool:
        """Return True if the QObject is a common interactive widget.

        This restricts click sounds to controls users interact with:
        buttons, combo boxes, line edits, spinboxes, checkboxes,
        list widgets, text edits, and tab widgets.
        """
        try:
            from PyQt6.QtWidgets import (QPushButton, QComboBox, QLineEdit,
                                         QSpinBox, QCheckBox, QListWidget,
                                         QTextEdit, QTabBar, QPlainTextEdit,
                                         QSlider)
            interactive_types = (
                QPushButton, QComboBox, QLineEdit,
                QSpinBox, QCheckBox, QListWidget,
                QTextEdit, QPlainTextEdit, QTabBar, QSlider
            )

            cur = obj
            while cur is not None:
                try:
                    if isinstance(cur, interactive_types):
                        return True
                except Exception:
                    pass
                try:
                    cur = cur.parent()
                except Exception:
                    break
            return False
        except Exception:
            return False

    def setup_background_music(self):
        try:
            base = get_base_dir()
            music_path = os.path.join(base, 'components/audio/music', 'yalia.ogg')
            if not os.path.exists(music_path):
                return

            self._bg_player = QMediaPlayer(self)
            self._bg_output = QAudioOutput(self)
            self._bg_player.setAudioOutput(self._bg_output)
            try:
                self._bg_output.setVolume(0.25)
            except Exception:
                pass

            try:
                url = QUrl.fromLocalFile(music_path)
                self._bg_player.setSource(url)
            except Exception:
                try:
                    url = QUrl.fromLocalFile(music_path)
                    self._bg_player.setSource(url)
                except Exception:
                    return

            try:
                loops_attr = getattr(QMediaPlayer, 'Loops', None)
                if loops_attr is not None and hasattr(self._bg_player, 'setLoops'):
                    self._bg_player.setLoops(QMediaPlayer.Loops.Infinite)
                elif hasattr(self._bg_player, 'setLoopCount'):
                    try:
                        self._bg_player.setLoopCount(-1)
                    except Exception:
                        pass
                else:
                    def _on_status_changed(status):
                        try:
                            if status == QMediaPlayer.MediaStatus.EndOfMedia:
                                self._bg_player.setPosition(0)
                                self._bg_player.play()
                        except Exception:
                            pass
                    try:
                        self._bg_player.mediaStatusChanged.connect(_on_status_changed)
                    except Exception:
                        pass
            except Exception:
                pass

            try:
                self._bg_player.play()
            except Exception:
                try:
                    self._bg_player.play()
                except Exception:
                    pass
        except Exception:
            pass

    def get_settings_path(self):
        """Return path to settings JSON in AppData (Windows) or user config dir fallback."""
        try:
            local = os.getenv('LOCALAPPDATA') or os.getenv('APPDATA')
            if local:
                folder = os.path.join(local, 'KaiakK', 'YaliLauncher')
            else:
                folder = os.path.join(os.path.expanduser('~'), '.config', 'YaliLauncher')
            os.makedirs(folder, exist_ok=True)
            return os.path.join(folder, 'yali_settings.json')
        except Exception:
            return os.path.join(os.path.expanduser('~'), 'yali_settings.json')

    def load_app_settings(self):
        path = self.get_settings_path()
        defaults = {
            'sfx_volume': 35,
            'music_volume': 15,
            'sfx_enabled': True,
            'music_enabled': True
        }
        try:
            if not os.path.exists(path):
                try:
                    with open(path, 'w', encoding='utf-8') as f:
                        json.dump(defaults, f, indent=2)
                except Exception:
                    pass

            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = defaults
        except Exception:
            data = defaults

        try:
            if hasattr(self, 'sfx_slider'):
                self.sfx_slider.blockSignals(True)
                self.sfx_slider.setValue(int(data.get('sfx_volume', defaults['sfx_volume'])))
                self.sfx_slider.blockSignals(False)
            if hasattr(self, 'music_slider'):
                self.music_slider.blockSignals(True)
                self.music_slider.setValue(int(data.get('music_volume', defaults['music_volume'])))
                self.music_slider.blockSignals(False)
            if hasattr(self, 'sfx_enable'):
                self.sfx_enable.blockSignals(True)
                self.sfx_enable.setChecked(bool(data.get('sfx_enabled', defaults['sfx_enabled'])))
                self.sfx_enable.blockSignals(False)
            if hasattr(self, 'music_enable'):
                self.music_enable.blockSignals(True)
                self.music_enable.setChecked(bool(data.get('music_enabled', defaults['music_enabled'])))
                self.music_enable.blockSignals(False)
        except Exception:
            pass

        try:
            vol = max(0, min(100, int(data.get('sfx_volume', defaults['sfx_volume'])))) / 100.0
            if getattr(self, '_click_output', None):
                try:
                    self._click_output.setVolume(vol)
                except Exception:
                    pass
            mvol = max(0, min(100, int(data.get('music_volume', defaults['music_volume'])))) / 100.0
            if getattr(self, '_bg_output', None):
                try:
                    self._bg_output.setVolume(mvol)
                except Exception:
                    pass

            if not data.get('music_enabled', defaults['music_enabled']):
                try:
                    if getattr(self, '_bg_player', None):
                        self._bg_player.pause()
                except Exception:
                    pass
            else:
                try:
                    if getattr(self, '_bg_player', None):
                        self._bg_player.play()
                except Exception:
                    pass
        except Exception:
            pass

        try:
            self._settings_path = path
            try:
                self._settings_mtime = os.path.getmtime(path) if os.path.exists(path) else 0
            except Exception:
                self._settings_mtime = 0

            try:
                if not hasattr(self, '_settings_watch_timer'):
                    self._settings_watch_timer = QTimer(self)
                    self._settings_watch_timer.setInterval(10000)
                    self._settings_watch_timer.timeout.connect(self.check_app_settings_file)
                    self._settings_watch_timer.start()
            except Exception:
                pass
        except Exception:
            pass

        try:
            last_dir = None
            if isinstance(data, dict):
                last_dir = data.get('last_server_directory') or data.get('last_directory')
            if last_dir and os.path.exists(last_dir):
                try:
                    self.server_directory = last_dir
                except Exception:
                    pass
                try:
                    if hasattr(self, 'server_dir_input'):
                        self.server_dir_input.setText(last_dir)
                except Exception:
                    pass
                try:
                    QTimer.singleShot(0, self.on_server_dir_changed)
                except Exception:
                    pass
        except Exception:
            pass

    def save_app_settings(self):
        """Persist current app settings to AppData JSON file."""
        path = self.get_settings_path()
        try:
            try:
                last_dir_val = self.server_directory if getattr(self, 'server_directory', None) else (
                    self.server_dir_input.text() if hasattr(self, 'server_dir_input') else ''
                )
            except Exception:
                last_dir_val = ''

            data = {
                'sfx_volume': int(self.sfx_slider.value()) if hasattr(self, 'sfx_slider') else 35,
                'music_volume': int(self.music_slider.value()) if hasattr(self, 'music_slider') else 12,
                'sfx_enabled': bool(self.sfx_enable.isChecked()) if hasattr(self, 'sfx_enable') else True,
                'music_enabled': bool(self.music_enable.isChecked()) if hasattr(self, 'music_enable') else True,
                'last_server_directory': last_dir_val
            }
            tmp = path + '.tmp'
            try:
                with open(tmp, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2)
                try:
                    os.replace(tmp, path)
                except Exception:
                    os.rename(tmp, path)
            finally:
                try:
                    if os.path.exists(tmp):
                        os.remove(tmp)
                except Exception:
                    pass

            try:
                self._settings_mtime = os.path.getmtime(path)
                self._settings_path = path
            except Exception:
                pass
        except Exception:
            pass

    def check_app_settings_file(self):
        """Poll the settings file; if mtime changed, reload and apply settings."""
        try:
            path = getattr(self, '_settings_path', None) or self.get_settings_path()
            if not path or not os.path.exists(path):
                return
            try:
                mtime = os.path.getmtime(path)
            except Exception:
                mtime = 0
            if getattr(self, '_settings_mtime', 0) != mtime:
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                except Exception:
                    return

                defaults = {'sfx_volume': 35, 'music_volume': 15, 'sfx_enabled': True, 'music_enabled': True}
                try:
                    if hasattr(self, 'sfx_slider'):
                        self.sfx_slider.blockSignals(True)
                        self.sfx_slider.setValue(int(data.get('sfx_volume', defaults['sfx_volume'])))
                        self.sfx_slider.blockSignals(False)
                    if hasattr(self, 'music_slider'):
                        self.music_slider.blockSignals(True)
                        self.music_slider.setValue(int(data.get('music_volume', defaults['music_volume'])))
                        self.music_slider.blockSignals(False)
                    if hasattr(self, 'sfx_enable'):
                        self.sfx_enable.blockSignals(True)
                        self.sfx_enable.setChecked(bool(data.get('sfx_enabled', defaults['sfx_enabled'])))
                        self.sfx_enable.blockSignals(False)
                    if hasattr(self, 'music_enable'):
                        self.music_enable.blockSignals(True)
                        self.music_enable.setChecked(bool(data.get('music_enabled', defaults['music_enabled'])))
                        self.music_enable.blockSignals(False)
                except Exception:
                    pass

                try:
                    vol = max(0, min(100, int(data.get('sfx_volume', defaults['sfx_volume'])))) / 100.0
                    if getattr(self, '_click_output', None):
                        try:
                            self._click_output.setVolume(vol)
                        except Exception:
                            pass
                    mvol = max(0, min(100, int(data.get('music_volume', defaults['music_volume'])))) / 100.0
                    if getattr(self, '_bg_output', None):
                        try:
                            self._bg_output.setVolume(mvol)
                        except Exception:
                            pass

                    if not data.get('music_enabled', defaults['music_enabled']):
                        try:
                            if getattr(self, '_bg_player', None):
                                self._bg_player.pause()
                        except Exception:
                            pass
                    else:
                        try:
                            if getattr(self, '_bg_player', None):
                                self._bg_player.play()
                        except Exception:
                            pass
                except Exception:
                    pass

                try:
                    sfx_enabled = bool(data.get('sfx_enabled', defaults['sfx_enabled']))
                    sfx_val = max(0, min(100, int(data.get('sfx_volume', defaults['sfx_volume'])))) / 100.0
                    try:
                        if getattr(self, '_click_effect', None):
                            try:
                                if not sfx_enabled:
                                    self._click_effect.setVolume(0.0)
                                else:
                                    self._click_effect.setVolume(sfx_val)
                            except Exception:
                                pass
                    except Exception:
                        pass

                    try:
                        if getattr(self, '_click_output', None):
                            try:
                                if not sfx_enabled:
                                    self._click_output.setVolume(0.0)
                                else:
                                    self._click_output.setVolume(sfx_val)
                            except Exception:
                                pass
                    except Exception:
                        pass
                except Exception:
                    pass

                try:
                    self._settings_mtime = mtime
                except Exception:
                    pass
        except Exception:
            pass

    def on_sfx_volume_changed(self, value):
        try:
            vol = max(0, min(100, int(value))) / 100.0
            try:
                if getattr(self, '_click_effect', None):
                    try:
                        self._click_effect.setVolume(vol)
                    except Exception:
                        pass
                elif getattr(self, '_click_output', None):
                    try:
                        self._click_output.setVolume(vol)
                    except Exception:
                        pass
            except Exception:
                pass
            try:
                self._last_sfx_volume = vol
            except Exception:
                self._last_sfx_volume = None
        except Exception:
            pass
        try:
            self.save_app_settings()
        except Exception:
            pass

    def on_music_volume_changed(self, value):
        try:
            vol = max(0, min(100, int(value))) / 100.0
            if getattr(self, '_bg_output', None):
                try:
                    self._bg_output.setVolume(vol)
                except Exception:
                    pass
        except Exception:
            pass
        try:
            self.save_app_settings()
        except Exception:
            pass

    def on_sfx_toggled(self, checked: bool):
        try:
            if not checked:
                try:
                    if getattr(self, '_click_effect', None):
                        try:
                            self._last_sfx_volume = getattr(self, '_last_sfx_volume', self.sfx_slider.value() / 100.0)
                            self._click_effect.setVolume(0.0)
                        except Exception:
                            pass
                    if getattr(self, '_click_output', None):
                        try:
                            self._last_sfx_volume = getattr(self, '_last_sfx_volume', self.sfx_slider.value() / 100.0)
                            self._click_output.setVolume(0.0)
                        except Exception:
                            pass
                    if getattr(self, '_click_player', None):
                        try:
                            self._click_player.stop()
                        except Exception:
                            pass
                except Exception:
                    pass
            else:
                try:
                    vol = getattr(self, '_last_sfx_volume', None)
                    if vol is None:
                        vol = max(0, min(100, int(self.sfx_slider.value()))) / 100.0
                    if getattr(self, '_click_effect', None):
                        try:
                            self._click_effect.setVolume(vol)
                        except Exception:
                            pass
                    if getattr(self, '_click_output', None):
                        try:
                            self._click_output.setVolume(vol)
                        except Exception:
                            pass
                except Exception:
                    pass
        except Exception:
            pass
        try:
            self.save_app_settings()
        except Exception:
            pass

    def on_music_toggled(self, checked: bool):
        try:
            if getattr(self, '_bg_player', None):
                try:
                    if checked:
                        self._bg_player.play()
                    else:
                        self._bg_player.pause()
                except Exception:
                    pass
        except Exception:
            pass
        try:
            self.save_app_settings()
        except Exception:
            pass

    def get_launcher_version(self):
        try:
            base = get_base_dir()
            env_path = os.path.join(base, 'private_data', 'version.env')
            if not os.path.exists(env_path):
                return 'dev'

            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if '=' in line:
                        _, val = line.split('=', 1)
                        val = val.strip().strip('"\'')
                        if val:
                            return val
                    else:
                        return line
        except Exception:
            return 'dev'
        return 'dev'
        
    def _set_widget_state(self, widget, prop_name: str, value: str):
        """Set a dynamic property on a widget and refresh its style so QSS rules apply."""
        try:
            if not widget:
                return
            widget.setProperty(prop_name, value)
            try:
                widget.style().unpolish(widget)
                widget.style().polish(widget)
            except Exception:
                pass
        except Exception:
            pass
        
    def init_ui(self):
        """Initialize the user interface"""
        version = self.get_launcher_version()
        self.setWindowTitle(f"YaliLauncher v{version} - Easy Server Management!")
        self.setMinimumSize(960, 540)
        self.resize(1024, 576)  
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        title_label = QLabel("Minecraft Server Launcher")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setObjectName("titleLabel")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)
        
        subtitle_label = QLabel("by YaliLauncher - We make self-hosting and management 10x easier and more local!")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setObjectName("subtitleLabel")
        main_layout.addWidget(subtitle_label)
        
        main_layout.addSpacing(10)
        
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        self.create_installation_tab()
        self.create_console_tab()
        self.create_monitoring_tab()
        self.create_settings_tab()
        self.create_addons_tab()
        self.create_configuration_tab()
        self.create_world_manager_tab()
        self.create_yali_settings_tab()
        self.create_info_tab()
        
    def create_installation_tab(self):
        """Create the installation tab"""
        install_widget = QWidget()
        install_layout = QVBoxLayout(install_widget)
        
        config_group = QGroupBox("Server Configuration")
        config_layout = QVBoxLayout()
        
        version_layout = QHBoxLayout()
        version_label = QLabel("Minecraft Version:")
        version_label.setMinimumWidth(150)
        self.version_combo = ScrollableComboBox()
        self.populate_versions()
        try:
            self.version_combo.setMaxVisibleItems(8)
        except Exception:
            pass
        version_layout.addWidget(version_label)
        version_layout.addWidget(self.version_combo)
        config_layout.addLayout(version_layout)
        
        software_layout = QHBoxLayout()
        software_label = QLabel("Server Software:")
        software_label.setMinimumWidth(150)
        self.software_combo = QComboBox()
        self.software_combo.addItems([
            "Vanilla", "Paper", "Purpur", "Fabric", "Folia",
            "BungeeCord", "Waterfall", "Velocity", "NeoForge",
            "Forge", "Spigot", "Bukkit"
        ])
        self.software_combo.setCurrentText("Paper")
        self.software_combo.currentTextChanged.connect(self.on_software_changed)
        software_layout.addWidget(software_label)
        software_layout.addWidget(self.software_combo)
        config_layout.addLayout(software_layout)
        
        dir_layout = QHBoxLayout()
        dir_label = QLabel("Download Directory:")
        dir_label.setMinimumWidth(150)
        self.dir_input = QLineEdit()
        self.dir_input.setPlaceholderText("Select download directory...")
        self.dir_button = QPushButton("Browse...")
        self.dir_button.clicked.connect(self.browse_directory)
        dir_layout.addWidget(dir_label)
        dir_layout.addWidget(self.dir_input)
        dir_layout.addWidget(self.dir_button)
        config_layout.addLayout(dir_layout)
        
        ram_layout = QHBoxLayout()
        ram_label = QLabel("RAM Allocation:")
        ram_label.setMinimumWidth(150)
        self.ram_spinbox = QSpinBox()
        self.ram_spinbox.setRange(1, 64)
        self.ram_spinbox.setValue(4)
        self.ram_spinbox.setSuffix(" GB")
        ram_layout.addWidget(ram_label)
        ram_layout.addWidget(self.ram_spinbox)
        ram_layout.addStretch()
        config_layout.addLayout(ram_layout)
        
        self.info_label = QLabel()
        self.info_label.setWordWrap(True)
        self.info_label.setProperty('class', 'infoLabel')
        config_layout.addWidget(self.info_label)
        self.update_info_label()
        
        config_group.setLayout(config_layout)
        install_layout.addWidget(config_group)
        
        java_h = QHBoxLayout()
        self.java_label = QLabel("Required: Java ?")
        self.java_label.setProperty('class', 'infoLabel')
        self.java_installed_label = QLabel("Checking Java...")
        self.java_installed_label.setProperty('class', 'infoLabel')
        self.java_installed_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        java_h.addWidget(self.java_label, 3)
        java_h.addWidget(self.java_installed_label, 2)
        install_layout.addLayout(java_h)

        java_select_h = QHBoxLayout()
        java_select_label = QLabel("Use Java:")
        java_select_label.setMinimumWidth(150)
        self.java_combo = QComboBox()
        self.java_combo.setObjectName('javaCombo')
        self.java_combo.setToolTip('Select Java executable to use for the server start script')
        self.java_combo.setEnabled(False)
        java_select_h.addWidget(java_select_label)
        java_select_h.addWidget(self.java_combo)
        install_layout.addLayout(java_select_h)
        
        self.download_button = QPushButton("Download Server")
        self.download_button.setMinimumHeight(40)
        self.download_button.setObjectName("downloadButton")
        self.download_button.clicked.connect(self.start_download)

        self.install_java_button = QPushButton("Install Java (Temurin)")
        self.install_java_button.setMinimumHeight(40)
        self.install_java_button.setObjectName("installJavaButton")
        self.install_java_button.clicked.connect(self.start_install_java)
        try:
            self.install_java_button.setEnabled(False)
        except Exception:
            pass

        btn_h = QHBoxLayout()
        btn_h.addWidget(self.download_button)
        btn_h.addWidget(self.install_java_button)
        install_layout.addLayout(btn_h)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        install_layout.addWidget(self.progress_bar)
        
        self.progress_label = QLabel()
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_label.setVisible(False)
        install_layout.addWidget(self.progress_label)
        
        log_group = QGroupBox("YaliLauncher Logs (debug)")
        log_layout = QVBoxLayout()
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMaximumHeight(200)
        self.log_output.setObjectName("logOutput")
        log_layout.addWidget(self.log_output)
        log_group.setLayout(log_layout)
        install_layout.addWidget(log_group)
        
        plugin_info_label = QLabel("Axior, Eventron and/or FoliaPerms may be installed depending on your platform, since they are made by me!")
        plugin_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        plugin_info_label.setObjectName("pluginInfoLabel")
        install_layout.addWidget(plugin_info_label)
        
        self.version_combo.currentTextChanged.connect(self.on_version_changed)
        
        self.tab_widget.addTab(install_widget, "Installation")
    
    def create_console_tab(self):
        """Create the console tab"""
        console_widget = QWidget()
        console_layout = QVBoxLayout(console_widget)

        top_layout = QHBoxLayout()
        dir_group = QGroupBox("Server Directory")
        dir_group_layout = QHBoxLayout()

        self.server_dir_input = QLineEdit()
        self.server_dir_input.setPlaceholderText("Select server directory...")
        self.server_dir_input.textChanged.connect(self.on_server_dir_changed)

        self.server_dir_button = QPushButton("Browse...")
        self.server_dir_button.clicked.connect(self.browse_server_directory)

        dir_group_layout.addWidget(QLabel("Server Directory:"))
        dir_group_layout.addWidget(self.server_dir_input)
        dir_group_layout.addWidget(self.server_dir_button)
        dir_group.setLayout(dir_group_layout)
        top_layout.addWidget(dir_group, 3)

        ram_group = QGroupBox("Server Settings")
        ram_group_layout = QHBoxLayout()
        ram_label = QLabel("RAM Allocation:")
        self.console_ram_spinbox = QSpinBox()
        self.console_ram_spinbox.setRange(1, 64)
        self.console_ram_spinbox.setValue(4)
        self.console_ram_spinbox.setSuffix(" GB")
        ram_group_layout.addWidget(ram_label)
        ram_group_layout.addWidget(self.console_ram_spinbox)
        ram_group_layout.addStretch()
        ram_group.setLayout(ram_group_layout)
        top_layout.addWidget(ram_group, 1)

        console_layout.addLayout(top_layout)

        main_h = QHBoxLayout()

        console_group = QGroupBox("Server Console")
        console_output_layout = QVBoxLayout()
        self.console_output = QTextEdit()
        self.console_output.setReadOnly(True)
        self.console_output.setObjectName("consoleOutput")
        console_output_layout.addWidget(self.console_output)

        command_layout = QHBoxLayout()
        command_label = QLabel("Command:")
        self.command_input = HistoryLineEdit(self)
        self.command_input.setPlaceholderText("Enter server command... (Use ↑/↓ for history)")
        self.command_input.returnPressed.connect(self.send_command)
        self.command_input.setEnabled(False)

        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.send_command)
        self.send_button.setEnabled(False)

        command_layout.addWidget(command_label)
        command_layout.addWidget(self.command_input, 1)
        command_layout.addWidget(self.send_button)
        console_output_layout.addLayout(command_layout)

        console_group.setLayout(console_output_layout)
        main_h.addWidget(console_group, 4)

        side_widget = QWidget()
        side_layout = QVBoxLayout(side_widget)
        control_group = QGroupBox("Server Controls")
        control_layout = QHBoxLayout()

        self.start_button = QPushButton("Start Server")
        self.start_button.setMinimumHeight(35)
        self.start_button.setObjectName("startButton")
        self.start_button.clicked.connect(self.start_server)
        self.start_button.setEnabled(False)
        try:
            self.start_button.setStyleSheet("QPushButton:disabled { background-color: #2b2b2b; color: #7a7a7a; }")
        except Exception:
            pass

        self.stop_button = QPushButton("Stop Server")
        self.stop_button.setMinimumHeight(35)
        self.stop_button.setObjectName("stopButton")
        self.stop_button.clicked.connect(self.stop_server)
        self.stop_button.setEnabled(False)
        try:
            self.stop_button.setStyleSheet("QPushButton:disabled { background-color: #2b2b2b; color: #7a7a7a; }")
        except Exception:
            pass

        control_layout.addWidget(self.start_button)
        control_layout.addWidget(self.stop_button)
        control_group.setLayout(control_layout)
        side_layout.addWidget(control_group)

        self.status_label = QLabel("Status: Not Running")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setProperty('state', 'idle')
        side_layout.addWidget(self.status_label)

        side_layout.addStretch()
        main_h.addWidget(side_widget, 1)

        console_layout.addLayout(main_h)

        self.tab_widget.addTab(console_widget, "Console")

    def create_monitoring_tab(self):
        """Create a Monitoring tab that shows RAM usage and TPS graphs for the running server."""
        mon_widget = QWidget()
        mon_layout = QVBoxLayout(mon_widget)

        plots_h = QHBoxLayout()

        left_col = QVBoxLayout()
        self.cpu_label = QLabel("CPU: N/A")
        self.cpu_label.setObjectName('cpuLabel')
        left_col.addWidget(self.cpu_label, 0, Qt.AlignmentFlag.AlignLeft)
        if HAS_PG and PlotWidget is not None:
            self.cpu_plot = PlotWidget()
            self.cpu_plot.setBackground('#282828')
            self.cpu_curve = self.cpu_plot.plot(pen=pg.mkPen(color=(200,120,50), width=2))
        else:
            self.cpu_plot = SimplePlot(self, max_samples=120, color=(200,120,50))
            self.cpu_curve = None
        left_col.addWidget(self.cpu_plot)

        self.disk_label = QLabel("Disk I/O: N/A")
        self.disk_label.setObjectName('diskLabel')
        left_col.addWidget(self.disk_label, 0, Qt.AlignmentFlag.AlignLeft)
        if HAS_PG and PlotWidget is not None:
            self.disk_plot = PlotWidget()
            self.disk_plot.setBackground('#282828')
            self.disk_curve = self.disk_plot.plot(pen=pg.mkPen(color=(120,180,120), width=2))
        else:
            self.disk_plot = SimplePlot(self, max_samples=120, color=(120,180,120))
            self.disk_curve = None
        left_col.addWidget(self.disk_plot)

        plots_h.addLayout(left_col, 1)

        right_col = QVBoxLayout()
        self.ram_label = QLabel("RAM: N/A")
        self.ram_label.setObjectName('ramLabel')
        right_col.addWidget(self.ram_label, 0, Qt.AlignmentFlag.AlignLeft)
        if HAS_PG and PlotWidget is not None:
            self.ram_plot = PlotWidget()
            self.ram_plot.setBackground('#282828')
            self.ram_curve = self.ram_plot.plot(pen=pg.mkPen(color=(100,180,255), width=2))
        else:
            self.ram_plot = SimplePlot(self, max_samples=120, color=(100,180,255))
            self.ram_curve = None
        right_col.addWidget(self.ram_plot)

        plots_h.addLayout(right_col, 2)

        mon_layout.addLayout(plots_h)

        net_h = QHBoxLayout()
        self.net_read_label = QLabel("Net Read: N/A")
        self.net_read_label.setObjectName('netReadLabel')
        net_left = QVBoxLayout()
        net_left.addWidget(self.net_read_label, 0, Qt.AlignmentFlag.AlignLeft)
        if HAS_PG and PlotWidget is not None:
            self.net_read_plot = PlotWidget()
            self.net_read_plot.setBackground('#282828')
            self.net_read_curve = self.net_read_plot.plot(pen=pg.mkPen(color=(120,200,255), width=2))
        else:
            self.net_read_plot = SimplePlot(self, max_samples=120, color=(120,200,255))
            self.net_read_curve = None
        net_left.addWidget(self.net_read_plot)
        net_h.addLayout(net_left, 1)

        self.net_write_label = QLabel("Net Write: N/A")
        self.net_write_label.setObjectName('netWriteLabel')
        net_right = QVBoxLayout()
        net_right.addWidget(self.net_write_label, 0, Qt.AlignmentFlag.AlignLeft)
        if HAS_PG and PlotWidget is not None:
            self.net_write_plot = PlotWidget()
            self.net_write_plot.setBackground('#282828')
            self.net_write_curve = self.net_write_plot.plot(pen=pg.mkPen(color=(255,170,120), width=2))
        else:
            self.net_write_plot = SimplePlot(self, max_samples=120, color=(255,170,120))
            self.net_write_curve = None
        net_right.addWidget(self.net_write_plot)
        net_h.addLayout(net_right, 1)

        mon_layout.addLayout(net_h)

        note = QLabel("Monitoring attaches to the currently running server process.")
        note.setProperty('class', 'infoLabel')
        mon_layout.addWidget(note)

        self.tab_widget.addTab(mon_widget, "Monitoring")

    def _monitor_tick(self):
        """Periodic monitor tick: sample server process metrics and parse console for TPS."""
        pid = None
        proc = getattr(self, 'server_process', None)
        try:
            if proc:
                try:
                    pid = int(proc.processId())
                except Exception:
                    pid = None
        except Exception:
            pid = None

        ram_val = None
        cpu_val = None
        if pid and HAS_PSUTIL:
            try:
                if not hasattr(self, '_ps_proc') or getattr(self, '_ps_proc_pid', None) != pid:
                    try:
                        self._ps_proc = psutil.Process(pid)
                        self._ps_proc_pid = pid
                        try:
                            self._ps_proc.cpu_percent(interval=None)
                        except Exception:
                            pass
                        cpu_val = None
                    except Exception:
                        self._ps_proc = None
                        self._ps_proc_pid = None
                        cpu_val = None
                else:
                    try:
                        cpu_val = self._ps_proc.cpu_percent(interval=None)
                    except Exception:
                        cpu_val = None

                if getattr(self, '_ps_proc', None):
                    try:
                        ram_val = self._ps_proc.memory_info().rss / (1024.0*1024.0)
                    except Exception:
                        ram_val = None
            except Exception:
                ram_val = None
                cpu_val = None

        if ram_val is not None:
            self.ram_label.setText(f"RAM: {ram_val:.1f} MB")
        else:
            self.ram_label.setText("RAM: N/A")

        if cpu_val is not None:
            self.cpu_label.setText(f"CPU: {cpu_val:.0f}%")
        else:
            self.cpu_label.setText("CPU: N/A")

        tps_val = None
        try:
            txt = ''
            if getattr(self, '_raw_console_lines', None) and len(self._raw_console_lines) > 0:
                try:
                    lines = list(self._raw_console_lines)[-800:]
                    joined = '\n'.join(lines)
                except Exception:
                    joined = ''
            else:
                if getattr(self, 'console_output', None):
                    txt = self.console_output.toPlainText()
                if txt:
                    lines = txt.splitlines()[-800:]
                    joined = '\n'.join(lines)
                    try:
                        joined = re.sub(r'\x1B\[[0-?]*[ -/]*[@-~]', '', joined)
                    except Exception:
                        pass
                m = re.search(r'(?:TPS[:=\s]*([0-9]+(?:\.[0-9]+)?)|([0-9]+(?:\.[0-9]+)?)\s*(?:TPS|tps))', joined, flags=re.IGNORECASE)
                if m:
                    g = m.group(1) or m.group(2)
                    try:
                        tps_val = float(g)
                    except Exception:
                        tps_val = None
                else:
                    mm = re.search(r'mean\s*tick\s*time[:\s:=]*([0-9]+(?:\.[0-9]+)?)\s*ms', joined, flags=re.IGNORECASE)
                    if not mm:
                        mm = re.search(r'([0-9]+(?:\.[0-9]+)?)\s*ms\s*/?\s*tick', joined, flags=re.IGNORECASE)
                    if mm:
                        try:
                            ms = float(mm.group(1))
                            if ms > 0:
                                tps_val = min(20.0, 1000.0 / ms)
                        except Exception:
                            tps_val = None
                    else:
                        mlist = re.search(r'TPS[:=\s]*([0-9]+(?:\.[0-9]+)?(?:\s*,\s*[0-9]+(?:\.[0-9]+)?)*)', joined, flags=re.IGNORECASE)
                        if mlist:
                            try:
                                nums = [float(x.strip()) for x in mlist.group(1).split(',') if x.strip()]
                                if nums:
                                    tps_val = nums[0]
                            except Exception:
                                tps_val = None
        except Exception:
            tps_val = None


        try:
            total_disk = None
            net_read = None
            net_write = None
            try:
                if HAS_PSUTIL:
                    dio = psutil.disk_io_counters()
                    if dio is not None:
                        total_disk = (getattr(dio, 'read_bytes', 0) or 0) + (getattr(dio, 'write_bytes', 0) or 0)
            except Exception:
                total_disk = None

            try:
                if HAS_PSUTIL:
                    nio = psutil.net_io_counters()
                    if nio is not None:
                        net_read = getattr(nio, 'bytes_recv', 0) or 0
                        net_write = getattr(nio, 'bytes_sent', 0) or 0
            except Exception:
                net_read = None
                net_write = None

            disk_kb_s = None
            if total_disk is not None:
                if self._last_disk_io is None:
                    disk_kb_s = 0.0
                else:
                    disk_kb_s = max(0.0, (total_disk - self._last_disk_io) / 1024.0)
                self._last_disk_io = total_disk

            net_read_kb_s = None
            net_write_kb_s = None
            if net_read is not None and net_write is not None:
                if self._last_net_io is None:
                    net_read_kb_s = 0.0
                    net_write_kb_s = 0.0
                else:
                    last_r, last_w = self._last_net_io
                    net_read_kb_s = max(0.0, (net_read - last_r) / 1024.0)
                    net_write_kb_s = max(0.0, (net_write - last_w) / 1024.0)
                self._last_net_io = (net_read, net_write)

            try:
                self.ram_samples.append(ram_val if ram_val is not None else None)
                self.cpu_samples.append(cpu_val if cpu_val is not None else None)
                self.disk_samples.append(disk_kb_s if disk_kb_s is not None else None)
                self.net_read_samples.append(net_read_kb_s if net_read_kb_s is not None else None)
                self.net_write_samples.append(net_write_kb_s if net_write_kb_s is not None else None)
            except Exception:
                pass

            try:
                if disk_kb_s is not None:
                    self.disk_label.setText(f"Disk I/O: {disk_kb_s:.1f} KB/s")
                else:
                    self.disk_label.setText("Disk I/O: N/A")
            except Exception:
                pass
            try:
                if net_read_kb_s is not None:
                    self.net_read_label.setText(f"Net Read: {net_read_kb_s:.1f} KB/s")
                else:
                    self.net_read_label.setText("Net Read: N/A")
                if net_write_kb_s is not None:
                    self.net_write_label.setText(f"Net Write: {net_write_kb_s:.1f} KB/s")
                else:
                    self.net_write_label.setText("Net Write: N/A")
            except Exception:
                pass

            def to_series(dq):
                return [v if v is not None else float('nan') for v in dq]

            try:
                if getattr(self, 'ram_curve', None) is not None:
                    self.ram_curve.setData(to_series(self.ram_samples))
                elif getattr(self, 'ram_plot', None):
                    self.ram_plot.add_sample(ram_val if ram_val is not None else None)
            except Exception:
                pass

            try:
                if getattr(self, 'cpu_curve', None) is not None:
                    self.cpu_curve.setData(to_series(self.cpu_samples))
                elif getattr(self, 'cpu_plot', None):
                    self.cpu_plot.add_sample(cpu_val if cpu_val is not None else None)
            except Exception:
                pass

            try:
                if getattr(self, 'disk_curve', None) is not None:
                    self.disk_curve.setData(to_series(self.disk_samples))
                elif getattr(self, 'disk_plot', None):
                    self.disk_plot.add_sample(disk_kb_s if disk_kb_s is not None else None)
            except Exception:
                pass


            try:
                if getattr(self, 'net_read_curve', None) is not None:
                    self.net_read_curve.setData(to_series(self.net_read_samples))
                elif getattr(self, 'net_read_plot', None):
                    self.net_read_plot.add_sample(net_read_kb_s if net_read_kb_s is not None else None)
            except Exception:
                pass

            try:
                if getattr(self, 'net_write_curve', None) is not None:
                    self.net_write_curve.setData(to_series(self.net_write_samples))
                elif getattr(self, 'net_write_plot', None):
                    self.net_write_plot.add_sample(net_write_kb_s if net_write_kb_s is not None else None)
            except Exception:
                pass
        except Exception:
            pass
    
    def create_settings_tab(self):
        """Create the settings tab for server.properties"""
        settings_widget = QWidget()
        settings_layout = QVBoxLayout(settings_widget)
        

        info_label = QLabel("Configure your server settings below. Select a server directory in the Console tab first.")
        info_label.setWordWrap(True)
        info_label.setProperty('class', 'infoLabel')
        settings_layout.addWidget(info_label)
        
        self.settings_status_label = QLabel("No server directory selected")
        self.settings_status_label.setObjectName("settingsStatus")
        self.settings_status_label.setProperty('state', 'idle')
        settings_layout.addWidget(self.settings_status_label)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        
        basic_group = QGroupBox("Basic Settings")
        basic_layout = QFormLayout()
        
        self.motd_input = QLineEdit()
        self.motd_input.setPlaceholderText("A Minecraft Server")
        basic_layout.addRow("Server MOTD:", self.motd_input)
        
        self.port_spinbox = QSpinBox()
        self.port_spinbox.setRange(1, 65535)
        self.port_spinbox.setValue(25565)
        basic_layout.addRow("Server Port:", self.port_spinbox)
        
        self.max_players_spinbox = QSpinBox()
        self.max_players_spinbox.setRange(1, 10000)
        self.max_players_spinbox.setValue(20)
        basic_layout.addRow("Max Players:", self.max_players_spinbox)
        
        self.difficulty_combo = QComboBox()
        self.difficulty_combo.addItems(["peaceful", "easy", "normal", "hard"])
        self.difficulty_combo.setCurrentText("easy")
        basic_layout.addRow("Difficulty:", self.difficulty_combo)
        
        self.gamemode_combo = QComboBox()
        self.gamemode_combo.addItems(["survival", "creative", "adventure", "spectator"])
        basic_layout.addRow("Default Gamemode:", self.gamemode_combo)
        
        basic_group.setLayout(basic_layout)
        scroll_layout.addWidget(basic_group)
        
        world_group = QGroupBox("World Settings")
        world_layout = QFormLayout()
        
        self.level_name_input = QLineEdit()
        self.level_name_input.setPlaceholderText("world")
        world_layout.addRow("World Name:", self.level_name_input)
        
        self.level_seed_input = QLineEdit()
        self.level_seed_input.setPlaceholderText("Leave empty for random")
        world_layout.addRow("World Seed:", self.level_seed_input)
        
        self.level_type_combo = QComboBox()
        self.level_type_combo.addItems(["minecraft:normal", "minecraft:flat", "minecraft:large_biomes", "minecraft:amplified"])
        world_layout.addRow("World Type:", self.level_type_combo)
        
        self.generate_structures_check = QCheckBox()
        self.generate_structures_check.setChecked(True)
        world_layout.addRow("Generate Structures:", self.generate_structures_check)
        
        self.spawn_animals_check = QCheckBox()
        self.spawn_animals_check.setChecked(True)
        world_layout.addRow("Spawn Animals:", self.spawn_animals_check)
        
        self.spawn_monsters_check = QCheckBox()
        self.spawn_monsters_check.setChecked(True)
        world_layout.addRow("Spawn Monsters:", self.spawn_monsters_check)
        
        self.spawn_npcs_check = QCheckBox()
        self.spawn_npcs_check.setChecked(True)
        world_layout.addRow("Spawn NPCs:", self.spawn_npcs_check)
        
        world_group.setLayout(world_layout)
        scroll_layout.addWidget(world_group)
        
        server_group = QGroupBox("Server Settings")
        server_layout = QFormLayout()
        
        self.online_mode_check = QCheckBox()
        self.online_mode_check.setChecked(True)
        server_layout.addRow("Online Mode:", self.online_mode_check)
        
        self.pvp_check = QCheckBox()
        self.pvp_check.setChecked(True)
        server_layout.addRow("PvP:", self.pvp_check)
        
        self.allow_flight_check = QCheckBox()
        self.allow_flight_check.setChecked(False)
        server_layout.addRow("Allow Flight:", self.allow_flight_check)
        
        self.allow_nether_check = QCheckBox()
        self.allow_nether_check.setChecked(True)
        server_layout.addRow("Allow Nether:", self.allow_nether_check)
        
        self.enable_command_block_check = QCheckBox()
        self.enable_command_block_check.setChecked(False)
        server_layout.addRow("Enable Command Blocks:", self.enable_command_block_check)
        
        self.view_distance_spinbox = QSpinBox()
        self.view_distance_spinbox.setRange(3, 32)
        self.view_distance_spinbox.setValue(10)
        server_layout.addRow("View Distance:", self.view_distance_spinbox)
        
        self.simulation_distance_spinbox = QSpinBox()
        self.simulation_distance_spinbox.setRange(3, 32)
        self.simulation_distance_spinbox.setValue(10)
        server_layout.addRow("Simulation Distance:", self.simulation_distance_spinbox)
        
        server_group.setLayout(server_layout)
        scroll_layout.addWidget(server_group)
        
        network_group = QGroupBox("Network Settings")
        network_layout = QFormLayout()
        
        self.white_list_check = QCheckBox()
        self.white_list_check.setChecked(False)
        network_layout.addRow("Enable Whitelist:", self.white_list_check)
        
        self.enforce_whitelist_check = QCheckBox()
        self.enforce_whitelist_check.setChecked(False)
        network_layout.addRow("Enforce Whitelist:", self.enforce_whitelist_check)
        
        self.max_tick_time_spinbox = QSpinBox()
        self.max_tick_time_spinbox.setRange(-1, 60000)
        self.max_tick_time_spinbox.setValue(60000)
        network_layout.addRow("Max Tick Time:", self.max_tick_time_spinbox)
        
        network_group.setLayout(network_layout)
        scroll_layout.addWidget(network_group)
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        settings_layout.addWidget(scroll)

        self.console_color_checkbox = QCheckBox("Colorize Output")
        self.console_color_checkbox.setChecked(True)
        settings_layout.addWidget(self.console_color_checkbox)

        self.autorestart_check = QCheckBox("Auto-Restart on Crash")
        self.autorestart_check.setChecked(False)
        settings_layout.addWidget(self.autorestart_check)
        
        button_layout = QHBoxLayout()
        
        self.load_settings_button = QPushButton("Load Settings")
        self.load_settings_button.setObjectName("refreshButton")
        self.load_settings_button.clicked.connect(self.load_server_properties)
        self.load_settings_button.setEnabled(False)
        
        self.save_settings_button = QPushButton("Save Settings")
        self.save_settings_button.setObjectName("saveSettingsButton")
        self.save_settings_button.clicked.connect(self.save_server_properties)
        self.save_settings_button.setEnabled(False)
        
        button_layout.addStretch()
        button_layout.addWidget(self.load_settings_button)
        button_layout.addWidget(self.save_settings_button)
        settings_layout.addLayout(button_layout)
        
        self.tab_widget.addTab(settings_widget, "Server Settings")
    
    def create_addons_tab(self):
        """Create the addons tab for managing plugins/mods"""
        addons_widget = QWidget()
        addons_layout = QVBoxLayout(addons_widget)
        
        info_label = QLabel("Manage your server plugins or mods. Select a server directory in the Console tab first.")
        info_label.setWordWrap(True)
        info_label.setProperty('class', 'infoLabel')
        addons_layout.addWidget(info_label)
        
        self.addons_status_label = QLabel("No server directory selected")
        self.addons_status_label.setObjectName("addonsStatus")
        self.addons_status_label.setProperty('state', 'idle')
        addons_layout.addWidget(self.addons_status_label)
        
        self.addon_type_label = QLabel("")
        self.addon_type_label.setObjectName("addonTypeLabel")
        addons_layout.addWidget(self.addon_type_label)
        
        search_group = QGroupBox("Search Modrinth")
        search_layout = QVBoxLayout()
        
        search_input_layout = QHBoxLayout()
        self.modrinth_search_input = QLineEdit()
        self.modrinth_search_input.setPlaceholderText("Search for plugins or mods...")
        self.modrinth_search_input.returnPressed.connect(self.search_modrinth)
        
        self.modrinth_search_button = QPushButton("Search")
        self.modrinth_search_button.setObjectName("modrinthSearchButton")
        self.modrinth_search_button.clicked.connect(self.search_modrinth)
        
        search_input_layout.addWidget(self.modrinth_search_input)
        search_input_layout.addWidget(self.modrinth_search_button)
        search_layout.addLayout(search_input_layout)
        
        self.modrinth_results = QListWidget()
        self.modrinth_results.setMaximumHeight(150)
        self.modrinth_results.setObjectName("modrinthResults")
        self.modrinth_results.itemDoubleClicked.connect(self.download_modrinth_addon)
        search_layout.addWidget(self.modrinth_results)
        
        download_hint = QLabel("💡 Double-click an item to download and install")
        download_hint.setObjectName("downloadHint")
        search_layout.addWidget(download_hint)
        
        search_group.setLayout(search_layout)
        addons_layout.addWidget(search_group)
        
        list_group = QGroupBox("Installed Addons")
        list_layout = QVBoxLayout()
        
        self.addons_list = AddonListWidget(self)
        self.addons_list.setObjectName("addonsList")
        self.addons_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        list_layout.addWidget(self.addons_list)
        
        list_group.setLayout(list_layout)
        addons_layout.addWidget(list_group)
        
        button_layout = QHBoxLayout()
        
        self.refresh_addons_button = QPushButton("Refresh List")
        self.refresh_addons_button.setObjectName("refreshButton")
        self.refresh_addons_button.clicked.connect(self.refresh_addons_list)
        self.refresh_addons_button.setEnabled(False)
        
        self.add_addon_button = QPushButton("Add Addon")
        self.add_addon_button.setObjectName("addAddonButton")
        self.add_addon_button.clicked.connect(self.add_addon)
        self.add_addon_button.setEnabled(False)
        
        self.remove_addon_button = QPushButton("Remove Selected")
        self.remove_addon_button.setObjectName("removeAddonButton")
        self.remove_addon_button.clicked.connect(self.remove_addon)
        self.remove_addon_button.setEnabled(False)
        
        self.open_folder_button = QPushButton("Open Folder")
        self.open_folder_button.setObjectName("openFolderButton")
        self.open_folder_button.clicked.connect(self.open_addons_folder)
        self.open_folder_button.setEnabled(False)
        
        button_layout.addWidget(self.refresh_addons_button)
        button_layout.addWidget(self.add_addon_button)
        button_layout.addWidget(self.remove_addon_button)
        button_layout.addWidget(self.open_folder_button)
        button_layout.addStretch()
        addons_layout.addLayout(button_layout)
        
        self.tab_widget.addTab(addons_widget, "Addons")

    def create_configuration_tab(self):
        """Create Configuration tab to edit plugin/mod config files"""
        cfg_widget = QWidget()
        cfg_layout = QHBoxLayout(cfg_widget)

        left_layout = QVBoxLayout()
        self.config_folders_label = QLabel("Config Folders:")
        left_layout.addWidget(self.config_folders_label)

        self.config_folders_list = QListWidget()
        self.config_folders_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.config_folders_list.itemSelectionChanged.connect(self.on_config_folder_selected)
        left_layout.addWidget(self.config_folders_list)

        cfg_buttons = QHBoxLayout()
        self.refresh_config_button = QPushButton("Refresh")
        self.refresh_config_button.clicked.connect(self.refresh_config_folders)
        cfg_buttons.addWidget(self.refresh_config_button)
        cfg_buttons.addStretch()
        left_layout.addLayout(cfg_buttons)

        right_layout = QVBoxLayout()
        self.config_files_label = QLabel("Config Files:")
        right_layout.addWidget(self.config_files_label)

        self.config_files_list = QListWidget()
        self.config_files_list.setMaximumWidth(320)
        self.config_files_list.itemClicked.connect(self.on_config_file_selected)
        right_layout.addWidget(self.config_files_list)

        self.config_editor = QTextEdit()
        self.config_editor.setObjectName("configEditor")
        right_layout.addWidget(self.config_editor)

        editor_buttons = QHBoxLayout()
        self.save_config_button = QPushButton("Save")
        self.save_config_button.clicked.connect(self.save_config_file)
        self.save_config_button.setEnabled(False)
        editor_buttons.addWidget(self.save_config_button)

        self.revert_config_button = QPushButton("Revert")
        self.revert_config_button.clicked.connect(self.revert_config_file)
        self.revert_config_button.setEnabled(False)
        editor_buttons.addWidget(self.revert_config_button)

        editor_buttons.addStretch()
        right_layout.addLayout(editor_buttons)

        cfg_layout.addLayout(left_layout, 1)
        cfg_layout.addLayout(right_layout, 3)

        self.tab_widget.addTab(cfg_widget, "Configuration")

        self._current_config_folder = None
        self._current_config_file = None
        self._config_excludes = {".paper-remapped", "bstats", "spark", "pluginmetrics"}
        QTimer.singleShot(100, self.refresh_config_folders)

    def refresh_config_folders(self):
        """Populate config folders from plugins/mods directory, excluding known non-config folders."""
        self.config_folders_list.clear()
        self.config_files_list.clear()
        self.config_editor.clear()
        self.save_config_button.setEnabled(False)
        self.revert_config_button.setEnabled(False)

        addon_type, addon_folder = self.get_addon_folder_type()
        if not addon_folder or not os.path.exists(addon_folder):
            self.config_folders_label.setText("Config Folders: (no addons folder)")
            return

        try:
            entries = [d for d in os.listdir(addon_folder) if os.path.isdir(os.path.join(addon_folder, d))]
            good = []
            for d in sorted(entries):
                if d.startswith('.'):
                    continue
                if d.lower() in self._config_excludes:
                    continue
                good.append(d)

            for d in good:
                item = QListWidgetItem(d)
                item.setData(Qt.ItemDataRole.UserRole, os.path.join(addon_folder, d))
                self.config_folders_list.addItem(item)

            self.config_folders_label.setText(f"Config Folders: ({len(good)})")
        except Exception as e:
            self.config_folders_label.setText(f"Config Folders: (error: {e})")

    def on_config_folder_selected(self):
        self.config_files_list.clear()
        self.config_editor.clear()
        self.save_config_button.setEnabled(False)
        self.revert_config_button.setEnabled(False)
        sel = self.config_folders_list.currentItem()
        if not sel:
            self._current_config_folder = None
            return
        folder = sel.data(Qt.ItemDataRole.UserRole)
        self._current_config_folder = folder
        files = []
        for root, dirs, filenames in os.walk(folder):
            if root != folder:
                pass
            for fn in filenames:
                if fn.lower().endswith(('.yml', '.yaml', '.toml', '.json')):
                    rel = os.path.relpath(os.path.join(root, fn), folder)
                    files.append((rel, os.path.join(root, fn)))
        files = sorted(files, key=lambda x: x[0])
        for rel, full in files:
            item = QListWidgetItem(rel)
            item.setData(Qt.ItemDataRole.UserRole, full)
            self.config_files_list.addItem(item)

        self.config_files_label.setText(f"Config Files: ({len(files)})")

    def on_config_file_selected(self, item: QListWidgetItem):
        path = item.data(Qt.ItemDataRole.UserRole)
        if not path or not os.path.exists(path):
            QMessageBox.warning(self, "File Missing", "Selected config file was not found on disk.")
            return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = f.read()
        except Exception as e:
            QMessageBox.critical(self, "Read Error", f"Failed to read file:\n{e}")
            return

        self._current_config_file = path
        self.config_editor.setPlainText(data)
        self.save_config_button.setEnabled(True)
        self.revert_config_button.setEnabled(True)

    def save_config_file(self):
        if not self._current_config_file:
            return
        try:
            text = self.config_editor.toPlainText()
            with open(self._current_config_file, 'w', encoding='utf-8', newline='\n') as f:
                f.write(text)
            QMessageBox.information(self, "Saved", f"Saved: {os.path.basename(self._current_config_file)}")
        except Exception as e:
            QMessageBox.critical(self, "Save Failed", f"Failed to save file:\n{e}")

    def revert_config_file(self):
        if not self._current_config_file:
            return
        try:
            with open(self._current_config_file, 'r', encoding='utf-8') as f:
                data = f.read()
            self.config_editor.setPlainText(data)
            QMessageBox.information(self, "Reverted", "Reverted to disk contents.")
        except Exception as e:
            QMessageBox.critical(self, "Revert Failed", f"Failed to revert file:\n{e}")
    
    def create_world_manager_tab(self):
        """Create the world manager tab for managing Minecraft worlds"""
        world_widget = QWidget()
        world_layout = QVBoxLayout(world_widget)
        
        info_label = QLabel("Manage your Minecraft worlds. Select a server directory in the Console tab first.")
        info_label.setWordWrap(True)
        info_label.setProperty('class', 'infoLabel')
        world_layout.addWidget(info_label)
        
        self.world_status_label = QLabel("No server directory selected")
        self.world_status_label.setObjectName("worldStatus")
        self.world_status_label.setProperty('state', 'idle')
        world_layout.addWidget(self.world_status_label)
        
        list_group = QGroupBox("Detected Worlds")
        list_layout = QVBoxLayout()
        
        self.worlds_list = WorldListWidget()
        self.worlds_list.setObjectName("worldsList")
        self.worlds_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        list_layout.addWidget(self.worlds_list)
        
        list_group.setLayout(list_layout)
        world_layout.addWidget(list_group)
        
        button_layout = QHBoxLayout()
        
        self.import_world_button = QPushButton("Import World")
        self.import_world_button.setObjectName("importWorldButton")
        self.import_world_button.clicked.connect(self.import_world)
        self.import_world_button.setEnabled(False)
        
        self.refresh_worlds_button = QPushButton("Refresh List")
        self.refresh_worlds_button.setObjectName("refreshButton")
        self.refresh_worlds_button.clicked.connect(self.refresh_worlds_list)
        self.refresh_worlds_button.setEnabled(False)
        
        self.open_world_folder_button = QPushButton("Open Folder")
        self.open_world_folder_button.setObjectName("openWorldFolderButton")
        self.open_world_folder_button.clicked.connect(self.open_world_folder)
        self.open_world_folder_button.setEnabled(False)
        
        self.delete_world_button = QPushButton("Delete Selected")
        self.delete_world_button.setObjectName("deleteWorldButton")
        self.delete_world_button.clicked.connect(self.delete_world)
        self.delete_world_button.setEnabled(False)
        
        self.backup_world_button = QPushButton("Backup Selected")
        self.backup_world_button.setObjectName("backupWorldButton")
        self.backup_world_button.clicked.connect(self.backup_world)
        self.backup_world_button.setEnabled(False)
        
        button_layout.addWidget(self.import_world_button)
        button_layout.addWidget(self.refresh_worlds_button)
        button_layout.addWidget(self.open_world_folder_button)
        button_layout.addWidget(self.backup_world_button)
        button_layout.addWidget(self.delete_world_button)
        button_layout.addStretch()
        world_layout.addLayout(button_layout)
        
        self.tab_widget.addTab(world_widget, "World Manager")
        
    def create_yali_settings_tab(self):
        """Create a separate tab for Yali/App settings (SFX and Music)."""
        yali_widget = QWidget()
        yali_layout = QVBoxLayout(yali_widget)

        app_group = QGroupBox("App Settings")
        app_layout = QHBoxLayout()

        sfx_layout = QVBoxLayout()
        sfx_label = QLabel("SFX Volume")
        self.sfx_slider = QSlider(Qt.Orientation.Horizontal)
        self.sfx_slider.setRange(0, 100)
        self.sfx_slider.setValue(35)
        self.sfx_slider.valueChanged.connect(self.on_sfx_volume_changed)
        self.sfx_enable = QCheckBox("Enable SFX")
        self.sfx_enable.setChecked(True)
        self.sfx_enable.toggled.connect(self.on_sfx_toggled)
        sfx_layout.addWidget(sfx_label)
        sfx_layout.addWidget(self.sfx_slider)
        sfx_layout.addWidget(self.sfx_enable)

        music_layout = QVBoxLayout()
        music_label = QLabel("Music Volume")
        self.music_slider = QSlider(Qt.Orientation.Horizontal)
        self.music_slider.setRange(0, 100)
        self.music_slider.setValue(12)
        self.music_slider.valueChanged.connect(self.on_music_volume_changed)
        self.music_enable = QCheckBox("Enable Music")
        self.music_enable.setChecked(True)
        self.music_enable.toggled.connect(self.on_music_toggled)
        music_layout.addWidget(music_label)
        music_layout.addWidget(self.music_slider)
        music_layout.addWidget(self.music_enable)

        app_layout.addLayout(sfx_layout)
        app_layout.addLayout(music_layout)
        app_group.setLayout(app_layout)
        yali_layout.addWidget(app_group)

        hint = QLabel("SFX controls UI click sounds; Music is background playback.")
        hint.setProperty('class', 'infoLabel')
        yali_layout.addWidget(hint)

        yali_layout.addStretch()
        self.tab_widget.addTab(yali_widget, "Yali Settings")
        
    def create_info_tab(self):
        """Create an Info tab that displays markdown documents from
        `data/documents` with small toggle boxes to switch between them."""
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)

        mini_layout = QHBoxLayout()
        mini_layout.setSpacing(6)
        docs = [
            ("YALI", "YALI.md"),
            ("LICENSE", "LICENSE.md"),
            ("LICENSES", "LICENSES.md"),
            ("CHANGELOG", "CHANGELOG.md"),
        ]

        self._info_buttons = {}
        for label, fname in docs:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setProperty('class', 'miniTab')
            btn.setFixedHeight(22)
            btn.clicked.connect(lambda _checked, f=fname, b=label: self._show_info_doc(f, b))
            mini_layout.addWidget(btn)
            self._info_buttons[label] = btn

        mini_layout.addStretch()
        info_layout.addLayout(mini_layout)

        self.info_view = QTextEdit()
        self.info_view.setReadOnly(True)
        self.info_view.setAcceptRichText(True)
        self.info_view.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        info_layout.addWidget(self.info_view)

        self.tab_widget.addTab(info_widget, "Info")

        try:
            default_label = 'YALI'
            if default_label in self._info_buttons:
                self._info_buttons[default_label].setChecked(True)
                self._show_info_doc('YALI.md', default_label)
            else:
                first = docs[0][1]
                self._info_buttons[docs[0][0]].setChecked(True)
                self._show_info_doc(first, docs[0][0])
        except Exception:
            pass

    def _show_info_doc(self, filename: str, label: str = None):
        """Load and display the requested markdown document from data/documents."""
        try:
            if label:
                for k, b in self._info_buttons.items():
                    try:
                        b.setChecked(k == label)
                    except Exception:
                        pass

            base = get_base_dir()
            doc_path = os.path.join(base, 'data', 'documents', filename)
            if not os.path.exists(doc_path):
                self.info_view.setPlainText(f"Document not found: {doc_path}")
                return
            with open(doc_path, 'r', encoding='utf-8') as f:
                text = f.read()
            try:
                self.info_view.setMarkdown(text)
            except Exception:
                try:
                    self.info_view.setPlainText(text)
                except Exception:
                    self.info_view.setPlainText('Unable to load document')
        except Exception:
            try:
                self.info_view.setPlainText('Error loading document')
            except Exception:
                pass
        
    def populate_versions(self):
        """Populate version dropdown"""
        versions = [
            "1.21.11", "1.21.10", "1.21.9", "1.21.8", "1.21.7", "1.21.6", "1.21.5", "1.21.4", "1.21.3", "1.21.2", "1.21.1", "1.21",
            "1.20.6", "1.20.5", "1.20.4", "1.20.3", "1.20.2", "1.20.1", "1.20",
            "1.19.4", "1.19.3", "1.19.2", "1.19.1", "1.19",
            "1.18.2", "1.18.1", "1.18",
            "1.17.1", "1.17",
            "1.16.5", "1.16.4", "1.16.3", "1.16.2", "1.16.1", "1.16",
            "1.15.2", "1.15.1", "1.15",
            "1.14.4", "1.14.3", "1.14.2", "1.14.1", "1.14",
            "1.13.2", "1.13.1", "1.13",
            "1.12.2", "1.12.1", "1.12",
            "1.11.2", "1.11.1", "1.11",
            "1.10.2", "1.10.1", "1.10",
            "1.9.4", "1.9.3", "1.9.2", "1.9.1", "1.9",
            "1.8.9", "1.8.8"
        ]
        self.version_combo.addItems(versions)
        self.version_combo.setCurrentText("1.21")
        try:
            self.version_combo.setMaxVisibleItems(12)
        except Exception:
            pass
        
    def update_info_label(self):
        """Update info label based on selected software"""
        software = self.software_combo.currentText()
        
        info_texts = {
            "Vanilla": "Official Minecraft server from Mojang",
            "Paper": "High-performance Spigot fork with plugin support (Recommended)",
            "Purpur": "Feature-rich Paper fork with extensive customization",
            "Fabric": "Lightweight modding platform for modern Minecraft",
            "Folia": "Multi-threaded Paper fork (Experimental, 1.18+ only)",
            "BungeeCord": "Proxy server for connecting multiple servers",
            "Waterfall": "Improved BungeeCord fork by PaperMC",
            "Velocity": "Modern, high-performance proxy server",
            "NeoForge": "⚠ Downloads installer only - requires extra setup with it's own server installer",
            "Forge": "⚠ Requires manual installer - not automatically downloadable",
            "Spigot": "⚠ Requires BuildTools compilation - not automatically downloadable",
            "Bukkit": "⚠ Requires BuildTools compilation - not automatically downloadable"
        }
        
        self.info_label.setText(info_texts.get(software, ""))
        
    def on_software_changed(self):
        """Handle software selection change"""
        self.update_info_label()
        if self.java_check_done:
            self.update_java_label()
        
    def on_version_changed(self):
        """Handle version selection change"""
        if self.java_check_done:
            self.update_java_label()

    def detect_all_java_installations(self):
        """Scan common locations and PATH for java executables and record their major versions.

        Populates `self.java_candidates` with dicts: {'major': int, 'path': str, 'source': str}
        """
        candidates = []

        def run_and_parse(java_path, source_label):
            try:
                result = subprocess.run(
                    [java_path, '-version'],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
                )
                out = (result.stderr or result.stdout) or ''
                m = re.search(r'version\s+"?(\d+)(?:\.(\d+))?(?:\.(\d+))?', out)
                if m:
                    major = int(m.group(1))
                    if major == 1 and m.group(2):
                        major = int(m.group(2))
                    candidates.append({'major': major, 'path': java_path, 'source': source_label})
            except Exception:
                return

        try:
            jh = os.environ.get('JAVA_HOME')
            if jh:
                jp = os.path.join(jh, 'bin', 'java.exe') if sys.platform == 'win32' else os.path.join(jh, 'bin', 'java')
                if os.path.exists(jp):
                    run_and_parse(jp, 'JAVA_HOME')
        except Exception:
            pass

        try:
            path_env = os.environ.get('PATH', '')
            for p in path_env.split(os.pathsep):
                if not p:
                    continue
                jp = os.path.join(p, 'java.exe') if sys.platform == 'win32' else os.path.join(p, 'java')
                if os.path.exists(jp):
                    run_and_parse(jp, 'PATH')
        except Exception:
            pass

        if sys.platform == 'win32':
            roots = []
            try:
                roots.append(os.environ.get('ProgramFiles', r'C:\Program Files'))
            except Exception:
                pass
            try:
                roots.append(os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)'))
            except Exception:
                pass

            for root in [r for r in roots if r]:
                try:
                    for child in os.listdir(root):
                        child_path = os.path.join(root, child)
                        if not os.path.isdir(child_path):
                            continue
                        jp = os.path.join(child_path, 'bin', 'java.exe')
                        if os.path.exists(jp):
                            run_and_parse(jp, 'ProgramFiles')
                except Exception:
                    continue

            try:
                user_home = os.path.expanduser('~')
                user_roots = [
                    os.path.join(user_home, '.local', 'opt'),
                    os.path.join(user_home, '.jdks'),
                    os.path.join(user_home, 'jdk'),
                    os.path.join(user_home, 'java'),
                ]
                for root in user_roots:
                    if not root or not os.path.isdir(root):
                        continue
                    try:
                        for child in os.listdir(root):
                            child_path = os.path.join(root, child)
                            if not os.path.isdir(child_path):
                                continue
                            jp = os.path.join(child_path, 'bin', 'java.exe') if sys.platform == 'win32' else os.path.join(child_path, 'bin', 'java')
                            if os.path.exists(jp):
                                run_and_parse(jp, 'UserLocal')
                    except Exception:
                        continue

                try:
                    for child in os.listdir(user_home):
                        child_path = os.path.join(user_home, child)
                        if not os.path.isdir(child_path):
                            continue
                        if re.search(r'(?i)^(jdk|openjdk|temurin|adoptium|adoptopenjdk|java)', child):
                            jp = os.path.join(child_path, 'bin', 'java.exe') if sys.platform == 'win32' else os.path.join(child_path, 'bin', 'java')
                            if os.path.exists(jp):
                                run_and_parse(jp, 'UserHome')
                except Exception:
                    pass
            except Exception:
                pass

        seen = set()
        uniq = []
        for c in candidates:
            key = (c.get('major'), os.path.normcase(os.path.abspath(c.get('path'))))
            if key in seen:
                continue
            seen.add(key)
            uniq.append(c)

        self.java_candidates = uniq
        try:
            if hasattr(self, 'refresh_java_selection'):
                try:
                    self.refresh_java_selection()
                except Exception:
                    pass
        except Exception:
            pass
    
    def check_java_version_once(self):
        """Check Java version once at startup"""
        try:
            self.java_candidates = []
            self.detect_all_java_installations()
        except Exception:
            self.java_candidates = []

        try:
            result = subprocess.run(
                ['java', '-version'],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )
            output = result.stderr or result.stdout or ''
            version_match = re.search(r'version\s+"?(\d+)(?:\.(\d+))?(?:\.(\d+))?', output)
            if version_match:
                major = int(version_match.group(1))
                if major == 1 and version_match.group(2):
                    self.java_version = int(version_match.group(2))
                else:
                    self.java_version = major
            else:
                self.java_version = None
        except Exception:
            self.java_version = None

        self.java_check_done = True
        try:
            self.update_java_label()
        except Exception:
            pass
    
    def update_java_label(self):
        """Update Java label based on current selection"""
        version = self.version_combo.currentText()
        parts = version.split('.')
        minor = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
        patch = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0

        required_java = 8
        if minor <= 16:
            required_java = 8
        elif minor == 17:
            required_java = 16
        elif minor == 18 or minor == 19:
            required_java = 17
        elif minor == 20:
            required_java = 21 if patch >= 5 else 17
        elif minor >= 21:
            required_java = 21

        try:
            self.java_label.setText(f"Required: Java {required_java}+")
        except Exception:
            pass

        try:
            candidates = getattr(self, 'java_candidates', []) or []

            exact = next((c for c in candidates if c.get('major') == required_java), None)

            ge = next((c for c in candidates if c.get('major') >= required_java), None)

            path_java = getattr(self, 'java_version', None)

            if exact:
                p = exact.get('path')
                m = exact.get('major')
                short = os.path.basename(os.path.dirname(os.path.dirname(p))) if p else p
                self.java_installed_label.setText(f"✓ Java {m} found ({short})")
                self._set_widget_state(self.java_installed_label, 'state', 'ok')
                try:
                    if hasattr(self, 'download_button'):
                        self.download_button.setEnabled(True)
                        self.download_button.setToolTip("")
                        try:
                            self._set_widget_state(self.download_button, 'state', 'enabled')
                        except Exception:
                            pass
                        try:
                            if hasattr(self, 'install_java_button'):
                                self.install_java_button.setEnabled(False)
                                self.install_java_button.setToolTip("")
                        except Exception:
                            pass
                except Exception:
                    pass
                return

            self.java_installed_label.setText(f"✗ Java {required_java} not found!")
            self._set_widget_state(self.java_installed_label, 'state', 'error')
            try:
                if hasattr(self, 'download_button'):
                    self.download_button.setEnabled(False)
                    self.download_button.setToolTip(f"Requires Java {required_java}; not found on this system")
                    try:
                        self.download_button.setStyleSheet(
                            "QPushButton:disabled { background-color: #2b2b2b; color: #7a7a7a; }"
                        )
                    except Exception:
                        pass
                    try:
                        self._set_widget_state(self.download_button, 'state', 'disabled')
                    except Exception:
                        pass
                    try:
                        if hasattr(self, 'install_java_button'):
                            self.install_java_button.setEnabled(True)
                            self.install_java_button.setToolTip(f"Download and install Java {required_java} (Temurin)")
                    except Exception:
                        pass
            except Exception:
                pass

        except Exception:
            try:
                self.java_installed_label.setText("✗ Java detection error")
                self._set_widget_state(self.java_installed_label, 'state', 'error')
            except Exception:
                pass

    def refresh_java_selection(self):
        """Populate the `self.java_combo` combobox from `self.java_candidates`."""
        try:
            combo = getattr(self, 'java_combo', None)
            if combo is None:
                return
            combo.blockSignals(True)
            combo.clear()
            candidates = getattr(self, 'java_candidates', []) or []
            for c in candidates:
                path = c.get('path')
                major = c.get('major')
                try:
                    short = os.path.basename(os.path.dirname(os.path.dirname(path))) if path else path
                except Exception:
                    short = path
                label = f"Java {major} — {short}"
                combo.addItem(label, path)
            if combo.count() > 0:
                combo.setEnabled(True)
                combo.setCurrentIndex(0)
            else:
                combo.addItem("(No JDKs detected)", None)
                combo.setEnabled(False)
            combo.blockSignals(False)
        except Exception:
            pass
    
    def browse_directory(self):
        """Open directory browser"""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Download Directory",
            "",
            QFileDialog.Option.ShowDirsOnly
        )
        
        if directory:
            self.dir_input.setText(directory)
    
    def browse_server_directory(self):
        """Open directory browser for server directory"""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Server Directory",
            "",
            QFileDialog.Option.ShowDirsOnly
        )
        
        if directory:
            self.server_dir_input.setText(directory)
    
    def on_server_dir_changed(self):
        """Handle server directory change"""
        directory = self.server_dir_input.text()
        
        if not directory or not os.path.exists(directory):
            self.start_button.setEnabled(False)
            self.load_settings_button.setEnabled(False)
            self.save_settings_button.setEnabled(False)
            self.refresh_addons_button.setEnabled(False)
            self.add_addon_button.setEnabled(False)
            self.remove_addon_button.setEnabled(False)
            self.open_folder_button.setEnabled(False)
            self.import_world_button.setEnabled(False)
            self.refresh_worlds_button.setEnabled(False)
            self.open_world_folder_button.setEnabled(False)
            self.delete_world_button.setEnabled(False)
            self.backup_world_button.setEnabled(False)
            self.settings_status_label.setText("No server directory selected")
            self._set_widget_state(self.settings_status_label, 'state', 'warn')
            self.addons_status_label.setText("No server directory selected")
            self._set_widget_state(self.addons_status_label, 'state', 'warn')
            self.world_status_label.setText("No server directory selected")
            self._set_widget_state(self.world_status_label, 'state', 'warn')
            return
        
        candidates = [f for f in os.listdir(directory) if f.lower().endswith('.jar')]

        if not candidates:
            versions_dir = os.path.join(directory, 'versions')
            if os.path.isdir(versions_dir):
                for v in os.listdir(versions_dir):
                    vpath = os.path.join(versions_dir, v)
                    if os.path.isdir(vpath):
                        for f in os.listdir(vpath):
                            if f.lower().endswith('.jar'):
                                candidates.append(os.path.join(vpath, f))

        chosen = None
        name_hints = ['server', 'paper', 'purpur', 'spigot', 'bukkit', 'forge', 'fabric', 'neoforge', 'velocity', 'waterfall', 'bungeecord']
        candidates = [os.path.join(directory, c) if not os.path.isabs(c) and os.path.exists(os.path.join(directory, c)) else c for c in candidates]

        for c in candidates:
            base = os.path.basename(c).lower()
            if any(h in base for h in name_hints):
                chosen = c
                break

        if not chosen:
            for c in candidates:
                try:
                    with zipfile.ZipFile(c, 'r') as z:
                        try:
                            mf = z.read('META-INF/MANIFEST.MF').decode('utf-8', errors='ignore')
                        except KeyError:
                            mf = ''
                        mf_l = mf.lower()
                        if 'main-class' in mf_l or 'net.minecraft' in mf_l or 'minecraft_server' in mf_l or 'org.bukkit' in mf_l:
                            chosen = c
                            break
                except Exception:
                    continue

        if not chosen and candidates:
            chosen = candidates[0]

        if chosen:
            self.server_jar_path = chosen
            self.server_directory = directory
            self.start_button.setEnabled(True)
            try:
                self.start_button.setStyleSheet("")
                self.stop_button.setStyleSheet("")
            except Exception:
                pass
            self.load_settings_button.setEnabled(True)
            self.save_settings_button.setEnabled(True)
            self.refresh_addons_button.setEnabled(True)
            self.add_addon_button.setEnabled(True)
            self.remove_addon_button.setEnabled(True)
            self.open_folder_button.setEnabled(True)
            self.import_world_button.setEnabled(True)
            self.refresh_worlds_button.setEnabled(True)
            self.open_world_folder_button.setEnabled(True)
            self.delete_world_button.setEnabled(True)
            self.backup_world_button.setEnabled(True)
            
            self.detect_ram_from_bat(directory)
            
            properties_path = os.path.join(directory, "server.properties")
            if os.path.exists(properties_path):
                self.settings_status_label.setText(f"✓ Connected to: {directory}")
                self._set_widget_state(self.settings_status_label, 'state', 'ok')
                self.load_server_properties()
            else:
                self.settings_status_label.setText(f"Connected to: {directory} (server.properties will be created on save)")
                self._set_widget_state(self.settings_status_label, 'state', 'normal')
            
            self.refresh_addons_list()
            
            self.refresh_addons_list()
            try:
                self.refresh_config_folders()
            except Exception:
                pass

            self.refresh_worlds_list()
        else:
            self.server_jar_path = None
            self.server_directory = None
            self.start_button.setEnabled(False)
            try:
                self.start_button.setStyleSheet("QPushButton:disabled { background-color: #2b2b2b; color: #7a7a7a; }")
                self.stop_button.setStyleSheet("QPushButton:disabled { background-color: #2b2b2b; color: #7a7a7a; }")
            except Exception:
                pass
            self.load_settings_button.setEnabled(False)
            self.save_settings_button.setEnabled(False)
            self.refresh_addons_button.setEnabled(False)
            self.add_addon_button.setEnabled(False)
            self.remove_addon_button.setEnabled(False)
            self.open_folder_button.setEnabled(False)
            try:
                self.refresh_config_folders()
            except Exception:
                pass
            self.import_world_button.setEnabled(False)
            self.refresh_worlds_button.setEnabled(False)
            self.open_world_folder_button.setEnabled(False)
            self.delete_world_button.setEnabled(False)
            self.backup_world_button.setEnabled(False)
            self.settings_status_label.setText("No server JAR found in directory")
            self._set_widget_state(self.settings_status_label, 'state', 'error')
            self.addons_status_label.setText("No server JAR found in directory")
            self._set_widget_state(self.addons_status_label, 'state', 'error')
            self.world_status_label.setText("No server JAR found in directory")
            self._set_widget_state(self.world_status_label, 'state', 'error')
            
    def log(self, message):
        """Add message to log output"""
        try:
            self.append_colored(self.log_output, message)
        except Exception:
            self.log_output.append(message)
            self.log_output.moveCursor(QTextCursor.MoveOperation.End)

    def get_severity_color(self, text):
        """Return HTML color for a given log/console line based on severity"""
        t = text.upper()
        if "ERROR" in t or "EXCEPTION" in t or "SEVERE" in t or "CRITICAL" in t:
            return "#ff5555"
        if "WARN" in t or "WARNING" in t:
            return "#ffd700"
        return "#d4d4d4"

    def append_colored(self, widget, message):
        """Append text to a QTextEdit `widget`, coloring each line by severity when enabled."""
        colorize = getattr(self, 'console_color_checkbox', None)
        enabled = True if not colorize else bool(colorize.isChecked())

        lines = str(message).splitlines()
        if not lines:
            lines = [""]

        for i, line in enumerate(lines):
            if enabled:
                color = self.get_severity_color(line)
                safe = html.escape(line)
                html_line = f"<pre style=\"margin:0; font-family: Consolas, monospace; color: {color};\">{safe}</pre>"
                widget.append(html_line)
            else:
                widget.append(line)

        widget.moveCursor(QTextCursor.MoveOperation.End)
    
    def detect_ram_from_bat(self, directory):
        """Detect RAM allocation from start.bat file"""
        bat_path = os.path.join(directory, "start.bat")
        
        if not os.path.exists(bat_path):
            return
        
        try:
            with open(bat_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            import re
            xmx_match = re.search(r'-Xmx(\d+)([GM])', content, re.IGNORECASE)
            
            if xmx_match:
                value = int(xmx_match.group(1))
                unit = xmx_match.group(2).upper()
                
                if unit == 'G':
                    ram_gb = value
                elif unit == 'M':
                    ram_gb = max(1, value // 1024)
                else:
                    return
                
                if 1 <= ram_gb <= 64:
                    self.console_ram_spinbox.setValue(ram_gb)
        
        except Exception:
            pass
        
    def start_download(self):
        """Start download process"""
        version = self.version_combo.currentText()
        software = self.software_combo.currentText()
        directory = self.dir_input.text()
        ram = f"{self.ram_spinbox.value()}G"
        
        if not directory:
            QMessageBox.warning(self, "Missing Directory", "Please select a download directory.")
            return
            
        if not os.path.exists(directory):
            reply = QMessageBox.question(
                self,
                "Create Directory?",
                f"Directory does not exist:\n{directory}\n\nCreate it?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                try:
                    os.makedirs(directory, exist_ok=True)
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to create directory:\n{str(e)}")
                    return
            else:
                return
                
        if software in ["Forge", "Spigot", "Bukkit"]:
            if software == "Forge":
                msg = f"""Forge requires manual installation:

1. Visit: https://files.minecraftforge.net/
2. Download the Installer for version {version}
3. Run the installer and select 'Install server'
4. Choose installation directory: {directory}
5. The server files will be created there"""
            else:
                msg = f"""{software} requires BuildTools compilation:

1. Download BuildTools.jar from:
   https://hub.spigotmc.org/jenkins/job/BuildTools/lastSuccessfulBuild/artifact/target/BuildTools.jar
2. Place BuildTools.jar in: {directory}
3. Open terminal in that directory
4. Run: java -jar BuildTools.jar --rev {version}
5. Wait 10-30 minutes for compilation"""
                
            QMessageBox.information(self, "Manual Installation Required", msg)
            return
            
        self.log_output.clear()
        self.log("="*60)
        self.log("Starting download process...")
        self.log("="*60)
        
        self.download_button.setEnabled(False)
        try:
            self.progress_bar.setRange(0, 100)
        except Exception:
            pass
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.progress_label.setVisible(True)
        
        java_exe = None
        try:
            if hasattr(self, 'java_combo') and self.java_combo.isEnabled() and self.java_combo.currentIndex() >= 0:
                sel = self.java_combo.currentData()
                if sel:
                    java_exe = sel
        except Exception:
            java_exe = None

        try:
            parts = version.split('.')
            minor = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
            patch = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0

            required_java = 8
            if minor <= 16:
                required_java = 8
            elif minor == 17:
                required_java = 16
            elif minor == 18 or minor == 19:
                required_java = 17
            elif minor == 20:
                required_java = 21 if patch >= 5 else 17
            elif minor >= 21:
                required_java = 21

            candidates = getattr(self, 'java_candidates', []) or []
            exact = next((c for c in candidates if c.get('major') == required_java), None)
            ge = next((c for c in candidates if c.get('major') >= required_java), None)
            if not java_exe:
                if exact:
                    java_exe = exact.get('path')
                elif ge:
                    java_exe = ge.get('path')
            else:
                jh = os.environ.get('JAVA_HOME')
                if jh:
                    java_exe_try = os.path.join(jh, 'bin', 'java.exe') if sys.platform == 'win32' else os.path.join(jh, 'bin', 'java')
                    if os.path.exists(java_exe_try):
                        java_exe = java_exe_try
        except Exception:
            java_exe = None

        self.download_thread = DownloadThread(version, software, directory, ram, java_exe)
        self.download_thread.log_signal.connect(self.log)
        self.download_thread.progress_signal.connect(self.update_progress)
        self.download_thread.finished_signal.connect(self.download_finished)
        self.download_thread.start()
        
    def update_progress(self, percent, text):
        """Update progress bar"""
        try:
            if percent is None:
                percent = -1
            if percent < 0:
                try:
                    self.progress_bar.setRange(0, 0)
                except Exception:
                    pass
            else:
                try:
                    self.progress_bar.setRange(0, 100)
                    self.progress_bar.setValue(max(0, min(100, int(percent))))
                except Exception:
                    pass
            self.progress_label.setText(text)
        except Exception:
            pass
        
    def download_finished(self, success, message):
        """Handle download completion"""
        self.download_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        
        if success:
            self.log("\n" + "="*60)
            self.log("✓ DOWNLOAD COMPLETE!")
            self.log("="*60)
            self.log(f"\nServer files created in:")
            self.log(f"  {os.path.dirname(message)}")
            self.log(f"\nTo start your server:")
            self.log("  1. Double-click start.bat")
            self.log("  2. Configure server.properties as needed")
            
            self.server_jar_path = message
            self.server_directory = os.path.dirname(message)
            self.server_dir_input.setText(self.server_directory)
            self.start_button.setEnabled(True)
            
            QMessageBox.information(
                self,
                "Success!",
                f"Server downloaded successfully!\n\nLocation:\n{os.path.dirname(message)}\n\nDouble-click start.bat or use the Console tab to launch your server."
            )
        else:
            self.log("\n" + "="*60)
            self.log("✗ DOWNLOAD FAILED")
            self.log("="*60)
            self.log(f"\nError: {message}")
            
            QMessageBox.critical(
                self,
                "Download Failed",
                f"Failed to download server:\n\n{message}"
            )

    def start_install_java(self):
        """Begin the Temurin download+install process for the required Java major."""
        try:
            version = self.version_combo.currentText()
            parts = version.split('.')
            minor = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0

            required_java = 8
            if minor <= 16:
                required_java = 8
            elif minor == 17:
                required_java = 16
            elif minor == 18 or minor == 19:
                required_java = 17
            elif minor == 20:
                patch = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0
                required_java = 21 if patch >= 5 else 17
            elif minor >= 21:
                required_java = 21

            dest = self.dir_input.text() or os.path.join(get_base_dir(), 'downloads')
            os.makedirs(dest, exist_ok=True)

            self.temurin_thread = TemurinInstallThread(required_java, dest, install_dir=None, set_java_home=True)
            self.temurin_thread.log_signal.connect(self.log)
            self.temurin_thread.progress_signal.connect(self.update_progress)
            self.temurin_thread.finished_signal.connect(self._on_temurin_finished)
            try:
                self.install_java_button.setEnabled(False)
            except Exception:
                pass
            try:
                self.progress_bar.setVisible(True)
                self.progress_label.setVisible(True)
            except Exception:
                pass
            self.temurin_thread.start()
        except Exception as e:
            self.log(f"[ERROR] Failed to start Temurin installer: {e}")

    def _on_temurin_finished(self, success: bool, message: str):
        try:
            try:
                self.progress_bar.setVisible(False)
                self.progress_label.setVisible(False)
            except Exception:
                pass
            if success:
                self.log(f"[INFO] Temurin install completed: {message}")
                try:
                    QMessageBox.information(self, "Java Installed", f"Java installed: {message}")
                except Exception:
                    pass
                try:
                    self.detect_all_java_installations()
                except Exception:
                    pass
                try:
                    self.refresh_java_selection()
                except Exception:
                    pass
                try:
                    self.update_java_label()
                except Exception:
                    pass
            else:
                self.log(f"[ERROR] Temurin install failed: {message}")
                try:
                    QMessageBox.warning(self, "Install Failed", f"Failed to install Java: {message}")
                except Exception:
                    pass
        except Exception:
            pass
        finally:
            try:
                self.install_java_button.setEnabled(True)
            except Exception:
                pass
    
    def start_server(self):
        """Start the Minecraft server"""
        if not self.server_jar_path or not os.path.exists(self.server_jar_path):
            QMessageBox.warning(self, "No Server", "No server JAR found. Please download a server first.")
            return
        
        self.server_process = QProcess(self)
        self.server_process.setWorkingDirectory(self.server_directory)
        self.server_process.readyReadStandardOutput.connect(self.handle_stdout)
        self.server_process.readyReadStandardError.connect(self.handle_stderr)
        self.server_process.finished.connect(lambda exitCode, exitStatus: self.server_finished(exitCode, exitStatus))
        
        ram = f"{self.console_ram_spinbox.value()}G"
        
        jar_name = os.path.basename(self.server_jar_path)
        args = ["-Xmx" + ram, "-Xms" + ram, "-jar", jar_name, "nogui"]

        java_cmd = "java"
        try:
            if hasattr(self, 'java_combo') and self.java_combo.isEnabled() and self.java_combo.currentIndex() >= 0:
                sel = self.java_combo.currentData()
                if sel:
                    java_cmd = sel
        except Exception:
            pass

        try:
            if java_cmd and os.path.isdir(java_cmd):
                java_cmd = os.path.join(java_cmd, 'bin', 'java.exe' if sys.platform == 'win32' else 'java')
        except Exception:
            pass

        try:
            if (not os.path.isabs(java_cmd)) or (isinstance(java_cmd, str) and not os.path.exists(java_cmd)):
                jh = os.environ.get('JAVA_HOME')
                if jh:
                    candidate = os.path.join(jh, 'bin', 'java.exe' if sys.platform == 'win32' else 'java')
                    if os.path.exists(candidate):
                        java_cmd = candidate
                if shutil is not None:
                    try:
                        found = shutil.which(java_cmd) if java_cmd else None
                        if found:
                            java_cmd = found
                    except Exception:
                        pass
        except Exception:
            pass

        self.console_output.clear()
        self.console_output.append(f"Starting server: {java_cmd} {' '.join(args)}\n")
        self.console_output.append("="*60 + "\n")

        self.server_start_time = time.time()
        self.server_process.start(java_cmd, args)
        
        self.status_label.setText("Status: Starting...")
        self._set_widget_state(self.status_label, 'state', 'warn')
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.command_input.setEnabled(True)
        self.send_button.setEnabled(True)
        
    def stop_server(self):
        """Stop the Minecraft server"""
        if self.server_process and self.server_process.state() == QProcess.ProcessState.Running:
            self.console_output.append("> stop")
            self.server_process.write(b"stop\n")
            
    def send_command(self):
        """Send command to server console"""
        if self.server_process and self.server_process.state() == QProcess.ProcessState.Running:
            command = self.command_input.text().strip()
            if command:
                self.console_output.append(f"> {command}")
                self.server_process.write((command + "\n").encode())
                
                if not self.command_history or self.command_history[-1] != command:
                    self.command_history.append(command)
                self.history_index = len(self.command_history)
                
                self.command_input.clear()
                
    def handle_stdout(self):
        """Handle server stdout"""
        if self.server_process:
            data = self.server_process.readAllStandardOutput()
            text = bytes(data).decode('utf-8', errors='ignore')
            try:
                for ln in text.splitlines():
                    self._raw_console_lines.append(ln)
            except Exception:
                pass
            try:
                self.append_colored(self.console_output, text.rstrip())
            except Exception:
                self.console_output.append(text.rstrip())
                self.console_output.moveCursor(QTextCursor.MoveOperation.End)
            
            if "Done" in text and "For help, type" in text:
                self.status_label.setText("Status: Running")
                self._set_widget_state(self.status_label, 'state', 'ok')
            try:
                self.check_for_plugin_crash(text)
            except Exception:
                pass
                
    def handle_stderr(self):
        """Handle server stderr"""
        if self.server_process:
            data = self.server_process.readAllStandardError()
            text = bytes(data).decode('utf-8', errors='ignore')
            try:
                for ln in text.splitlines():
                    self._raw_console_lines.append(ln)
            except Exception:
                pass
            try:
                self.append_colored(self.console_output, text.rstrip())
            except Exception:
                self.console_output.append(text.rstrip())
                self.console_output.moveCursor(QTextCursor.MoveOperation.End)
            try:
                self.check_for_plugin_crash(text)
            except Exception:
                pass

    def check_for_plugin_crash(self, text: str):
        """Heuristic detection of plugin crashes or plugin-related exceptions in console output.

        If a likely plugin exception is found, show a short popup (throttled).
        """
        try:
            if not text:
                return

            t_lower = text.lower()
            t_upper = text.upper()

            plugin_indicators = [
                '.jar', 'plugin', 'plugins', 'org.bukkit.plugin', 'org.bukkit.craftbukkit',
                'could not pass event', 'could not load plugin', 'failed to load plugin',
                'java.lang.noclassdeffounderror', 'java.lang.classnotfoundexception',
                'java.lang.exceptionininitializererror'
            ]

            severity_indicators = ['EXCEPTION', 'ERROR', 'SEVERE', 'CAUSED BY', 'TRACEBACK']

            has_plugin_hint = any(ind in t_lower for ind in plugin_indicators)
            has_severity = any(ind in t_upper for ind in severity_indicators)

            if not (has_plugin_hint and has_severity):
                return

            snippet = text.strip().splitlines()[0][:400]
            now = time.time()

            if getattr(self, '_last_plugin_alert_time', 0) + 10 > now and getattr(self, '_last_plugin_alert', '') == snippet:
                return

            self._last_plugin_alert = snippet
            self._last_plugin_alert_time = now

            try:
                QMessageBox.warning(self, "Plugin Error Detected", f"A plugin-related error was detected:\n\n{snippet}\n\nSee the console for full details.")
            except Exception:
                pass
        except Exception:
            return
            
    def server_finished(self, exitCode=0, exitStatus=None):
        """Handle server process finished. Detect crashes and optionally auto-restart."""
        self.console_output.append("\n" + "="*60)

        crashed = False
        try:
            if exitStatus is not None:
                try:
                    crashed = (exitStatus == QProcess.ProcessExitStatus.CrashExit) or (exitCode != 0)
                except Exception:
                    crashed = (exitCode != 0)
            else:
                crashed = (exitCode != 0)
        except Exception:
            crashed = (exitCode != 0)

        if crashed:
            self.console_output.append(f"[ERROR] Server exited unexpectedly (exit code {exitCode}).")
            try:
                QMessageBox.critical(self, "Server Crashed", f"Server stopped unexpectedly (exit code {exitCode}).")
            except Exception:
                pass
        else:
            self.console_output.append("Server stopped.")

        self.console_output.append("="*60)

        self.status_label.setText("Status: Not Running")
        self._set_widget_state(self.status_label, 'state', 'idle')
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.command_input.setEnabled(False)
        self.send_button.setEnabled(False)

        if crashed and getattr(self, 'autorestart_check', None) and self.autorestart_check.isChecked():
            try:
                self.console_output.append("[INFO] Auto-restart enabled; restarting server in 1.5s...")
                QTimer.singleShot(1500, self.start_server)
            except Exception:
                pass
    
    def load_server_properties(self):
        """Load server.properties file into UI"""
        if not self.server_directory:
            QMessageBox.warning(self, "No Server", "Please select a server directory first.")
            return
        
        properties_path = os.path.join(self.server_directory, "server.properties")
        
        if not os.path.exists(properties_path):
            QMessageBox.information(self, "No Properties", "server.properties not found. Using default values.")
            return
        
        try:
            with open(properties_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        if key == 'motd':
                            self.motd_input.setText(value)
                        elif key == 'server-port':
                            self.port_spinbox.setValue(int(value))
                        elif key == 'max-players':
                            self.max_players_spinbox.setValue(int(value))
                        elif key == 'difficulty':
                            self.difficulty_combo.setCurrentText(value)
                        elif key == 'gamemode':
                            self.gamemode_combo.setCurrentText(value)
                        elif key == 'level-name':
                            self.level_name_input.setText(value)
                        elif key == 'level-seed':
                            self.level_seed_input.setText(value)
                        elif key == 'level-type':
                            self.level_type_combo.setCurrentText(value)
                        elif key == 'generate-structures':
                            self.generate_structures_check.setChecked(value.lower() == 'true')
                        elif key == 'spawn-animals':
                            self.spawn_animals_check.setChecked(value.lower() == 'true')
                        elif key == 'spawn-monsters':
                            self.spawn_monsters_check.setChecked(value.lower() == 'true')
                        elif key == 'spawn-npcs':
                            self.spawn_npcs_check.setChecked(value.lower() == 'true')
                        elif key == 'online-mode':
                            self.online_mode_check.setChecked(value.lower() == 'true')
                        elif key == 'pvp':
                            self.pvp_check.setChecked(value.lower() == 'true')
                        elif key == 'allow-flight':
                            self.allow_flight_check.setChecked(value.lower() == 'true')
                        elif key == 'allow-nether':
                            self.allow_nether_check.setChecked(value.lower() == 'true')
                        elif key == 'enable-command-block':
                            self.enable_command_block_check.setChecked(value.lower() == 'true')
                        elif key == 'view-distance':
                            self.view_distance_spinbox.setValue(int(value))
                        elif key == 'simulation-distance':
                            self.simulation_distance_spinbox.setValue(int(value))
                        elif key == 'white-list':
                            self.white_list_check.setChecked(value.lower() == 'true')
                        elif key == 'enforce-whitelist':
                            self.enforce_whitelist_check.setChecked(value.lower() == 'true')
                        elif key == 'max-tick-time':
                            self.max_tick_time_spinbox.setValue(int(value))
            
            self.settings_status_label.setText(f"✓ Loaded settings from: {properties_path}")
            self._set_widget_state(self.settings_status_label, 'state', 'ok')
            
        except Exception as e:
            QMessageBox.critical(self, "Load Error", f"Failed to load server.properties:\n{str(e)}")
    
    def save_server_properties(self):
        """Save UI values to server.properties file"""
        if not self.server_directory:
            QMessageBox.warning(self, "No Server", "Please select a server directory first.")
            return
        
        properties_path = os.path.join(self.server_directory, "server.properties")
        
        existing_properties = {}
        comments = []
        property_order = []
        
        if os.path.exists(properties_path):
            try:
                with open(properties_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        stripped = line.strip()
                        if not stripped or stripped.startswith('#'):
                            comments.append(line)
                        elif '=' in stripped:
                            key = stripped.split('=', 1)[0].strip()
                            existing_properties[key] = line
                            property_order.append(key)
            except:
                pass
        
        new_properties = {
            'motd': self.motd_input.text() or 'A Minecraft Server',
            'server-port': str(self.port_spinbox.value()),
            'max-players': str(self.max_players_spinbox.value()),
            'difficulty': self.difficulty_combo.currentText(),
            'gamemode': self.gamemode_combo.currentText(),
            'level-name': self.level_name_input.text() or 'world',
            'level-seed': self.level_seed_input.text(),
            'level-type': self.level_type_combo.currentText(),
            'generate-structures': 'true' if self.generate_structures_check.isChecked() else 'false',
            'spawn-animals': 'true' if self.spawn_animals_check.isChecked() else 'false',
            'spawn-monsters': 'true' if self.spawn_monsters_check.isChecked() else 'false',
            'spawn-npcs': 'true' if self.spawn_npcs_check.isChecked() else 'false',
            'online-mode': 'true' if self.online_mode_check.isChecked() else 'false',
            'pvp': 'true' if self.pvp_check.isChecked() else 'false',
            'allow-flight': 'true' if self.allow_flight_check.isChecked() else 'false',
            'allow-nether': 'true' if self.allow_nether_check.isChecked() else 'false',
            'enable-command-block': 'true' if self.enable_command_block_check.isChecked() else 'false',
            'view-distance': str(self.view_distance_spinbox.value()),
            'simulation-distance': str(self.simulation_distance_spinbox.value()),
            'white-list': 'true' if self.white_list_check.isChecked() else 'false',
            'enforce-whitelist': 'true' if self.enforce_whitelist_check.isChecked() else 'false',
            'max-tick-time': str(self.max_tick_time_spinbox.value())
        }
        
        try:
            with open(properties_path, 'w', encoding='utf-8') as f:
                if not existing_properties:
                    f.write("#Minecraft server properties\n")
                    f.write("#Generated by YaliLauncher\n")
                
                if comments and existing_properties:
                    for comment in comments:
                        if comment.strip():
                            f.write(comment)
                
                written = set()
                for key in property_order:
                    if key in new_properties:
                        f.write(f"{key}={new_properties[key]}\n")
                        written.add(key)
                
                for key, value in new_properties.items():
                    if key not in written:
                        f.write(f"{key}={value}\n")
            
            self.settings_status_label.setText(f"✓ Saved settings to: {properties_path}")
            self._set_widget_state(self.settings_status_label, 'state', 'ok')
            QMessageBox.information(self, "Success", "Server settings saved successfully!\n\nRestart your server for changes to take effect.")
            
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save server.properties:\n{str(e)}")
    
    def detect_server_info(self):
        """Detect server software and Minecraft version from jar file"""
        if not self.server_jar_path:
            return None, None
        
        jar_name = os.path.basename(self.server_jar_path).lower()
        
        import re
        version_match = re.search(r'(\d+\.\d+(?:\.\d+)?)', jar_name)
        mc_version = version_match.group(1) if version_match else None
        
        software_type = None
        if 'fabric' in jar_name:
            software_type = 'fabric'
        elif 'forge' in jar_name or 'neoforge' in jar_name:
            software_type = 'forge'
        elif 'paper' in jar_name or 'purpur' in jar_name or 'spigot' in jar_name or 'bukkit' in jar_name or 'folia' in jar_name:
            software_type = 'bukkit'
        elif 'vanilla' in jar_name:
            software_type = 'vanilla'
        
        return mc_version, software_type
    
    def get_addon_folder_type(self):
        """Determine if server uses plugins or mods folder"""
        if not self.server_directory:
            return None, None
        
        plugins_folder = os.path.join(self.server_directory, "plugins")
        mods_folder = os.path.join(self.server_directory, "mods")
        
        if os.path.exists(plugins_folder):
            return "plugins", plugins_folder
        elif os.path.exists(mods_folder):
            return "mods", mods_folder
        else:
            if self.server_jar_path:
                jar_name = os.path.basename(self.server_jar_path).lower()
                if any(x in jar_name for x in ['fabric', 'forge', 'neoforge']):
                    os.makedirs(mods_folder, exist_ok=True)
                    return "mods", mods_folder
                else:
                    os.makedirs(plugins_folder, exist_ok=True)
                    return "plugins", plugins_folder
        
        return None, None
    
    def refresh_addons_list(self):
        """Refresh the list of installed addons"""
        self.addons_list.clear()
        
        if not self.server_directory:
            self.addons_status_label.setText("No server directory selected")
            self._set_widget_state(self.addons_status_label, 'state', 'normal')
            return
        
        addon_type, addon_folder = self.get_addon_folder_type()
        
        if not addon_folder:
            self.addons_status_label.setText("Could not determine addon folder type")
            self._set_widget_state(self.addons_status_label, 'state', 'normal')
            self.addon_type_label.setText("")
            return
        
        try:
            if os.path.exists(addon_folder):
                jar_files = [f for f in os.listdir(addon_folder) if f.endswith('.jar')]
                
                if jar_files:
                    for jar in sorted(jar_files):
                        file_path = os.path.join(addon_folder, jar)
                        size = os.path.getsize(file_path)
                        size_str = f"{size / 1024:.1f} KB" if size < 1024*1024 else f"{size / (1024*1024):.1f} MB"
                        
                        item = QListWidgetItem(f"{jar} ({size_str})")
                        item.setData(Qt.ItemDataRole.UserRole, jar)
                        self.addons_list.addItem(item)
                    
                    self.addons_status_label.setText(f"✓ Found {len(jar_files)} {addon_type} in: {addon_folder}")
                    self._set_widget_state(self.addons_status_label, 'state', 'ok')
                else:
                    self.addons_status_label.setText(f"No {addon_type} installed (folder exists but is empty)")
                    self._set_widget_state(self.addons_status_label, 'state', 'normal')
            else:
                self.addons_status_label.setText(f"{addon_type.capitalize()} folder not found")
                self._set_widget_state(self.addons_status_label, 'state', 'normal')
        
        except Exception as e:
            self.addons_status_label.setText(f"Error reading {addon_type} folder: {str(e)}")
            self._set_widget_state(self.addons_status_label, 'state', 'error')
    
    def add_addon(self):
        """Add a new addon by copying a JAR file"""
        addon_type, addon_folder = self.get_addon_folder_type()
        
        if not addon_folder:
            QMessageBox.warning(self, "No Folder", "Could not determine addon folder. Please start your server first to create the folder.")
            return
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            f"Select {addon_type.capitalize()[:-1]} JAR File",
            "",
            "JAR Files (*.jar)"
        )
        
        if not file_path:
            return
        
        try:
            filename = os.path.basename(file_path)
            destination = os.path.join(addon_folder, filename)
            
            if os.path.exists(destination):
                reply = QMessageBox.question(
                    self,
                    "File Exists",
                    f"{filename} already exists. Overwrite?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.No:
                    return
            
            shutil.copy2(file_path, destination)
            self.refresh_addons_list()
            QMessageBox.information(self, "Success", f"Added {filename} to {addon_type} folder!")
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to add addon:\n{str(e)}")
    
    def remove_addon(self):
        """Remove selected addon"""
        selected_items = self.addons_list.selectedItems()
        
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select an addon to remove.")
            return
        
        addon_type, addon_folder = self.get_addon_folder_type()
        
        if not addon_folder:
            return
        
        item = selected_items[0]
        filename = item.data(Qt.ItemDataRole.UserRole)
        
        reply = QMessageBox.question(
            self,
            "Confirm Removal",
            f"Are you sure you want to remove {filename}?\n\nThis cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                file_path = os.path.join(addon_folder, filename)
                os.remove(file_path)
                self.refresh_addons_list()
                QMessageBox.information(self, "Success", f"Removed {filename}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to remove addon:\n{str(e)}")
    
    def open_addons_folder(self):
        """Open the addons folder in file explorer"""
        addon_type, addon_folder = self.get_addon_folder_type()
        
        if not addon_folder:
            QMessageBox.warning(self, "No Folder", "Could not find addon folder.")
            return
        
        if not os.path.exists(addon_folder):
            os.makedirs(addon_folder, exist_ok=True)
        
        if sys.platform == 'win32':
            os.startfile(addon_folder)
        elif sys.platform == 'darwin':
            subprocess.run(['open', addon_folder])
        else:
            subprocess.run(['xdg-open', addon_folder])
    
    def is_valid_world(self, world_path):
        """Check if a directory is a valid Minecraft world"""
        if not os.path.isdir(world_path):
            return False
        
        if not os.path.exists(os.path.join(world_path, 'level.dat')):
            return False
        
        has_region = (
            os.path.isdir(os.path.join(world_path, 'region')) or
            os.path.isdir(os.path.join(world_path, 'DIM-1', 'region')) or
            os.path.isdir(os.path.join(world_path, 'DIM1', 'region'))
        )
        
        if not has_region:
            return False
        
        return True
    
    def get_world_dimensions(self, world_path):
        """Detect which dimensions exist in a world"""
        dimensions = []
        
        if os.path.isdir(os.path.join(world_path, 'region')):
            dimensions.append('Overworld')
        
        nether_paths = [
            os.path.join(world_path, 'DIM-1', 'region'),
            os.path.join(world_path, 'dimensions', 'minecraft', 'the_nether', 'region')
        ]
        
        if any(os.path.isdir(p) for p in nether_paths):
            dimensions.append('Nether')
        
        end_paths = [
            os.path.join(world_path, 'DIM1', 'region'),
            os.path.join(world_path, 'dimensions', 'minecraft', 'the_end', 'region')
        ]
        
        if any(os.path.isdir(p) for p in end_paths):
            dimensions.append('End')
        
        if not dimensions:
            dimensions.append('Overworld')
        
        return dimensions
    
    def detect_worlds(self):
        """Detect all valid Minecraft worlds in the server directory"""
        if not self.server_directory:
            return []
        
        worlds = []
        
        try:
            for item in os.listdir(self.server_directory):
                item_path = os.path.join(self.server_directory, item)
                
                if self.is_valid_world(item_path):
                    worlds.append(item)
                    
        except Exception as e:
            self.log(f"[WARNING] Error detecting worlds: {e}")
        
        return sorted(worlds)
    
    def refresh_worlds_list(self):
        """Refresh the list of detected worlds"""
        self.worlds_list.clear()
        
        if not self.server_directory:
            self.world_status_label.setText("No server directory selected")
            self._set_widget_state(self.world_status_label, 'state', 'warn')
            return
        
        worlds = self.detect_worlds()
        
        if worlds:
            self.world_status_label.setText(f"Found {len(worlds)} world(s)")
            self._set_widget_state(self.world_status_label, 'state', 'ok')
            
            for world in worlds:
                world_path = os.path.join(self.server_directory, world)
                
                try:
                    total_size = 0
                    for dirpath, dirnames, filenames in os.walk(world_path):
                        for filename in filenames:
                            filepath = os.path.join(dirpath, filename)
                            if os.path.exists(filepath):
                                total_size += os.path.getsize(filepath)
                    
                    size_mb = total_size / (1024 * 1024)
                    if size_mb < 1024:
                        size_str = f"{size_mb:.1f} MB"
                    else:
                        size_str = f"{size_mb / 1024:.2f} GB"
                    
                    dimensions = self.get_world_dimensions(world_path)
                    dim_str = ', '.join(dimensions)
                    
                    item = QListWidgetItem(f"{world} ({size_str}) - [{dim_str}]")
                    item.setData(Qt.ItemDataRole.UserRole, world)
                    self.worlds_list.addItem(item)
                except Exception:
                    try:
                        dimensions = self.get_world_dimensions(world_path)
                        dim_str = ', '.join(dimensions)
                        item = QListWidgetItem(f"{world} - [{dim_str}]")
                    except Exception:
                        item = QListWidgetItem(world)
                    item.setData(Qt.ItemDataRole.UserRole, world)
                    self.worlds_list.addItem(item)
        else:
            self.world_status_label.setText("No worlds detected in server directory")
            self._set_widget_state(self.world_status_label, 'state', 'idle')
    
    def open_world_folder(self):
        """Open the selected world folder in file explorer"""
        selected_items = self.worlds_list.selectedItems()
        
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select a world to open.")
            return
        
        world_name = selected_items[0].data(Qt.ItemDataRole.UserRole)
        world_path = os.path.join(self.server_directory, world_name)
        
        if not os.path.exists(world_path):
            QMessageBox.warning(self, "Error", f"World folder not found: {world_name}")
            return
        
        if sys.platform == 'win32':
            os.startfile(world_path)
        elif sys.platform == 'darwin':
            subprocess.run(['open', world_path])
        else:
            subprocess.run(['xdg-open', world_path])
    
    def delete_world(self):
        """Delete the selected world"""
        selected_items = self.worlds_list.selectedItems()
        
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select a world to delete.")
            return
        
        world_name = selected_items[0].data(Qt.ItemDataRole.UserRole)
        world_path = os.path.join(self.server_directory, world_name)
        
        reply = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete the world '{world_name}'?\n\nThis action cannot be undone!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                shutil.rmtree(world_path)
                self.log(f"[SUCCESS] Deleted world: {world_name}")
                QMessageBox.information(self, "Success", f"World '{world_name}' has been deleted.")
                self.refresh_worlds_list()
            except Exception as e:
                self.log(f"[ERROR] Failed to delete world {world_name}: {e}")
                QMessageBox.critical(self, "Error", f"Failed to delete world:\n{str(e)}")
    
    def backup_world(self):
        """Create a backup of the selected world"""
        selected_items = self.worlds_list.selectedItems()
        
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select a world to backup.")
            return
        
        world_name = selected_items[0].data(Qt.ItemDataRole.UserRole)
        world_path = os.path.join(self.server_directory, world_name)
        
        if not os.path.exists(world_path):
            QMessageBox.warning(self, "Error", f"World folder not found: {world_name}")
            return
        
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{world_name}_backup_{timestamp}"
        backup_path = os.path.join(self.server_directory, backup_name)
        
        try:
            self.log(f"[INFO] Creating backup of {world_name}...")
            shutil.copytree(world_path, backup_path)
            self.log(f"[SUCCESS] Backup created: {backup_name}")
            QMessageBox.information(self, "Success", f"Backup created successfully:\n{backup_name}")
            self.refresh_worlds_list()
        except Exception as e:
            self.log(f"[ERROR] Failed to backup world {world_name}: {e}")
            QMessageBox.critical(self, "Error", f"Failed to create backup:\n{str(e)}")
    
    def search_modrinth(self):
        """Search Modrinth for plugins/mods"""
        query = self.modrinth_search_input.text().strip()
        if not query:
            QMessageBox.warning(self, "Empty Search", "Please enter a search term.")
            return
        
        self.modrinth_results.clear()
        self.modrinth_results.addItem("Searching Modrinth...")
        
        try:
            addon_type, addon_folder = self.get_addon_folder_type()
            mc_version, software_type = self.detect_server_info()
            
            facets = []
            if addon_type == "plugins":
                facets.append('["project_type:plugin"]')
            elif addon_type == "mods":
                facets.append('["project_type:mod"]')
            
            if mc_version:
                facets.append(f'["versions:{mc_version}"]')
            
            if software_type:
                if software_type == 'fabric':
                    facets.append('["categories:fabric"]')
                elif software_type == 'forge':
                    facets.append('["categories:forge","categories:neoforge"]')
                elif software_type == 'bukkit':
                    facets.append('["categories:bukkit","categories:spigot","categories:paper","categories:purpur"]')
            
            facet_str = f"&facets=[{','.join(facets)}]" if facets else ""
            url = f"https://api.modrinth.com/v2/search?query={query}{facet_str}&limit=20"
            
            self.log(f"[INFO] Searching for '{query}' (MC {mc_version or 'any'}, {software_type or 'any platform'})")
            
            data = http.get_json(url, timeout=10)
            hits = data.get('hits', [])
            
            self.modrinth_results.clear()
            
            if not hits:
                self.modrinth_results.addItem(f"No results found for {software_type or 'this platform'} {mc_version or ''}")
                return
            
            for hit in hits:
                project_id = hit.get('project_id', '')
                title = hit.get('title', 'Unknown')
                description = hit.get('description', '')[:60]
                downloads = hit.get('downloads', 0)
                
                item_text = f"{title} - {downloads:,} downloads\n  {description}..."
                item = QListWidgetItem(item_text)
                item.setData(Qt.ItemDataRole.UserRole, project_id)
                self.modrinth_results.addItem(item)
            
            self.log(f"[INFO] Found {len(hits)} compatible results for '{query}'")
            
        except Exception as e:
            self.modrinth_results.clear()
            self.modrinth_results.addItem(f"Error: {str(e)}")
            self.log(f"[ERROR] Modrinth search failed: {e}")
    
    def download_modrinth_addon(self, item):
        """Download and install addon from Modrinth"""
        project_id = item.data(Qt.ItemDataRole.UserRole)
        if not project_id:
            return
        
        addon_type, addon_folder = self.get_addon_folder_type()
        if not addon_folder:
            QMessageBox.warning(self, "No Folder", "Could not determine addon folder.")
            return
        
        mc_version, software_type = self.detect_server_info()
        
        try:
            self.log(f"[INFO] Fetching project details from Modrinth...")
            
            project_url = f"https://api.modrinth.com/v2/project/{project_id}"
            project_data = http.get_json(project_url, timeout=10)
            
            project_name = project_data.get('title', 'Unknown')
            
            params = {}
            if mc_version:
                params['game_versions'] = f'["{mc_version}"]'
            
            if software_type:
                if software_type == 'fabric':
                    params['loaders'] = '["fabric"]'
                elif software_type == 'forge':
                    params['loaders'] = '["forge","neoforge"]'
                elif software_type == 'bukkit':
                    params['loaders'] = '["bukkit","spigot","paper","purpur"]'
            
            versions_url = f"https://api.modrinth.com/v2/project/{project_id}/version"
            versions_data = http.get_json(versions_url, timeout=10, params=params)
            
            if not versions_data:
                msg = f"No compatible versions found for {project_name}"
                if mc_version:
                    msg += f" (MC {mc_version}"
                if software_type:
                    msg += f", {software_type}"
                if mc_version:
                    msg += ")"
                QMessageBox.warning(self, "No Compatible Versions", msg)
                self.log(f"[WARNING] {msg}")
                return
            
            latest_version = versions_data[0]
            version_number = latest_version.get('version_number', 'unknown')
            game_versions = latest_version.get('game_versions', [])
            loaders = latest_version.get('loaders', [])
            
            self.log(f"[INFO] Found compatible version {version_number} (MC: {', '.join(game_versions[:3])}, Loaders: {', '.join(loaders)})")
            
            files = latest_version.get('files', [])
            
            if not files:
                QMessageBox.warning(self, "No Files", f"No files available for {project_name}")
                return
            
            primary_file = next((f for f in files if f.get('primary', False)), files[0])
            download_url = primary_file.get('url')
            filename = primary_file.get('filename')
            
            if not download_url or not filename:
                QMessageBox.warning(self, "Invalid File", "Could not find download URL")
                return
            
            self.log(f"[INFO] Downloading {filename}...")
            dest_path = os.path.join(addon_folder, filename)
            downloader.download_file(download_url, dest_path)
            self.log(f"[SUCCESS] Downloaded {filename} from Modrinth!")
            QMessageBox.information(self, "Success", f"Downloaded and installed:\n{filename}\n\nRestart your server to load the {addon_type[:-1]}.")
            self.refresh_addons_list()
            
        except Exception as e:
            self.log(f"[ERROR] Failed to download from Modrinth: {e}")
            QMessageBox.critical(self, "Download Failed", f"Failed to download addon:\n{str(e)}")
    
    def closeEvent(self, event):
        """Handle window close event"""
        try:
            try:
                self.save_app_settings()
            except Exception:
                pass
        except Exception:
            pass
        try:
            if self.server_process and self.server_process.state() == QProcess.ProcessState.Running:
                self.log("[INFO] Stopping server because launcher is closing...")
                self.stop_server()
        except Exception:
            pass

        try:
            app = QApplication.instance()
            if app:
                try:
                    app.removeEventFilter(self)
                except Exception:
                    pass
        except Exception:
            pass

        try:
            if getattr(self, '_click_effect', None):
                try:
                    self._click_effect.stop()
                except Exception:
                    pass
                try:
                    self._click_effect.deleteLater()
                except Exception:
                    pass
            if getattr(self, '_click_player', None):
                try:
                    self._click_player.stop()
                except Exception:
                    pass
                try:
                    self._click_player.deleteLater()
                except Exception:
                    pass
            if getattr(self, '_click_output', None):
                try:
                    self._click_output.deleteLater()
                except Exception:
                    pass
            if getattr(self, '_bg_player', None):
                try:
                    self._bg_player.stop()
                except Exception:
                    pass
                try:
                    self._bg_player.deleteLater()
                except Exception:
                    pass
            if getattr(self, '_bg_output', None):
                try:
                    self._bg_output.deleteLater()
                except Exception:
                    pass
        except Exception:
            pass

        event.accept()

    
    def import_world(self):
        """Import a world folder from file system"""
        if not self.server_directory:
            QMessageBox.warning(self, "No Server", "Please select a server directory first.")
            return
        
        world_dir = QFileDialog.getExistingDirectory(
            self,
            "Select World Folder to Import",
            "",
            QFileDialog.Option.ShowDirsOnly
        )
        
        if not world_dir:
            return
        
        if not self.is_valid_world(world_dir):
            QMessageBox.warning(
                self,
                "Invalid World",
                "The selected folder is not a valid Minecraft world or isn't fully initialized.\n\nA valid world must contain:\n- level.dat\n- region/ folder (or dimension folders)"
            )
            return
        
        world_name = os.path.basename(world_dir)
        dest_path = os.path.join(self.server_directory, world_name)
        
        if os.path.exists(dest_path):
            reply = QMessageBox.question(
                self,
                "World Exists",
                f"A world named '{world_name}' already exists.\n\nOverwrite it?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.No:
                return
            
            try:
                shutil.rmtree(dest_path)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to remove existing world:\n{str(e)}")
                return
        
        try:
            self.log(f"[INFO] Importing world: {world_name}...")
            shutil.copytree(world_dir, dest_path)
            self.log(f"[SUCCESS] Imported world: {world_name}")
            QMessageBox.information(self, "Success", f"World '{world_name}' imported successfully!")
            self.refresh_worlds_list()
        except Exception as e:
            self.log(f"[ERROR] Failed to import world: {e}")
            QMessageBox.critical(self, "Import Failed", f"Failed to import world:\n{str(e)}")


class HistoryLineEdit(QLineEdit):
    """QLineEdit with command history navigation using up/down arrows"""
    def __init__(self, parent):
        super().__init__(parent)
        self.parent_window = parent
    
    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Up:
            if hasattr(self.parent_window, 'command_history') and self.parent_window.command_history:
                if self.parent_window.history_index > 0:
                    self.parent_window.history_index -= 1
                    self.setText(self.parent_window.command_history[self.parent_window.history_index])
        elif event.key() == Qt.Key.Key_Down:
            if hasattr(self.parent_window, 'command_history') and self.parent_window.command_history:
                if self.parent_window.history_index < len(self.parent_window.command_history) - 1:
                    self.parent_window.history_index += 1
                    self.setText(self.parent_window.command_history[self.parent_window.history_index])
                elif self.parent_window.history_index == len(self.parent_window.command_history) - 1:
                    self.parent_window.history_index = len(self.parent_window.command_history)
                    self.clear()
        else:
            super().keyPressEvent(event)


def main():
    app = QApplication(sys.argv)
    try:
        base_dir = os.path.dirname(__file__)
        font_candidates = [
            os.path.join(base_dir, 'components/fonts/roboto', 'RobotoMedium.ttf'),
        ]
        for fp in font_candidates:
            if os.path.isfile(fp):
                font_id = QFontDatabase.addApplicationFont(fp)
                if font_id != -1:
                    families = QFontDatabase.applicationFontFamilies(font_id)
                    if families:
                        app.setFont(QFont(families[0]))
                break
    except Exception:
        pass
    
    app.setStyle('Fusion')
    try:
        base = get_base_dir()
        qss_path = os.path.join(base, 'components/ui', 'yali.qss')
        if os.path.exists(qss_path):
            try:
                with open(qss_path, 'r', encoding='utf-8') as f:
                    app.setStyleSheet(f.read())
            except Exception:
                pass
    except Exception:
        pass

    try:
        base = get_base_dir()
        icon_path = os.path.join(base, 'components/icon', 'icon.ico')
        if os.path.exists(icon_path):
            try:
                app.setWindowIcon(QIcon(icon_path))
            except Exception:
                pass
    except Exception:
        pass

    window = ServerLauncherGUI()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()