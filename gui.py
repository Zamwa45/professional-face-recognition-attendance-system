from getpass import getpass

import customtkinter as ctk
from tkinter import ttk, messagebox
import cv2
from tkinter import messagebox
import numpy as np
import face_recognition
import os
from datetime import datetime, timedelta
import json
import pandas as pd
from PIL import Image, ImageTk
import threading
import time
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pytz
from dark_mode_utils import *
import tkinter as tk
from teacher_login import TeacherLogin
import uuid
from leave_management import *
import warnings
warnings.filterwarnings("ignore", category=UserWarning)
# Set customtkinter appearance

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


def generate_random_user_id():
    """Generate a unique random user ID"""
    return str(uuid.uuid4())[:8]

class FaceAttendanceSystem:
    def __init__(self, root, department=None):  # Add department parameter with default None
        self.root = root
        self.root.title("Face Recognition Attendance System")
        self.root.geometry("1400x800")
        # Store department
        self.department = department

        self.theme_manager = ThemeManager()

        self.leave_manager = LeaveManagement()

        # Set timezone
        self.timezone = pytz.timezone("Asia/Baghdad")

        # Rest of your initialization code...

        # Initialize variables

        self.camera = None
        self.is_capturing = False
        self.known_face_encodings = []
        self.known_face_names = []
        self.known_face_ids = []
        self.current_frame = None
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        self.settings = self.load_settings()


        # Load known faces

        self.load_known_faces()

        # Create main UI

        self.create_widgets()

        # Initialize attendance dictionary

        self.today_attendance = {}
        self.load_today_attendance()

        # Protocol for closing the window

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Setup notifications

        self.setup_notifications()

        # Start time update

        self.update_time_display()

    def get_current_time(self):
        """Get current time in Baghdad timezone"""
        utc_now = datetime.utcnow()
        baghdad_now = utc_now.replace(tzinfo=pytz.UTC).astimezone(self.timezone)
        return baghdad_now

    def update_time_display(self):
        """Update the time display every second"""
        if hasattr(self, "time_label"):
            current_time = self.get_current_time().strftime("%Y-%m-%d %H:%M:%S")
            self.time_label.configure(text=f"Current Time: {current_time}")
        self.root.after(1000, self.update_time_display)

    def load_settings(self):
        try:
            with open("settings.json", "r") as f:
                settings = json.load(f)
                # Validate and fix time format

                start_time = settings["working_hours"]["start"]
                end_time = settings["working_hours"]["end"]

                # Clean and validate time format

                settings["working_hours"]["start"] = self.clean_time_format(start_time)
                settings["working_hours"]["end"] = self.clean_time_format(end_time)

                return settings
        except FileNotFoundError:
            default_settings = {
                "camera_index": 1,
                "attendance_threshold": 0.6,
                "auto_capture": False,
                "notification_enabled": True,
                "working_hours": {"start": "09:00", "end": "17:00"},
                "grace_period_minutes": 10,
                "late_penalty_minutes": 1,
                "timezone": "Asia/Baghdad",
            }
            with open("settings.json", "w") as f:
                json.dump(default_settings, f, indent=4)
            return default_settings

    def clean_time_format(self, time_str):
        """Clean and validate time format"""
        try:
            # Remove any non-digit characters except colon

            cleaned = "".join(c for c in time_str if c.isdigit() or c == ":")

            # Split hours and minutes

            if ":" in cleaned:
                hours, minutes = cleaned.split(":")
            else:
                # If no colon, assume last two digits are minutes

                hours = cleaned[:-2]
                minutes = cleaned[-2:]
            # Ensure proper formatting

            hours = str(int(hours) % 24).zfill(2)  # Convert to 24-hour format
            minutes = str(int(minutes) % 60).zfill(2)  # Ensure valid minutes

            return f"{hours}:{minutes}"
        except Exception:
            return "09:00"  # Return default time if parsing fails


    def load_known_faces(self):
        if not os.path.exists("face_data"):
            os.makedirs("face_data")
        try:
            with open("user_records.json", "r") as f:
                self.user_data = json.load(f)
        except FileNotFoundError:
            self.user_data = {}
        for user_id, user_info in self.user_data.items():
            if "photo_path" in user_info:
                image_path = user_info["photo_path"]
                if os.path.exists(image_path):
                    image = face_recognition.load_image_file(image_path)
                    face_encodings = face_recognition.face_encodings(image)
                    if face_encodings:
                        self.known_face_encodings.append(face_encodings[0])
                        self.known_face_names.append(user_info["name"])
                        self.known_face_ids.append(user_id)

    def validate_date(self, date_str):
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            return True
        except ValueError:
            return False

    def get_baghdad_time(self, dt=None):
        """Convert any datetime to Baghdad time or get current Baghdad time"""
        if dt is None:
            dt = datetime.utcnow()
        if dt.tzinfo is None:
            dt = pytz.UTC.localize(dt)
        return dt.astimezone(self.timezone)

    def format_time(self, dt):
        """Format datetime object to string"""
        return dt.strftime("%Y-%m-%d %H:%M:%S")

    # Add to setup_settings_tab method
    def setup_email_settings(self, settings_frame):
        email_frame = ctk.CTkFrame(settings_frame)
        email_frame.pack(pady=10, fill="x")

        ctk.CTkLabel(email_frame, text="Email Settings",
                     font=("Helvetica", 16, "bold")).pack(pady=5)

        ctk.CTkLabel(email_frame, text="SMTP Server:").pack()
        self.smtp_server = ctk.CTkEntry(email_frame)
        self.smtp_server.insert(0, self.email_notifier.settings['smtp_server'])
        self.smtp_server.pack()

        ctk.CTkLabel(email_frame, text="SMTP Port:").pack()
        self.smtp_port = ctk.CTkEntry(email_frame)
        self.smtp_port.insert(0, str(self.email_notifier.settings['smtp_port']))
        self.smtp_port.pack()

        ctk.CTkLabel(email_frame, text="Sender Email:").pack()
        self.sender_email = ctk.CTkEntry(email_frame)
        self.sender_email.insert(0, self.email_notifier.settings['sender_email'])
        self.sender_email.pack()

        ctk.CTkLabel(email_frame, text="Password:").pack()
        self.email_password = ctk.CTkEntry(email_frame, show="*")
        self.email_password.insert(0, self.email_notifier.settings['sender_password'])
        self.email_password.pack()

        self.email_enabled = ctk.CTkCheckBox(email_frame, text="Enable Email Notifications")
        self.email_enabled.pack(pady=5)
        if self.email_notifier.settings['enabled']:
            self.email_enabled.select()

    def setup_backup_settings(self, settings_frame):
        backup_frame = ctk.CTkFrame(settings_frame)
        backup_frame.pack(pady=10, fill="x")

        ctk.CTkLabel(backup_frame, text="Backup Settings",
                     font=("Helvetica", 16, "bold")).pack(pady=5)

        ctk.CTkLabel(backup_frame, text="Backup Directory:").pack()
        self.backup_dir = ctk.CTkEntry(backup_frame)
        self.backup_dir.insert(0, self.backup_system.settings['backup_directory'])
        self.backup_dir.pack()

        ctk.CTkLabel(backup_frame, text="Backup Frequency:").pack()
        self.backup_freq = ttk.Combobox(backup_frame,
                                        values=["daily", "weekly", "monthly"],
                                        state="readonly")
        self.backup_freq.set(self.backup_system.settings['backup_frequency'])
        self.backup_freq.pack()

        ctk.CTkLabel(backup_frame, text="Retention Days:").pack()
        self.retention_days = ctk.CTkEntry(backup_frame)
        self.retention_days.insert(0, str(self.backup_system.settings['retention_days']))
        self.retention_days.pack()

        self.backup_enabled = ctk.CTkCheckBox(backup_frame, text="Enable Automatic Backups")
        self.backup_enabled.pack(pady=5)
        if self.backup_system.settings['enabled']:
            self.backup_enabled.select()

        backup_now_btn = ctk.CTkButton(backup_frame, text="Backup Now",
                                       command=self.backup_system.create_backup)
        backup_now_btn.pack(pady=5)

        restore_btn = ctk.CTkButton(backup_frame, text="Restore Backup",
                                    command=self.show_restore_dialog)
        restore_btn.pack(pady=5)

    def show_restore_dialog(self):
        backup_dir = self.backup_system.settings['backup_directory']
        backups = [f for f in os.listdir(backup_dir) if f.startswith('backup_')]

        if not backups:
            messagebox.showinfo("Info", "No backups available")
            return

        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Restore Backup")
        dialog.geometry("300x400")

        ctk.CTkLabel(dialog, text="Select Backup to Restore:").pack(pady=10)

        backup_var = tk.StringVar(dialog)
        backup_list = tk.Listbox(dialog, width=40, height=10)
        backup_list.pack(pady=10, padx=10)

        for backup in sorted(backups, reverse=True):
            backup_list.insert(tk.END, backup)

        def do_restore():
            selection = backup_list.curselection()
            if not selection:
                messagebox.showwarning("Warning", "Please select a backup")
                return

            backup_file = backup_list.get(selection[0])
            if messagebox.askyesno("Confirm Restore",
                                   "This will overwrite current data. Continue?"):
                if self.backup_system.restore_backup(backup_file):
                    messagebox.showinfo("Success", "Backup restored successfully")
                    dialog.destroy()
                    self.root.destroy()  # Restart app to load restored data
                else:
                    messagebox.showerror("Error", "Failed to restore backup")

        ctk.CTkButton(dialog, text="Restore", command=do_restore).pack(pady=10)
        ctk.CTkButton(dialog, text="Cancel", command=dialog.destroy).pack(pady=5)

    def setup_notifications(self):
        def check_late_arrivals():
            while True:
                if self.settings["notification_enabled"]:
                    current_time = datetime.now().strftime("%H:%M")
                    start_time = self.settings["working_hours"]["start"]

                    if current_time > start_time:
                        current_date = datetime.now().strftime("%Y-%m-%d")
                        try:
                            with open(f"attendance_{current_date}.json", "r") as f:
                                data = json.load(f)
                                for user_id, info in self.user_data.items():
                                    if user_id not in data.get(current_date, {}):
                                        messagebox.showwarning(
                                            "Late Arrival",
                                            f"{info['name']} has not arrived yet!",
                                        )
                        except FileNotFoundError:
                            pass
                time.sleep(300)  # Check every 5 minutes

        # Start notification thread

        notification_thread = threading.Thread(target=check_late_arrivals, daemon=True)
        notification_thread.start()

    def create_widgets(self):
        # Create tabview
        self.tabview = ctk.CTkTabview(self.root)
        self.tabview.pack(pady=10, expand=True, fill="both")

        # Create tabs
        self.attendance_tab = self.tabview.add("Mark Attendance")
        self.registration_tab = self.tabview.add("Register New User")
        self.records_tab = self.tabview.add("View Records")
        self.settings_tab = self.tabview.add("Settings")
        self.analytics_tab = self.tabview.add("Analytics")
        self.profile_tab = self.tabview.add("Profile")
        self.leave_tab = self.tabview.add("Leave Management")

        self.setup_attendance_tab()
        self.setup_registration_tab()
        self.setup_records_tab()
        self.setup_settings_tab()
        self.setup_analytics_tab()
        self.setup_profile_tab()
        self.setup_leave_request_tab()
        self.setup_notification_system()


    def setup_attendance_tab(self):
        # Create frames
        left_frame = ctk.CTkFrame(self.attendance_tab)
        left_frame.pack(side="left", padx=10, pady=10, fill="both", expand=True)

        right_frame = ctk.CTkFrame(self.attendance_tab)
        right_frame.pack(side="right", padx=10, pady=10, fill="both", expand=True)

        # Camera frame
        self.camera_label = ctk.CTkLabel(left_frame, text="")
        self.camera_label.pack(pady=10)

        # Camera control button
        self.camera_button = ctk.CTkButton(
            left_frame, text="Start Camera", command=self.toggle_camera
        )
        self.camera_button.pack(pady=10)

        # Attendance display
        header_frame = ctk.CTkFrame(right_frame)
        header_frame.pack(fill="x", pady=10)

        ctk.CTkLabel(
            header_frame, text="Today's Attendance", font=("Helvetica", 20, "bold")
        ).pack(side="left", padx=10)

        # Add Delete buttons
        button_frame = ctk.CTkFrame(header_frame)
        button_frame.pack(side="right", padx=10)

        ctk.CTkButton(
            button_frame,
            text="Delete Selected",
            command=self.delete_selected_attendance,
            fg_color="#FF5555",  # Red color for warning
            hover_color="#FF0000"  # Darker red for hover
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            button_frame,
            text="Delete All",
            command=self.confirm_delete_all_attendance,
            fg_color="#FF3333",  # Darker red for more dangerous action
            hover_color="#CC0000"  # Even darker red for hover
        ).pack(side="left", padx=5)

        # Create attendance table
        columns = ("ID", "Name", "Time", "Status")
        self.attendance_tree = self.create_treeview(right_frame, columns)

        # Add right-click menu
        self.create_context_menu()

    def setup_profile_tab(self):
        profile_frame = ctk.CTkFrame(self.profile_tab)
        profile_frame.pack(padx=20, pady=20, fill="both", expand=True)

        # User Info
        info_frame = ctk.CTkFrame(profile_frame)
        info_frame.pack(pady=10, fill="x")

        self.profile_photo_label = ctk.CTkLabel(info_frame, text="")
        self.profile_photo_label.pack(pady=10)

        # User statistics
        stats_frame = ctk.CTkFrame(profile_frame)
        stats_frame.pack(pady=10, fill="x")

        self.attendance_rate_label = ctk.CTkLabel(stats_frame, text="Attendance Rate: 0%")
        self.attendance_rate_label.pack(pady=5)

        self.punctuality_rate_label = ctk.CTkLabel(stats_frame, text="Punctuality Rate: 0%")
        self.punctuality_rate_label.pack(pady=5)

    def setup_leave_request_tab(self):
        leave_frame = ctk.CTkFrame(self.leave_tab)
        leave_frame.pack(padx=20, pady=20, fill="both", expand=True)

        # Leave request form
        form_frame = ctk.CTkFrame(leave_frame)
        form_frame.pack(pady=10)

        ctk.CTkLabel(form_frame, text="Start Date:").pack()
        self.leave_start_date = ctk.CTkEntry(form_frame)
        self.leave_start_date.pack()

        ctk.CTkLabel(form_frame, text="End Date:").pack()
        self.leave_end_date = ctk.CTkEntry(form_frame)
        self.leave_end_date.pack()

        ctk.CTkLabel(form_frame, text="Reason:").pack()
        self.leave_reason = ctk.CTkTextbox(form_frame, height=100)
        self.leave_reason.pack()

        ctk.CTkButton(form_frame, text="Submit Request",
                      command=self.submit_leave_request).pack(pady=10)

        # Leave requests display
        requests_frame = ctk.CTkFrame(leave_frame)
        requests_frame.pack(pady=10, fill="both", expand=True)

        ctk.CTkLabel(requests_frame, text="My Leave Requests",
                     font=("Helvetica", 16, "bold")).pack(pady=5)

        # Create Treeview for leave requests
        columns = ("Request ID", "Start Date", "End Date", "Status")
        self.leave_requests_tree = self.create_treeview(requests_frame, columns)

        # Update the display
        self.update_leave_requests_display()
    def create_context_menu(self):
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Delete Record", command=self.delete_selected_attendance)

        # Bind right-click to show context menu
        self.attendance_tree.bind("<Button-3>", self.show_context_menu)

    def show_context_menu(self, event):
        # Only show menu if items are selected
        if self.attendance_tree.selection():
            self.context_menu.post(event.x_root, event.y_root)

    def delete_selected_attendance(self):
        # Get selected items
        selected_items = self.attendance_tree.selection()

        if not selected_items:
            messagebox.showwarning("Warning", "Please select records to delete")
            return

        # Confirm deletion
        if not messagebox.askyesno("Confirm Deletion",
                                   f"Are you sure you want to delete {len(selected_items)} selected record(s)?"):
            return

        current_date = self.get_current_time().strftime("%Y-%m-%d")

        try:
            # Get IDs of selected items
            selected_ids = []
            for item in selected_items:
                values = self.attendance_tree.item(item)['values']
                if values:
                    selected_ids.append(values[0])  # ID is the first column

            # Remove from attendance dictionary
            if current_date in self.today_attendance:
                for user_id in selected_ids:
                    if str(user_id) in self.today_attendance[current_date]:
                        del self.today_attendance[current_date][str(user_id)]

            # Save updated attendance
            self.save_attendance()

            # Update display
            self.update_attendance_display()

            messagebox.showinfo("Success", f"Successfully deleted {len(selected_items)} record(s)")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete records: {str(e)}")

    def confirm_delete_all_attendance(self):
        current_date = self.get_current_time().strftime("%Y-%m-%d")

        if current_date not in self.today_attendance or not self.today_attendance[current_date]:
            messagebox.showinfo("Info", "No attendance records to delete")
            return

        record_count = len(self.today_attendance[current_date])

        # Show warning dialog with count
        if not messagebox.askyesno("Warning",
                                   f"Are you sure you want to delete ALL {record_count} attendance records for today?\n\n"
                                   "This action cannot be undone!", icon='warning'):
            return

        # Double confirm for bulk deletion
        if not messagebox.askyesno("Final Confirmation",
                                   "Please confirm again that you want to delete ALL attendance records for today.",
                                   icon='warning'):
            return

        try:
            # Clear today's attendance
            self.today_attendance[current_date] = {}

            # Save empty attendance
            self.save_attendance()

            # Update display
            self.update_attendance_display()

            messagebox.showinfo("Success", f"Successfully deleted all {record_count} attendance records for today")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete records: {str(e)}")

    def setup_notification_system(self):
        """Initialize and setup the notification system"""
        # Initialize notification related attributes
        self.notifications = []
        self.leave_requests = {}  # Initialize leave_requests dictionary

        def check_notifications():
            try:
                current_time = self.get_current_time()

                # Check for upcoming leave requests
                if hasattr(self, 'leave_manager'):
                    for request_id, request in self.leave_manager.leave_requests.items():
                        if request['status'] == 'Approved':
                            try:
                                start_date = datetime.strptime(request['start_date'], "%Y-%m-%d")
                                if (start_date - current_time).days == 1:  # Check if leave starts tomorrow
                                    self.show_notification(
                                        f"Leave reminder: Your approved leave starts tomorrow"
                                    )
                            except (ValueError, TypeError) as e:
                                print(f"Date parsing error in notifications: {e}")

                # Check for low attendance rates
                if hasattr(self, 'user_data'):
                    for user_id, data in self.user_data.items():
                        try:
                            attendance_rate = self.calculate_attendance_rate(user_id)
                            if attendance_rate < 0.8:  # 80% threshold
                                self.show_notification(
                                    f"Low attendance rate warning for {data['name']}"
                                )
                        except Exception as e:
                            print(f"Error calculating attendance rate: {e}")

                # Schedule next check
                if hasattr(self, 'root') and self.root:
                    self.root.after(3600000, check_notifications)  # Check every hour

            except Exception as e:
                print(f"Error in notification check: {e}")

        # Start the notification check cycle
        self.root.after(1000, check_notifications)  # Start first check after 1 second

    def show_notification(self, message):
        """Display a notification message"""
        try:
            notification_window = ctk.CTkToplevel(self.root)
            notification_window.title("Notification")
            notification_window.geometry("300x150")
            notification_window.transient(self.root)  # Make window transient to main window

            # Center the notification window
            x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 150
            y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 75
            notification_window.geometry(f"+{x}+{y}")

            # Create frames
            message_frame = ctk.CTkFrame(notification_window)
            message_frame.pack(pady=10, padx=10, fill="x", expand=True)

            button_frame = ctk.CTkFrame(notification_window)
            button_frame.pack(pady=5, padx=10, fill="x")

            # Add message with word wrap
            message_label = ctk.CTkLabel(
                message_frame,
                text=message,
                wraplength=250  # Enable word wrap
            )
            message_label.pack(pady=10, padx=10)

            # Add timestamp
            timestamp = self.get_current_time().strftime("%H:%M:%S")
            time_label = ctk.CTkLabel(
                message_frame,
                text=f"Time: {timestamp}",
                font=("Helvetica", 10)
            )
            time_label.pack(pady=5)

            # Add dismiss button
            dismiss_button = ctk.CTkButton(
                button_frame,
                text="Dismiss",
                command=notification_window.destroy,
                width=100
            )
            dismiss_button.pack(pady=5)

            # Auto-dismiss after 10 seconds
            notification_window.after(10000, notification_window.destroy)

            # Store notification
            self.notifications.append({
                'message': message,
                'timestamp': timestamp,
                'window': notification_window
            })

        except Exception as e:
            print(f"Error showing notification: {e}")

    def calculate_attendance_rate(self, user_id):
        """Calculate attendance rate for a user"""
        try:
            total_working_days = self.get_total_working_days()
            attended_days = self.get_attended_days(user_id)
            return attended_days / total_working_days if total_working_days > 0 else 0
        except Exception as e:
            print(f"Error calculating attendance rate: {e}")
            return 0

    def get_total_working_days(self):
        """Calculate total working days"""
        try:
            current_date = self.get_current_time().date()
            start_of_month = current_date.replace(day=1)
            total_days = (current_date - start_of_month).days + 1

            # Subtract weekends
            weekend_days = sum(1 for day in range(total_days)
                               if (start_of_month + timedelta(days=day)).weekday() >= 5)

            return total_days - weekend_days
        except Exception as e:
            print(f"Error calculating total working days: {e}")
            return 0

    def get_attended_days(self, user_id):
        """Calculate attended days for a user"""
        try:
            current_date = self.get_current_time().date()
            start_of_month = current_date.replace(day=1)

            attended_days = 0
            current = start_of_month

            while current <= current_date:
                date_str = current.strftime("%Y-%m-%d")
                filename = f"attendance_{date_str}.json"

                try:
                    with open(filename, "r") as f:
                        attendance_data = json.load(f)
                        if date_str in attendance_data and str(user_id) in attendance_data[date_str]:
                            attended_days += 1
                except FileNotFoundError:
                    pass

                current += timedelta(days=1)

            return attended_days
        except Exception as e:
            print(f"Error calculating attended days: {e}")
            return 0

    def create_treeview(self, parent, columns):
        # Create a frame to hold the treeview and scrollbar
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="both", expand=True)

        # Create Treeview with custom style
        style = ttk.Style()
        style.configure(
            "Custom.Treeview",
            background="#2b2b2b",
            foreground="white",
            fieldbackground="#2b2b2b",
            borderwidth=0,
        )
        style.map("Custom.Treeview", background=[("selected", "#1f538d")])

        tree = ttk.Treeview(
            frame, columns=columns, show="headings", style="Custom.Treeview", height=20
        )

        # Configure scrollbars
        vsb = ctk.CTkScrollbar(frame, orientation="vertical", command=tree.yview)
        hsb = ctk.CTkScrollbar(frame, orientation="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        # Configure columns
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=150)

        # Grid layout
        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)

        return tree

    def toggle_camera(self):
        if not self.is_capturing:
            self.camera = cv2.VideoCapture(self.settings["camera_index"])
            if not self.camera.isOpened():
                messagebox.showerror(
                    "Error",
                    "Could not open camera. Try index 0 or check camera connection.",
                )
                return
            self.is_capturing = True
            self.camera_button.configure(text="Stop Camera")
            self.update_camera()
        else:
            self.camera.release()
            self.is_capturing = False
            self.camera_button.configure(text="Start Camera")
            self.camera_label.configure(image=None)

    def update_camera(self):
        if self.is_capturing:
            ret, frame = self.camera.read()
            if ret:
                # Face recognition process
                small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
                rgb_small_frame = small_frame[:, :, ::-1]

                face_locations = face_recognition.face_locations(rgb_small_frame)
                face_encodings = face_recognition.face_encodings(
                    rgb_small_frame, face_locations
                )

                # Draw rectangles around faces
                for top, right, bottom, left in face_locations:
                    top *= 4
                    right *= 4
                    bottom *= 4
                    left *= 4
                    cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)

                # Process each face found
                for face_encoding in face_encodings:
                    matches = face_recognition.compare_faces(
                        self.known_face_encodings, face_encoding
                    )
                    if True in matches:
                        first_match_index = matches.index(True)
                        user_id = self.known_face_ids[first_match_index]
                        name = self.known_face_names[first_match_index]
                        self.mark_attendance(user_id, name)

                # Display frame
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                image = Image.fromarray(frame)
                image = image.resize((640, 480))
                photo = ImageTk.PhotoImage(image=image)
                self.camera_label.configure(image=photo)
                self.camera_label.image = photo

            self.root.after(10, self.update_camera)

    def setup_registration_tab(self):
        # Create main frame
        form_frame = ctk.CTkFrame(self.registration_tab)
        form_frame.pack(padx=20, pady=20)

        # Registration form fields
        ctk.CTkLabel(form_frame, text="Student ID:", font=("Helvetica", 14)).pack(pady=5)

        # Create the reg_id entry FIRST, then configure it
        self.reg_id = ctk.CTkEntry(form_frame, width=200)
        self.reg_id.pack(pady=5)
        self.reg_id.configure(state='disabled')  # Now configure it after creation

        ctk.CTkLabel(form_frame, text="Name:", font=("Helvetica", 14)).pack(pady=5)
        self.reg_name = ctk.CTkEntry(form_frame, width=200)
        self.reg_name.pack(pady=5)

        # Department selection with Combobox
        ctk.CTkLabel(form_frame, text="Department:", font=("Helvetica", 14)).pack(pady=5)

        # Define departments list
        departments = [
            "Computer Science",
            "Information Technology",
            "Electrical Engineering",
            "Mechanical Engineering",
            "Civil Engineering",
            "Business Administration",
            "Mathematics",
            "Physics",
            "Chemistry",
            "Biology"
        ]

        # Create a frame for the combobox to match the styling
        combo_frame = ctk.CTkFrame(form_frame)
        combo_frame.pack(pady=5)

        # Create and configure the combobox
        self.reg_dept = ttk.Combobox(combo_frame, values=departments, width=30, state="readonly")
        self.reg_dept.set("Select Department")  # Set default text

        # Style the combobox to match dark theme
        style = ttk.Style()
        style.configure('Custom.TCombobox',
                        fieldbackground='#2b2b2b',
                        background='#2b2b2b',
                        foreground='white',
                        selectbackground='#1f538d',
                        selectforeground='white'
                        )
        self.reg_dept.configure(style='Custom.TCombobox')
        self.reg_dept.pack(pady=5)

        # Camera preview
        self.reg_camera_label = ctk.CTkLabel(form_frame, text="")
        self.reg_camera_label.pack(pady=10)

        # Buttons
        button_frame = ctk.CTkFrame(form_frame)
        button_frame.pack(pady=10)

        ctk.CTkButton(
            button_frame,
            text="Capture Photo",
            command=self.capture_registration_photo,
            width=120,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            button_frame,
            text="Register",
            command=self.register_user,
            width=120
        ).pack(side="left", padx=5)

    def mark_attendance(self, user_id, name):
        # Get current time in Baghdad timezone
        current_datetime = self.get_baghdad_time()
        current_time = current_datetime.strftime("%H:%M:%S")
        current_date = current_datetime.strftime("%Y-%m-%d")

        if current_date not in self.today_attendance:
            self.today_attendance[current_date] = {}

        if user_id not in self.today_attendance[current_date]:
            try:
                # Convert times to datetime.time objects for proper comparison
                arrival_time = current_datetime.time()

                # Get start time in Baghdad timezone
                start_time_str = self.clean_time_format(
                    self.settings["working_hours"]["start"]
                )
                start_time = datetime.strptime(start_time_str, "%H:%M").time()

                # Calculate grace period time
                start_datetime = datetime.combine(current_datetime.date(), start_time)
                start_datetime = self.timezone.localize(start_datetime)
                grace_datetime = start_datetime + timedelta(
                    minutes=self.settings["grace_period_minutes"]
                )
                grace_time = grace_datetime.time()

                # Determine attendance status
                if arrival_time <= start_time:
                    status = "On Time"
                elif arrival_time <= grace_time:
                    status = "Within Grace Period"
                else:
                    minutes_late = (
                        datetime.combine(current_datetime.date(), arrival_time)
                        - datetime.combine(current_datetime.date(), start_time)
                    ).seconds // 60
                    status = f"Late by {minutes_late} minutes"

                self.today_attendance[current_date][user_id] = {
                    "name": name,
                    "time": current_time,
                    "status": status,
                    "timezone": "Asia/Baghdad",
                }

                # Show notification for attendance
                messagebox.showinfo(
                    "Attendance Marked",
                    f"Attendance marked for {name}\n"
                    f"Time: {current_time}\n"
                    f"Status: {status}\n"
                    f"Date: {current_date}\n"
                    f"Time Zone: Baghdad (UTC+3)",
                )

                self.update_attendance_display()
                self.save_attendance()

            except Exception as e:
                messagebox.showerror("Error", f"Failed to mark attendance: {str(e)}")

    def capture_registration_photo(self):
        if not self.is_capturing:
            self.camera = cv2.VideoCapture(self.settings["camera_index"])
            ret, frame = self.camera.read()

            if ret:
                # Generate temporary ID for the photo
                temp_id = str(uuid.uuid4())[:8]

                if not os.path.exists("face_data"):
                    os.makedirs("face_data")

                filename = f"face_data/temp_capture.jpg"  # Use temporary filename
                cv2.imwrite(filename, frame)

                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                image = Image.fromarray(frame)
                image = image.resize((320, 240))
                photo = ImageTk.PhotoImage(image=image)
                self.reg_camera_label.configure(image=photo)
                self.reg_camera_label.image = photo

                # Store the temporary filename for use during registration
                self.temp_photo_path = filename

            self.camera.release()

    def register_user(self):
        # Generate random ID
        user_id = generate_random_user_id()
        name = self.reg_name.get()
        department = self.reg_dept.get()

        # Validate department selection
        if department == "Select Department":
            messagebox.showerror("Error", "Please select a department")
            return

        if not name:
            messagebox.showerror("Error", "Please enter a name")
            return

        if not hasattr(self, 'temp_photo_path') or not os.path.exists(self.temp_photo_path):
            messagebox.showerror("Error", "Please capture photo first")
            return

        try:
            # Move temporary photo to permanent location
            permanent_photo_path = f"face_data/user_{user_id}.jpg"
            if os.path.exists(self.temp_photo_path):
                os.rename(self.temp_photo_path, permanent_photo_path)

            # Add user to records
            self.user_data[user_id] = {
                "name": name,
                "department": department,
                "photo_path": permanent_photo_path,
                "registration_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }

            # Save user records
            with open("user_records.json", "w") as f:
                json.dump(self.user_data, f, indent=4)

            # Reload known faces
            self.load_known_faces()

            messagebox.showinfo("Success", f"User registered successfully\nID: {user_id}")

            # Clear form
            self.reg_name.delete(0, ctk.END)
            self.reg_dept.set("Select Department")  # Reset department selection
            self.reg_camera_label.configure(image=None)
            if hasattr(self, 'temp_photo_path'):
                delattr(self, 'temp_photo_path')

        except Exception as e:
            messagebox.showerror("Error", f"Registration failed: {str(e)}")

    def update_attendance_display(self):
        for item in self.attendance_tree.get_children():
            self.attendance_tree.delete(item)

        current_date = self.get_current_time().strftime("%Y-%m-%d")
        if current_date in self.today_attendance:
            for user_id, data in self.today_attendance[current_date].items():
                self.attendance_tree.insert(
                    "",
                    "end",
                    values=(user_id, data["name"], data["time"], data["status"]),
                )

    def save_attendance(self):
        filename = f"attendance_{self.get_current_time().strftime('%Y-%m-%d')}.json"
        try:
            with open(filename, "w") as f:
                json.dump(self.today_attendance, f, indent=4)

            # Create backup
            backup_dir = "attendance_backups"
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)

            backup_filename = os.path.join(
                backup_dir,
                f"backup_attendance_{self.get_current_time().strftime('%Y-%m-%d_%H-%M-%S')}.json"
            )
            with open(backup_filename, "w") as f:
                json.dump(self.today_attendance, f, indent=4)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save attendance: {str(e)}")

    def load_today_attendance(self):
        current_date = datetime.now().strftime("%Y-%m-%d")
        filename = f"attendance_{current_date}.json"
        try:
            with open(filename, "r") as f:
                self.today_attendance = json.load(f)
        except FileNotFoundError:
            self.today_attendance = {current_date: {}}
        self.update_attendance_display()

    def setup_settings_tab(self):
        # Add settings tab
        settings_frame = ctk.CTkFrame(self.settings_tab)
        settings_frame.pack(padx=20, pady=20, fill="both", expand=True)

        # Theme Settings
        appearance_frame = ctk.CTkFrame(settings_frame)
        appearance_frame.pack(pady=10, fill="x")

        ctk.CTkLabel(appearance_frame, text="Theme Settings",
                     font=("Helvetica", 16, "bold")).pack(pady=5)

        # Theme toggle button
        theme_button = ctk.CTkButton(
            appearance_frame,
            text="Toggle Dark/Light Mode",
            command=self.theme_manager.toggle_theme
        )
        theme_button.pack(pady=5)

        # Reset theme button
        reset_button = ctk.CTkButton(
            appearance_frame,
            text="Reset Theme to Default",
            command=self.theme_manager.reset_to_defaults
        )
        reset_button.pack(pady=5)

        # Time zone information
        timezone_frame = ctk.CTkFrame(settings_frame)
        timezone_frame.pack(pady=10, fill="x")

        ctk.CTkLabel(timezone_frame, text="Time Zone Settings",
                     font=("Helvetica", 16, "bold")).pack(pady=5)

        ctk.CTkLabel(timezone_frame, text=f"Current Time Zone: Asia/Baghdad").pack(pady=5)

        # Create time label with larger font
        self.time_label = ctk.CTkLabel(
            timezone_frame,
            text="2025-02-11 13:50:43",  # Updated with current time
            font=("Helvetica", 20)
        )
        self.time_label.pack(pady=10)

        # Camera settings
        camera_frame = ctk.CTkFrame(settings_frame)
        camera_frame.pack(pady=10, fill="x")

        ctk.CTkLabel(camera_frame, text="Camera Settings",
                     font=("Helvetica", 16, "bold")).pack(pady=5)

        camera_label = ctk.CTkLabel(camera_frame, text="Camera Index:")
        camera_label.pack(pady=5)
        self.camera_index = ctk.CTkEntry(camera_frame)
        self.camera_index.insert(0, str(self.settings["camera_index"]))
        self.camera_index.pack(pady=5)

        # Working hours settings
        hours_frame = ctk.CTkFrame(settings_frame)
        hours_frame.pack(pady=10, fill="x")

        ctk.CTkLabel(hours_frame, text="Working Hours Settings",
                     font=("Helvetica", 16, "bold")).pack(pady=5)

        time_frame = ctk.CTkFrame(hours_frame)
        time_frame.pack(pady=5)

        start_frame = ctk.CTkFrame(time_frame)
        start_frame.pack(side="left", padx=10)
        ctk.CTkLabel(start_frame, text="Start Time:").pack(side="left", padx=5)
        self.start_time = ctk.CTkEntry(start_frame, width=100)
        self.start_time.insert(0, self.settings["working_hours"]["start"])
        self.start_time.pack(side="left")

        end_frame = ctk.CTkFrame(time_frame)
        end_frame.pack(side="left", padx=10)
        ctk.CTkLabel(end_frame, text="End Time:").pack(side="left", padx=5)
        self.end_time = ctk.CTkEntry(end_frame, width=100)
        self.end_time.insert(0, self.settings["working_hours"]["end"])
        self.end_time.pack(side="left")

        # Grace period settings
        grace_frame = ctk.CTkFrame(settings_frame)
        grace_frame.pack(pady=10, fill="x")

        ctk.CTkLabel(grace_frame, text="Attendance Settings",
                     font=("Helvetica", 16, "bold")).pack(pady=5)

        grace_input_frame = ctk.CTkFrame(grace_frame)
        grace_input_frame.pack(pady=5)

        ctk.CTkLabel(grace_input_frame, text="Grace Period (minutes):").pack(side="left", padx=5)
        self.grace_period = ctk.CTkEntry(grace_input_frame, width=100)
        self.grace_period.insert(0, str(self.settings.get("grace_period_minutes", 10)))
        self.grace_period.pack(side="left", padx=5)

        # Save settings button
        save_button = ctk.CTkButton(
            settings_frame,
            text="Save Settings",
            command=self.save_settings,
            font=("Helvetica", 14)
        )
        save_button.pack(pady=20)

    def setup_analytics_tab(self):
        # Add analytics tab
        analytics_frame = ctk.CTkFrame(self.analytics_tab)
        analytics_frame.pack(padx=20, pady=20, fill="both", expand=True)

        # Date range selection
        date_frame = ctk.CTkFrame(analytics_frame)
        date_frame.pack(pady=10)

        ctk.CTkLabel(date_frame, text="From:").pack(side="left", padx=5)
        self.from_date = ctk.CTkEntry(date_frame, width=100)
        self.from_date.pack(side="left", padx=5)
        self.from_date.insert(0, (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"))

        ctk.CTkLabel(date_frame, text="To:").pack(side="left", padx=5)
        self.to_date = ctk.CTkEntry(date_frame, width=100)
        self.to_date.pack(side="left", padx=5)
        self.to_date.insert(0, datetime.now().strftime("%Y-%m-%d"))

        # Generate report button
        generate_button = ctk.CTkButton(
            analytics_frame,
            text="Generate Report",
            command=self.generate_analytics
        )
        generate_button.pack(pady=10)

        # Canvas for matplotlib
        self.analytics_canvas_frame = ctk.CTkFrame(analytics_frame)
        self.analytics_canvas_frame.pack(fill="both", expand=True)

    def setup_records_tab(self):
        # Create main frame
        main_frame = ctk.CTkFrame(self.records_tab)
        main_frame.pack(padx=20, pady=20, fill="both", expand=True)

        # Date selection frame
        date_frame = ctk.CTkFrame(main_frame)
        date_frame.pack(pady=10)

        ctk.CTkLabel(date_frame, text="Date:", font=("Helvetica", 14)).pack(
            side="left", padx=5
        )
        self.date_entry = ctk.CTkEntry(date_frame, width=150)
        self.date_entry.pack(side="left", padx=5)
        self.date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))

        ctk.CTkButton(
            date_frame, text="View Records", command=self.view_records, width=120
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            date_frame, text="Export Report...", command=self.export_records, width=120
        ).pack(side="left", padx=5)

        # Records display
        columns = ("ID", "Name", "Time", "Status")
        self.records_tree = self.create_treeview(main_frame, columns)

    def generate_analytics(self):
        from_date = datetime.strptime(self.from_date.get(), "%Y-%m-%d")
        to_date = datetime.strptime(self.to_date.get(), "%Y-%m-%d")

        # Collect attendance data
        attendance_data = {"total": {}, "on_time": {}, "late": {}}

        current_date = from_date
        while current_date <= to_date:
            date_str = current_date.strftime("%Y-%m-%d")
            try:
                with open(f"attendance_{date_str}.json", "r") as f:
                    data = json.load(f)
                    daily_data = data.get(date_str, {})

                    attendance_data["total"][date_str] = len(daily_data)
                    attendance_data["on_time"][date_str] = len(
                        [x for x in daily_data.values() if x["status"] == "On Time"]
                    )
                    attendance_data["late"][date_str] = len(
                        [x for x in daily_data.values() if "Late" in x["status"]]
                    )
            except FileNotFoundError:
                attendance_data["total"][date_str] = 0
                attendance_data["on_time"][date_str] = 0
                attendance_data["late"][date_str] = 0
            current_date += timedelta(days=1)

        # Create matplotlib figure
        plt.style.use('dark_background')
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
        fig.patch.set_facecolor('#2b2b2b')

        # Plot daily attendance
        dates = list(attendance_data["total"].keys())
        total = list(attendance_data["total"].values())
        on_time = list(attendance_data["on_time"].values())
        late = list(attendance_data["late"].values())

        ax1.bar(dates, total, label="Total", color='#1f538d')
        ax1.set_xlabel("Date")
        ax1.set_ylabel("Attendance Count")
        ax1.set_title("Daily Attendance Report")
        ax1.tick_params(axis="x", rotation=45)
        ax1.legend()

        # Plot on-time vs late
        ax2.bar(dates, on_time, label="On Time", color="green")
        ax2.bar(dates, late, bottom=on_time, label="Late", color="red")
        ax2.set_xlabel("Date")
        ax2.set_ylabel("Count")
        ax2.set_title("On-time vs Late Attendance")
        ax2.tick_params(axis="x", rotation=45)
        ax2.legend()

        plt.tight_layout()

        # Clear previous canvas if exists
        for widget in self.analytics_canvas_frame.winfo_children():
            widget.destroy()

        # Add new canvas
        canvas = FigureCanvasTkAgg(fig, self.analytics_canvas_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def submit_leave_request(self):
        """Submit a new leave request"""
        try:
            start_date = self.leave_start_date.get()
            end_date = self.leave_end_date.get()
            reason = self.leave_reason.get("1.0", "end-1c")  # Get text from textbox

            # Validate dates
            if not all([start_date, end_date]):
                messagebox.showerror("Error", "Please enter both start and end dates")
                return

            try:
                start = datetime.strptime(start_date, "%Y-%m-%d")
                end = datetime.strptime(end_date, "%Y-%m-%d")

                if start > end:
                    messagebox.showerror("Error", "End date must be after start date")
                    return

                if start < datetime.now():
                    messagebox.showerror("Error", "Start date cannot be in the past")
                    return

            except ValueError:
                messagebox.showerror("Error", "Invalid date format. Please use YYYY-MM-DD")
                return

            if not reason.strip():
                messagebox.showerror("Error", "Please enter a reason for leave")
                return

            # Get current user's ID (you'll need to implement this based on your login system)
            current_user_id = self.get_current_user_id()

            # Submit the request
            request_id = self.leave_manager.request_leave(
                user_id=current_user_id,
                start_date=start_date,
                end_date=end_date,
                reason=reason
            )

            # Clear the form
            self.leave_start_date.delete(0, 'end')
            self.leave_end_date.delete(0, 'end')
            self.leave_reason.delete("1.0", "end")

            messagebox.showinfo("Success",
                                f"Leave request submitted successfully!\nRequest ID: {request_id}")

            # Update leave requests display if you have one
            self.update_leave_requests_display()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to submit leave request: {str(e)}")

    def get_current_user_id(self):
        """Get the current user's ID"""
        # If you store the current user's ID during login, return it here
        # For now, returning a placeholder
        return str(uuid.uuid4())[:8]

    def update_leave_requests_display(self):
        """Update the display of leave requests"""
        if hasattr(self, 'leave_requests_tree'):
            # Clear existing items
            for item in self.leave_requests_tree.get_children():
                self.leave_requests_tree.delete(item)

            # Add current requests
            for request_id, request in self.leave_manager.leave_requests.items():
                if request['user_id'] == self.get_current_user_id():
                    self.leave_requests_tree.insert(
                        "",
                        "end",
                        values=(
                            request_id,
                            request['start_date'],
                            request['end_date'],
                            request['status']
                        )
                    )
    def export_records(self):
        from tkinter import filedialog
        import os
        import platform

        selected_date = self.date_entry.get()
        filename = f"attendance_{selected_date}.json"

        try:
            # Ask user for save location
            default_filename = f"attendance_report_{selected_date}.xlsx"
            export_filename = filedialog.asksaveasfilename(
                initialfile=default_filename,
                defaultextension=".xlsx",
                filetypes=[("Excel Files", "*.xlsx"), ("All Files", "*.*")],
                title="Save Attendance Report As"
            )

            # If user cancels the file dialog
            if not export_filename:
                return

            # Read attendance data
            with open(filename, "r") as f:
                attendance_data = json.load(f)

            # Create a more detailed DataFrame
            data = []
            for user_id, record in attendance_data[selected_date].items():
                department = self.user_data.get(user_id, {}).get('department', 'N/A')

                minutes_late = 0
                if "Late by" in record["status"]:
                    minutes_late = int(record["status"].split("Late by ")[1].split(" ")[0])

                data.append({
                    'ID': user_id,
                    'Name': record['name'],
                    'Department': department,
                    'Time': record['time'],
                    'Status': record['status'],
                    'Minutes Late': minutes_late,
                    'Date': selected_date,
                    'Time Zone': record.get('timezone', 'Asia/Baghdad')
                })

            df = pd.DataFrame(data)

            with pd.ExcelWriter(export_filename, engine='xlsxwriter') as writer:
                # Write the main data
                df.to_excel(writer, sheet_name='Attendance', index=False)

                workbook = writer.book
                worksheet = writer.sheets['Attendance']

                # Add formats
                header_format = workbook.add_format({
                    'bold': True,
                    'align': 'center',
                    'bg_color': '#D3D3D3',
                    'border': 1
                })

                cell_format = workbook.add_format({
                    'align': 'center',
                    'border': 1
                })

                # Format the header
                for col_num, value in enumerate(df.columns.values):
                    worksheet.write(0, col_num, value, header_format)

                # Format all cells
                for row in range(len(df)):
                    for col in range(len(df.columns)):
                        worksheet.write(row + 1, col, df.iloc[row, col], cell_format)

                # Adjust column widths
                for i, col in enumerate(df.columns):
                    max_length = max(
                        df[col].astype(str).apply(len).max(),
                        len(str(col))
                    )
                    worksheet.set_column(i, i, max_length + 2)

                # Add summary statistics
                summary_data = {
                    'Total Entries': len(df),
                    'On Time': len(df[df['Status'] == 'On Time']),
                    'Within Grace Period': len(df[df['Status'] == 'Within Grace Period']),
                    'Late': len(df[df['Status'].str.contains('Late', na=False)]),
                    'Average Minutes Late': df['Minutes Late'].mean()
                }

                # Write summary to new worksheet
                summary_df = pd.DataFrame(list(summary_data.items()),
                                          columns=['Metric', 'Value'])
                summary_df.to_excel(writer, sheet_name='Summary', index=False)

                # Format summary sheet
                summary_sheet = writer.sheets['Summary']
                summary_sheet.set_column('A:A', 20)
                summary_sheet.set_column('B:B', 15)

                # Add charts
                chart_sheet = workbook.add_worksheet('Analytics')

                # Create pie chart for attendance status
                pie_chart = workbook.add_chart({'type': 'pie'})
                status_summary = df['Status'].value_counts()
                pie_chart.add_series({
                    'name': 'Attendance Status',
                    'categories': ['Summary', 1, 0, 4, 0],
                    'values': ['Summary', 1, 1, 4, 1],
                })
                pie_chart.set_title({'name': 'Attendance Status Distribution'})
                chart_sheet.insert_chart('A2', pie_chart)

                # Create bar chart for departmental analysis
                dept_summary = df.groupby('Department').size().reset_index(name='Count')
                dept_summary.to_excel(writer, sheet_name='DeptAnalysis', index=False)

                bar_chart = workbook.add_chart({'type': 'column'})
                bar_chart.add_series({
                    'name': 'Department Attendance',
                    'categories': '=DeptAnalysis!$A$2:$A$' + str(len(dept_summary) + 1),
                    'values': '=DeptAnalysis!$B$2:$B$' + str(len(dept_summary) + 1),
                })
                bar_chart.set_title({'name': 'Attendance by Department'})
                chart_sheet.insert_chart('A18', bar_chart)

            # Open the containing folder and select the file
            export_dir = os.path.dirname(export_filename)
            if platform.system() == "Windows":
                os.system(f'explorer /select,"{export_filename}"')
            elif platform.system() == "Darwin":  # macOS
                os.system(f'open -R "{export_filename}"')
            else:  # Linux
                os.system(f'xdg-open "{export_dir}"')

            messagebox.showinfo("Success",
                                f"Report exported successfully!\n"
                                f"Location: {export_filename}\n"
                                f"Total records: {len(df)}\n"
                                f"Sheets included: Attendance, Summary, Analytics"
                                )

        except FileNotFoundError:
            messagebox.showerror("Error", "No records found for selected date")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export records: {str(e)}")

    def open_exports_folder(self):
        import os
        import platform
        import subprocess

        export_dir = "exports"
        if not os.path.exists(export_dir):
            os.makedirs(export_dir)

        abs_export_dir = os.path.abspath(export_dir)

        try:
            if platform.system() == "Windows":
                os.startfile(abs_export_dir)
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", abs_export_dir])
            else:  # Linux
                subprocess.run(["xdg-open", abs_export_dir])
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open exports folder: {str(e)}")

    def view_records(self):
        selected_date = self.date_entry.get()

        if not self.validate_date(selected_date):
            messagebox.showerror("Error", "Invalid date format. Please use YYYY-MM-DD")
            return

        filename = f"attendance_{selected_date}.json"

        for item in self.records_tree.get_children():
            self.records_tree.delete(item)

        try:
            with open(filename, "r") as f:
                attendance_data = json.load(f)

            if selected_date not in attendance_data or not attendance_data[selected_date]:
                messagebox.showinfo("Info", "No records found for selected date")
                return

            for user_id, data in attendance_data[selected_date].items():
                self.records_tree.insert(
                    "",
                    "end",
                    values=(user_id, data["name"], data["time"], data["status"]),
                )
        except FileNotFoundError:
            messagebox.showinfo("Info", "No records found for selected date")
        except Exception as e:
            messagebox.showerror("Error", f"Error loading records: {str(e)}")

    def save_settings(self):
        """
        Save all application settings including camera and working hours configurations.
        """
        try:
            # Validate and collect all settings before saving
            settings_to_save = {}

            # 1. Camera Settings
            try:
                camera_index = int(self.camera_index.get())
                if camera_index < 0:
                    raise ValueError("Camera index must be non-negative")
                settings_to_save["camera_index"] = camera_index
            except ValueError as e:
                messagebox.showerror("Error", f"Invalid camera index: {str(e)}")
                return False

            # 2. Working Hours Settings
            try:
                start_time = self.clean_time_format(self.start_time.get())
                end_time = self.clean_time_format(self.end_time.get())

                # Validate time order
                start_dt = datetime.strptime(start_time, "%H:%M")
                end_dt = datetime.strptime(end_time, "%H:%M")
                if end_dt <= start_dt:
                    raise ValueError("End time must be after start time")

                settings_to_save["working_hours"] = {
                    "start": start_time,
                    "end": end_time
                }
            except ValueError as e:
                messagebox.showerror("Error", f"Invalid working hours: {str(e)}")
                return False

            # 3. Grace Period Settings
            try:
                grace_period = int(self.grace_period.get())
                if grace_period < 0:
                    raise ValueError("Grace period must be non-negative")
                settings_to_save["grace_period_minutes"] = grace_period
            except ValueError as e:
                messagebox.showerror("Error", f"Invalid grace period: {str(e)}")
                return False

            # 4. Attendance Settings
            settings_to_save["attendance_threshold"] = 0.6  # Default threshold
            settings_to_save["auto_capture"] = False  # Default auto capture setting
            settings_to_save["notification_enabled"] = True  # Default notification setting
            settings_to_save["timezone"] = "Asia/Baghdad"  # Default timezone

            # 5. Save all settings to main settings file
            try:
                self.settings.update(settings_to_save)
                with open("settings.json", "w") as f:
                    json.dump(self.settings, f, indent=4)

                # Create a backup of settings
                backup_time = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_file = f"settings_backup_{backup_time}.json"
                with open(backup_file, "w") as f:
                    json.dump(self.settings, f, indent=4)

                # Log the settings change
                self.log_settings_change(self.settings)

                messagebox.showinfo("Success",
                                    "Settings saved successfully!\n\n"
                                    "Please restart the application for some changes to take effect.")
                return True

            except Exception as e:
                messagebox.showerror("Error", f"Failed to save settings: {str(e)}")
                return False

        except Exception as e:
            messagebox.showerror("Error", f"Unexpected error while saving settings: {str(e)}")
            return False

    def log_settings_change(self, new_settings):
        """Log settings changes for auditing purposes"""
        try:
            log_dir = "logs"
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)

            log_file = os.path.join(log_dir, "settings_changes.log")
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            with open(log_file, "a") as f:
                f.write(f"\n{'=' * 50}\n")
                f.write(f"Settings changed at: {timestamp}\n")
                f.write(f"Changed by user: {getpass.getuser()}\n")
                f.write("New settings:\n")
                f.write(json.dumps(new_settings, indent=2))
                f.write("\n")

        except Exception as e:
            print(f"Failed to log settings change: {str(e)}")

    def on_closing(self):
        if self.camera is not None:
            self.camera.release()
        self.root.destroy()

    # Main execution


def main():
    def launch_main_app(department):
        root = ctk.CTk()
        app = FaceAttendanceSystem(root, department)  # Now this will work correctly
        root.mainloop()

    login_window = TeacherLogin(launch_main_app)
    login_window.window.mainloop()

if __name__ == "__main__":
    main()
