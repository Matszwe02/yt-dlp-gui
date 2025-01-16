import json
import logging
import shlex
import subprocess as sp
import sys
import os
import time

import PySide6.QtCore as qtc

logger = logging.getLogger(__name__)

TITLE = 0
FORMAT = 1
SIZE = 2
PROGRESS = 3
STATUS = 4
SPEED = 5
ETA = 6


sb_categories = {
    "Sponsor" : 'sponsor',
    "Interaction" : 'interaction',
    "Self Promo" : 'selfpromo',
    "Intro" : 'intro',
    "Endcards" : 'outro',
    "Preview" : 'preview',
    "Filler" : 'filler',
    "Non-Music" : 'music_offtopic',
}

class Worker(qtc.QThread):
    finished = qtc.Signal(int)
    progress = qtc.Signal(object, list)
    #Modded
    def __init__(
        self,
        item,
        args,
        link,
        path,
        filename,
        fmt,
        cargs,
        sponsorblock,
        sb_categories,
        metadata,
        thumbnail,
        subtitles,
        autosubtitles,
        embedsubs,
        mkvremux,
    ):
        super().__init__()
        self.item = item
        self.args = args
        self.link = link
        self.path = path
        self.filename = filename
        self.fmt = fmt
        self.cargs = cargs
        self.sponsorblock = sponsorblock
        self.sb_categories = sb_categories
        self.metadata = metadata
        self.thumbnail = thumbnail
        self.subtitles = subtitles
        self.autosubtitles = autosubtitles
        self.embedsubs = embedsubs
        self.mkvremux = mkvremux
        self.mutex = qtc.QMutex()
        self._stop = False
        self.rawr = "Rawr"
        self.extst = '.mp4'
        self.ext = '.mkv'
    def __str__(self):
        s = (
            f"(link={self.link}, "
            f"args={self.args}, "
            f"path={self.path}, "
            f"filename={self.filename}, "
            f"format={self.fmt}, "
            f"cargs={self.cargs}, "
            f"sponsorblock={self.sponsorblock}, "
            f"sb_categories={','.join(self.sb_categories)}, "
            f"metadata={self.metadata}, "
            f"thumbnail={self.thumbnail}, "
            f"embedsubs={self.subtitles}, "
            f"autosubtitles={self.autosubtitles}, "
            f"embedsubs={self.embedsubs}, "
            f"subtitles={self.mkvremux})"
        )
        return s
    def build_command(self):
        args = [
            "yt-dlp",
            "--newline",
            "--ignore-errors",
            "--ignore-config",
            "--no-simulate",
            "--progress",
            "--progress-template",
            "%(progress.status)s %(progress._total_bytes_estimate_str)s "
            "%(progress._percent_str)s %(progress._speed_str)s %(progress._eta_str)s",
            "--dump-json",
            "-v",
            ]

        args += self.args if isinstance(self.args, list) else shlex.split(self.args)
        if self.cargs:
            args += (
                self.cargs if isinstance(self.cargs, list) else shlex.split(self.cargs)
            )

        if self.autosubtitles:
            args += ["--write-auto-sub"]
            args += ["--convert-subs", "srt"]
        if self.subtitles:
            args += ["--write-sub"]
            args += ["--sub-lang", "en"]
        if self.mkvremux:
             args += ["--remux-video", "mkv"]
        if self.metadata:
            args += ["--embed-metadata"]
        if self.thumbnail:
            args += ["--embed-thumbnail"]
        if self.embedsubs:
            args += ["--embed-subs"]
        if self.sponsorblock:
            categories = "all" if 'all' in self.sb_categories else ",".join(sb_categories.get(cat, 'all') for cat in self.sb_categories)
            if self.sponsorblock == "remove":
                args += ["--sponsorblock-remove", categories]
            else:
                args += ["--sponsorblock-mark", categories]

        #end custom config
        if self.path:
            args += ["-o", f"{self.path}/{self.filename}" if self.filename else self.path]
        args += ["--", self.link]
        return args
    def sizeof_fmt(self, num, suffix="B"):
        for unit in ("", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"):
            if abs(num) < 1024.0:
                return f"{num:3.1f}{unit}{suffix}"
            num /= 1024.0
        return f"{num:.1f}Yi{suffix}"
    
    def stop(self):
        with qtc.QMutexLocker(self.mutex):
            self._stop = True
    
    def restart(self):
        # self.stop()
        self._stop = False
        # self.run()
    
    def run(self):
        while True:
            create_window = sp.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            command = self.build_command()
            output = []
            logger.info(
                f"Download ({self.item.id}) starting with cmd: " + shlex.join(command)
            )

            with sp.Popen(
                command,
                stdout=sp.PIPE,
                stderr=sp.STDOUT,
                text=True,
                universal_newlines=True,
                creationflags=create_window,
            ) as p:
                for line in p.stdout:
                    output.append(line)
                    #logger.info(f"Info ({line})")
                    with qtc.QMutexLocker(self.mutex):
                        if self._stop:
                            p.terminate()
                            break
                    if line.startswith("{"):
                        title = json.loads(line)["title"]
                        #mkv remux fix complete size finished
                        self.rawr  = json.loads(line)["filename"]
                        #end mkv remux fix complete size finished
                        logger.debug(f"Download ({self.item.id}) title: {title}")
                        self.progress.emit(
                            self.item,
                            [(TITLE, title), (STATUS, "Processing")],
                        )
                    elif line.lower().startswith("downloading"):
                        data = line.split()
                        self.progress.emit(
                            self.item,
                            [
                                (SIZE, data[1]),
                                (PROGRESS, data[2]),
                                (SPEED, data[3]),
                                (ETA, data[4]),
                                (STATUS, "Downloading"),
                            ],
                        )
                    elif line.startswith(("[Merger]", "[ExtractAudio]")):
                        self.progress.emit(self.item, [(STATUS, "Converting")])
                    #mkv remux fix complete size finished
                    elif line.startswith("[EmbedThumbnail"):
                        if ".mp4" in self.rawr:
                            self.extst = '.mp4'
                        elif ".webm" in self.rawr:
                            self.extst = '.webm'
                        elif ".webp" in self.rawr:
                            self.extst = '.webp'
                        if ".mp4" in line:
                            self.ext = '.mp4'
                        elif ".webm" in line:
                            self.ext = '.webm'
                        elif ".webp" in line:
                            self.ext = '.webp'
                        elif ".mkv" in line:
                            self.ext = '.mkv'
                        MEOW = self.rawr.replace(self.extst, self.ext)
                        MEOW2 = os.path.getsize(MEOW)
                        MEOW3 = self.sizeof_fmt(MEOW2) or ""
                        self.progress.emit(
                            self.item,
                            [
                                (TITLE,MEOW),
                                (SIZE,MEOW3),
                            ],
                        )          
            if p.returncode == 0: break
            
            logger.error(f"Download ({self.item.id}) returncode: {p.returncode}")
            self.progress.emit(
                self.item,
                [
                    (SIZE, "ERROR"),
                    (STATUS, "ERROR"),
                    (SPEED, "ERROR"),
                ],
            )
            self._stop = True
            while self._stop == True:
                time.sleep(1)
            
        self.progress.emit(
            self.item,
            [
                (PROGRESS, "100%"),
                (STATUS, "Finished"),
            ],
        )
        self.finished.emit(self.item.id)