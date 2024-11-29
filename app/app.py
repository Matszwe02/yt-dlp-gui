"""
I modded a lot. I believe I added # to all mods.
"""
import logging, threading, os, sys, shutil, time, subprocess, requests, version
import win32event, win32api, concurrent.futures
import pywinctl as gw

from winerror import ERROR_ALREADY_EXISTS
from utils import *
from dep_dl import DownloadWindow
from PySide6 import QtCore as qtc, QtWidgets as qtw, QtGui
from PySide6.QtCore import QThread, QTimer, Signal
from PySide6.QtWidgets import QWidget, QSystemTrayIcon, QMenu
from PySide6.QtGui import QClipboard, QIcon, QAction, QPixmap
from ui.app_ui import Ui_MainWindow
from worker import Worker
FILEBROWSER_PATH = os.path.join(os.getenv('WINDIR'), 'explorer.exe')
os.environ["PATH"] += os.pathsep + str(ROOT / "bin")
#style="{",
#datefmt="%Y-%m-%d %H:%M",
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s (%(module)s:%(lineno)d) %(message)s",
    datefmt="%Y-%m-%d %H:%M",
    handlers=[
        logging.FileHandler("debug.log", encoding="utf-8", delay=True),
        logging.StreamHandler(),
    ],
)

class MainWindow(qtw.QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.tw.setColumnWidth(0, 200)

       
        #Select input for ctrl v
        self.load_config()
        self.le_link.clearFocus()
        self.le_filename.clearFocus()
        self.gb_args.clearFocus()
        self.setFocus()
        if not self.cb_ctrlv.isChecked():
            self.le_link.setFocus()
        #end Select input for ctrl v

        self.statusBar.showMessage(f"Version {version.__version__} -- {version.__subversion__} ")
        self.form = DownloadWindow()
        self.form.finished.connect(self.form.close)
        self.form.finished.connect(self.show)
        self.to_dl = {}
        self.worker = {}
        self.index = 0
        self.tb_path.clicked.connect(self.button_path)
        self.open_path.clicked.connect(self.button_open)
        self.dd_format.currentTextChanged.connect(self.load_preset)
        self.pb_save_preset.clicked.connect(self.save_preset)
        self.pb_add.clicked.connect(self.button_add)
        self.pb_clear.clicked.connect(self.button_clear)
        self.pb_download.clicked.connect(self.button_download)
        self.tw.itemClicked.connect(self.remove_item)
        #clipboard monitor & Keyboard input event
        self.clipboard = QClipboard()
        self.old_link = self.clipboard.text()
        self.cb_clipboardmonitor.clicked.connect(self.clip_change)
        self.installEventFilter(self)
        self.setup_timer()
        self.downloading = False
        #end clipboard monitor & Keyboard input event
        """
        self.icon_folder = self.resources_path()
        #self.tray_ico = QPixmap(self.icon_folder+"\yt-dlp-gui.ico")
        #self.setup_tray()
        """

    #Clipboard check
    def setup_timer(self):
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.auto_check)
        if self.cb_clipboardmonitor.isChecked():
            self.timer.start()

    def auto_check(self):
        self.current_link = self.clipboard.text()
        if self.current_link == self.old_link:
            return
        if "https://www.youtube.com/watch" in self.current_link:
            logger.info(f"Copy Link `{self.current_link}`")
            self.le_link.paste()
            self.button_add()
        self.old_link = self.current_link
    #endclipboard check
    def remove_item(self, item, column):
        modifiers = qtw.QApplication.keyboardModifiers()      
        if not self.isme or (self.isme and modifiers == qtc.Qt.ShiftModifier):
            ret = qtw.QMessageBox.question(
                self,
                "Application Message",
                f"Would you like to remove {item.text(0)} ?",
                qtw.QMessageBox.Yes | qtw.QMessageBox.No,
                qtw.QMessageBox.No,
            )
            if ret == qtw.QMessageBox.Yes:
                if self.to_dl.get(item.id):
                    logger.debug(f"Removing queued download ({item.id}): {item.text(0)}")
                    self.to_dl.pop(item.id)
                elif worker := self.worker.get(item.id):
                    logger.info(
                        f"Stopping and removing download ({item.id}): {item.text(0)}"
                    )
                    worker.stop()
                    self.tw.takeTopLevelItem(self.tw.indexOfTopLevelItem(item))
        else:
            if "Finished" in item.text(4):
                paths = os.path.normpath(item.text(0))
                arg = ['W:\\Down\\Rar\\Tools\\PortablePot\\PotPlayerPortable\\PotPlayerPortable.exe', paths,'/insert']
                subprocess.Popen(arg)

    def button_path(self):
        path = qtw.QFileDialog.getExistingDirectory(
            self, "Select a folder", qtc.QDir.homePath(), qtw.QFileDialog.ShowDirsOnly
        )

        if path:
            self.le_path.setText(path)

    def clip_change(self):
        self.old_link = self.clipboard.text()
        if self.cb_clipboardmonitor.isChecked():
            self.timer.start()
        else:
            self.timer.stop()

    def format_change(self, fmt):
        #added 1080
        if fmt in ("mp3", "flac"):
            self.cb_thumbnail.setEnabled(True)
            self.cb_mkvremux.setEnabled(False)
            self.cb_subtitle.setEnabled(False)
            self.cb_autosubtitles.setEnabled(False)
            self.cb_subtitlesembed.setEnabled(False)
        else:
            self.cb_thumbnail.setEnabled(True)
            self.cb_mkvremux.setEnabled(False)
            self.cb_subtitle.setEnabled(False)
            self.cb_autosubtitles.setEnabled(False)
            self.cb_subtitlesembed.setEnabled(True)
    def button_open(self):
        path = self.le_path.text()
        paths = os.path.normpath(path)
        subprocess.Popen([FILEBROWSER_PATH, paths])

    def button_add(self):
        #auto paste
        logger.info("Button Add")
        link = self.le_link.text()

        if self.cb_ctrlv.isChecked() and not link:
            self.le_link.paste()
        #end auto paste
        link = self.le_link.text()
        path = self.le_path.text()
        filename = self.le_filename.text()
        if not "youtube" in link and not "youtu.be" in link:
           return logger.info(f"Item {link} youtube not found")
        if "&list" in link:
            ret = qtw.QMessageBox.question(
                self,
                "Playlist Found",
                f"Download playlist? {link}",
                qtw.QMessageBox.Yes | qtw.QMessageBox.No,
                qtw.QMessageBox.No,
            )
            if ret == qtw.QMessageBox.No:
                logger.debug(f"Removing Playlist from link ({link})")
                link = link.split("&list")[0]
                
        if self.preset.get("default") is True and not all([link, path, self.fmt, filename]):
            return qtw.QMessageBox.information(
                self,
                "Application Message",
                "Unable to add the download because required fields are missing.\nRequired fields: Link, Path, Format & Filename.",
            )
        elif not link:
            return qtw.QMessageBox.information(
                self,
                "Application Message",
                "Unable to add the download because required fields are missing.\nRequired fields: Link.",
            )

        item = qtw.QTreeWidgetItem(self.tw, [link, self.fmt, "-", "0%", "Queued", "-", "-"])
        pb = qtw.QProgressBar()
        pb.setStyleSheet("QProgressBar { margin-bottom: 3px; }")
        pb.setTextVisible(False)
        self.tw.setItemWidget(item, 3, pb)
        [item.setTextAlignment(i, qtc.Qt.AlignCenter) for i in range(1, 6)]
        item.id = self.index
        self.le_link.clear()

        self.to_dl[self.index] = Worker(
            item,
            self.preset["args"],
            link,
            path,
            filename,
            self.fmt,
            self.le_cargs.text(),
            self.dd_sponsorblock.currentText(),
            self.cb_metadata.isChecked(),
            self.cb_thumbnail.isChecked(),
            self.cb_subtitles.isChecked(),
            self.cb_autosubtitles.isChecked(),
            self.cb_subtitlesembed.isChecked(),
            self.cb_mkvremux.isChecked(),
            self.isme,
        )

        logger.info(f"Queue download ({item.id}) added: {self.to_dl[self.index]}")
        if self.cb_auto.isChecked():
            if self.cb_onedl.isChecked():
                index = 0
                for k, v in self.to_dl.items():
                    self.worker[k] = v
                    self.worker[k].finished.connect(self.worker[k].deleteLater)
                    self.worker[k].finished.connect(lambda x: self.finisha(x))
                    self.worker[k].finished.connect(lambda x: self.worker.pop(x))
                    self.worker[k].progress.connect(self.update_progress)
                self.to_dl = {}
                print(" ")
                if not self.downloading:
                    self.downloading = True
                    try:
                        self.worker[self.index].start()
                    except KeyError:
                        pass
            else:
                for k, v in self.to_dl.items():
                    self.worker[k] = v
                    self.worker[k].finished.connect(self.worker[k].deleteLater)
                    self.worker[k].finished.connect(lambda x: self.worker.pop(x))
                    self.worker[k].progress.connect(self.update_progress)
                    self.worker[k].start()
                self.to_dl = {}
        self.index += 1

    def button_clear(self):
        if self.worker:
            return qtw.QMessageBox.critical(
                self,
                "Application Message",
                "Unable to clear list because there are active downloads in progress.\n"
                "Remove a download by clicking on it.",
            )

        self.worker = {}
        self.to_dl = {}
        self.tw.clear()

    def finisha(self, numa):
        numa = numa + 1
        print(" ")
        try:
            self.worker[numa].start()
        except KeyError:
            print('Done Downloading All')
            self.downloading = False
            pass

    def button_download(self):
        if self.cb_onedl.isChecked():
            for k, v in self.to_dl.items():
                self.worker[k] = v
                self.worker[k].finished.connect(self.worker[k].deleteLater)
                self.worker[k].finished.connect(lambda x: self.finisha(x))
                self.worker[k].finished.connect(lambda x: self.worker.pop(x))
                self.worker[k].progress.connect(self.update_progress)
            self.to_dl = {}
            if not self.downloading:
                self.downloading = True
                self.worker[0].start()
        else:
            for k, v in self.to_dl.items():
                self.worker[k] = v
                self.worker[k].finished.connect(self.worker[k].deleteLater)
                self.worker[k].finished.connect(lambda x: self.worker.pop(x))
                self.worker[k].progress.connect(self.update_progress)
                self.worker[k].start()
            self.to_dl = {}

    def update_progress(self, item, emit_data):
        try:
            for data in emit_data:
                index, update = data
                #if index == 4 and update == "Finished":

                if index != 3:
                    item.setText(index, update)
                else:
                    pb = self.tw.itemWidget(item, index)
                    pb.setValue(round(float(update.replace("%", ""))))
        except AttributeError:
            logger.info(f"Download ({item.id}) no longer exists")

    def closeEvent(self, event):
        self.config["format"] = self.dd_format.currentIndex()
        self.config["onedl"] = self.cb_onedl.isChecked()
        self.config["autostart"] = self.cb_auto.isChecked()
        self.config["ctrlv"] = self.cb_ctrlv.isChecked()
        self.config["clipboardmonitor"] = self.cb_clipboardmonitor.isChecked()
        self.config["mkvremux"] = self.cb_mkvremux.isChecked()
        save_json("config.json", self.config)
        event.accept()

    #ctrlv and enter
    def eventFilter(self, obj, event):
        if event.type() == qtc.QEvent.KeyPress:
            if event.key() == qtc.Qt.Key_V and event.modifiers() == qtc.Qt.ControlModifier and self.cb_ctrlv.isChecked():
                self.button_add()
        if event.type() == qtc.QEvent.KeyPress and obj is self.le_link:
            if event.key() == qtc.Qt.Key_Return and self.le_link.hasFocus():
                self.button_add()
        return super().eventFilter(obj, event)
    #end ctrlv and enter
    #onefile
    def resource_path(self):
        try:
            base_path = sys._MEIPASS
        except AttributeError:
            base_path = os.path.abspath("./config")
        return base_path
    #End onefile
    def load_config(self):
        #onefile
        if not os.path.isfile("config.json"):
            shutil.copy(os.path.join(self.resource_path(), "config.json"), "config.json")
        #end onefile
        config_path = "config.json"

        try:
            self.config = load_json(config_path)
        except FileNotFoundError:
            qtw.QMessageBox.critical(
                self,
                "Application Message",
                f"Config file not found at: {config_path}",
            )
            qtw.QApplication.exit()
        except json.decoder.JSONDecodeError:
            qtw.QMessageBox.critical(
                self,
                "Application Message",
                "Config file JSON decoding failed, check the log for more info.\n"
                "debug.log",
            )
            logger.error("Config file JSON decoding failed", exc_info=True)
            qtw.QApplication.exit()

        self.dd_format.addItems(self.config["presets"].keys())
        self.dd_format.setCurrentIndex(self.config["format"])
        self.load_preset(self.dd_format.currentText())

    def save_preset(self):
        if "path" in self.preset:
            self.preset["path"] = self.le_path.text()
        if "sponsorblock" in self.preset:
            self.preset["sponsorblock"] = self.dd_sponsorblock.currentIndex()
        if "metadata" in self.preset:
            self.preset["metadata"] = self.cb_metadata.isChecked()
        if "thumbnail" in self.preset:
            self.preset["thumbnail"] = self.cb_thumbnail.isChecked()
        if "subtitles" in self.preset:
            self.preset["subtitles"] = self.cb_subtitles.isChecked()
        if "autosubtitles" in self.preset:
            self.preset["autosubtitles"] = self.cb_autosubtitles.isChecked()    
        if "embedsubs" in self.preset:
            self.preset["embedsubs"] = self.cb_subtitlesembed.isChecked()
        if "filename" in self.preset:
            self.preset["filename"] = self.le_filename.text()
        if "extra_args" in self.preset:
            self.preset["extra_args"] = self.le_cargs.text()
        save_json("config.json", self.config)

        qtw.QMessageBox.information(
                self,
                "Application Message",
                f"Preset for {self.fmt} saved successfully.",
            )
    
    def load_preset(self, fmt):
        if not (preset := self.config["presets"].get(fmt)):
            self.le_path.clear()
            self.tb_path.setEnabled(False)
            self.dd_sponsorblock.setCurrentIndex(-1)
            self.dd_sponsorblock.setEnabled(False)
            self.cb_metadata.setChecked(False)
            self.cb_metadata.setEnabled(False)
            self.cb_thumbnail.setChecked(False)
            self.cb_thumbnail.setEnabled(False)
            self.cb_subtitles.setChecked(False)
            self.cb_subtitles.setEnabled(False)
            self.cb_autosubtitles.setChecked(False)
            self.cb_autosubtitles.setEnabled(False)
            self.cb_subtitlesembed.setChecked(False)
            self.cb_subtitlesembed.setEnabled(False)
            self.cb_mkvremux.setChecked(False)
            self.cb_mkvremux.setEnabled(False)
            self.le_cargs.clear()
            self.le_cargs.setEnabled(False)
            self.le_filename.clear()
            self.le_filename.setEnabled(False)

            self.le_link.setEnabled(False)
            self.gb_controls.setEnabled(False)

            self.cb_auto.setChecked(False)
            self.cb_ctrlv.setChecked(False)
            self.cb_clipboardmonitor.setChecked(False)
            self.cb_onedl.setChecked(False)
            return

        if not preset.get("args"):
            qtw.QMessageBox.critical(
                self,
                "Application Message",
                "The args key does not exist in the current preset and therefore it cannot be used.",
            )
            self.dd_format.setCurrentIndex(-1)
            return

        logger.debug(f"Changed format to {fmt} preset: {preset}")
        self.le_link.setEnabled(True)
        self.gb_controls.setEnabled(True)

        config = self.config
        if "path" in preset:
            self.tb_path.setEnabled(True)
            self.le_path.setText(preset["path"])
        else:
            self.le_path.clear()
            self.tb_path.setEnabled(False)

        if "sponsorblock" in preset:
            self.dd_sponsorblock.setEnabled(True)
            self.dd_sponsorblock.setCurrentIndex(preset["sponsorblock"])
        else:
            self.dd_sponsorblock.setCurrentIndex(-1)
            self.dd_sponsorblock.setEnabled(False)

        if "metadata" in preset:
            self.cb_metadata.setEnabled(True)
            self.cb_metadata.setChecked(preset["metadata"])
        else:
            self.cb_metadata.setChecked(False)
            self.cb_metadata.setEnabled(False)

        if "thumbnail" in preset:
            self.cb_thumbnail.setEnabled(True)
            self.cb_thumbnail.setChecked(preset["thumbnail"])
        else:
            self.cb_thumbnail.setChecked(False)
            self.cb_thumbnail.setEnabled(False)

        if "subtitles" in preset:
            self.cb_subtitles.setEnabled(True)
            self.cb_subtitles.setChecked(preset["subtitles"])
        else:
            self.cb_subtitles.setChecked(False)
            self.cb_subtitles.setEnabled(False)

        if "autosubtitles" in preset:
            self.cb_autosubtitles.setEnabled(True)
            self.cb_autosubtitles.setChecked(preset["autosubtitles"])
        else:
            self.cb_autosubtitles.setChecked(False)
            self.cb_autosubtitles.setEnabled(False)

        if "embedsubs" in preset:
            self.cb_subtitlesembed.setEnabled(True)
            self.cb_subtitlesembed.setChecked(preset["embedsubs"])
        else:
            self.cb_subtitlesembed.setChecked(False)
            self.cb_subtitlesembed.setEnabled(False)  

        if "mp3" in fmt:
            self.cb_mkvremux.setEnabled(False)
            self.cb_mkvremux.setChecked(False)
        elif "mkvremux" in config:
            self.cb_mkvremux.setEnabled(True)
            self.cb_mkvremux.setChecked(config["mkvremux"])
        else:
            self.cb_mkvremux.setChecked(False)
            self.cb_mkvremux.setEnabled(False)


        if "extra_args" in preset:
            self.le_cargs.setEnabled(True)
            self.le_cargs.setText(preset["extra_args"])
        else:
            self.le_cargs.clear()
            self.le_cargs.setEnabled(False)

        if "filename" in preset:
            self.le_filename.setEnabled(True)
            self.le_filename.setText(preset["filename"])
        else:
            self.le_filename.clear()
            self.le_filename.setEnabled(False)

        if "ctrlv" in config:
            self.cb_ctrlv.setEnabled(True)
            self.cb_ctrlv.setChecked(config["ctrlv"])
        else:
            self.cb_ctrlv.setChecked(False)
            self.cb_ctrlv.setEnabled(False)

        if "autostart" in config:
            self.cb_auto.setEnabled(True)
            self.cb_auto.setChecked(config["autostart"])
        else:
            self.cb_auto.setChecked(False)
            self.cb_auto.setEnabled(False)

        if "clipboardmonitor" in config:
            self.cb_clipboardmonitor.setEnabled(True)
            self.cb_clipboardmonitor.setChecked(config["clipboardmonitor"])
        else:
            self.cb_clipboardmonitor.setChecked(False)
            self.cb_clipboardmonitor.setEnabled(False)

        if "isme" in config:
            self.isme = config["isme"]

        if "onedl" in config:
            self.cb_onedl.setEnabled(True)
            self.cb_onedl.setChecked(config["onedl"]) 
        else:
            self.cb_clipboardmonitor.setChecked(False)
            self.cb_clipboardmonitor.setEnabled(False)
        self.preset = preset
        self.fmt = fmt

