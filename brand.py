"""FubarXS brand tokens, widget styles and assets (see BRAND.md / STYLE-GUIDE.md).
All colors live ONLY here. Assets (icons/) are made by make_icon.py and make_assets.py."""
import os
import tkinter as tk

try:
    from PIL import Image, ImageTk
except ImportError:  # the app still works, just without pictures
    Image = ImageTk = None

ICONS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons")

VERSION = "0.5.6"
KOFI_URL = "https://ko-fi.com/fubarxs"

BG, PANEL = "#000000", "#1a1411"
PANEL_BORDER = "#38251c"  # rgba(255,150,100,.13) over the panel color
BORDER, BORDER_H = "#382a24", "#4a342b"
BTN, BTN_H = "#251c18", "#31241f"
TEXT, MUTED, DIM = "#f4ede7", "#a89c95", "#766d68"
MAGMA1, MAGMA2, HOT = "#c71d06", "#fe5505", "#ffc233"  # magma 1: fills only, never text
GREEN, ORANGE = "#3ecf8e", "#f5a524"  # states only
INPUT, DARK = "#0a0706", "#140804"  # field background (= icon tile), text on orange/gradient
ACCENT, ACCENT_H = MAGMA2, "#ff7a2e"
SEL, SEL_H = MAGMA1, "#e0270b"  # selected tab / segment (a fill)
RADIUS_LG, RADIUS_MD = 10, 7

CARD = dict(fg_color=PANEL, corner_radius=RADIUS_LG, border_width=1, border_color=PANEL_BORDER)
ENTRY = dict(fg_color=INPUT, border_color=BORDER, text_color=TEXT, corner_radius=RADIUS_MD, height=32)
BOX = dict(fg_color=INPUT, text_color=TEXT, corner_radius=RADIUS_MD)
BTN2 = dict(fg_color=BTN, hover_color=BTN_H, border_width=1, border_color=BORDER, text_color=TEXT, corner_radius=RADIUS_MD)
OPTION = dict(fg_color=BTN, button_color=BTN_H, button_hover_color=BORDER_H, text_color=TEXT, dropdown_fg_color=PANEL,
              dropdown_hover_color=BTN_H, dropdown_text_color=TEXT, corner_radius=RADIUS_MD)
SEG = dict(selected_color=SEL, selected_hover_color=SEL_H, unselected_color=BTN, unselected_hover_color=BTN_H,
           fg_color=BG, text_color=TEXT)
TABS = dict(fg_color=PANEL, segmented_button_fg_color=BG, segmented_button_selected_color=SEL,
            segmented_button_selected_hover_color=SEL_H, segmented_button_unselected_color=BTN,
            segmented_button_unselected_hover_color=BTN_H, text_color=TEXT)
COMBO = dict(fg_color=INPUT, border_color=BORDER, button_color=BTN_H, button_hover_color=BORDER_H, text_color=TEXT,
             dropdown_fg_color=PANEL, dropdown_hover_color=BTN_H, dropdown_text_color=TEXT, corner_radius=RADIUS_MD)
SLIDER = dict(progress_color=ACCENT, button_color=ACCENT, button_hover_color=ACCENT_H, fg_color=BORDER)
SWITCH = dict(progress_color=ACCENT, fg_color=BORDER, button_color=TEXT, button_hover_color="#ffffff", text_color=TEXT)


def image(name, size):
    """CTkImage from icons/<name>, or None when Pillow or the file is missing."""
    path = os.path.join(ICONS, name)
    if Image is None or not os.path.exists(path):
        return None
    import customtkinter as ctk
    return ctk.CTkImage(Image.open(path), size=size)


def window_icon(window):
    # Every size is handed over, so the title bar (16-24 px) and the taskbar (32-48 px) get their own picture; with only
    # the 128 px one Tk shrinks it without any smoothing and the small icon comes out jagged.
    paths = [os.path.join(ICONS, f"icon{s}.png") for s in (16, 20, 24, 32, 40, 48, 64, 128)]
    paths = [p for p in paths if os.path.exists(p)]
    if paths:
        try:
            photos = [tk.PhotoImage(file=p) for p in paths]
            window._icon_ref = photos
            window.after(300, lambda: window.iconphoto(True, *photos))  # CTk sets its own icon after ~200 ms
            ico = os.path.join(ICONS, "app.ico")
            if os.name == "nt" and os.path.exists(ico):
                window.after(320, lambda: window.iconbitmap(ico))
                window.after(500, lambda: _sharp_windows_icon(window, ico))
        except Exception:
            pass


def _sharp_windows_icon(window, ico):
    """Tk gives Windows only one 32 px icon, which Windows then stretches on the taskbar at 125/150 % scaling (blurry).
    Here the exact size for the current scaling is loaded from app.ico and set as the big and the small window icon."""
    try:
        import ctypes
        from ctypes import wintypes
        u = ctypes.windll.user32
        u.LoadImageW.restype = wintypes.HANDLE
        u.LoadImageW.argtypes = [wintypes.HINSTANCE, wintypes.LPCWSTR, wintypes.UINT, ctypes.c_int, ctypes.c_int, wintypes.UINT]
        u.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        hwnd = u.GetParent(window.winfo_id()) or window.winfo_id()
        try:
            dpi = u.GetDpiForWindow(hwnd) or 96
        except Exception:
            dpi = 96
        big, small = round(32 * dpi / 96), round(16 * dpi / 96)
        for kind, px in ((1, big), (0, small)):  # WM_SETICON: ICON_BIG = 1, ICON_SMALL = 0
            h = u.LoadImageW(None, ico, 1, px, px, 0x10)  # IMAGE_ICON, LR_LOADFROMFILE
            if h:
                u.SendMessageW(hwnd, 0x0080, kind, h)
        window._icon_handles = True
    except Exception:
        pass


class BrandButton(tk.Label):
    """Main action button: magma gradient (brand rule: main actions only), dark bold text.
    Modes: 'start' (gradient) and 'stop' (solid magma 1, bone text). Falls back to flat colors without Pillow."""

    def __init__(self, master, text, command, width=210, height=42):
        self.imgs, self.mode, self.command = {}, "start", command
        if ImageTk is not None:
            for key, f in (("start", "btn_gradient.png"), ("hover", "btn_gradient_hover.png"), ("stop", "btn_stop.png")):
                p = os.path.join(ICONS, f)
                if os.path.exists(p):
                    self.imgs[key] = ImageTk.PhotoImage(Image.open(p).resize((width, height), Image.LANCZOS))
        super().__init__(master, text=text, font=("Segoe UI", 12, "bold"), compound="center", bd=0, bg=BG,
                         highlightthickness=0, cursor="hand2", padx=24, pady=10)
        self.bind("<Button-1>", lambda e: self.command())
        self.bind("<Enter>", lambda e: self._look(True))
        self.bind("<Leave>", lambda e: self._look(False))
        self._look(False)

    def _look(self, hover):
        stop = self.mode == "stop"
        img = self.imgs.get("stop" if stop else ("hover" if hover else "start"))
        fg = TEXT if stop else DARK
        if img:
            self.configure(image=img, fg=fg)
        else:
            self.configure(image="", fg=fg, bg=MAGMA1 if stop else (ACCENT_H if hover else ACCENT))

    def set_mode(self, mode, text, command):
        self.mode, self.command = mode, command
        self.configure(text=text)
        self._look(False)
