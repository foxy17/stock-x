import sys
import datetime
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QLabel, QPushButton, QLineEdit, QMessageBox, QListWidgetItem
)
from PyQt5.QtCore import QTimer, Qt, QUrl
from PyQt5.QtGui import QDesktopServices, QColor, QBrush
import logging

try:
    # Expect link to be returned now
    from tracking import get_new_items, get_initial_items 
except ImportError as e:
    print(f"Error importing from tracking.py: {e}")
    sys.exit(1)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NSE Announcements Tracker")
        self.setGeometry(100, 100, 900, 700)
        
        # Set central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # URL Input section
        url_layout = QHBoxLayout()
        url_label = QLabel("XML URL:")
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Enter XML feed URL (https://...)")
        # Set the NSE announcements feed URL by default
        self.url_input.setText("https://nsearchives.nseindia.com/content/RSS/Online_announcements.xml")
        url_layout.addWidget(url_label)
        url_layout.addWidget(self.url_input)
        main_layout.addLayout(url_layout)
        
        # Control Buttons section
        buttons_layout = QHBoxLayout()
        self.start_button = QPushButton("Start Polling")
        self.stop_button = QPushButton("Stop Polling")
        self.stop_button.setEnabled(False)  # Initially disabled
        
        self.start_button.clicked.connect(self.start_polling)
        self.stop_button.clicked.connect(self.stop_polling)
        
        buttons_layout.addWidget(self.start_button)
        buttons_layout.addWidget(self.stop_button)
        main_layout.addLayout(buttons_layout)
        
        # Status Label
        self.status_label = QLabel("Status: Idle")
        main_layout.addWidget(self.status_label)
        
        # List Widget for displaying items
        self.list_widget = QListWidget()
        self.list_widget.setWordWrap(True)
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff) # Disable horizontal scroll
        # Style the list items for better readability with alternating colors
        self.list_widget.setStyleSheet("""
            QListWidget {
                alternate-background-color: #f0f0f0;
                background-color: white;
                font-size: 11pt;
            }
            QListWidget::item { 
                border-bottom: 1px solid #e0e0e0; 
                padding: 10px;
                padding-right: 20px; /* Added right padding */
                margin: 3px;
            }
            QListWidget::item:selected {
                background-color: #d0e7ff;
                color: black;
            }
            QListWidget::item:hover {
                background-color: #e5f0ff;
            }
        """)
        self.list_widget.setAlternatingRowColors(True)
        self.list_widget.itemClicked.connect(self.on_item_clicked)
        main_layout.addWidget(self.list_widget)
        
        # Set up timer for polling
        self.timer = QTimer(self)
        self.timer.setInterval(5000)  # 5 seconds
        self.timer.timeout.connect(self.poll_data)
        
        # Set up timer for updating highlights
        self.highlight_timer = QTimer(self)
        self.highlight_timer.setInterval(10000)  # Check every 10 seconds
        self.highlight_timer.timeout.connect(self.update_highlights)
        self.highlight_timer.start()
        
        # Initialize state variables
        self.polling = False
        self.target_url = ""
        self.item_data = []  # Store item data including link
        
        # Dictionary to track highlighted items with their addition time
        self.highlighted_items = {}  # {list_index: addition_timestamp}
        
        # Colors
        self.new_item_color = QColor(220, 255, 220)  # Light green
        
        # --- Load and display initial items from storage ---
        self.load_initial_items()
        # -----------------------------------------------------
    
    def load_initial_items(self):
        """Loads items from storage via tracking.py and displays them."""
        try:
            initial_items = get_initial_items()
            logging.info(f"Loading {len(initial_items)} initial items into UI.")
            # Add items in the order they are stored (older first, likely)
            # To show newest first from storage, use reversed(initial_items)
            for item_dict in initial_items: 
                self.add_item_to_list(item_dict, highlight=False) # Add without highlighting
            logging.info(f"Finished loading initial items. List count: {self.list_widget.count()}")
        except Exception as e:
            logging.error(f"Error loading initial items into UI: {e}")
            QMessageBox.warning(self, "Load Error", f"Could not load initial items: {e}")

    def add_item_to_list(self, item_dict, highlight=False):
        """Adds a single item (dictionary) to the list widget."""
        timestamp = item_dict.get("timestamp", "")
        title = item_dict.get("title", "No Title")
        description = item_dict.get("description", "No Description")
        link = item_dict.get("link") # Keep link separate

        # Store item data in the format expected by on_item_clicked
        # Insert at the beginning to maintain newest-first order for self.item_data
        self.item_data.insert(0, {"timestamp": timestamp, "title": title, "description": description, "link": link}) 
        
        # Format the friendly timestamp
        friendly_time = self.format_timestamp(timestamp)
        
        # Create a custom item
        item = QListWidgetItem()
        
        display_string = f""" 
            <div style='margin-bottom: 8px;font-size: 10pt;'>{friendly_time}</div>
            <div style='font-size: 12pt;'><b>Title:</b> {title}</div>
            <div style='font-size: 13pt; margin-top: 12px;'>{description}</div>
        """
        
        label = QLabel(display_string)
        label.setWordWrap(True)
        label.setTextFormat(Qt.RichText)
        label.setStyleSheet("background-color: transparent;")
        label.adjustSize()
        item.setSizeHint(label.sizeHint())
        
        # Apply highlight color if needed
        if highlight:
            item.setBackground(QBrush(self.new_item_color))
        
        # Insert at the top of the list (position 0)
        self.list_widget.insertItem(0, item)
        self.list_widget.setItemWidget(item, label)

        # If highlighting, update tracking
        if highlight:
             # Track this item for highlighting
            self.highlighted_items[0] = datetime.datetime.now()
            
            # Update indices of previously highlighted items
            updated_highlights = {}
            for idx, time_added in list(self.highlighted_items.items()): # Iterate over a copy
                if idx != 0:  # Skip the one we just added
                    updated_highlights[idx + 1] = time_added
                else: # Keep the newly added item
                    updated_highlights[0] = time_added
            self.highlighted_items = updated_highlights

    def start_polling(self):
        url = self.url_input.text().strip()
        
        # Validate URL
        if not url:
            QMessageBox.warning(self, "Invalid URL", "Please enter a URL")
            return
        
        if not (url.startswith("http://") or url.startswith("https://")):
            QMessageBox.warning(self, "Invalid URL", "URL must start with http:// or https://")
            return
        
        if not self.polling:
            self.polling = True
            self.target_url = url
            self.timer.start()
            self.status_label.setText("Status: Polling started")
            
            # Update UI controls
            self.stop_button.setEnabled(True)
            self.start_button.setEnabled(False)
            self.url_input.setEnabled(False)
            
            # Poll immediately for initial data
            self.poll_data()
    
    def stop_polling(self):
        if self.polling:
            self.polling = False
            self.timer.stop()
            self.status_label.setText("Status: Idle")
            
            # Update UI controls
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self.url_input.setEnabled(True)
    
    def format_timestamp(self, timestamp_str):
        """Format timestamp to be user-friendly, omit date if it's today, include AM/PM"""
        try:
            # Try to parse the timestamp format: 04-May-2025 07:00:00
            dt = datetime.datetime.strptime(timestamp_str, "%d-%b-%Y %H:%M:%S")
            time_format = "%I:%M %p" # Use %I for 12-hour clock, %p for AM/PM
            
            # Check if it's today
            today = datetime.datetime.now().date()
            if dt.date() == today:
                return f"Today at {dt.strftime(time_format)}"
            elif dt.date() == today - datetime.timedelta(days=1):
                return f"Yesterday at {dt.strftime(time_format)}"
            else:
                return dt.strftime(f"%d %b %Y at {time_format}")
        except ValueError:
             # Fallback: Try parsing with timezone (if the original format included it)
            try:
                dt = datetime.datetime.strptime(timestamp_str, "%a, %d %b %Y %H:%M:%S %z")
                time_format = "%I:%M %p" # Use %I for 12-hour clock, %p for AM/PM
                today = datetime.datetime.now(dt.tzinfo).date() # Use timezone-aware comparison
                if dt.date() == today:
                    return f"Today at {dt.strftime(time_format)}"
                elif dt.date() == today - datetime.timedelta(days=1):
                    return f"Yesterday at {dt.strftime(time_format)}"
                else:
                    return dt.strftime(f"%d %b %Y at {time_format}")
            except Exception:
                # If all parsing fails, return the original string
                return timestamp_str
        except Exception:
            logging.warning(f"Could not format timestamp: {timestamp_str}", exc_info=True)
            return timestamp_str # Catch any other parsing errors
    
    def poll_data(self):
        if not self.polling:
            return
        
        self.status_label.setText("Status: Fetching (this may take a moment)...")
        QApplication.processEvents()  # Keep UI responsive
        
        try:
            # Disable start/stop buttons during fetch to prevent multiple concurrent requests
            self.stop_button.setEnabled(False)
            QApplication.processEvents()
            
            # get_new_items now returns a list of dictionaries
            new_items = get_new_items(self.target_url) 
            
            # Re-enable buttons
            if self.polling:
                self.stop_button.setEnabled(True)
            
            new_items_count = 0
            if new_items:
                # Process items in reverse order to show newest at top
                # new_items is already a list of dictionaries
                for item_dict in reversed(new_items):
                    new_items_count += 1
                    # Add the new item to the list, with highlighting
                    self.add_item_to_list(item_dict, highlight=True)
            
            current_time = self.get_current_time()
            status_text = f"Status: Last check at {current_time}"
            if new_items_count > 0:
                status_text += f" | {new_items_count} new item{'s' if new_items_count > 1 else ''} found"
            self.status_label.setText(status_text)
            
        except Exception as e:
            self.status_label.setText(f"Status: Error polling: {str(e)}")
            QMessageBox.critical(self, "Error", f"An error occurred while polling: {str(e)}")
            
            # Re-enable buttons in case of error
            if self.polling:
                self.stop_button.setEnabled(True)
    
    def update_highlights(self):
        """Remove highlighting from items that have been highlighted for 5+ minutes"""
        current_time = datetime.datetime.now()
        items_to_remove = []
        
        for idx, time_added in self.highlighted_items.items():
            # Check if more than 5 minutes (300 seconds) have passed
            if (current_time - time_added).total_seconds() > 300:
                # Remove highlighting if the item index is still valid
                if 0 <= idx < self.list_widget.count():
                    item = self.list_widget.item(idx)
                    if item: # Check if item exists
                        item.setBackground(QBrush())  # Reset to default background
                items_to_remove.append(idx)
        
        # Remove processed items from the tracking dictionary
        for idx in items_to_remove:
            if idx in self.highlighted_items:
                 del self.highlighted_items[idx]
    
    def get_current_time(self):
        return datetime.datetime.now().strftime("%H:%M:%S")
    
    def closeEvent(self, event):
        # Ensure polling is stopped when the window is closed
        self.stop_polling()
        event.accept()

    def on_item_clicked(self, item):
        """Handle item click to prompt opening the associated link."""
        index = self.list_widget.row(item)
        if 0 <= index < len(self.item_data):
            item_info = self.item_data[index]
            link = item_info.get("link") # Get the link from stored data
            
            if link:
                reply = QMessageBox.question(self, 'Open Link?',
                                             f"Do you want to open the following link in your browser?\n\n{link}",
                                             QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                
                if reply == QMessageBox.Yes:
                    QDesktopServices.openUrl(QUrl(link))
            else:
                QMessageBox.information(self, "No Link", "No link is associated with this item.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    # Enable High DPI scaling for better visuals
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_()) 