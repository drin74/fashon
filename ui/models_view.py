import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from PIL import Image
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.lib.pagesizes import A4

import db
from config import IMAGES_DIR, EXPORTS_DIR


# ---------- Лимиты символов ----------
LIMIT_SEARCH = 100
LIMIT_NAME = 150
LIMIT_CATEGORY = 50
LIMIT_SEASON = 30
LIMIT_COLOR = 7
LIMIT_FABRIC = 100
LIMIT_PRICE = 15
LIMIT_DESCRIPTION = 1000


# ---------- Хелперы ----------
def _limit_entry(parent, max_len, initial="", **kwargs):
    """CTkEntry с молчаливым ограничением по количеству символов."""
    var = tk.StringVar(value=str(initial or "")[:max_len])
    entry = ctk.CTkEntry(parent, textvariable=var, **kwargs)

    def on_write(*_):
        v = var.get()
        if len(v) > max_len:
            var.set(v[:max_len])
            entry.icursor(max_len)

    var.trace_add("write", on_write)
    return entry, var


def _limit_textbox(parent, max_len, initial="", **kwargs):
    """CTkTextbox с молчаливым ограничением по количеству символов."""
    tb = ctk.CTkTextbox(parent, **kwargs)
    if initial:
        tb.insert("1.0", str(initial)[:max_len])

    def check(event=None):
        content = tb.get("1.0", "end-1c")
        if len(content) > max_len:
            tb.delete("1.0", "end")
            tb.insert("1.0", content[:max_len])

    tb.bind("<KeyRelease>", check)
    tb.bind("<<Paste>>", lambda e: tb.after(10, check))
    return tb


