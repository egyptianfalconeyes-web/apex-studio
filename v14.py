# -*- coding: utf-8 -*-
"""
Apex Master AI Studio - Ultimate Edition v14.0
المبتكرون العرب لصناعة البرمجيات والإلكترونيات
إشراف إدارة: م. عادل الدريني
"""
import sys
import os
import json
import time
import uuid
import hashlib
import asyncio
import subprocess
import threading
import shutil
from PIL import Image, ImageDraw, ImageFont

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTextEdit, QPushButton, QProgressBar, QFrame, QComboBox,
    QMessageBox, QFileDialog, QListWidget, QLineEdit, QDialog,
    QFormLayout, QDialogButtonBox, QGraphicsDropShadowEffect, QCheckBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QUrl
from PyQt5.QtGui import QColor, QPixmap, QDesktopServices

import edge_tts

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    HAS_BIDI = True
except ImportError:
    HAS_BIDI = False

def fix_ar(text):
    if not text or not HAS_BIDI:
        return str(text or "")
    try:
        return get_display(arabic_reshaper.reshape(str(text)))
    except Exception:
        return str(text)

try:
    from google import genai
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False

# ---------------------------------------------------------------
# 1. نظام التفعيل وحساب فترة التجربة (15 يوماً)
# ---------------------------------------------------------------
SECRET_SALT = "ARAB_INNOVATORS_2026_PRO_KEY_SALT"

def get_hwid():
    try:
        if sys.platform == "win32":
            cmd = "wmic csproduct get uuid"
            uuid_str = subprocess.check_output(cmd, shell=True).decode().split('\n')[1].strip()
            if uuid_str:
                return hashlib.md5(uuid_str.encode()).hexdigest()[:12].upper()
    except Exception:
        pass
    mac = hex(uuid.getnode())[2:].zfill(12)
    return hashlib.md5(mac.encode()).hexdigest()[:12].upper()

def verify_license_key(hwid: str, key: str):
    key = key.strip().upper()
    parts = key.split("-")
    if len(parts) != 5:
        return False, "INVALID"
    prefix = parts[0]
    body = "-".join(parts[1:])
    
    mode = "LIFETIME" if prefix == "LIF" else ("YEAR1" if prefix == "Y1Y" else "TRIAL15")
    raw = f"{hwid.strip().upper()}::{mode}::{SECRET_SALT}"
    digest = hashlib.sha256(raw.encode('utf-8')).hexdigest().upper()
    expected_body = "-".join([digest[i:i+4] for i in range(0, 16, 4)])
    
    if body == expected_body:
        return True, mode
    return False, "INVALID"

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".apex_studio_v14")
LIC_FILE = os.path.join(CONFIG_DIR, "license.dat")

def get_license_info():
    os.makedirs(CONFIG_DIR, exist_ok=True)
    hwid = get_hwid()
    now = int(time.time())
    
    data = {"first_run": now, "last_run": now, "activated": False, "key": "", "mode": "TRIAL"}
    if os.path.exists(LIC_FILE):
        try:
            with open(LIC_FILE, "r", encoding="utf-8") as f:
                data.update(json.load(f))
        except Exception:
            pass
            
    if data.get("key"):
        valid, mode = verify_license_key(hwid, data["key"])
        if valid:
            data["activated"] = True
            data["mode"] = mode
            return data

    if now < data.get("last_run", 0):
        data["tampered"] = True
    else:
        data["last_run"] = now

    with open(LIC_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f)
        
    return data

# ---------------------------------------------------------------
# 2. التهيئة والمسارات الأساسية
# ---------------------------------------------------------------
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

PROJECTS_DIR = os.path.join(BASE_DIR, "Apex_Projects")
os.makedirs(PROJECTS_DIR, exist_ok=True)

VOICE_MAPPING = {
    "🎙️ مصري (عامية - سلمى)": "ar-EG-SalmaNeural",
    "🎙️ مصري (رسمي - شاكر)": "ar-EG-ShakirNeural",
    "🎙️ فصحى (سعودي - زيد)": "ar-SA-ZaydNeural",
    "🎙️ إنجليزي (Christopher)": "en-US-ChristopherNeural",
}

