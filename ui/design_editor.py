import os
import json
import uuid
import tkinter as tk
from tkinter import filedialog, colorchooser, messagebox
from PIL import Image, ImageTk, ImageDraw, ImageFont
import customtkinter as ctk

import db
from config import IMAGES_DIR


# ---------- Единственный шаблон ----------
TEMPLATE = {
    "label": "Футболка классическая",
    "w": 500, "h": 600,
    "print_area": (150, 180, 350, 480),
}


# ---------- Ограничения ----------
MAX_TEXT_LEN = 50
MAX_NAME_LEN = 100


# ---------- Палитры ----------
PRODUCT_PALETTE = [
    ("Белый",        "#fbfbfb"),
    ("Меланж",       "#bcbcbc"),
    ("Серый",        "#9b978e"),
    ("Графит",       "#444444"),
    ("Чёрный",       "#272f34"),
    ("Бежевый",      "#d0c79c"),
    ("Хаки",         "#4d4c3c"),
    ("Коричневый",   "#47362b"),
    ("Красный",      "#ec0c0c"),
    ("Бордовый",     "#5b2530"),
    ("Оранжевый",    "#ffa500"),
    ("Жёлтый",       "#ffde1b"),
    ("Салатовый",    "#c1db3c"),
    ("Зелёный",      "#60a24d"),
    ("Тёмно-зелёный","#032D23"),
    ("Голубой",      "#a7e6f3"),
    ("Синий",        "#296DC1"),
    ("Тёмно-синий",  "#090069"),
    ("Фиолетовый",   "#800080"),
    ("Розовый",      "#f6b4a7"),
    ("Малиновый",    "#b6326d"),
]

BRUSH_PALETTE = [
    "#000000", "#ffffff", "#9b978e", "#444444",
    "#ec0c0c", "#ff7f50", "#ffa500", "#ffde1b",
    "#c1db3c", "#60a24d", "#032D23", "#8dc4b6",
    "#a7e6f3", "#296DC1", "#090069", "#800080",
    "#d0a2c7", "#f6b4a7", "#b6326d", "#47362b",
]


# ============================================================
# Диалог с ограничением символов
# ============================================================
class LimitedInputDialog(ctk.CTkToplevel):
    def __init__(self, parent, title, prompt, initial="", max_len=50):
        super().__init__(parent)
        self.title(title)
        self.geometry("420x200")
        self.resizable(False, False)
        self.max_len = max_len
        self.result = None

        ctk.CTkLabel(self, text=prompt,
                     font=ctk.CTkFont(size=13)).pack(
            padx=20, pady=(20, 6), anchor="w")

        self._var = tk.StringVar(value=initial)
        self.entry = ctk.CTkEntry(self, width=360, textvariable=self._var)
        self.entry.pack(padx=20)
        self.entry.focus_set()
        self.entry.icursor("end")

        self.counter = ctk.CTkLabel(self, text=f"{len(initial)}/{max_len}",
                                    text_color="#888",
                                    font=ctk.CTkFont(size=11))
        self.counter.pack(padx=20, anchor="e", pady=(2, 0))

        self._var.trace_add("write", self._on_change)

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(pady=14)
        ctk.CTkButton(btns, text="OK", command=self._ok, width=110).pack(
            side="left", padx=6)
        ctk.CTkButton(btns, text="Отмена", command=self._cancel, width=110,
                      fg_color="#555").pack(side="left", padx=6)

        self.bind("<Return>", lambda e: self._ok())
        self.bind("<Escape>", lambda e: self._cancel())
        self.grab_set()

    def _on_change(self, *args):
        val = self._var.get()
        if len(val) > self.max_len:
            self._var.set(val[:self.max_len])
            self.entry.icursor(self.max_len)
        self.counter.configure(text=f"{len(self._var.get())}/{self.max_len}")

    def _ok(self):
        self.result = self._var.get().strip()
        self.destroy()

    def _cancel(self):
        self.result = None
        self.destroy()


