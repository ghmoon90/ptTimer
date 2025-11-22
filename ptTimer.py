import tkinter as tk
from tkinter import simpledialog, messagebox
import threading
import time
import sys

# --- Configuration Constants ---
DEFAULT_DESIGNATED_TIME_SECONDS = 10 * 60  # 10 minutes
DEFAULT_WARNING_TIME_SECONDS = 8 * 60      # 8 minutes
# TIMER_TICK_INTERVAL_S controls the background thread's tick rate
TIMER_TICK_INTERVAL_S = 0.1                

# --- Timer Logic (Background Thread) ---
class TimerThread(threading.Thread):
    """
    Manages the core timing logic in a separate thread to prevent GUI freezing.
    """
    def __init__(self, app_instance):
        super().__init__()
        self.app = app_instance
        self._stop_event = threading.Event()
        self._running = False
        self.elapsed_time = 0.0
        self.daemon = True # Allows the application to exit when the main thread dies

    def run(self):
        """The main loop for the thread, counting time."""
        while not self._stop_event.is_set():
            if self._running:
                self.elapsed_time += TIMER_TICK_INTERVAL_S
                # Request a UI update from the main thread
                # The 'after' call is safe and ensures thread-safe UI updates.
                self.app.after(1, self.app.update_display)
            
            time.sleep(TIMER_TICK_INTERVAL_S)

    def start_timer(self):
        """Starts or resumes the timer."""
        self._running = True

    def pause_timer(self):
        """Pauses the timer (used for 'Stop' functionality)."""
        self._running = False

    def reset_timer(self):
        """Enforces a pause, resets the time, and updates display."""
        self.pause_timer()
        self.elapsed_time = 0.0
        # Force a UI update to show 00:00
        self.app.after(1, self.app.update_display)

    def stop(self):
        """Stops the thread gracefully."""
        self._stop_event.set()

