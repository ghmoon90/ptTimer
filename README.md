# ptTimer
presentation timer widget
# Presentation Timer Widget - Technical Documentation
## 1. OverviewThe 
Presentation Timer is a desktop widget application developed in Python using tkinter. It is designed to provide presenters with a non-intrusive, always-on-top visual reference for their time usage.
Core Capabilities:
- Frameless UI: A minimalist window without a title bar or borders.
- Transparency: 40% transparency to blend into the desktop environment.
- Threaded Timing: accurate timekeeping that does not freeze the interface.
- State Awareness: Visual color changes (White/Orange/Red) to signal time thresholds.

## 2. Architecture & ConcurrencyThe 
application employs an Event-Driven Architecture combined with a Worker Thread pattern.
###The Concurrency Model
Standard GUI frameworks like tkinter are not thread-safe. This means you cannot modify UI elements (like changing a label's text) directly from a background thread. The application solves this using a request queue mechanism:
- Main Thread (GUI): Handles drawing the window, processing mouse clicks, and listening for events.
- TimerThread (Background): Loops indefinitely (while running), calculates the elapsed time, and sleeps for 0.1 seconds.The 
- Bridge (after() method): Instead of updating the label directly, the TimerThread calls self.app.after(1, self.app.update_display). This places a "request" in the Main Thread's event queue to run update_display as soon as it is idle.
## 3. Class Breakdown
### A.TimerThread (extends threading.Thread)
This class encapsulates the "engine" of the timer.daemon = True: Ensures the thread terminates immediately when the main application window closes, preventing "zombie" processes.run(): The infinite loop. It manages the elapsed_time counter.stop(): Uses a threading.Event to break the loop cleanly.
### B. SettingsDialog (extends simpledialog.Dialog)
This class manages user configuration.Centering Logic (center_dialog_on_screen):Standard tkinter dialogs often appear in random locations. This method calculates the precise center of the monitor:$$x = (Screen Width / 2) - (Window Width / 2)$$$$y = (Screen Height / 2) - (Window Height / 2)$$buttonbox() Override: This is a critical implementation detail. The centering logic is triggered via after_idle inside buttonbox. This ensures the calculation happens after the dialog size is determined but before the user interacts with it.
### C. TimerWidget (extends tk.Tk)
The main controller class.Window Configuration:overrideredirect(True): Removes the OS window frame.wm_attributes('-topmost', 1): Forces the window to stay above PowerPoint/Keynote.wm_attributes('-alpha', 0.6): Sets opacity.
## 4. Logic Flow: Color Alerts
The visual feedback logic is executed on the Main Thread every time update_display() is called.
- Input: Current elapsed_time.
- Condition 1: Is elapsed_time $\ge$ designated_time?
-   Yes: Set Text Color to Red. 
- Condition 2: Is elapsed_time $\ge$ warning_time?
-   Yes: Set Text Color to Orange.
- 4: Default: Set Text Color to White.
## 5. Logic Flow: Custom Dragging
Because the standard title bar is removed (overrideredirect), the native OS "drag to move" functionality is lost. The code reimplements this:
- Event <Button-1> (Click): The application records the exact (x, y) coordinates of the mouse pointer relative to the widget.
- Event <B1-Motion> (Drag): As the mouse moves, the code calculates the delta (difference) between the new mouse position and the start position, instantly updating the window's geometry to match.