# ============================================================
# РЕДАКТОР
# ============================================================
class DesignEditor(ctk.CTkFrame):
    """Редактор дизайна: один шаблон — классическая футболка."""

    def __init__(self, master, design_id=None):
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.design_id = design_id
        self.objects = []
        self.selected = None
        self.history = []
        self.redo_stack = []
        self._dragging = None
        self._drag_offset = (0, 0)
        self._scale_factor = 1.0
        self._origin = (0, 0)
        self._print_area = (0, 0, 0, 0)

        self._drawing_mode = False
        self._brush_color = "#000000"
        self._brush_width = 6
        self._strokes = []
        self._current_stroke = None

        self.product_color = "#fbfbfb"

        self._build_toolbar()
        self._build_canvas()
        self._build_inspector()

        if design_id:
            self._load_design(design_id)
        else:
            self.after(50, self._first_draw)

    def _first_draw(self):
        self._redraw()
        self._snapshot()

    # ============================================================
    # UI — ТУЛБАР
    # ============================================================
    def _build_toolbar(self):
        bar = ctk.CTkScrollableFrame(self, width=230)
        bar.grid(row=0, column=0, sticky="nsw", padx=(0, 6), pady=4)

        ctk.CTkLabel(bar, text="🎨 Редактор",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(6, 8))

        ctk.CTkButton(bar, text="+ Фото",
                      command=self.add_image).pack(fill="x", padx=8, pady=3)
        ctk.CTkButton(bar, text="+ Текст",
                      command=self.add_text).pack(fill="x", padx=8, pady=3)

        # ---------- ЦВЕТ ИЗДЕЛИЯ ----------
        self._build_product_color_picker(bar)

        # ---------- КИСТЬ ----------
        self.brush_btn = ctk.CTkButton(bar, text="✏ Кисть: ВЫКЛ",
                                       command=self._toggle_draw_mode,
                                       fg_color="#555")
        self.brush_btn.pack(fill="x", padx=8, pady=(12, 4))

        ctk.CTkLabel(bar, text="Цвет кисти",
                     font=ctk.CTkFont(size=12, weight="bold")).pack(pady=(4, 2))
        self._build_brush_palette(bar)

        ctk.CTkLabel(bar, text="Толщина кисти").pack(pady=(8, 0))
        self.brush_width_slider = ctk.CTkSlider(
            bar, from_=1, to=40, command=self._set_brush_width)
        self.brush_width_slider.set(self._brush_width)
        self.brush_width_slider.pack(fill="x", padx=8, pady=4)

        # ---------- Слои ----------



        ctk.CTkButton(bar, text="↶ Undo", command=self.undo,
                      fg_color="#444").pack(fill="x", padx=8, pady=(10, 2))
        ctk.CTkButton(bar, text="↷ Redo", command=self.redo,
                      fg_color="#444").pack(fill="x", padx=8, pady=2)

        ctk.CTkButton(bar, text="💾 Сохранить", command=self.save,
                      fg_color="green").pack(fill="x", padx=8, pady=(14, 4))
        ctk.CTkButton(bar, text="📤 Экспорт PNG",
                      command=self.export_png).pack(fill="x", padx=8, pady=(4, 10))

    def _build_product_color_picker(self, parent):
        ctk.CTkLabel(parent, text="Цвет изделия",
                     font=ctk.CTkFont(size=12, weight="bold")).pack(pady=(10, 2))

        grid = ctk.CTkFrame(parent, fg_color="transparent")
        grid.pack(fill="x", padx=8, pady=2)

        cols = 7
        for i, (name, hex_) in enumerate(PRODUCT_PALETTE):
            r, c = divmod(i, cols)
            btn = ctk.CTkButton(
                grid, text="", width=24, height=24,
                fg_color=hex_, hover_color=hex_,
                corner_radius=4, border_width=1, border_color="#555",
                command=lambda h=hex_: self._set_product_color(h),
            )
            btn.grid(row=r, column=c, padx=2, pady=2)
            btn._tooltip_name = name

        ctk.CTkButton(
            parent, text="🎨 Свой цвет изделия",
            command=self._pick_custom_product_color,
        ).pack(fill="x", padx=8, pady=(6, 2))

        self.product_color_preview = ctk.CTkFrame(
            parent, height=22, fg_color=self.product_color, corner_radius=4,
            border_width=1, border_color="#555")
        self.product_color_preview.pack(fill="x", padx=8, pady=(2, 4))

    def _build_brush_palette(self, parent):
        self.brush_color_preview = ctk.CTkFrame(
            parent, height=20, fg_color=self._brush_color, corner_radius=4,
            border_width=1, border_color="#555")
        self.brush_color_preview.pack(fill="x", padx=8, pady=(0, 4))

        grid = ctk.CTkFrame(parent, fg_color="transparent")
        grid.pack(fill="x", padx=8, pady=2)

        cols = 5
        for i, hex_ in enumerate(BRUSH_PALETTE):
            r, c = divmod(i, cols)
            btn = ctk.CTkButton(
                grid, text="", width=26, height=26,
                fg_color=hex_, hover_color=hex_,
                corner_radius=4, border_width=1, border_color="#555",
                command=lambda h=hex_: self._set_brush_color(h),
            )
            btn.grid(row=r, column=c, padx=2, pady=2)

        ctk.CTkButton(parent, text="🎨 Свой цвет кисти",
                      command=self._pick_brush_color).pack(
            fill="x", padx=8, pady=(6, 2))

    # ============================================================
    # UI — ХОЛСТ И ИНСПЕКТОР
    # ============================================================
    def _build_canvas(self):
        wrap = ctk.CTkFrame(self)
        wrap.grid(row=0, column=1, sticky="nsew", padx=6, pady=4)

        self.canvas = tk.Canvas(wrap, bg="#1e1e1e", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.canvas.bind("<Button-1>", self._on_mouse_down)
        self.canvas.bind("<B1-Motion>", self._on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_mouse_up)
        self.canvas.bind("<MouseWheel>", self._on_wheel)
        self.canvas.bind("<Configure>", lambda e: self._redraw())

    def _build_inspector(self):
        insp = ctk.CTkFrame(self, width=200)
        insp.grid(row=0, column=2, sticky="nse", padx=(6, 0), pady=4)
        insp.grid_propagate(False)

        ctk.CTkLabel(insp, text="Свойства",
                     font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(12, 8))

        self.prop_info = ctk.CTkLabel(insp, text="Ничего не выбрано",
                                      justify="left", wraplength=180)
        self.prop_info.pack(padx=8, pady=4, anchor="w")

        ctk.CTkLabel(insp, text="Масштаб %").pack(anchor="w", padx=8, pady=(10, 0))
        self.scale_slider = ctk.CTkSlider(insp, from_=10, to=300,
                                          command=self._on_scale)
        self.scale_slider.set(100)
        self.scale_slider.pack(fill="x", padx=8)

        ctk.CTkButton(insp, text="🎨 Цвет текста",
                      command=self._change_text_color).pack(fill="x", padx=8, pady=(12, 2))
        ctk.CTkButton(insp, text="✏ Изменить текст",
                      command=self._edit_text).pack(fill="x", padx=8, pady=2)
        ctk.CTkButton(insp, text="🗑 Удалить", fg_color="#a33",
                      command=self._delete_selected).pack(fill="x", padx=8, pady=(12, 2))

    # ============================================================
    # ЦВЕТА
    # ============================================================
    def _set_product_color(self, hex_):
        self.product_color = hex_
        self.product_color_preview.configure(fg_color=hex_)
        self._redraw()

    def _pick_custom_product_color(self):
        rgb, hex_ = colorchooser.askcolor(color=self.product_color,
                                          title="Цвет изделия")
        if hex_:
            self._set_product_color(hex_)

    def _set_brush_color(self, hex_):
        self._brush_color = hex_
        self.brush_color_preview.configure(fg_color=hex_)

    def _pick_brush_color(self):
        rgb, hex_ = colorchooser.askcolor(color=self._brush_color,
                                          title="Цвет кисти")
        if hex_:
            self._set_brush_color(hex_)

    def _set_brush_width(self, value):
        self._brush_width = int(value)

    # ============================================================
    # ОТРИСОВКА
    # ============================================================
    def _redraw(self):
        self.canvas.delete("all")
        w = self.canvas.winfo_width() or 600
        h = self.canvas.winfo_height() or 700
        if w < 50 or h < 50:
            return

        tpl = TEMPLATE
        self._scale_factor = min(w / (tpl["w"] + 60), h / (tpl["h"] + 60))
        cx = w / 2
        cy = h / 2
        self._origin = (cx, cy)

        self._draw_tshirt(cx, cy, tpl, self.product_color)

        x1, y1, x2, y2 = tpl["print_area"]
        self._print_area = (
            cx + (x1 - tpl["w"] / 2) * self._scale_factor,
            cy + (y1 - tpl["h"] / 2) * self._scale_factor,
            cx + (x2 - tpl["w"] / 2) * self._scale_factor,
            cy + (y2 - tpl["h"] / 2) * self._scale_factor,
        )

        if self._drawing_mode:
            self._highlight_print_area()

        for obj in sorted(self.objects, key=lambda o: o.get("z", 0)):
            obj["_tk_id"] = self._render_object(obj)

        self._refresh_layers()
        self._update_inspector()

    def _draw_tshirt(self, cx, cy, tpl, color):
        sf = self._scale_factor
        w = tpl["w"] * sf
        h = tpl["h"] * sf
        x = cx - w / 2
        y = cy - h / 2

        # Левый рукав
        self.canvas.create_polygon(
            x + w * 0.15, y + h * 0.10,
            x - w * 0.02, y + h * 0.25,
            x + w * 0.08, y + h * 0.40,
            x + w * 0.22, y + h * 0.20,
            fill=color, outline="#888", width=2)

        # Правый рукав
        self.canvas.create_polygon(
            x + w * 0.85, y + h * 0.10,
            x + w * 1.02, y + h * 0.25,
            x + w * 0.92, y + h * 0.40,
            x + w * 0.78, y + h * 0.20,
            fill=color, outline="#888", width=2)

        # Тело
        body_pts = [
            x + w * 0.25, y + h * 0.05,
            x + w * 0.75, y + h * 0.05,
            x + w * 0.85, y + h * 0.20,
            x + w * 0.80, y + h * 0.95,
            x + w * 0.20, y + h * 0.95,
            x + w * 0.15, y + h * 0.20,
        ]
        self.canvas.create_polygon(body_pts, fill=color, outline="#888",
                                   width=2)

        # Горловина
        self.canvas.create_oval(cx - w * 0.10, y + h * 0.02,
                                cx + w * 0.10, y + h * 0.12,
                                fill="#1e1e1e", outline="#888")

    def _render_object(self, obj):
        sf = self._scale_factor
        cx, cy = self._origin
        tpl = TEMPLATE
        ox = cx + (obj["x"] - tpl["w"] / 2) * sf
        oy = cy + (obj["y"] - tpl["h"] / 2) * sf

        if obj["type"] == "image":
            try:
                img = Image.open(obj["path"]).convert("RGBA")
            except Exception:
                return None

            new_w = max(10, int(obj["w"] * obj.get("scale", 1) * sf))
            new_h = max(10, int(obj["h"] * obj.get("scale", 1) * sf))
            img = img.resize((new_w, new_h), Image.LANCZOS)

            mask = Image.new("L", (new_w, new_h), 0)
            md = ImageDraw.Draw(mask)
            left = ox - new_w / 2
            top = oy - new_h / 2
            for poly in self._tshirt_polygons():
                shifted = [(px - left, py - top) for (px, py) in poly]
                md.polygon(shifted, fill=255)

            r, g, b, a = img.split()
            a = Image.composite(a, Image.new("L", (new_w, new_h), 0), mask)
            img = Image.merge("RGBA", (r, g, b, a))

            obj["_photo"] = ImageTk.PhotoImage(img)
            return self.canvas.create_image(
                ox, oy, image=obj["_photo"],
                tags=("obj", f"obj_{id(obj)}"))
        else:
            font_size = max(8, int(obj.get("size", 24) * obj.get("scale", 1) * sf))
            return self.canvas.create_text(
                ox, oy, text=obj["text"], fill=obj.get("color", "#000"),
                font=(obj.get("font", "Arial"), font_size),
                tags=("obj", f"obj_{id(obj)}"))

    # ============================================================
    # СИЛУЭТ
    # ============================================================
    def _tshirt_polygons(self):
        cx, cy = self._origin
        sf = self._scale_factor
        tpl = TEMPLATE
        w = tpl["w"] * sf
        h = tpl["h"] * sf
        x = cx - w / 2
        y = cy - h / 2

        left_sleeve = [
            (x + w * 0.15, y + h * 0.10),
            (x - w * 0.02, y + h * 0.25),
            (x + w * 0.08, y + h * 0.40),
            (x + w * 0.22, y + h * 0.20),
        ]
        right_sleeve = [
            (x + w * 0.85, y + h * 0.10),
            (x + w * 1.02, y + h * 0.25),
            (x + w * 0.92, y + h * 0.40),
            (x + w * 0.78, y + h * 0.20),
        ]
        body = [
            (x + w * 0.25, y + h * 0.05),
            (x + w * 0.75, y + h * 0.05),
            (x + w * 0.85, y + h * 0.20),
            (x + w * 0.80, y + h * 0.95),
            (x + w * 0.20, y + h * 0.95),
            (x + w * 0.15, y + h * 0.20),
        ]
        return [body, left_sleeve, right_sleeve]

    def _point_in_polygon(self, x, y, poly):
        n = len(poly)
        inside = False
        j = n - 1
        for i in range(n):
            xi, yi = poly[i]
            xj, yj = poly[j]
            if ((yi > y) != (yj > y)) and \
               (x < (xj - xi) * (y - yi) / (yj - yi + 1e-9) + xi):
                inside = not inside
            j = i
        return inside

    def _in_tshirt(self, x, y):
        for poly in self._tshirt_polygons():
            if self._point_in_polygon(x, y, poly):
                return True
        return False

    def _clamp_to_tshirt(self, x, y):
        if self._in_tshirt(x, y):
            return (x, y)
        best = None
        best_d2 = float("inf")
        for poly in self._tshirt_polygons():
            n = len(poly)
            for i in range(n):
                x1, y1 = poly[i]
                x2, y2 = poly[(i + 1) % n]
                dx, dy = x2 - x1, y2 - y1
                if dx == 0 and dy == 0:
                    px, py = x1, y1
                else:
                    t = ((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy)
                    t = max(0.0, min(1.0, t))
                    px, py = x1 + t * dx, y1 + t * dy
                d2 = (px - x) ** 2 + (py - y) ** 2
                if d2 < best_d2:
                    best_d2 = d2
                    best = (px, py)
        return best if best else (x, y)

    # ============================================================
    # ДОБАВЛЕНИЕ
    # ============================================================
    def add_image(self):
        path = filedialog.askopenfilename(
            filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp")])
        if not path:
            return
        os.makedirs(IMAGES_DIR, exist_ok=True)
        dst = os.path.join(IMAGES_DIR, f"design_{uuid.uuid4().hex}.png")
        Image.open(path).convert("RGBA").save(dst)

        tpl = TEMPLATE
        x1, y1, x2, y2 = tpl["print_area"]
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2

        self.objects.append({
            "type": "image", "path": dst,
            "x": cx, "y": cy, "w": 200, "h": 200,
            "scale": 1.0, "z": len(self.objects),
        })
        self._redraw()
        self._snapshot()

    def add_text(self):
        dlg = LimitedInputDialog(
            self, "Текст", f"Введите надпись (макс. {MAX_TEXT_LEN}):",
            initial="", max_len=MAX_TEXT_LEN)
        self.wait_window(dlg)
        text = dlg.result
        if not text:
            return

        tpl = TEMPLATE
        x1, y1, x2, y2 = tpl["print_area"]
        self.objects.append({
            "type": "text", "text": text,
            "x": (x1 + x2) / 2, "y": (y1 + y2) / 2,
            "w": 200, "h": 40,
            "scale": 1.0, "size": 28, "color": "#000000", "font": "Arial",
            "z": len(self.objects),
        })
        self._redraw()
        self._snapshot()

    # ============================================================
    # РИСОВАНИЕ
    # ============================================================
    def _toggle_draw_mode(self):
        self._drawing_mode = not self._drawing_mode
        if self._drawing_mode:
            self.brush_btn.configure(text="✏ Кисть: ВКЛ", fg_color="#1f6aa5")
            self.canvas.configure(cursor="pencil")
            self.selected = None
            self._update_inspector()
            self._highlight_print_area()
        else:
            self.brush_btn.configure(text="✏ Кисть: ВЫКЛ", fg_color="#555")
            self.canvas.configure(cursor="")
            self.canvas.delete("print_area_highlight")

    def _highlight_print_area(self):
        self.canvas.delete("print_area_highlight")
        for poly in self._tshirt_polygons():
            flat = [c for pt in poly for c in pt]
            self.canvas.create_polygon(
                *flat, outline="#1f6aa5", fill="",
                width=2, dash=(6, 4),
                tags=("print_area_highlight",))

    def _stroke_to_object(self):
        if not self._strokes:
            return
        xs = [p[0] for st in self._strokes for p in st]
        ys = [p[1] for st in self._strokes for p in st]
        pad = self._brush_width
        minx, maxx = min(xs) - pad, max(xs) + pad
        miny, maxy = min(ys) - pad, max(ys) + pad
        w = max(1, int(maxx - minx))
        h = max(1, int(maxy - miny))

        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        for st in self._strokes:
            pts = [(x - minx, y - miny) for (x, y) in st]
            if len(pts) == 1:
                x, y = pts[0]
                d.ellipse((x - self._brush_width / 2, y - self._brush_width / 2,
                           x + self._brush_width / 2, y + self._brush_width / 2),
                          fill=self._brush_color)
            else:
                d.line(pts, fill=self._brush_color, width=self._brush_width,
                       joint="curve")

        mask = Image.new("L", (w, h), 0)
        md = ImageDraw.Draw(mask)
        for poly in self._tshirt_polygons():
            shifted = [(px - minx, py - miny) for (px, py) in poly]
            md.polygon(shifted, fill=255)

        r, g, b, a = img.split()
        a = Image.composite(a, Image.new("L", (w, h), 0), mask)
        img = Image.merge("RGBA", (r, g, b, a))

        os.makedirs(IMAGES_DIR, exist_ok=True)
        path = os.path.join(IMAGES_DIR, f"draw_{uuid.uuid4().hex}.png")
        img.save(path)

        cx, cy = self._origin
        sf = self._scale_factor
        tpl = TEMPLATE
        obj_cx = (minx + maxx) / 2
        obj_cy = (miny + maxy) / 2
        tmpl_x = (obj_cx - cx) / sf + tpl["w"] / 2
        tmpl_y = (obj_cy - cy) / sf + tpl["h"] / 2
        tmpl_w = w / sf
        tmpl_h = h / sf

        self.objects.append({
            "type": "image", "path": path,
            "x": tmpl_x, "y": tmpl_y,
            "w": tmpl_w, "h": tmpl_h,
            "scale": 1.0, "z": len(self.objects),
        })

        self._strokes = []
        self._current_stroke = None
        self._redraw()
        self._snapshot()

    # ============================================================
    # МЫШЬ
    # ============================================================
    def _hit(self, ex, ey):
        items = self.canvas.find_overlapping(ex - 5, ey - 5, ex + 5, ey + 5)
        for it in reversed(items):
            tags = self.canvas.gettags(it)
            for obj in self.objects:
                if f"obj_{id(obj)}" in tags:
                    return obj
        return None

    def _on_mouse_down(self, e):
        if self._drawing_mode:
            if not self._in_tshirt(e.x, e.y):
                return
            self._current_stroke = [(e.x, e.y)]
            self._strokes.append(self._current_stroke)
            return

        obj = self._hit(e.x, e.y)
        self.selected = obj
        self._update_inspector()
        if obj:
            self._dragging = obj
            cx, cy = self._origin
            sf = self._scale_factor
            tpl = TEMPLATE
            ox = cx + (obj["x"] - tpl["w"] / 2) * sf
            oy = cy + (obj["y"] - tpl["h"] / 2) * sf
            self._drag_offset = (e.x - ox, e.y - oy)

    def _on_mouse_drag(self, e):
        if self._drawing_mode and self._current_stroke is not None:
            px, py = self._clamp_to_tshirt(e.x, e.y)
            self._current_stroke.append((px, py))
            if len(self._current_stroke) >= 2:
                x1, y1 = self._current_stroke[-2]
                x2, y2 = self._current_stroke[-1]
                self.canvas.create_line(
                    x1, y1, x2, y2,
                    fill=self._brush_color,
                    width=self._brush_width,
                    capstyle="round", smooth=True,
                    tags=("stroke",))
            return

        if not self._dragging:
            return
        obj = self._dragging
        cx, cy = self._origin
        sf = self._scale_factor
        tpl = TEMPLATE
        nx = (e.x - self._drag_offset[0] - cx) / sf + tpl["w"] / 2
        ny = (e.y - self._drag_offset[1] - cy) / sf + tpl["h"] / 2
        obj["x"], obj["y"] = nx, ny
        self._redraw()

    def _on_mouse_up(self, e):
        if self._drawing_mode:
            if self._strokes and len(self._strokes[-1]) >= 2:
                self._stroke_to_object()
            else:
                self._strokes = []
                self._current_stroke = None
            return

        if self._dragging:
            self._snapshot()
        self._dragging = None

    def _on_wheel(self, e):
        if not self.selected:
            return
        delta = 1.08 if e.delta > 0 else 0.92
        self.selected["scale"] = max(0.1, min(5.0,
                                              self.selected.get("scale", 1) * delta))
        self._redraw()
        self._snapshot()

    # ============================================================
    # СВОЙСТВА
    # ============================================================
    def _on_scale(self, value):
        if self.selected:
            self.selected["scale"] = float(value) / 100.0
            self._redraw()

    def _change_text_color(self):
        if not self.selected or self.selected["type"] != "text":
            return
        rgb, hex_ = colorchooser.askcolor(color=self.selected.get("color", "#000"))
        if hex_:
            self.selected["color"] = hex_
            self._redraw()
            self._snapshot()

    def _edit_text(self):
        if not self.selected or self.selected["type"] != "text":
            return
        dlg = LimitedInputDialog(
            self, "Текст", f"Изменить (макс. {MAX_TEXT_LEN}):",
            initial=self.selected["text"], max_len=MAX_TEXT_LEN)
        self.wait_window(dlg)
        t = dlg.result
        if t:
            self.selected["text"] = t
            self._redraw()
            self._snapshot()

    def _delete_selected(self):
        if self.selected:
            self.objects.remove(self.selected)
            self.selected = None
            self._redraw()
            self._snapshot()

    def _update_inspector(self):
        if not self.selected:
            self.prop_info.configure(text="Ничего не выбрано")
            return
        o = self.selected
        txt = (f"Тип: {o['type']}\n"
               f"X: {o['x']:.0f}\nY: {o['y']:.0f}\n"
               f"Масштаб: {o.get('scale', 1):.2f}")
        if o["type"] == "text":
            txt += f"\nТекст: {o['text'][:20]}"
        self.prop_info.configure(text=txt)
        self.scale_slider.set(o.get("scale", 1) * 100)

    # ============================================================
    # СЛОИ
    # ============================================================
    def _refresh_layers(self):
        self.layers_box.delete(0, "end")
        for obj in sorted(self.objects, key=lambda o: o.get("z", 0), reverse=True):
            if obj["type"] == "image":
                label = f"[img] {os.path.basename(obj['path'])}"
            else:
                label = f"[txt] {obj['text'][:18]}"
            self.layers_box.insert("end", label)

    def _on_layer_select(self, _):
        idx = self.layers_box.curselection()
        if not idx:
            return
        sorted_objs = sorted(self.objects, key=lambda o: o.get("z", 0), reverse=True)
        self.selected = sorted_objs[idx[0]]
        self._update_inspector()

    # ============================================================
    # UNDO / REDO
    # ============================================================
    def _state(self):
        return json.dumps([{k: v for k, v in o.items() if not k.startswith("_")}
                           for o in self.objects])

    def _snapshot(self):
        s = self._state()
        if not self.history or self.history[-1] != s:
            self.history.append(s)
            self.redo_stack.clear()

    def undo(self):
        if len(self.history) < 2:
            return
        self.redo_stack.append(self.history.pop())
        self._restore(self.history[-1])

    def redo(self):
        if not self.redo_stack:
            return
        s = self.redo_stack.pop()
        self.history.append(s)
        self._restore(s)

    def _restore(self, s):
        self.objects = []
        for o in json.loads(s):
            self.objects.append(o)
        self.selected = None
        self._redraw()

    # ============================================================
    # СОХРАНЕНИЕ / ЭКСПОРТ
    # ============================================================
    def _render_preview(self, path):
        tpl = TEMPLATE
        W, H = tpl["w"], tpl["h"]
        base = Image.new("RGB", (W, H), "#222")
        d = ImageDraw.Draw(base)

        x, y = 0, 0
        w, h = W, H

        left_sleeve = [
            (x + w * 0.15, y + h * 0.10),
            (x - w * 0.02, y + h * 0.25),
            (x + w * 0.08, y + h * 0.40),
            (x + w * 0.22, y + h * 0.20),
        ]
        right_sleeve = [
            (x + w * 0.85, y + h * 0.10),
            (x + w * 1.02, y + h * 0.25),
            (x + w * 0.92, y + h * 0.40),
            (x + w * 0.78, y + h * 0.20),
        ]
        body = [
            (x + w * 0.25, y + h * 0.05),
            (x + w * 0.75, y + h * 0.05),
            (x + w * 0.85, y + h * 0.20),
            (x + w * 0.80, y + h * 0.95),
            (x + w * 0.20, y + h * 0.95),
            (x + w * 0.15, y + h * 0.20),
        ]

        color = self.product_color

        d.polygon(left_sleeve, fill=color, outline="#888")
        d.polygon(right_sleeve, fill=color, outline="#888")
        d.polygon(body, fill=color, outline="#888")

        cx = W / 2
        d.ellipse((cx - w * 0.10, y + h * 0.02,
                   cx + w * 0.10, y + h * 0.12),
                  fill="#222", outline="#888")

        mask = Image.new("L", (W, H), 0)
        md = ImageDraw.Draw(mask)
        md.polygon(left_sleeve, fill=255)
        md.polygon(right_sleeve, fill=255)
        md.polygon(body, fill=255)

        for obj in sorted(self.objects, key=lambda o: o.get("z", 0)):
            layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))

            if obj["type"] == "image":
                try:
                    im = Image.open(obj["path"]).convert("RGBA")
                    sc = obj.get("scale", 1)
                    im = im.resize(
                        (max(1, int(obj["w"] * sc)),
                         max(1, int(obj["h"] * sc))),
                        Image.LANCZOS)
                    px = int(obj["x"] - im.width / 2)
                    py = int(obj["y"] - im.height / 2)
                    layer.paste(im, (px, py), im)
                except Exception:
                    continue
            else:
                try:
                    font = ImageFont.truetype(
                        "arial.ttf",
                        int(obj.get("size", 24) * obj.get("scale", 1)))
                except Exception:
                    font = ImageFont.load_default()
                ld = ImageDraw.Draw(layer)
                ld.text((obj["x"], obj["y"]), obj["text"],
                        fill=obj.get("color", "#000"), font=font, anchor="mm")

            r, g, b, a = layer.split()
            a = Image.composite(a, Image.new("L", (W, H), 0), mask)
            layer = Image.merge("RGBA", (r, g, b, a))
            base.paste(layer, (0, 0), layer)

        base.save(path)

    def save(self):
        dlg = LimitedInputDialog(
            self, "Сохранение", f"Название дизайна (макс. {MAX_NAME_LEN}):",
            initial="Мой дизайн", max_len=MAX_NAME_LEN)
        self.wait_window(dlg)
        name = dlg.result
        if not name:
            return

        preview_dir = os.path.join(IMAGES_DIR, "previews")
        os.makedirs(preview_dir, exist_ok=True)
        preview_path = os.path.join(preview_dir, f"preview_{uuid.uuid4().hex}.png")
        self._render_preview(preview_path)

        canvas_json = self._state()
        if self.design_id:
            db.update_design(self.design_id, name, self.product_color,
                             canvas_json, preview_path)
        else:
            self.design_id = db.add_design(
                name, "classic_tee", self.product_color,
                canvas_json, preview_path)
        messagebox.showinfo("Готово", f"Дизайн сохранён (id={self.design_id})")

    def export_png(self):
        path = filedialog.asksaveasfilename(defaultextension=".png",
                                            filetypes=[("PNG", "*.png")])
        if path:
            self._render_preview(path)
            messagebox.showinfo("Экспорт", f"Сохранено: {path}")

    def _load_design(self, did):
        d = db.get_design(did)
        if not d:
            return

        stored = d["product_color"] or "#fbfbfb"
        if not stored.startswith("#"):
            found = None
            for name, hex_ in PRODUCT_PALETTE:
                if name.lower() == stored.lower() or stored in hex_:
                    found = hex_
                    break
            stored = found or "#fbfbfb"
        self.product_color = stored
        self.product_color_preview.configure(fg_color=stored)

        self.objects = []
        for o in json.loads(d["canvas_json"] or "[]"):
            self.objects.append(o)
        self.after(50, self._first_draw)