# ---------- Вид ----------
class ModelsView(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self.selected_id = None

        # -------- Панель инструментов --------
        top = ctk.CTkFrame(self)
        top.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        top.grid_columnconfigure(1, weight=1)

        self.search_entry, self.search_var = _limit_entry(
            top, LIMIT_SEARCH, placeholder_text="Поиск...")
        self.search_entry.grid(row=0, column=0, padx=8, pady=8, sticky="ew")
        self.search_entry.bind("<KeyRelease>", lambda e: self.refresh())

        self.sort_var = ctk.StringVar(value="name")
        ctk.CTkOptionMenu(top, values=["name", "category", "season", "price", "created_at"],
                          variable=self.sort_var, command=lambda _: self.refresh(),
                          width=140).grid(row=0, column=1, padx=4)

        self.dir_var = ctk.StringVar(value="ASC")
        ctk.CTkOptionMenu(top, values=["ASC", "DESC"], variable=self.dir_var,
                          command=lambda _: self.refresh(), width=90).grid(row=0, column=2, padx=4)

        # ---- Кнопка-фильтр "Избранное" ----
        self.fav_var = ctk.BooleanVar(value=False)
        self.fav_btn = ctk.CTkButton(
            top, text="☆ Избранное: ВЫКЛ",
            command=self._toggle_fav_filter,
            fg_color="#444", hover_color="#555",
            text_color="#ffffff",
            width=180)
        self.fav_btn.grid(row=0, column=3, padx=8)

        ctk.CTkButton(top, text="+ Добавить", command=self.open_add).grid(
            row=0, column=4, padx=8)

        # -------- Список --------
        self.list_frame = ctk.CTkScrollableFrame(self)
        self.list_frame.grid(row=2, column=0, sticky="nsew")
        self.list_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self.refresh()

    # ================= Фильтр избранного =================
    def _toggle_fav_filter(self):
        self.fav_var.set(not self.fav_var.get())
        if self.fav_var.get():
            self.fav_btn.configure(
                text="★ Избранное: ВКЛ",
                fg_color="#1f6aa5",
                hover_color="#1a5a8f",
                text_color="#ffffff",
            )
        else:
            self.fav_btn.configure(
                text="☆ Избранное: ВЫКЛ",
                fg_color="#444",
                hover_color="#555",
                text_color="#ffffff",
            )
        self.refresh()

    # ================= CRUD =================
    def refresh(self):
        for w in self.list_frame.winfo_children():
            w.destroy()

        models = db.get_models(
            search=self.search_var.get().strip(),
            order_by=self.sort_var.get(),
            order_dir=self.dir_var.get(),
            only_fav=self.fav_var.get()
        )

        for i, m in enumerate(models):
            self._card(m, i)

    def _card(self, m, idx):
        card = ctk.CTkFrame(self.list_frame, corner_radius=10)
        card.grid(row=idx // 3, column=idx % 3, padx=8, pady=8, sticky="nsew")
        card.grid_columnconfigure(0, weight=1)

        img_path = m.get("image_path")
        if img_path and os.path.exists(img_path):
            pil = Image.open(img_path)
            pil.thumbnail((200, 200))
            img = ctk.CTkImage(light_image=pil, dark_image=pil, size=pil.size)
            ctk.CTkLabel(card, image=img, text="").grid(row=0, column=0, pady=6)
        else:
            ctk.CTkLabel(card, text="[нет фото]", height=80).grid(row=0, column=0, pady=6)

        fav_mark = "★ " if m["is_favorite"] else ""
        ctk.CTkLabel(card, text=f"{fav_mark}{m['name']}",
                     font=ctk.CTkFont(size=15, weight="bold")).grid(row=1, column=0)

        info = f"{m['category'] or '-'} · {m['season'] or '-'}\n{m['fabric'] or '-'} · {m['price'] or 0} ₽"
        ctk.CTkLabel(card, text=info, justify="center").grid(row=2, column=0)

        if m.get("color_hex"):
            try:
                swatch = ctk.CTkFrame(card, width=30, height=30,
                                      fg_color=m["color_hex"], corner_radius=15)
                swatch.grid(row=3, column=0, pady=4)
            except Exception:
                pass

        btns = ctk.CTkFrame(card, fg_color="transparent")
        btns.grid(row=4, column=0, pady=6)

        # ---- Кнопка ★ / ☆, контрастная на любом фоне ----
        fav_active = bool(m["is_favorite"])
        ctk.CTkButton(
            btns,
            text="★" if fav_active else "☆",
            width=40,
            fg_color="#f0a500" if fav_active else "#333",
            hover_color="#d18f00" if fav_active else "#444",
            text_color="#1a1a1a" if fav_active else "#cccccc",
            font=ctk.CTkFont(size=16),
            command=lambda mid=m["id"]: self._toggle_fav(mid),
        ).pack(side="left", padx=2)

        ctk.CTkButton(btns, text="✏", width=40,
                      command=lambda mid=m["id"]: self.open_edit(mid)).pack(side="left", padx=2)
        ctk.CTkButton(btns, text="📄", width=40,
                      command=lambda mid=m["id"]: self.export_pdf(mid)).pack(side="left", padx=2)
        ctk.CTkButton(btns, text="🗑", width=40, fg_color="#a33",
                      command=lambda mid=m["id"]: self._delete(mid)).pack(side="left", padx=2)

    def _toggle_fav(self, mid):
        db.toggle_favorite(mid)
        self.refresh()

    def _delete(self, mid):
        if messagebox.askyesno("Удалить", "Удалить модель?"):
            db.delete_model(mid)
            self.refresh()

    # ================= Форма =================
    def open_add(self):
        self._form(None)

    def open_edit(self, mid):
        self._form(db.get_model(mid))

    def _form(self, model):
        win = ctk.CTkToplevel(self)
        win.title("Модель")
        win.geometry("500x760")
        win.grab_set()

        fields = {}
        self._img_path = tk.StringVar(value=model["image_path"] if model else "")

        def add(label, key, default="", max_len=150):
            ctk.CTkLabel(win, text=label, anchor="w").pack(fill="x", padx=20, pady=(8, 0))
            entry, var = _limit_entry(win, max_len, initial=default)
            entry.pack(fill="x", padx=20)
            fields[key] = var

        add("Название *", "name",
            model["name"] if model else "", LIMIT_NAME)
        add("Категория (платье/брюки/...)", "category",
            model["category"] if model else "", LIMIT_CATEGORY)
        add("Сезон (лето/зима/демисезон)", "season",
            model["season"] if model else "", LIMIT_SEASON)
        add("Цвет (HEX #RRGGBB)", "color_hex",
            model["color_hex"] if model else "#000000", LIMIT_COLOR)
        add("Ткань", "fabric",
            model["fabric"] if model else "", LIMIT_FABRIC)
        add("Цена", "price",
            model["price"] if model else "", LIMIT_PRICE)

        ctk.CTkLabel(win, text="Описание").pack(fill="x", padx=20, pady=(8, 0))
        desc = _limit_textbox(
            win, LIMIT_DESCRIPTION,
            initial=model["description"] if model and model["description"] else "",
            height=90)
        desc.pack(fill="x", padx=20)

        collections = db.get_collections()
        coll_names = ["— нет —"] + [c["name"] for c in collections]
        ctk.CTkLabel(win, text="Коллекция").pack(fill="x", padx=20, pady=(8, 0))
        coll_menu = ctk.CTkOptionMenu(win, values=coll_names)
        coll_menu.pack(fill="x", padx=20)
        if model and model.get("collection_id"):
            for c in collections:
                if c["id"] == model["collection_id"]:
                    coll_menu.set(c["name"])

        img_label = ctk.CTkLabel(win, text="Изображение не выбрано")
        img_label.pack(pady=8)

        def choose_img():
            path = filedialog.askopenfilename(
                filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp")])
            if path:
                self._img_path.set(path)
                img_label.configure(text=os.path.basename(path))

        ctk.CTkButton(win, text="Выбрать изображение", command=choose_img).pack(pady=4)

        def save():
            name = fields["name"].get().strip()
            if not name:
                messagebox.showerror("Ошибка", "Название обязательно")
                return

            final_img = self._img_path.get()
            if final_img and not final_img.startswith(IMAGES_DIR):
                os.makedirs(IMAGES_DIR, exist_ok=True)
                dst = os.path.join(IMAGES_DIR, os.path.basename(final_img))
                try:
                    shutil.copy(final_img, dst)
                    final_img = dst
                except Exception:
                    pass

            coll_id = None
            if coll_menu.get() != "— нет —":
                for c in collections:
                    if c["name"] == coll_menu.get():
                        coll_id = c["id"]

            try:
                price = float(fields["price"].get() or 0)
            except ValueError:
                price = 0

            data = {
                "name": name[:LIMIT_NAME],
                "category": fields["category"].get()[:LIMIT_CATEGORY],
                "season": fields["season"].get()[:LIMIT_SEASON],
                "color_hex": fields["color_hex"].get()[:LIMIT_COLOR],
                "fabric": fields["fabric"].get()[:LIMIT_FABRIC],
                "price": price,
                "description": desc.get("1.0", "end").strip()[:LIMIT_DESCRIPTION],
                "image_path": final_img,
                "collection_id": coll_id,
                "is_favorite": model["is_favorite"] if model else 0,
            }

            if model:
                db.update_model(model["id"], data)
            else:
                db.add_model(data)
            win.destroy()
            self.refresh()

        ctk.CTkButton(win, text="Сохранить", command=save,
                      fg_color="green").pack(pady=16, fill="x", padx=20)

    # ================= Экспорт PDF =================
    def export_pdf(self, mid):
        m = db.get_model(mid)
        if not m:
            return
        path = os.path.join(EXPORTS_DIR, f"model_{mid}.pdf")
        c = pdfcanvas.Canvas(path, pagesize=A4)
        w, h = A4
        c.setFont("Helvetica-Bold", 18)
        c.drawString(50, h - 50, f"Модель: {m['name']}")

        c.setFont("Helvetica", 12)
        y = h - 90
        for label, key in [("Категория", "category"), ("Сезон", "season"),
                           ("Ткань", "fabric"), ("Цена", "price"),
                           ("Цвет", "color_hex")]:
            c.drawString(50, y, f"{label}: {m.get(key) or '-'}")
            y -= 20

        c.drawString(50, y, "Описание:")
        y -= 20
        text_obj = c.beginText(50, y)
        text_obj.setFont("Helvetica", 11)
        for line in (m.get("description") or "").split("\n"):
            text_obj.textLine(line[:90])
        c.drawText(text_obj)

        img = m.get("image_path")
        if img and os.path.exists(img):
            try:
                c.drawImage(img, 50, 80, width=200, height=200,
                            preserveAspectRatio=True, mask='auto')
            except Exception:
                pass

        c.save()
        messagebox.showinfo("Готово", f"PDF сохранён:\n{path}")