# --- Settings Dialog ---
class SettingsDialog(simpledialog.Dialog):
    """A custom dialog window to set the timer and warning times."""
    def __init__(self, parent, designated_sec, warning_sec):
        self.designated_sec = designated_sec
        self.warning_sec = warning_sec
        # Initialize the dialog
        super().__init__(parent, title="Timer Settings")
        
    def center_dialog_on_screen(self):
        """Calculates screen center and positions the dialog there."""
        # Ensure widget size is calculated before asking for its width/height
        self.update_idletasks()
        
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        window_width = self.winfo_width()
        window_height = self.winfo_height()
        
        # Calculate central position
        x = (screen_width // 2) - (window_width // 2)
        y = (screen_height // 2) - (window_height // 2)
        
        # Apply the new geometry, overriding the default parent-centering
        self.geometry(f'+{x}+{y}')

    def body(self, master):
        """Creates the input fields for designated and warning times."""
        # Removed premature call to center_dialog_on_screen
        
        tk.Label(master, text="Designated Time (MM:SS):").grid(row=0, sticky="w", padx=5, pady=5)
        tk.Label(master, text="Warning Time (MM:SS):").grid(row=1, sticky="w", padx=5, pady=5)

        # Designated Time Entry setup
        self.designated_minutes = tk.StringVar(value=str(self.designated_sec // 60).zfill(2))
        self.designated_seconds = tk.StringVar(value=str(self.designated_sec % 60).zfill(2))
        
        frame_designate = tk.Frame(master)
        # Store the Entry widget to return it for focus
        self.designated_minutes_entry = tk.Entry(frame_designate, width=4, textvariable=self.designated_minutes)
        self.designated_minutes_entry.pack(side=tk.LEFT) 
        tk.Label(frame_designate, text=":").pack(side=tk.LEFT)
        tk.Entry(frame_designate, width=4, textvariable=self.designated_seconds).pack(side=tk.LEFT)
        frame_designate.grid(row=0, column=1, sticky="ew")

        # Warning Time Entry setup
        self.warning_minutes = tk.StringVar(value=str(self.warning_sec // 60).zfill(2))
        self.warning_seconds = tk.StringVar(value=str(self.warning_sec % 60).zfill(2))

        frame_warning = tk.Frame(master)
        tk.Entry(frame_warning, width=4, textvariable=self.warning_minutes).pack(side=tk.LEFT)
        tk.Label(frame_warning, text=":").pack(side=tk.LEFT)
        tk.Entry(frame_warning, width=4, textvariable=self.warning_seconds).pack(side=tk.LEFT)
        frame_warning.grid(row=1, column=1, sticky="ew")

        # Return the Entry widget itself for focus
        return self.designated_minutes_entry 

    def buttonbox(self):
        """Adds standard buttons and schedules centering."""
        super().buttonbox()
        # Schedule centering to occur after the dialog initialization 
        # (which sets default geometry) is complete.
        self.after_idle(self.center_dialog_on_screen)

    def validate(self):
        """Validates the input fields."""
        try:
            d_min = int(self.designated_minutes.get() or 0)
            d_sec = int(self.designated_seconds.get() or 0)
            w_min = int(self.warning_minutes.get() or 0)
            w_sec = int(self.warning_seconds.get() or 0)

            if d_min < 0 or d_sec < 0 or w_min < 0 or w_sec < 0 or d_sec >= 60 or w_sec >= 60:
                raise ValueError("Time values must be positive and seconds must be less than 60.")

            self.result = {
                'designated': d_min * 60 + d_sec,
                'warning': w_min * 60 + w_sec,
            }
            # Also check that warning time is less than designated time
            if self.result['warning'] > self.result['designated']:
                messagebox.showwarning("Warning Time Issue", "Warning time is greater than designated time. This might lead to unexpected coloring behavior.")
                
            return True
        except ValueError as e:
            # Use messagebox.showerror for error presentation
            messagebox.showerror("Invalid Input", f"Please enter valid time values.\n{e}")
            return False

# --- Main Timer Widget ---
class TimerWidget(tk.Tk):
    """
    The main transparent, always-on-top window displaying the timer.
    """
    def __init__(self):
        super().__init__()
        self.title("Presentation Timer")
        
        # Initial timer state
        self.designated_time = DEFAULT_DESIGNATED_TIME_SECONDS
        self.warning_time = DEFAULT_WARNING_TIME_SECONDS
        
        self.configure_window()
        
        # Initialize thread BEFORE UI setup to prevent errors
        self.timer_thread = TimerThread(self)
        self.timer_thread.start()
        
        self.setup_ui()
        
        # Ensure the thread is stopped when the app closes
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def configure_window(self):
        """Sets window properties for a non-intrusive widget."""
        # Remove window decoration (title bar, border)
        self.overrideredirect(True)
        # Always keep on top
        self.wm_attributes('-topmost', True)
        # Make the background transparent (40% transparent means alpha = 1.0 - 0.4 = 0.6)
        self.wm_attributes('-alpha', 0.6) 
        
        # Initial positioning (bottom-right)
        self.update_idletasks() # Ensure geometry is calculated
        self.position_widget()
        
    def position_widget(self):
        """Positions the widget in the bottom right corner."""
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        window_width = 100 # Approx size of the label
        window_height = 40

        # Adjust position slightly from the absolute corner
        x = screen_width - window_width - 20
        y = screen_height - window_height - 60
        
        self.geometry(f'{window_width}x{window_height}+{x}+{y}')

    def setup_ui(self):
        """Creates the timer label and binds the right-click menu."""
        self.time_label = tk.Label(
            self, 
            text="00:00", 
            font=("Inter", 24, "bold"), 
            fg="green", 
            bg="black",
            padx=10, 
            pady=5
        )
        self.time_label.pack(expand=True, fill='both')
        
        # Setup context menu on right click
        self.menu = tk.Menu(self, tearoff=0)
        self.menu.add_command(label="Start", command=self.timer_thread.start_timer)
        self.menu.add_command(label="Stop", command=self.timer_thread.pause_timer) 
        self.menu.add_command(label="Reset", command=self.timer_thread.reset_timer)
        self.menu.add_separator()
        self.menu.add_command(label="Settings", command=self.open_settings)
        self.menu.add_command(label="Exit", command=self.on_close)
        
        self.time_label.bind("<Button-3>", self.show_context_menu)
        # Add ability to drag the widget (left-click)
        self.time_label.bind("<Button-1>", self.start_move)
        self.time_label.bind("<B1-Motion>", self.do_move)

    def start_move(self, event):
        """Records the mouse position when drag starts."""
        self.x = event.x
        self.y = event.y

    def do_move(self, event):
        """Moves the window relative to the initial click."""
        deltax = event.x - self.x
        deltay = event.y - self.y
        x = self.winfo_x() + deltax
        y = self.winfo_y() + deltay
        self.geometry(f"+{x}+{y}")

    def show_context_menu(self, event):
        """Displays the right-click context menu."""
        try:
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()

    def open_settings(self):
        """Opens the Settings dialog and updates times if successful."""
        # The SettingsDialog handles centering itself on the main screen.
        dialog = SettingsDialog(self, self.designated_time, self.warning_time)
        if dialog.result:
            self.designated_time = dialog.result['designated']
            self.warning_time = dialog.result['warning']
            print(f"Times updated: Designated={self.designated_time}s, Warning={self.warning_time}s")
            self.update_display() # Update display with new coloring rules

    def update_display(self):
        """
        Updates the timer label text and color based on elapsed time.
        This method is called from the main thread via an 'after' call
        requested by the TimerThread.
        """
        elapsed = int(self.timer_thread.elapsed_time)
        
        # Calculate MM:SS format
        minutes = elapsed // 60
        seconds = elapsed % 60
        time_string = f"{minutes:02d}:{seconds:02d}"
        
        # Determine color based on time limits
        if elapsed >= self.designated_time:
            color = "red"
        elif elapsed >= self.warning_time:
            color = "orange"
        else:
            color = "white"
            
        # Update the UI elements
        self.time_label.config(text=time_string, fg=color)

    def on_close(self):
        """Stops the background thread and destroys the application."""
        self.timer_thread.stop()
        self.destroy()

if __name__ == "__main__":
    from tkinter import messagebox
    try:
        app = TimerWidget()
        app.mainloop()
    except Exception as e:
        messagebox.showerror("Application Error", f"An unexpected error occurred: {e}")
        print(f"An error occurred: {e}", file=sys.stderr)