import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox
import db


# ---------- Лимиты ----------
LIMIT_NAME = 100
LIMIT_DESCRIPTION = 500

# ---------- Лимиты отображения в списке ----------
SHOW_NAME_LEN = 80          # макс. символов имени в карточке
SHOW_DESC_LEN = 300         # макс. символов описания в карточке


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


def _ellipsis(text, limit):
    """Обрезает текст и добавляет … если длиннее лимита."""
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit - 1].rstrip() + "…"


class CollectionsView(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # ---------- Форма создания ----------
        top = ctk.CTkFrame(self)
        top.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        top.grid_columnconfigure(0, weight=1)
        top.grid_columnconfigure(1, weight=2)

        self.name_entry, self.name_var = _limit_entry(
            top, LIMIT_NAME, placeholder_text="Название коллекции")
        self.name_entry.grid(row=0, column=0, padx=8, pady=8, sticky="ew")

        self.desc_entry, self.desc_var = _limit_entry(
            top, LIMIT_DESCRIPTION, placeholder_text="Описание")
        self.desc_entry.grid(row=0, column=1, padx=8, pady=8, sticky="ew")

        ctk.CTkButton(top, text="+ Добавить", command=self.add).grid(
            row=0, column=2, padx=8)

        # ---------- Список ----------
        self.list_frame = ctk.CTkScrollableFrame(self)
        self.list_frame.grid(row=2, column=0, sticky="nsew")
        self.list_frame.grid_columnconfigure(0, weight=1)

        self.refresh()

    def refresh(self):
        for w in self.list_frame.winfo_children():
            w.destroy()

        collections = db.get_collections()
        if not collections:
            ctk.CTkLabel(
                self.list_frame,
                text="Пока нет коллекций — добавь первую ↑",
                text_color="#888",
                font=ctk.CTkFont(size=13),
            ).pack(pady=20)
            return

        for c in collections:
            self._card(c)

    def _card(self, c):
        card = ctk.CTkFrame(self.list_frame, corner_radius=10)
        card.pack(fill="x", padx=6, pady=6)
        card.grid_columnconfigure(0, weight=1)

        # ---- Заголовок (имя + кнопки справа) ----
        head = ctk.CTkFrame(card, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=10, pady=(8, 2))
        head.grid_columnconfigure(0, weight=1)

        name_text = _ellipsis(c["name"], SHOW_NAME_LEN)
        ctk.CTkLabel(
            head, text=name_text, anchor="w",
            font=ctk.CTkFont(size=15, weight="bold"),
        ).grid(row=0, column=0, sticky="w")

        btns = ctk.CTkFrame(head, fg_color="transparent")
        btns.grid(row=0, column=1, sticky="e")

        ctk.CTkButton(
            btns, text="👁", width=36,
            fg_color="#444", hover_color="#555",
            command=lambda col=c: self.show_details(col),
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            btns, text="🗑", width=36, fg_color="#a33",
            hover_color="#922",
            command=lambda cid=c["id"]: self.delete(cid),
        ).pack(side="left", padx=2)

        # ---- Описание ----
        desc_text = _ellipsis(c["description"], SHOW_DESC_LEN)
        if desc_text:
            desc_label = ctk.CTkLabel(
                card, text=desc_text, anchor="w", justify="left",
                wraplength=900, text_color="#ccc",
            )
            desc_label.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 10))
            # Перенос по ширине окна
            card.bind("<Configure>",
                      lambda e, l=desc_label: l.configure(wraplength=max(200, e.width - 30)))

    # ================= Детали коллекции =================
    def show_details(self, c):
        win = ctk.CTkToplevel(self)
        win.title(f"Коллекция: {c['name'][:40]}")
        win.geometry("520x420")
        win.grab_set()

        ctk.CTkLabel(win, text="Название",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color="#888").pack(anchor="w", padx=20, pady=(16, 2))

        name_box = ctk.CTkTextbox(win, height=60, wrap="word")
        name_box.insert("1.0", c["name"])
        name_box.configure(state="disabled")
        name_box.pack(fill="x", padx=20)

        ctk.CTkLabel(win, text="Описание",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color="#888").pack(anchor="w", padx=20, pady=(12, 2))

        desc_box = ctk.CTkTextbox(win, height=200, wrap="word")
        desc_box.insert("1.0", c["description"] or "— (пусто) —")
        desc_box.configure(state="disabled")
        desc_box.pack(fill="both", expand=True, padx=20)

        ctk.CTkButton(win, text="Закрыть", command=win.destroy).pack(pady=12)

    # ================= Действия =================
    def add(self):
        name = self.name_var.get().strip()[:LIMIT_NAME]
        if not name:
            messagebox.showerror("Ошибка", "Введите название")
            return
        db.add_collection(name, self.desc_var.get().strip()[:LIMIT_DESCRIPTION])
        self.name_var.set("")
        self.desc_var.set("")
        self.refresh()

    def delete(self, cid):
        if messagebox.askyesno("Удалить", "Удалить коллекцию?"):
            db.delete_collection(cid)
            self.refresh()