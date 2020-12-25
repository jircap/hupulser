import tkinter as tk


class ToggleButton(tk.Frame):
    def __init__(self, parent, text, on=False, ind_width=8, ind_height=20, color_on='#00a000', color_off='#006000',
                 **kwargs):
        tk.Frame.__init__(self, parent)
        self._on = on
        self.color_on = color_on
        self.color_off = color_off
        if 'command' in kwargs.keys():
            self.button_callback = kwargs['command']  # save callback to button press
            kwargs.pop('command')
        else:
            self.button_callback = None
        self.button = tk.Button(self, text=text, relief=tk.GROOVE, command=self.__button_pres, **kwargs)  # set internal callback
        self.button.pack(side='left')
        self.indicator = tk.Canvas(self, width=ind_width, height=ind_height, bg='green4')
        self.indicator.pack(side='left')
        color = color_on if self._on else color_off
        self.indicator.config(bg=color)

    @property
    def on(self):
        return self._on

    @on.setter
    def on(self, value):
        self._on = value
        color = self.color_on if self._on else self.color_off
        relief = tk.SUNKEN if self._on else tk.GROOVE
        self.indicator.config(bg=color)
        self.button.config(relief=relief)

    def __button_pres(self):
        self.on = not self.on
        if self.button_callback is not None:
            self.button_callback()  # call external routine


class Indicator(tk.Frame):
    def __init__(self, parent, on=False, width=8, height=20, color_on='#00a000', color_off='#006000', **kwargs):
        tk.Frame.__init__(self, parent, **kwargs)
        self.canvas = tk.Canvas(self, width=width, height=height, bg=color_off)
        self.canvas.pack()
        self._on = on
        self.color_on = color_on
        self.color_off = color_off
        color = color_on if self._on else color_off
        self.canvas.config(bg=color)

    @property
    def on(self):
        return self._on

    @on.setter
    def on(self, value):
        self._on = value
        color = self.color_on if self._on else self.color_off
        self.canvas.config(bg=color)
