"""Pinned and SHA256-verified official Orca Linux .deb installer."""
import hashlib
import os
from pathlib import Path
import platform
import subprocess
import tempfile
import urllib.request

VERSION="1.4.226"
ASSETS={
  "x86_64":("amd64","673ef0b3f8b1019668fe263a3afcf6d6f4f8c91edd276875bcc7783ebe693c49"),
  "aarch64":("arm64","43aff1b8b2989b8782ca97fa8b4202107b97d2105e3a2a759da1a38d6fe341d4"),
}
MAX_BYTES=280_000_000

def install(progress=None):
    progress=progress or (lambda _:None)
    if platform.machine() not in ASSETS:
        raise ValueError("Unsupported Orca Linux architecture")
    arch,expected=ASSETS[platform.machine()]
    filename=f"orca-ide_{VERSION}_{arch}.deb"
    url=f"https://github.com/stablyai/orca/releases/download/v{VERSION}/{filename}"
    with tempfile.TemporaryDirectory(prefix="vps-orca-") as directory:
        location=Path(directory)/filename
        progress("Downloading signed-release Orca package "+VERSION)
        req=urllib.request.Request(url,headers={"User-Agent":"VPS-Control/1"})
        digest=hashlib.sha256()
        total=0
        with urllib.request.urlopen(req,timeout=60) as src,open(location,"wb") as dest:
            while True:
                chunk=src.read(1024*1024)
                if not chunk:break
                total+=len(chunk)
                if total>MAX_BYTES:raise ValueError("Orca download exceeds size limit")
                digest.update(chunk)
                dest.write(chunk)
                if total % (20*1024*1024)<len(chunk):
                    progress(f"Downloaded {total//(1024*1024)} MiB")
        if digest.hexdigest()!=expected:
            raise ValueError("Orca package SHA256 mismatch; refusing installation")
        progress("Verified Orca SHA256; installing headless dependencies")
        subprocess.run(["/usr/bin/apt-get","install","-y","--no-install-recommends",
                        "xvfb","libnss3","libgbm1","libxss1", "libx11-xcb1"],
                       check=True,capture_output=True,timeout=240,
                       env={"PATH":"/usr/sbin:/usr/bin:/sbin:/bin","DEBIAN_FRONTEND":"noninteractive"})
        progress("Installing verified Orca .deb")
        subprocess.run(["/usr/bin/apt-get","install","-y","--no-install-recommends",str(location)],
                       check=True,capture_output=True,timeout=360,
                       env={"PATH":"/usr/sbin:/usr/bin:/sbin:/bin","DEBIAN_FRONTEND":"noninteractive"})
    return {"installed":True,"tool":"orca-host","version":VERSION}
