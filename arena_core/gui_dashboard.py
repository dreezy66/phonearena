try:
    from kivy.app import App
    from kivy.uix.label import Label
except ImportError:
    print("[GUI] Kivy not installed, fallback to terminal dashboard")

class DashboardApp(App):
    def build(self):
        return Label(text="PhoneArena GUI Dashboard")
