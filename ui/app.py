import customtkinter as ctk
from ui.models_view import ModelsView
from ui.palette_view import PaletteView
from ui.collections_view import CollectionsView
from ui.designs_view import DesignsView   # ← добавь импорт

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class FashionApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Fashion Designer")
        self.geometry("1200x750")

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Боковое меню
        sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_rowconfigure(5, weight=1)

        ctk.CTkLabel(sidebar, text="👗 Fashion\nDesigner",
                     font=ctk.CTkFont(size=20, weight="bold")).grid(
            row=0, column=0, padx=20, pady=30)

        self.btn_models = ctk.CTkButton(sidebar, text="Модели",
                                        command=lambda: self.show("models"))
        self.btn_models.grid(row=1, column=0, padx=20, pady=8, sticky="ew")

        self.btn_collections = ctk.CTkButton(sidebar, text="Коллекции",
                                             command=lambda: self.show("collections"))
        self.btn_collections.grid(row=2, column=0, padx=20, pady=8, sticky="ew")

        self.btn_palette = ctk.CTkButton(sidebar, text="Палитра цветов",
                                         command=lambda: self.show("palette"))
        self.btn_palette.grid(row=3, column=0, padx=20, pady=8, sticky="ew")

        # ↓ НОВАЯ КНОПКА
        self.btn_designs = ctk.CTkButton(sidebar, text="Мои дизайны",
                                         command=lambda: self.show("designs"))
        self.btn_designs.grid(row=4, column=0, padx=20, pady=8, sticky="ew")

        # Контейнер контента
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        self.views = {
            "models": ModelsView(self.container),
            "collections": CollectionsView(self.container),
            "palette": PaletteView(self.container),
            "designs": DesignsView(self.container),   # ← ЭТОЙ СТРОКИ НЕ ХВАТАЛО
        }
        for v in self.views.values():
            v.grid(row=0, column=0, sticky="nsew")

        self.show("models")

    def show(self, name):
        self.views[name].tkraise()
        if hasattr(self.views[name], "refresh"):
            self.views[name].refresh()