PLATFORM_PRESETS = {
    "YOUTUBE": {
        "title": "YouTube & FB",
        "desc": "أفقي سينمائي (16:9)",
        "width": 1280, "height": 720,
        "color": "#ef4444", "glow": "#f87171",
        "safe_bottom": 50
    },
    "TIKTOK": {
        "title": "TikTok & Shorts",
        "desc": "رأسي حديث (9:16)",
        "width": 720, "height": 1280,
        "color": "#06b6d4", "glow": "#22d3ee",
        "safe_bottom": 160
    },
    "INSTAGRAM": {
        "title": "Instagram Post",
        "desc": "مربع متناسق (1:1)",
        "width": 1080, "height": 1080,
        "color": "#a855f7", "glow": "#c084fc",
        "safe_bottom": 80
    }
}

def get_font(size):
    candidates = [
        os.path.join(BASE_DIR, "assets", "font.ttf"),
        r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\arial.ttf",
    ]
    for path in candidates:
        if os.path.isfile(path):
            try: return ImageFont.truetype(path, size=size)
            except Exception: continue
    return ImageFont.load_default()

def wrap_text(draw, text, font, max_width):
    words = text.split()
    lines, current = [], ""
    for w in words:
        test = (current + " " + w).strip()
        box = draw.textbbox((0, 0), fix_ar(test), font=font)
        if box[2] - box[0] <= max_width or not current:
            current = test
        else:
            lines.append(current)
            current = w
    if current: lines.append(current)
    return lines or [text]

# ---------------------------------------------------------------
# 3. بطاقات التصدير التفاعلية (Preset Cards UI)
# ---------------------------------------------------------------
class PlatformCard(QFrame):
    clicked = pyqtSignal(str)

    def __init__(self, key, info):
        super().__init__()
        self.key = key
        self.info = info
        self.is_selected = False

        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(85)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        
        lbl_title = QLabel(info["title"])
        lbl_title.setStyleSheet("font-weight: 900; font-size: 13px; color: #ffffff;")
        
        lbl_desc = QLabel(info["desc"])
        lbl_desc.setStyleSheet("font-size: 11px; color: #94a3b8;")
        
        layout.addWidget(lbl_title)
        layout.addWidget(lbl_desc)
        
        self.update_style()

    def set_selected(self, selected: bool):
        self.is_selected = selected
        self.update_style()

    def update_style(self):
        c = self.info["color"]
        g = self.info["glow"]
        if self.is_selected:
            self.setStyleSheet(f"""
                PlatformCard {{
                    background-color: #1e293b;
                    border: 2px solid {c};
                    border-radius: 10px;
                }}
            """)
        else:
            self.setStyleSheet("""
                PlatformCard {
                    background-color: #020617;
                    border: 1px solid #1e293b;
                    border-radius: 10px;
                }
                PlatformCard:hover {
                    border: 1px solid #475569;
                }
            """)

    def mousePressEvent(self, event):
        self.clicked.emit(self.key)