if __name__ == "__main__":
    mutex = win32event.CreateMutex(None, False, 'yt-dlp-gui')
    last_error = win32api.GetLastError()
    win = gw.getWindowsWithTitle('yt-dlp-gui')
    if win:
        win[0].minimize()
        win[0].restore()
    if last_error == ERROR_ALREADY_EXISTS:
        sys.exit()

    app = qtw.QApplication(sys.argv)
    window = MainWindow()
    sys.exit(app.exec())




"""
    def resources_path(self):
        try:
            base_path = sys._MEIPASS
        except AttributeError:
            base_path = os.path.abspath("./static")
        return base_path
    def setup_tray(self):
        self.trayicon = QSystemTrayIcon()
        self.trayicon.setIcon(QIcon(self.icon_folder+"\yt-dlp-gui.ico"))
        self.trayicon.setToolTip("yt-dlp GUI")
        self.context_menu()
        self.trayicon.show()
        self.trayicon.activated.connect(self.iconActivated)
    def iconActivated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            if self.isHidden():
                self.show()
            else:
                self.hide()
    def context_menu(self):
        context_menu = QMenu()
        quitapp = QAction("Quit", self)
        quitapp.triggered.connect(self.quit_app)
        context_menu.addAction(quitapp)
        self.trayicon.setContextMenu(context_menu)
    def quit_app(self):
        app.exit()
"""

