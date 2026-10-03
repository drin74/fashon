import os
from tkinter import messagebox
from PIL import Image
import customtkinter as ctk
import db
from ui.design_editor import DesignEditor


class DesignsView(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        top = ctk.CTkFrame(self)
        top.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ctk.CTkLabel(top, text="Мои дизайны",
                     font=ctk.CTkFont(size=18, weight="bold")).pack(side="left", padx=12)
        ctk.CTkButton(top, text="+ Новый дизайн",
                      command=self.open_new).pack(side="right", padx=12, pady=8)

        self.list_frame = ctk.CTkScrollableFrame(self)
        self.list_frame.grid(row=1, column=0, sticky="nsew")
        self.list_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self.refresh()

    def refresh(self):
        for w in self.list_frame.winfo_children():
            w.destroy()
        for i, d in enumerate(db.get_designs()):
            self._card(d, i)

    def _card(self, d, idx):
        card = ctk.CTkFrame(self.list_frame, corner_radius=10)
        card.grid(row=idx // 3, column=idx % 3, padx=8, pady=8, sticky="nsew")

        if d.get("preview_path") and os.path.exists(d["preview_path"]):
            pil = Image.open(d["preview_path"])
            pil.thumbnail((200, 220))
            img = ctk.CTkImage(light_image=pil, dark_image=pil, size=pil.size)
            ctk.CTkLabel(card, image=img, text="").pack(pady=6)

        ctk.CTkLabel(card, text=d["name"],
                     font=ctk.CTkFont(size=14, weight="bold")).pack()
        ctk.CTkLabel(card, text=f"{d['template']} · {d['product_color']}").pack()

        btns = ctk.CTkFrame(card, fg_color="transparent")
        btns.pack(pady=6)
        ctk.CTkButton(btns, text="✏", width=40,
                      command=lambda did=d["id"]: self.open_edit(did)).pack(side="left", padx=2)
        ctk.CTkButton(btns, text="🗑", width=40, fg_color="#a33",
                      command=lambda did=d["id"]: self.delete(did)).pack(side="left", padx=2)

    def open_new(self):
        self._show_editor(None)

    def open_edit(self, did):
        self._show_editor(did)

    def _show_editor(self, did):
        win = ctk.CTkToplevel(self)
        win.title("Редактор дизайна")
        win.geometry("1200x800")
        editor = DesignEditor(win, design_id=did)
        editor.pack(fill="both", expand=True)
        win.grab_set()

    def delete(self, did):
        if messagebox.askyesno("Удалить", "Удалить дизайн?"):
            db.delete_design(did)
            self.refresh()