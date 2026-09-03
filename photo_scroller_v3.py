import json
import os
import sys
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageDraw, ImageOps, ImageTk

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    BaseTk = TkinterDnD.Tk
    DND_AVAILABLE = True
except Exception:
    BaseTk = tk.Tk
    DND_FILES = None
    DND_AVAILABLE = False

try:
    from screeninfo import get_monitors
except Exception:
    get_monitors = None

SUPPORTED = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp'}
APP_NAME = 'PhotoScrollerV3'
TRANSPARENT_KEY = '#ff00fe'


def config_path() -> Path:
    base = os.getenv('LOCALAPPDATA') or os.getenv('APPDATA') or str(Path.home())
    folder = Path(base) / APP_NAME
    folder.mkdir(parents=True, exist_ok=True)
    return folder / 'settings.json'


class PhotoScrollerV3(BaseTk):
    def __init__(self):
        super().__init__()
        self.title('Photo Scroller V3')
        self.geometry('1220x760')
        self.minsize(920, 580)
        self.protocol('WM_DELETE_WINDOW', self._on_close)

        self.image_paths = []
        self.items = []
        self.running = False
        self.presentation = False
        self._rebuild_job = None
        self._last_canvas_size = (0, 0)
        self._last_tick = None
        self._drag_hint_id = None

        # Settings
        self.speed = tk.DoubleVar(value=150.0)      # px / second
        self.photo_height_pct = tk.IntVar(value=62)
        self.gap = tk.IntVar(value=70)
        self.background = tk.StringVar(value='Czarne')
        self.monitor_index = tk.IntVar(value=0)
        self.autostart = tk.BooleanVar(value=False)
        self.shuffle = tk.BooleanVar(value=False)
        self.frame_style = tk.StringVar(value='Biała ramka')
        self.watch_folder = tk.StringVar(value=r'C:\Dropbox\PhotoScroller')
        self.auto_folder_sync = tk.BooleanVar(value=True)
        self._folder_snapshot = None
        self._gap_apply_job = None

        self._load_settings()
        self._build_ui()
        self._refresh_monitors()
        self._apply_background()
        self._setup_dnd()
        self.after(700, self._folder_watch_tick)

        self.bind('<Escape>', lambda _e: self._exit_presentation())
        self.bind('<F11>', lambda _e: self._toggle_presentation())
        self.bind('<space>', lambda _e: self._toggle_run())
        self.bind('<Control-o>', lambda _e: self._add_images())
        self.bind('<Delete>', lambda _e: self._remove_selected())
        self.canvas.bind('<Configure>', self._on_canvas_resize)

        self.after(100, self._restore_images)
        self.after(16, self._animate)

    # ---------- UI ----------
    def _build_ui(self):
        self.configure(bg='#151515')
        self.topbar = tk.Frame(self, bg='#202020', height=48)
        self.topbar.pack(side='top', fill='x')
        self.topbar.pack_propagate(False)

        title = tk.Label(self.topbar, text='Photo Scroller V3', font=('Segoe UI', 13, 'bold'), fg='white', bg='#202020')
        title.pack(side='left', padx=(16, 14))

        tk.Button(self.topbar, text='＋ Dodaj zdjęcia', command=self._add_images, padx=10).pack(side='left', padx=3, pady=8)
        tk.Button(self.topbar, text='📁 Folder Dropbox', command=self._choose_watch_folder, padx=10).pack(side='left', padx=3, pady=8)
        self.start_btn = tk.Button(self.topbar, text='▶ Start', command=self._toggle_run, padx=13)
        self.start_btn.pack(side='left', padx=3, pady=8)
        tk.Button(self.topbar, text='⛶ Prezentacja (F11)', command=self._toggle_presentation, padx=10).pack(side='left', padx=3, pady=8)

        self.status = tk.Label(self.topbar, text='0 zdjęć', fg='#d5d5d5', bg='#202020')
        self.status.pack(side='right', padx=16)

        self.main = tk.Frame(self, bg='#151515')
        self.main.pack(fill='both', expand=True)

        self.sidebar = tk.Frame(self.main, bg='#262626', width=300)
        self.sidebar.pack(side='left', fill='y')
        self.sidebar.pack_propagate(False)

        self.canvas = tk.Canvas(self.main, bg='black', highlightthickness=0)
        self.canvas.pack(side='right', fill='both', expand=True)

        self._build_sidebar()
        self._show_hint()

    def _build_sidebar(self):
        pad = 14
        tk.Label(self.sidebar, text='USTAWIENIA POKAZU', font=('Segoe UI', 10, 'bold'), fg='#cfcfcf', bg='#262626').pack(anchor='w', padx=pad, pady=(14, 7))

        self._add_scale('Prędkość', self.speed, 30, 500, 10, ' px/s')
        self._add_scale('Wysokość zdjęć', self.photo_height_pct, 25, 90, 1, '%', rebuild=True)
        self._add_scale('Odstęp między zdjęciami', self.gap, 0, 250, 5, ' px', on_change=self._schedule_gap_apply)

        self._add_label('Tło')
        bg_combo = ttk.Combobox(self.sidebar, textvariable=self.background, state='readonly', values=['Czarne', 'Białe', 'Ciemnoszare', 'Zielone (chroma)', 'Przezroczyste'], width=28)
        bg_combo.pack(anchor='w', padx=pad, pady=(0, 10))
        bg_combo.bind('<<ComboboxSelected>>', lambda _e: self._background_changed())

        self._add_label('Ramka')
        frame_combo = ttk.Combobox(self.sidebar, textvariable=self.frame_style, state='readonly', values=['Biała ramka', 'Czarna ramka', 'Bez ramki'], width=28)
        frame_combo.pack(anchor='w', padx=pad, pady=(0, 10))
        frame_combo.bind('<<ComboboxSelected>>', lambda _e: self._schedule_rebuild())

        self._add_label('Monitor prezentacji')
        self.monitor_combo = ttk.Combobox(self.sidebar, state='readonly', width=28)
        self.monitor_combo.pack(anchor='w', padx=pad, pady=(0, 10))
        self.monitor_combo.bind('<<ComboboxSelected>>', self._monitor_changed)

        checks = tk.Frame(self.sidebar, bg='#262626')
        checks.pack(fill='x', padx=pad, pady=(2, 8))
        tk.Checkbutton(checks, text='Start automatycznie po uruchomieniu', variable=self.autostart, fg='white', bg='#262626', selectcolor='#3a3a3a', activebackground='#262626', activeforeground='white').pack(anchor='w')
        tk.Checkbutton(checks, text='Losowa kolejność przy starcie', variable=self.shuffle, fg='white', bg='#262626', selectcolor='#3a3a3a', activebackground='#262626', activeforeground='white').pack(anchor='w')
        tk.Checkbutton(checks, text='Automatycznie synchronizuj folder Dropbox', variable=self.auto_folder_sync, command=self._folder_sync_toggled, fg='white', bg='#262626', selectcolor='#3a3a3a', activebackground='#262626', activeforeground='white').pack(anchor='w')

        self._add_label('Folder Dropbox')
        folder_row = tk.Frame(self.sidebar, bg='#262626')
        folder_row.pack(fill='x', padx=pad, pady=(0, 8))
        self.folder_entry = tk.Entry(folder_row, textvariable=self.watch_folder, bg='#181818', fg='white', insertbackground='white', relief='flat')
        self.folder_entry.pack(side='left', fill='x', expand=True)
        self.folder_entry.bind('<Return>', lambda _e: self._watch_folder_changed())
        tk.Button(folder_row, text='Wybierz', command=self._choose_watch_folder).pack(side='right', padx=(6, 0))

        tk.Frame(self.sidebar, height=1, bg='#444444').pack(fill='x', padx=pad, pady=7)
        tk.Label(self.sidebar, text='ZDJĘCIA', font=('Segoe UI', 10, 'bold'), fg='#cfcfcf', bg='#262626').pack(anchor='w', padx=pad, pady=(5, 6))

        list_frame = tk.Frame(self.sidebar, bg='#262626')
        list_frame.pack(fill='both', expand=True, padx=pad)
        self.photo_list = tk.Listbox(list_frame, selectmode='extended', bg='#181818', fg='white', selectbackground='#505050', relief='flat', highlightthickness=1, highlightbackground='#3b3b3b')
        scroll = tk.Scrollbar(list_frame, command=self.photo_list.yview)
        self.photo_list.configure(yscrollcommand=scroll.set)
        self.photo_list.pack(side='left', fill='both', expand=True)
        scroll.pack(side='right', fill='y')

        row = tk.Frame(self.sidebar, bg='#262626')
        row.pack(fill='x', padx=pad, pady=8)
        tk.Button(row, text='Usuń zaznaczone', command=self._remove_selected).pack(side='left')
        tk.Button(row, text='Wyczyść', command=self._clear_images).pack(side='right')

        tk.Label(self.sidebar, text='Przeciągnij JPG/PNG/WebP bezpośrednio\nna okno programu.  SPACE = Start/Pauza', justify='left', fg='#a9a9a9', bg='#262626', font=('Segoe UI', 9)).pack(anchor='w', padx=pad, pady=(0, 13))

    def _add_label(self, text):
        tk.Label(self.sidebar, text=text, fg='#e7e7e7', bg='#262626', font=('Segoe UI', 9)).pack(anchor='w', padx=14, pady=(5, 3))

    def _add_scale(self, label, variable, lo, hi, step, suffix='', rebuild=False, on_change=None):
        outer = tk.Frame(self.sidebar, bg='#262626')
        outer.pack(fill='x', padx=14, pady=(5, 4))
        header = tk.Frame(outer, bg='#262626')
        header.pack(fill='x')
        tk.Label(header, text=label, fg='#e7e7e7', bg='#262626', font=('Segoe UI', 9)).pack(side='left')
        value_label = tk.Label(header, text='', fg='#bdbdbd', bg='#262626', font=('Segoe UI', 9))
        value_label.pack(side='right')

        def changed(_=None):
            try:
                val = variable.get()
                shown = int(val) if float(val).is_integer() else round(float(val), 1)
                value_label.config(text=f'{shown}{suffix}')
            except Exception:
                pass
            if rebuild:
                self._schedule_rebuild()
            if on_change is not None:
                on_change()

        scale = tk.Scale(outer, from_=lo, to=hi, resolution=step, orient='horizontal', variable=variable, command=changed, showvalue=False, length=255, bg='#262626', fg='white', troughcolor='#444444', highlightthickness=0)
        scale.pack(fill='x')
        changed()

    # ---------- Dropbox / watched folder ----------
    def _choose_watch_folder(self):
        initial = self.watch_folder.get().strip() or r'C:\Dropbox\PhotoScroller'
        chosen = filedialog.askdirectory(title='Wybierz folder Dropbox ze zdjęciami', initialdir=initial if os.path.isdir(initial) else None)
        if chosen:
            self.watch_folder.set(os.path.abspath(chosen))
            self.auto_folder_sync.set(True)
            self._folder_snapshot = None
            self._sync_from_watch_folder(force=True)
            self._save_settings()

    def _watch_folder_changed(self):
        folder = os.path.abspath(os.path.expanduser(self.watch_folder.get().strip()))
        self.watch_folder.set(folder)
        self._folder_snapshot = None
        self._sync_from_watch_folder(force=True)
        self._save_settings()

    def _folder_sync_toggled(self):
        self._folder_snapshot = None
        if self.auto_folder_sync.get():
            self._sync_from_watch_folder(force=True)
        self._save_settings()

    def _scan_watch_folder(self):
        folder = os.path.abspath(os.path.expanduser(self.watch_folder.get().strip()))
        if not folder or not os.path.isdir(folder):
            return []
        result = []
        try:
            for entry in os.scandir(folder):
                try:
                    if entry.is_file() and Path(entry.name).suffix.lower() in SUPPORTED:
                        result.append(os.path.abspath(entry.path))
                except OSError:
                    continue
        except OSError:
            return []
        return sorted(result, key=lambda p: os.path.basename(p).lower())

    def _sync_from_watch_folder(self, force=False):
        if not self.auto_folder_sync.get():
            return
        folder = os.path.abspath(os.path.expanduser(self.watch_folder.get().strip()))
        if not os.path.isdir(folder):
            if force:
                self.status.config(text='Folder Dropbox nie istnieje')
            return
        paths = self._scan_watch_folder()
        snapshot_parts = []
        for p in paths:
            try:
                st = os.stat(p)
                snapshot_parts.append((p, st.st_mtime_ns, st.st_size))
            except OSError:
                snapshot_parts.append((p, 0, 0))
        snapshot = tuple(snapshot_parts)
        if force or snapshot != self._folder_snapshot:
            self._folder_snapshot = snapshot
            if paths != self.image_paths:
                self.image_paths = paths
                self._refresh_photo_list()
                self._schedule_rebuild(40)
                self._save_settings()

    def _folder_watch_tick(self):
        try:
            self._sync_from_watch_folder(force=False)
        finally:
            self.after(2000, self._folder_watch_tick)

    # ---------- Gap handling ----------
    def _schedule_gap_apply(self):
        if self._gap_apply_job:
            try:
                self.after_cancel(self._gap_apply_job)
            except Exception:
                pass
        self._gap_apply_job = self.after(35, self._apply_gap_live)

    def _apply_gap_live(self):
        self._gap_apply_job = None
        if len(self.items) < 2:
            self._save_settings()
            return
        positioned = []
        for it in self.items:
            coords = self.canvas.coords(it['id'])
            if coords:
                positioned.append((coords[0], it))
        if len(positioned) < 2:
            return
        positioned.sort(key=lambda pair: pair[0])
        gap = int(self.gap.get())
        y = self.canvas.winfo_height() / 2
        x = positioned[0][0]
        self.canvas.coords(positioned[0][1]['id'], x, y)
        # Lay out from left to right using current visual order. This applies both
        # increases and decreases immediately, instead of waiting for a full loop.
        prev_it = positioned[0][1]
        prev_x = x
        for _, it in positioned[1:]:
            new_x = prev_x + prev_it['w'] + gap
            self.canvas.coords(it['id'], new_x, y)
            prev_x = new_x
            prev_it = it
        self._save_settings()

    # ---------- Images ----------
    def _add_images(self):
        paths = filedialog.askopenfilenames(title='Wybierz zdjęcia', filetypes=[('Obrazy', '*.jpg *.jpeg *.png *.bmp *.gif *.webp'), ('Wszystkie pliki', '*.*')])
        self._append_paths(paths)

    def _append_paths(self, paths):
        added = 0
        for raw in paths:
            p = os.path.abspath(os.path.expanduser(str(raw)))
            if os.path.isfile(p) and os.path.splitext(p)[1].lower() in SUPPORTED and p not in self.image_paths:
                self.image_paths.append(p)
                added += 1
        if added:
            self._refresh_photo_list()
            self._schedule_rebuild(50)
            self._save_settings()

    def _remove_selected(self):
        selected = list(self.photo_list.curselection())
        if not selected:
            return
        for i in reversed(selected):
            if 0 <= i < len(self.image_paths):
                del self.image_paths[i]
        self._refresh_photo_list()
        self._schedule_rebuild(20)
        self._save_settings()

    def _clear_images(self):
        self.running = False
        self._update_start_button()
        self.image_paths.clear()
        self.items.clear()
        self.canvas.delete('all')
        self._refresh_photo_list()
        self._show_hint()
        self._save_settings()

    def _refresh_photo_list(self):
        self.photo_list.delete(0, 'end')
        for p in self.image_paths:
            self.photo_list.insert('end', os.path.basename(p))
        suffix = ' • Dropbox' if self.auto_folder_sync.get() and os.path.isdir(os.path.expanduser(self.watch_folder.get().strip())) else ''
        self.status.config(text=f'{len(self.image_paths)} zdjęć{suffix}')

    def _make_framed_image(self, path, target_h):
        with Image.open(path) as im:
            photo = ImageOps.exif_transpose(im).convert('RGBA')

        style = self.frame_style.get()
        frame_px = max(0, int(target_h * 0.035)) if style != 'Bez ramki' else 0
        shadow_px = max(3, int(target_h * 0.018)) if style != 'Bez ramki' else 0
        content_h = max(20, target_h - 2 * frame_px - 2 * shadow_px)
        scale = content_h / max(1, photo.height)
        new_w = max(1, int(photo.width * scale))
        photo = photo.resize((new_w, content_h), Image.Resampling.LANCZOS)

        if frame_px:
            frame_color = (248, 248, 248, 255) if style == 'Biała ramka' else (20, 20, 20, 255)
            photo = ImageOps.expand(photo, border=frame_px, fill=frame_color)

            # subtle shadow around the framed photo
            shadow = Image.new('RGBA', (photo.width + shadow_px * 4, photo.height + shadow_px * 4), (0, 0, 0, 0))
            d = ImageDraw.Draw(shadow)
            d.rounded_rectangle((shadow_px, shadow_px, shadow_px + photo.width, shadow_px + photo.height), radius=max(2, frame_px // 3), fill=(0, 0, 0, 105))
            shadow.alpha_composite(photo, (0, 0))
            photo = shadow

        # User request: always 6 degrees to the left (counter-clockwise).
        rotated = photo.rotate(6, resample=Image.Resampling.BICUBIC, expand=True, fillcolor=(0, 0, 0, 0))
        return rotated

    def _rebuild(self):
        self._rebuild_job = None
        self.canvas.delete('all')
        self.items.clear()
        if not self.image_paths:
            self._show_hint()
            return

        cw = max(500, self.canvas.winfo_width())
        ch = max(300, self.canvas.winfo_height())
        target_h = max(90, int(ch * self.photo_height_pct.get() / 100))
        y = ch / 2
        x = cw + 30
        failed = 0

        paths = list(self.image_paths)
        if self.shuffle.get():
            import random
            random.shuffle(paths)

        for path in paths:
            try:
                frame = self._make_framed_image(path, target_h)
                tk_img = ImageTk.PhotoImage(frame)
                item_id = self.canvas.create_image(x, y, image=tk_img, anchor='w')
                self.items.append({'id': item_id, 'img': tk_img, 'w': frame.width, 'path': path})
                x += frame.width + int(self.gap.get())
            except Exception:
                failed += 1

        self.status.config(text=f'{len(self.items)} zdjęć' + (f' • {failed} pominięto' if failed else ''))
        if not self.items:
            self._show_hint('Nie udało się wczytać zdjęć.\nSprawdź, czy pliki nadal istnieją.')
        elif self.autostart.get() and not self.running:
            self.running = True
            self._update_start_button()

    def _schedule_rebuild(self, delay=150):
        if self._rebuild_job:
            try:
                self.after_cancel(self._rebuild_job)
            except Exception:
                pass
        self._rebuild_job = self.after(delay, self._rebuild)

    # ---------- Animation ----------
    def _toggle_run(self):
        if not self.image_paths:
            messagebox.showinfo('Brak zdjęć', 'Najpierw dodaj zdjęcia.')
            return
        self.running = not self.running
        self._last_tick = None
        self._update_start_button()
        self._save_settings()

    def _update_start_button(self):
        if hasattr(self, 'start_btn'):
            self.start_btn.config(text='❚❚ Pauza' if self.running else '▶ Start')

    def _animate(self):
        import time
        now = time.perf_counter()
        if self._last_tick is None:
            dt = 0.016
        else:
            dt = min(0.05, now - self._last_tick)
        self._last_tick = now

        if self.running and self.items:
            dx = -float(self.speed.get()) * dt
            for it in self.items:
                self.canvas.move(it['id'], dx, 0)

            # Recycle all images that have fully left the screen.
            for it in self.items:
                coords = self.canvas.coords(it['id'])
                if not coords:
                    continue
                x = coords[0]
                if x + it['w'] < 0:
                    right_edge = max(self.canvas.coords(other['id'])[0] + other['w'] for other in self.items if self.canvas.coords(other['id']))
                    self.canvas.coords(it['id'], right_edge + int(self.gap.get()), self.canvas.winfo_height() / 2)

        self.after(16, self._animate)

    # ---------- Presentation / monitors ----------
    def _refresh_monitors(self):
        self.monitors = []
        if get_monitors:
            try:
                self.monitors = list(get_monitors())
            except Exception:
                self.monitors = []
        if not self.monitors:
            class M:
                x = 0; y = 0
                width = self.winfo_screenwidth(); height = self.winfo_screenheight()
                is_primary = True
            self.monitors = [M()]

        values = []
        for i, m in enumerate(self.monitors, start=1):
            suffix = ' — główny' if getattr(m, 'is_primary', False) else ''
            values.append(f'Ekran {i}: {m.width}×{m.height}{suffix}')
        self.monitor_combo['values'] = values
        idx = min(max(0, int(self.monitor_index.get())), len(values) - 1)
        self.monitor_index.set(idx)
        self.monitor_combo.current(idx)

    def _monitor_changed(self, _event=None):
        self.monitor_index.set(max(0, self.monitor_combo.current()))
        self._save_settings()

    def _toggle_presentation(self):
        if self.presentation:
            self._exit_presentation()
        else:
            self._enter_presentation()

    def _enter_presentation(self):
        if not self.image_paths:
            messagebox.showinfo('Brak zdjęć', 'Najpierw dodaj zdjęcia.')
            return
        idx = min(max(0, self.monitor_index.get()), len(self.monitors) - 1)
        m = self.monitors[idx]
        self.presentation = True
        self.topbar.pack_forget()
        self.sidebar.pack_forget()
        self.main.pack_forget()
        self.main.pack(fill='both', expand=True)
        self.canvas.pack_forget()
        self.canvas.pack(fill='both', expand=True)

        # Put window on selected monitor first, then remove window chrome.
        self.overrideredirect(False)
        self.attributes('-fullscreen', False)
        self.geometry(f'{m.width}x{m.height}+{m.x}+{m.y}')
        self.update_idletasks()
        self.overrideredirect(True)
        self.geometry(f'{m.width}x{m.height}+{m.x}+{m.y}')
        self.lift()
        try:
            self.focus_force()
        except Exception:
            pass
        self._apply_background()
        self._schedule_rebuild(120)

    def _exit_presentation(self):
        if not self.presentation:
            return
        self.presentation = False
        self.overrideredirect(False)
        try:
            self.attributes('-fullscreen', False)
        except Exception:
            pass
        self.main.pack_forget()
        self.topbar.pack(side='top', fill='x')
        self.main.pack(fill='both', expand=True)
        self.sidebar.pack(side='left', fill='y')
        self.canvas.pack_forget()
        self.canvas.pack(side='right', fill='both', expand=True)
        self.geometry('1220x760')
        self._apply_background()
        self._schedule_rebuild(120)

    # ---------- Background ----------
    def _background_changed(self):
        self._apply_background()
        self._save_settings()

    def _apply_background(self):
        mode = self.background.get()
        colors = {
            'Czarne': '#000000',
            'Białe': '#ffffff',
            'Ciemnoszare': '#202020',
            'Zielone (chroma)': '#00b140',
            'Przezroczyste': TRANSPARENT_KEY,
        }
        color = colors.get(mode, '#000000')
        if hasattr(self, 'canvas'):
            self.canvas.configure(bg=color)

        # Windows supports a transparent color key for top-level windows.
        try:
            if sys.platform.startswith('win'):
                if mode == 'Przezroczyste':
                    self.wm_attributes('-transparentcolor', TRANSPARENT_KEY)
                else:
                    self.wm_attributes('-transparentcolor', '')
        except tk.TclError:
            # On systems without this capability, fall back to the selected key color.
            pass

    # ---------- DnD ----------
    def _setup_dnd(self):
        if not DND_AVAILABLE:
            return
        try:
            self.drop_target_register(DND_FILES)
            self.dnd_bind('<<Drop>>', self._on_drop)
        except Exception:
            pass

    def _on_drop(self, event):
        try:
            paths = self.tk.splitlist(event.data)
        except Exception:
            paths = [event.data]
        self._append_paths(paths)

    # ---------- Persistence ----------
    def _load_settings(self):
        p = config_path()
        if not p.exists():
            return
        try:
            data = json.loads(p.read_text(encoding='utf-8'))
            self._saved_data = data
            self.speed.set(float(data.get('speed', self.speed.get())))
            self.photo_height_pct.set(int(data.get('photo_height_pct', self.photo_height_pct.get())))
            self.gap.set(int(data.get('gap', self.gap.get())))
            self.background.set(data.get('background', self.background.get()))
            self.monitor_index.set(int(data.get('monitor_index', 0)))
            self.autostart.set(bool(data.get('autostart', False)))
            self.shuffle.set(bool(data.get('shuffle', False)))
            self.frame_style.set(data.get('frame_style', self.frame_style.get()))
            self.watch_folder.set(data.get('watch_folder', self.watch_folder.get()))
            self.auto_folder_sync.set(bool(data.get('auto_folder_sync', True)))
        except Exception:
            self._saved_data = {}

    def _restore_images(self):
        if self.auto_folder_sync.get() and os.path.isdir(os.path.expanduser(self.watch_folder.get().strip())):
            self._sync_from_watch_folder(force=True)
            return
        data = getattr(self, '_saved_data', {})
        paths = [p for p in data.get('images', []) if os.path.isfile(p) and os.path.splitext(p)[1].lower() in SUPPORTED]
        self.image_paths = list(dict.fromkeys(paths))
        self._refresh_photo_list()
        if self.image_paths:
            self._schedule_rebuild(20)

    def _save_settings(self):
        data = {
            'speed': float(self.speed.get()),
            'photo_height_pct': int(self.photo_height_pct.get()),
            'gap': int(self.gap.get()),
            'background': self.background.get(),
            'monitor_index': int(self.monitor_index.get()),
            'autostart': bool(self.autostart.get()),
            'shuffle': bool(self.shuffle.get()),
            'frame_style': self.frame_style.get(),
            'watch_folder': self.watch_folder.get(),
            'auto_folder_sync': bool(self.auto_folder_sync.get()),
            'images': self.image_paths,
        }
        try:
            config_path().write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        except Exception:
            pass

    # ---------- Misc ----------
    def _on_canvas_resize(self, event):
        size = (event.width, event.height)
        old = self._last_canvas_size
        self._last_canvas_size = size
        if abs(size[0] - old[0]) > 60 or abs(size[1] - old[1]) > 60:
            if self.image_paths:
                self._schedule_rebuild(180)
            elif self._drag_hint_id:
                self.canvas.coords(self._drag_hint_id, event.width / 2, event.height / 2)

    def _show_hint(self, text=None):
        self.canvas.delete('all')
        text = text or ('Wrzuć zdjęcia do folderu Dropbox\nlub przeciągnij je tutaj\n\nZdjęcia będą w ramkach, pochylone 6° w lewo\ni przesuwane z prawej do lewej w nieskończonej pętli.')
        self._drag_hint_id = self.canvas.create_text(max(1, self.canvas.winfo_width())/2, max(1, self.canvas.winfo_height())/2, text=text, fill='#bcbcbc', font=('Segoe UI', 16), justify='center')

    def _on_close(self):
        self._save_settings()
        self.destroy()


if __name__ == '__main__':
    try:
        app = PhotoScrollerV3()
        app.mainloop()
    except Exception as exc:
        try:
            root = tk.Tk(); root.withdraw()
            messagebox.showerror('Photo Scroller V3', f'Błąd programu:\n{exc}')
        except Exception:
            print(exc)
        sys.exit(1)
