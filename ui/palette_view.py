import colorsys
import customtkinter as ctk
from tkinter import colorchooser


class PaletteView(ctk.CTkFrame):
    """Генератор гармоничных цветовых схем для дизайна одежды."""

    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self, text="🎨 Палитра и сочетания цветов",
                     font=ctk.CTkFont(size=20, weight="bold")).grid(
            row=0, column=0, pady=16)

        self.base_color = "#3498db"

        self.swatch = ctk.CTkFrame(self, width=120, height=60,
                                   fg_color=self.base_color, corner_radius=10)
        self.swatch.grid(row=1, column=0, pady=8)

        ctk.CTkButton(self, text="Выбрать базовый цвет",
                      command=self.pick_color).grid(row=2, column=0, pady=8)

        self.schemes_frame = ctk.CTkFrame(self)
        self.schemes_frame.grid(row=3, column=0, sticky="nsew", padx=20, pady=20)
        self.grid_rowconfigure(3, weight=1)

        self.render()

    def pick_color(self):
        rgb, hex_ = colorchooser.askcolor(color=self.base_color)
        if hex_:
            self.base_color = hex_
            self.swatch.configure(fg_color=hex_)
            self.render()

    def _hex_to_rgb(self, h):
        h = h.lstrip("#")
        return tuple(int(h[i:i+2], 16) / 255 for i in (0, 2, 4))

    def _rgb_to_hex(self, r, g, b):
        return "#{:02x}{:02x}{:02x}".format(
            int(r*255), int(g*255), int(b*255))

    def _shift_hue(self, hex_color, delta):
        r, g, b = self._hex_to_rgb(hex_color)
        h, l, s = colorsys.rgb_to_hls(r, g, b)
        h = (h + delta) % 1.0
        r, g, b = colorsys.hls_to_rgb(h, l, s)
        return self._rgb_to_hex(r, g, b)

    def render(self):
        for w in self.schemes_frame.winfo_children():
            w.destroy()

        base = self.base_color
        schemes = {
            "Комплиментарная": [base, self._shift_hue(base, 0.5)],
            "Триада": [base, self._shift_hue(base, 1/3), self._shift_hue(base, 2/3)],
            "Аналоговая": [self._shift_hue(base, -0.08), base,
                           self._shift_hue(base, 0.08)],
            "Тетрада": [base, self._shift_hue(base, 0.25),
                        self._shift_hue(base, 0.5), self._shift_hue(base, 0.75)],
        }

        for i, (name, colors) in enumerate(schemes.items()):
            row = ctk.CTkFrame(self.schemes_frame)
            row.grid(row=i, column=0, sticky="ew", pady=10, padx=10)
            row.grid_columnconfigure(1, weight=1)

            ctk.CTkLabel(row, text=name, width=140, anchor="w",
                         font=ctk.CTkFont(size=14, weight="bold")).grid(
                row=0, column=0, padx=8)

            swatches = ctk.CTkFrame(row, fg_color="transparent")
            swatches.grid(row=0, column=1, sticky="w")
            for c in colors:
                s = ctk.CTkFrame(swatches, width=70, height=50, corner_radius=8,
                                 fg_color=c)
                s.pack(side="left", padx=4)
                ctk.CTkLabel(swatches, text=c, font=ctk.CTkFont(size=10)).pack(
                    side="left", padx=(0, 10))