# ---------------------------------------------------------------
# 4. محرك المعالجة والتصدير الخلفي
# ---------------------------------------------------------------
class ProductionThread(QThread):
    progress_signal = pyqtSignal(int, str)
    finished_signal = pyqtSignal(list, str)

    def __init__(self, prompt, voice_code, platform_key):
        super().__init__()
        self.prompt = prompt
        self.voice_code = voice_code
        self.p_info = PLATFORM_PRESETS[platform_key]
        self.width = self.p_info["width"]
        self.height = self.p_info["height"]
        self.safe_bottom = self.p_info["safe_bottom"]
        self.cancel_event = threading.Event()

    def cancel(self):
        self.cancel_event.set()

    def create_background(self, text, idx):
        img = Image.new("RGB", (self.width, self.height))
        px = ImageDraw.Draw(img)
        for y in range(self.height):
            r = int(10 + 12 * y / self.height)
            g = int(15 + 18 * y / self.height)
            b = int(26 + 30 * y / self.height)
            px.line([(0, y), (self.width, y)], fill=(r, g, b))
        d = ImageDraw.Draw(img)
        big = get_font(int(self.height * 0.04))
        d.text((30, self.height // 2 - 20), f"Scene {idx}", fill=(16, 185, 129), font=big)
        return img

    def create_overlay_image(self, text):
        img = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        wm_font = get_font(max(14, int(self.height * 0.022)))
        sub_font = get_font(max(16, int(self.height * 0.032)))

        draw.text((25, 20), fix_ar("المبتكرون العرب - م. عادل الدريني"), fill=(16, 185, 129, 230), font=wm_font)

        lines = wrap_text(draw, text, sub_font, self.width - 80)[:4]
        line_h = int(self.height * 0.032) + 10
        box_h = line_h * len(lines) + 24
        
        top = self.height - box_h - self.safe_bottom
        draw.rectangle([(25, top), (self.width - 25, top + box_h)], fill=(15, 23, 42, 220))
        
        y = top + 10
        for line in lines:
            shaped = fix_ar(line)
            box = draw.textbbox((0, 0), shaped, font=sub_font)
            w = box[2] - box[0]
            draw.text(((self.width - w) // 2, y), shaped, fill=(255, 255, 255, 255), font=sub_font)
            y += line_h
        return img

    async def _process_audio(self, sentences, proj_dir):
        audio_files = []
        for idx, text in enumerate(sentences, 1):
            if self.cancel_event.is_set():
                raise RuntimeError("تم إلغاء العملية.")
            path = os.path.join(proj_dir, f"audio_{idx}.mp3")
            comm = edge_tts.Communicate(text, self.voice_code)
            await comm.save(path)
            audio_files.append(path)
        return audio_files

    def run(self):
        loop = None
        try:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            proj_dir = os.path.join(PROJECTS_DIR, f"Project_{timestamp}")
            os.makedirs(proj_dir, exist_ok=True)

            sentences = [s.strip() for s in self.prompt.replace(".", ".\n").split("\n") if len(s.strip()) > 2]
            if not sentences: sentences = [self.prompt]

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            self.progress_signal.emit(10, "جاري معالجة التعليق الصوتي...")
            audios = loop.run_until_complete(self._process_audio(sentences, proj_dir))

            scenes = []
            total = len(sentences)
            for idx, text in enumerate(sentences, 1):
                if self.cancel_event.is_set():
                    raise RuntimeError("تم الإلغاء.")
                self.progress_signal.emit(int(10 + (idx / total) * 85), f"بناء المشهد البصري {idx}/{total}...")
                
                img_p = os.path.join(proj_dir, f"image_{idx}.jpg")
                self.create_background(text, idx).save(img_p, quality=92)

                over_p = os.path.join(proj_dir, f"overlay_{idx}.png")
                self.create_overlay_image(text).save(over_p)

                scenes.append({
                    "id": idx, "text": text, "image": img_p,
                    "audio": audios[idx - 1], "overlay": over_p,
                })

            self.progress_signal.emit(100, "تم تجهيز كافة المشاهد")
            self.finished_signal.emit(scenes, proj_dir)
        except Exception as e:
            self.finished_signal.emit([], str(e))
        finally:
            if loop: loop.close()

# ---------------------------------------------------------------
# 5. نافذة التفعيل والشاشة الرئيسية
# ---------------------------------------------------------------
class ActivationDialog(QDialog):
    def __init__(self, hwid, parent=None):
        super().__init__(parent)
        self.hwid = hwid
        self.setWindowTitle("تفعيل البرنامج - المبتكرون العرب")
        self.setLayoutDirection(Qt.RightToLeft)
        self.setFixedSize(450, 250)
        self.setStyleSheet("""
            QDialog { background-color: #0b0f19; color: #ffffff; font-family: 'Segoe UI', sans-serif; }
            QLabel { color: #9ca3af; font-weight: bold; }
            QLineEdit { background-color: #111827; border: 1px solid #1f2937; border-radius: 6px; color: #10b981; padding: 8px; font-weight: bold; }
            QPushButton { background-color: #10b981; color: white; font-weight: bold; border-radius: 6px; padding: 8px 16px; border: none; }
        """)
        
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("رمز جهازك الفريد (أرسله للمهندس عادل الدريني):"))
        
        hwid_edit = QLineEdit(self.hwid)
        hwid_edit.setReadOnly(True)
        layout.addWidget(hwid_edit)
        
        layout.addWidget(QLabel("أدخل كود التفعيل الخاص بك هنا:"))
        self.key_edit = QLineEdit()
        self.key_edit.setPlaceholderText("XXXX-XXXX-XXXX-XXXX-XXXX")
        layout.addWidget(self.key_edit)
        
        btn_box = QHBoxLayout()
        btn_submit = QPushButton("تفعيل الآن 🔑")
        btn_submit.clicked.connect(self.accept)
        btn_box.addWidget(btn_submit)
        layout.addLayout(btn_box)

    def get_key(self):
        return self.key_edit.text().strip()

class ApexMasterStudio(QMainWindow):
    def __init__(self, lic_info):
        super().__init__()
        self.lic_info = lic_info
        self.scenes_data = []
        self.current_proj_dir = ""
        self.selected_platform = "TIKTOK"
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Apex Master AI Studio v14.0 Ultimate Edition")
        self.setGeometry(30, 30, 1400, 880)
        self.setLayoutDirection(Qt.RightToLeft)

        self.setStyleSheet("""
            QMainWindow { background-color: #080b11; font-family: 'Segoe UI', sans-serif; }
            #HeaderFrame { background: #0f172a; border-bottom: 1px solid #1e293b; }
            .CardFrame { background-color: #0f172a; border: 1px solid #1e293b; border-radius: 12px; }
            QTextEdit, QComboBox { background-color: #020617; border: 1px solid #1e293b; border-radius: 8px; color: #f8fafc; padding: 10px; }
            QPushButton { background-color: #1e293b; color: #f8fafc; font-size: 13px; font-weight: 700; border-radius: 8px; padding: 10px; border: 1px solid #334155; }
            QPushButton:hover { background-color: #334155; }
            #BtnRun { background: #2563eb; border: none; color: white; }
            #BtnExport { background: #10b981; border: none; color: white; }
            QListWidget { background-color: #020617; border: 1px solid #1e293b; border-radius: 8px; color: #f8fafc; }
            QProgressBar { background-color: #020617; border-radius: 6px; text-align: center; color: white; }
            QProgressBar::chunk { background: #10b981; }
        """)

        central = QWidget()
        self.setCentralWidget(central)
        main_lay = QVBoxLayout(central)
        main_lay.setContentsMargins(0, 0, 0, 0)

        # Header
        header = QFrame()
        header.setObjectName("HeaderFrame")
        h_lay = QHBoxLayout(header)
        
        lbl_title = QLabel("⚡ APEX MASTER AI STUDIO <span style='color: #10b981;'>v14.0</span>")
        lbl_title.setStyleSheet("color: white; font-weight: 900; font-size: 16px;")
        
        # Trial Banner
        hwid = get_hwid()
        if self.lic_info.get("activated"):
            lic_status = f"🟢 نسخة مفعلة بالكامل ({self.lic_info.get('mode')})"
        else:
            days_left = max(0, 15 - int((time.time() - self.lic_info.get("first_run", time.time())) / 86400))
            lic_status = f"⏳ فترة تجريبية متبقي: {days_left} يوماً"

        lbl_lic = QLabel(lic_status)
        lbl_lic.setStyleSheet("color: #38bdf8; font-weight: bold; background: #1e293b; padding: 6px 12px; border-radius: 6px;")
        
        btn_act = QPushButton("🔑 تفعيل")
        btn_act.clicked.connect(self.open_activation)

        h_lay.addWidget(lbl_title)
        h_lay.addStretch()
        h_lay.addWidget(lbl_lic)
        h_lay.addWidget(btn_act)
        main_lay.addWidget(header)

        # Body
        body = QWidget()
        b_lay = QHBoxLayout(body)

        # Left Panel
        left_p = QFrame()
        left_p.setProperty("class", "CardFrame")
        l_lay = QVBoxLayout(left_p)

        l_lay.addWidget(QLabel("🎯 اختر منصة التصدير (Preset Cards):"))
        cards_lay = QHBoxLayout()
        self.card_widgets = {}
        for k, v in PLATFORM_PRESETS.items():
            card = PlatformCard(k, v)
            card.clicked.connect(self.on_platform_selected)
            cards_lay.addWidget(card)
            self.card_widgets[k] = card
        l_lay.addLayout(cards_lay)
        self.on_platform_selected("TIKTOK")

        l_lay.addWidget(QLabel("📝 القصة / السيناريو:"))
        self.prompt_input = QTextEdit()
        self.prompt_input.setPlaceholderText("اكتب النص هنا.. كل جملة تنتهي بنقطة تعتبر مشهداً.")
        l_lay.addWidget(self.prompt_input)

        l_lay.addWidget(QLabel("🎙 التعليق الصوتي:"))
        self.voice_combo = QComboBox()
        self.voice_combo.addItems(list(VOICE_MAPPING.keys()))
        l_lay.addWidget(self.voice_combo)

        self.batch_check = QCheckBox("🚀 التصدير المتعدد الشامل (لكافة المنصات بضغطة زر)")
        self.batch_check.setStyleSheet("color: #10b981; font-weight: bold;")
        l_lay.addWidget(self.batch_check)

        grid_b = QHBoxLayout()
        self.btn_run = QPushButton("1. توليد المشاهد 🎬")
        self.btn_run.setObjectName("BtnRun")
        self.btn_run.clicked.connect(self.start_production)
        
        self.btn_export = QPushButton("2. تصدير MP4 🚀")
        self.btn_export.setObjectName("BtnExport")
        self.btn_export.setEnabled(False)
        grid_b.addWidget(self.btn_run)
        grid_b.addWidget(self.btn_export)
        l_lay.addLayout(grid_b)

        # Right Panel
        right_p = QFrame()
        right_p.setProperty("class", "CardFrame")
        r_lay = QVBoxLayout(right_p)

        self.viewport = QLabel("🎬 [شاشة المعاينة]")
        self.viewport.setAlignment(Qt.AlignCenter)
        self.viewport.setStyleSheet("background-color: #020617; color: #475569; border: 2px dashed #1e293b; border-radius: 8px;")
        r_lay.addWidget(self.viewport, stretch=3)

        self.scene_list = QListWidget()
        r_lay.addWidget(self.scene_list, stretch=2)

        b_lay.addWidget(left_p, stretch=2)
        b_lay.addWidget(right_p, stretch=3)
        main_lay.addWidget(body)

        # Footer
        footer = QFrame()
        f_lay = QHBoxLayout(footer)
        self.status_lbl = QLabel("النظام مستقر وجاهز")
        self.status_lbl.setStyleSheet("color: #10b981; font-weight: bold;")
        self.p_bar = QProgressBar()
        f_lay.addWidget(self.status_lbl, stretch=2)
        f_lay.addWidget(self.p_bar, stretch=2)
        main_lay.addWidget(footer)

    def on_platform_selected(self, key):
        self.selected_platform = key
        for k, card in self.card_widgets.items():
            card.set_selected(k == key)

    def open_activation(self):
        dlg = ActivationDialog(get_hwid(), self)
        if dlg.exec_():
            key = dlg.get_key()
            valid, mode = verify_license_key(get_hwid(), key)
            if valid:
                self.lic_info["activated"] = True
                self.lic_info["key"] = key
                self.lic_info["mode"] = mode
                with open(LIC_FILE, "w", encoding="utf-8") as f:
                    json.dump(self.lic_info, f)
                QMessageBox.information(self, "نجاح", "تم تفعيل البرنامج بنجاح!")
                self.init_ui()
            else:
                QMessageBox.critical(self, "خطأ", "كود التفعيل غير صحيح!")

    def start_production(self):
        prompt = self.prompt_input.toPlainText().strip()
        if not prompt:
            QMessageBox.warning(self, "تنبيه", "أدخل النص أولاً!")
            return
        self.btn_run.setEnabled(False)
        voice = VOICE_MAPPING[self.voice_combo.currentText()]
        self.worker = ProductionThread(prompt, voice, self.selected_platform)
        self.worker.progress_signal.connect(lambda p, s: (self.p_bar.setValue(p), self.status_lbl.setText(s)))
        self.worker.finished_signal.connect(self.on_scenes_ready)
        self.worker.start()

    def on_scenes_ready(self, scenes, proj_dir):
        self.btn_run.setEnabled(True)
        if scenes:
            self.scenes_data = scenes
            self.current_proj_dir = proj_dir
            self.btn_export.setEnabled(True)
            self.scene_list.clear()
            for s in scenes:
                self.scene_list.addItem(f"🎬 المشهد {s['id']}: {s['text'][:35]}...")
            QMessageBox.information(self, "تم", "تم توليد كافة المشاهد بنجاح!")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    lic = get_license_info()
    win = ApexMasterStudio(lic)
    win.show()
    sys.exit(app.exec_())