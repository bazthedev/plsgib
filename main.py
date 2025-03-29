import os
import glob
import shutil
import tempfile
import re
import os
import json
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import psutil
import random
import requests
from datetime import datetime
import discord
import sys
import pynput
import mousekey
import screeninfo as si
import webbrowser

MACROPATH = os.path.expandvars(r"%localappdata%\plsgib") # Windows Roaming Path
LOCALVERSION = "1.0.2"
DEFAULTSETTINGS = {"WEBHOOK_URL" : "", "__version__" : LOCALVERSION, "say_random_stuff" : True, "stuff_to_say" : ["pls gib", "goal progress: {goal_progress}"], "thank_you_messages" : ["tysm {donor}", "ty!", "ty", "thanks!"], "do_emotes" : True, "emotes" : ["dance", "dance2", "dance3", "wave"], "goal" : 0, "goal_progress" : 0, "booth_msg" : "goal: {goal_progress}", "goal_reached_msg" : "goal reached tysm!", "1_rbx_1_jump" : False, "failsafe_key" : "ctrl+e", "viewed_warning" : False}
VALIDSETTINGSKEYS = ["WEBHOOK_URL", "__version__", "say_random_stuff", "stuff_to_say", "thank_you_messages", "do_emotes", "emotes", "goal", "goal_progress", "booth_msg", "goal_reached_msg", "1_rbx_1_jump", "failsafe_key", "viewed_warning"]

RBLXPLAYER_LOGSDIR = os.path.expandvars(r"%localappdata%\Roblox\logs") # This is for the Roblox Player
MSRBLX_LOGSDIR = os.path.expandvars(r"%LOCALAPPDATA%\Packages\ROBLOXCorporation.ROBLOX_55nm5eh3cm0pr\LocalState\logs") # This is for the Microsoft Store version of Roblox
MACROTITLE = "plsgib"
WB_ICON_URL = "https://raw.githubusercontent.com/bazthedev/plsgib/0b16f0c28dc0a1382d02d01966e0aed24887f3f5/plsgib.png"

GLOBAL_LOGGER = None

previous_dono = {"donor" : "", "amount": 0, "recipient" : "", "timestamp" : "1970-1-1T0:0:0.0"}
current_players_info = {}
_KEYBOARD = pynput.keyboard.Controller()
mkey = mousekey.MouseKey()
screens = si.get_monitors()
monitor = None
for mon in screens:
    if mon.is_primary:
        monitor = mon
scale_w = monitor.width / 2560
scale_h = monitor.height / 1440

booth_edit_text_pos = ((1610 * scale_w), (674 * scale_h))
booth_close_pos = ((1660 * scale_w), (478 * scale_h))

class SettingsApp:
    def __init__(self, root):
        global GLOBAL_LOGGER
        self.root = root
        self.root.title(f"{MACROTITLE} v{LOCALVERSION}")

        try:
            self.root.iconbitmap(f"{MACROPATH}/icon.ico")
        except Exception:
            pass

        self.webhook = None
        self.previous_message = None

        self.original_settings = self.load_settings()
        self.entries = {}
        self.listbox_refs = {}

        self.threads = []
        self.running = False
        self.keyboard_lock = threading.Lock()
        self.pause_event = threading.Event()
        self.stop_event = threading.Event()

        self.create_ui()

        GLOBAL_LOGGER = self.logger

    class Logger:
        def __init__(self, text_widget):
            self.text_widget = text_widget
            self.write_log(f"Initialising {MACROTITLE}\n")

        def write_log(self, message):
            self.text_widget.configure(state='normal')
            self.text_widget.insert(tk.END, message + "\n")
            self.text_widget.see(tk.END)
            self.text_widget.configure(state='disabled')
        

    def load_settings(self):
        try:
            with open(f"{MACROPATH}/settings.json", "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def create_ui(self):
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True)

        settings_frame = ttk.Frame(notebook)
        notebook.add(settings_frame, text="Settings")

        logs_frame = ttk.Frame(notebook)
        notebook.add(logs_frame, text="Logs")

        self.logs_text = tk.Text(logs_frame, wrap="word", state="disabled", bg="#f0f0f0", height=20)
        self.logs_text.pack(fill=tk.BOTH, expand=True)

        self.logger = self.Logger(self.logs_text)

        container = ttk.Frame(settings_frame)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        canvas = tk.Canvas(container)
        scrollbar = ttk.Scrollbar(container, orient=tk.VERTICAL, command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.create_widgets(self.original_settings, self.scrollable_frame)

        button_frame = ttk.Frame(self.root)
        button_frame.pack(pady=10)

        save_button = ttk.Button(button_frame, text="Save and Start", command=self.start_macro)
        save_button.pack(side=tk.LEFT, padx=5)

        stop_button = ttk.Button(button_frame, text="Stop Macro", command=self.stop_macro)
        stop_button.pack(side=tk.LEFT, padx=5)

    def create_widgets(self, settings, parent):
        row = ttk.Frame(parent)
        row.pack(fill=tk.X, pady=5)
        label = ttk.Label(row, text=f"{MACROTITLE} v{LOCALVERSION}", width=25, anchor="w")
        label.pack(side=tk.LEFT)

        for key, value in settings.items():
            if key == "viewed_warning" or key == "__version__":
                continue
            row = ttk.Frame(parent)
            row.pack(fill=tk.X, pady=5)

            label = ttk.Label(row, text=f"{key}:", width=25, anchor="w")
            label.pack(side=tk.LEFT)

            if isinstance(value, bool):
                var = tk.BooleanVar(value=value)
                checkbox = ttk.Checkbutton(row, variable=var)
                checkbox.pack(side=tk.LEFT)
                self.entries[key] = var

            elif isinstance(value, list):
                self.create_list_widget(row, key, value)
            else:
                var = tk.StringVar(value=str(value))
                entry = ttk.Entry(row, textvariable=var, width=30)
                entry.pack(side=tk.LEFT)
                self.entries[key] = var

        row = ttk.Frame(parent)
        row.pack(fill=tk.X, pady=5)
        label = ttk.Label(row, text=f"{MACROTITLE} made by Baz", width=25, anchor="w")
        label.pack(side=tk.LEFT)

    def create_list_widget(self, parent, key, items):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, expand=True)

        listbox = tk.Listbox(frame, height=5, selectmode=tk.SINGLE)
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        for item in items:
            listbox.insert(tk.END, item)

        self.entries[key] = items
        self.listbox_refs[key] = listbox

        button_frame = ttk.Frame(frame)
        button_frame.pack(side=tk.RIGHT, padx=5)

        add_entry = ttk.Entry(button_frame, width=15)
        add_entry.pack(pady=2)

        add_button = ttk.Button(button_frame, text="Add", command=lambda: self.add_to_list(key, add_entry))
        add_button.pack(pady=2)

        remove_button = ttk.Button(button_frame, text="Remove", command=lambda: self.remove_from_list(key))
        remove_button.pack(pady=2)

    def add_to_list(self, key, entry):
        new_item = entry.get().strip()
        if new_item:
            listbox = self.listbox_refs[key]
            if new_item not in self.entries[key]:
                self.entries[key].append(new_item)
                listbox.insert(tk.END, new_item)
                entry.delete(0, tk.END)

    def remove_from_list(self, key):
        listbox = self.listbox_refs[key]
        selection = listbox.curselection()

        if selection:
            index = selection[0]
            listbox.delete(index)
            self.entries[key].pop(index)

    
    def start_macro(self):
        changes = self.save_settings()
        reload_settings()

        if changes:
            GLOBAL_LOGGER.write_log("Changes detected and saved.")
        else:
            GLOBAL_LOGGER.write_log("No changes detected.")

        if self.running:
            messagebox.showerror("Error", "Macro is already running!")
            return

        if settings["WEBHOOK_URL"] == "":
            messagebox.showerror("Error", "You need to provide a Webhook URL")
            return

        self.webhook = discord.Webhook.from_url(settings["WEBHOOK_URL"], adapter=discord.RequestsWebhookAdapter())

        self.running = True
        self.stop_event.clear()

        threading.Thread(target=self._run_macro, daemon=True).start()

    def _run_macro(self):
        GLOBAL_LOGGER.write_log("Starting Macro in 5 seconds")
        for _ in range(5):
            if self.stop_event.is_set():
                GLOBAL_LOGGER.write_log("Macro stopped before starting.")
                self.running = False
                return
            time.sleep(1)

        if settings["booth_msg"] != "":
            if settings["goal_progress"] >= settings["goal"]:
                GLOBAL_LOGGER.write_log("Your goal has already been completed. You may want to update this in the settings.")
                self.edit_booth_text(settings["goal_reached_msg"])
            else:
                if "{goal_progress}" in settings["booth_msg"].lower() and settings["goal_progress"] < settings["goal"]:
                    self.edit_booth_text(settings["booth_msg"].replace("{goal_progress}", f"{str(settings['goal_progress'])}/{str(settings['goal'])}"))
                else:
                    self.edit_booth_text(settings["booth_msg"])
            time.sleep(2)

        previous_thread = None
        for i in range(4):
            if self.stop_event.is_set():
                break

            if i == 0:
                GLOBAL_LOGGER.write_log("Starting Donation Detection")
                thread = threading.Thread(target=self.donation_detection, daemon=True)
                GLOBAL_LOGGER.write_log("Started Donation Detection")
            elif i == 2 and settings["say_random_stuff"] and len(settings["stuff_to_say"]) > 0:
                GLOBAL_LOGGER.write_log("Starting Periodic Chat Messages")
                thread = threading.Thread(target=self.periodic_chat_messages, daemon=True)
                GLOBAL_LOGGER.write_log("Started Periodic Chat Messages")
            elif i == 3 and settings["do_emotes"]:
                GLOBAL_LOGGER.write_log("Starting Periodic Emotes")
                thread = threading.Thread(target=self.do_emotes, daemon=True)
                GLOBAL_LOGGER.write_log("Started Periodic Emotes")
            elif i == 1:
                GLOBAL_LOGGER.write_log("Starting Player Detection")
                thread = threading.Thread(target=self.monitor_logs, args=(rblx_log_dir, userdata), daemon=True)
            
            if thread != previous_thread:
                thread.start()
                self.threads.append(thread)
            previous_thread = thread

        GLOBAL_LOGGER.write_log("Macro has started.")
        emb = discord.Embed(
            title=f"{MACROTITLE} has started.",
            description=f"Detected user: {userdata['name']} ({userdata['displayName']})",
            colour=discord.Colour.green()
        )
        emb.set_thumbnail(url=get_user_headshot_from_userdata(userdata))
        emb.set_footer(text=f"{MACROTITLE} v{LOCALVERSION}", icon_url=WB_ICON_URL)
        self.webhook.send(username=f"{MACROTITLE} Notifications", embed=emb)

    def stop_macro(self):
        if not self.running:
            messagebox.showerror("Error", "Macro is not running!")
            return

        GLOBAL_LOGGER.write_log("Stopping Macro...")
        self.stop_event.set()

        for thread in self.threads:
            thread.join(timeout=1)

        self.threads.clear()
        self.running = False

        GLOBAL_LOGGER.write_log("Connection terminated. I'm sorry Elizabeth...")
        emb = discord.Embed(
            title=f"{MACROTITLE} has stopped.",
            colour=discord.Colour.red()
        )
        emb.set_footer(text=f"{MACROTITLE} v{LOCALVERSION}", icon_url=WB_ICON_URL)
        self.webhook.send(username=f"{MACROTITLE} Notifications", embed=emb)
        messagebox.showinfo(MACROTITLE, "Macro has been stopped.")

    def get_updated_values(self, original, entries):
        updated_settings = {}

        for key, widget in entries.items():
            if isinstance(widget, list):
                updated_settings[key] = widget
            elif isinstance(widget, tk.BooleanVar):
                updated_settings[key] = widget.get()
            elif isinstance(widget, tk.StringVar):
                new_value = widget.get()
                if isinstance(original.get(key), bool):
                    new_value = new_value.lower() == "true"
                elif isinstance(original.get(key), (int, float)):
                    try:
                        new_value = int(new_value)
                    except ValueError:
                        try:
                            new_value = float(new_value)
                        except ValueError:
                            pass

                if new_value != original.get(key):
                    updated_settings[key] = new_value

        return updated_settings

    def save_settings(self):
        updated_values = self.get_updated_values(self.original_settings, self.entries)

        if updated_values:
            try:
                with open(f"{MACROPATH}/settings.json", "w") as f:
                    json.dump({**self.original_settings, **updated_values}, f, indent=4)
                self.original_settings.update(updated_values)
                messagebox.showinfo(MACROTITLE, "Settings saved successfully!")
            except Exception as e:
                messagebox.showerror(MACROTITLE, f"Failed to save settings:\n{e}")
        return updated_values

    def donation_detection(self):
        global previous_dono
        while not self.stop_event.is_set():
            if self.pause_event.is_set():
                self.pause_event.wait(0.5)
                continue

            latest_dono = get_latest_donation(rblx_log_dir)
            if latest_dono == None:
                continue

            try:
                if (latest_dono["recipient"] == userdata["displayName"] 
                    and latest_dono["timestamp"] > previous_dono["timestamp"]):

                    GLOBAL_LOGGER.write_log(f"Donation Detected at time: {str(latest_dono['timestamp'])}\n"
                                        f"Donated to: {latest_dono['recipient']}\n"
                                        f"Amount: {str(latest_dono['amount'])}\n"
                                        f"Donor: {latest_dono['donor']}")

                    previous_dono = latest_dono

                    emb = discord.Embed(
                        title="Donation Received!",
                        description=f"You were sent {latest_dono['amount']} by {latest_dono['donor']} at {latest_dono['timestamp']}",
                        colour=discord.Colour.from_rgb(255, 255, 255)
                    )
                    emb.set_thumbnail(url=get_user_headshot_from_userdata(current_players_info[latest_dono["donor"]]))
                    emb.set_footer(text=f"{MACROTITLE} v{LOCALVERSION}", icon_url=WB_ICON_URL)
                    self.webhook.send(username=f"{MACROTITLE} Notifications", embed=emb)

                    if len(settings["thank_you_messages"]) > 0:
                        self.pause_event.set()
                        self.thank_user(latest_dono["donor"])
                        self.pause_event.clear()

                    if settings["1_rbx_1_jump"] and not (settings["do_emotes"] or settings["say_random_stuff"]):
                        for _ in range(latest_dono["amount"] + 1):
                            if self.stop_event.is_set():
                                return
                            with self.keyboard_lock:
                                _KEYBOARD.press(pynput.keyboard.Key.space)
                                time.sleep(0.2)
                                _KEYBOARD.release(pynput.keyboard.Key.space)
                                time.sleep(0.2)

            except Exception as e:
                GLOBAL_LOGGER.write_log(f"Error in donation detection: {e}")

    def periodic_chat_messages(self):
        while not self.stop_event.is_set():
            if self.pause_event.is_set():
                self.pause_event.wait(0.5)
                continue

            msg = random.choice(settings["stuff_to_say"])
            if msg == self.previous_message:
                continue

            if "{goal_remainder}" in msg:
                msg = msg.replace("{goal_remainder}", f"{settings['goal'] - settings['goal_progress']}")
            if "{goal_progress}" in msg:
                msg = msg.replace("{goal_progress}", f"{settings['goal_progress']}/{settings['goal']}")

            self.send_message(msg)
            self.previous_message = msg
            time.sleep(random.randint(100, 180))
        
    def thank_user(self, user):
        msg = random.choice(settings["thank_you_messages"])
        with self.keyboard_lock:
            self.send_message(msg.replace("{donor}", f"{user.lower()}"))

    def do_emotes(self):
        while not self.stop_event.is_set():
            if self.pause_event.is_set():
                self.pause_event.wait(0.5)
                continue

            emote = random.choice(settings["emotes"])
            self.send_message(f"/e {emote}")
            time.sleep(random.randint(59, 73))

    def send_message(self, message):
        if self.stop_event.is_set():
            return

        with self.keyboard_lock:
            _KEYBOARD.press("/")
            time.sleep(0.1)
            _KEYBOARD.release("/")
            time.sleep(0.2)

            for char in message:
                _KEYBOARD.press(char)
                _KEYBOARD.release(char)
                time.sleep(0.05)

            time.sleep(0.1)
            _KEYBOARD.press(pynput.keyboard.Key.enter)
            time.sleep(0.05)
            _KEYBOARD.release(pynput.keyboard.Key.enter)
            time.sleep(0.1)
    
    def edit_booth_text(self, text):
        if self.stop_event.is_set():
            return

        with self.keyboard_lock:
            _KEYBOARD.press("e")
            time.sleep(3)
            _KEYBOARD.release("e")
            time.sleep(0.3)

            mkey.left_click_xy_natural(booth_edit_text_pos[0], booth_edit_text_pos[1], print_coords=False)
            time.sleep(0.5)

            mkey.left_click_xy_natural(booth_edit_text_pos[0], booth_edit_text_pos[1], print_coords=False)
            time.sleep(0.5)

            _KEYBOARD.press(pynput.keyboard.Key.ctrl)
            _KEYBOARD.press("a")
            time.sleep(0.2)
            _KEYBOARD.release("a")
            _KEYBOARD.release(pynput.keyboard.Key.ctrl)
            time.sleep(0.5)

            for char in text:
                _KEYBOARD.press(char)
                _KEYBOARD.release(char)
                time.sleep(0.05)

            time.sleep(0.5)
            mkey.left_click_xy_natural(booth_close_pos[0], booth_close_pos[1], print_coords=False)
            time.sleep(0.5)
            mkey.left_click_xy_natural(booth_close_pos[0], booth_close_pos[1], print_coords=False)

    def update_goal(self, donation):
        settings["goal_progress"] += donation
        update_settings(settings)
        reload_settings()
        if settings["goal_progress"] >= settings["goal"] and settings["goal_reached_msg"] != "":
            self.edit_booth_text(settings["goal_reached_msg"])
        if "{goal_progress}" in settings["booth_msg"].lower() and settings["goal_progress"] < settings["goal"]:
            self.edit_booth_text(settings["booth_msg"].replace("{goal_progress}", f"{str(settings['goal_progress'])}/{str(settings['goal'])}"))


    def fetch_user_data(self, username):
            url = "https://users.roblox.com/v1/usernames/users"
            headers = {"Content-Type": "application/json"}
            payload = {"usernames": [username], "excludeBannedUsers": True}

            try:
                response = requests.post(url, headers=headers, json=payload)
                if response.status_code == 200:
                    data = response.json()
                    if "data" in data and data["data"]:
                        return data["data"][0]
            except Exception as e:
                GLOBAL_LOGGER.write_log(f"Error fetching userdata: {e}")

            return None

    def find_latest_main_player_join(self, temp_file, main_username):
        pattern_add = re.compile(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z).*?playerlistdbg, adding player @(\w+)", re.MULTILINE)

        try:
            with open(temp_file, "r", encoding="utf-8", errors="ignore") as file:
                lines = file.readlines()

            for line in reversed(lines):
                match = pattern_add.search(line)
                if match:
                    timestamp, username = match.groups()
                    if username == main_username:
                        return timestamp

        except Exception as e:
            GLOBAL_LOGGER.write_log(f"Error reading logs: {e}")

        return None

    def monitor_logs(self, logs_dir, userdata):
        global current_players_info
        main_username = userdata["name"]

        pattern_add = re.compile(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z).*?playerlistdbg, adding player @(\w+)", re.MULTILINE)
        pattern_remove = re.compile(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z).*?playerlistdbg, removing player @(\w+)", re.MULTILINE)

        joined_players = set()
        left_players = set()
        last_processed_timestamp = None

        GLOBAL_LOGGER.write_log("Processing players currently in the server...")
        while not self.stop_event.is_set():
            log_files = glob.glob(os.path.join(logs_dir, "*.log"))
            if not log_files:
                GLOBAL_LOGGER.write_log("No log files found.")
                time.sleep(5)
                continue

            latest_log_file = max(log_files, key=os.path.getctime)

            try:
                temp_file = os.path.join(tempfile.gettempdir(), "plsgib_pl.log")
                shutil.copy2(latest_log_file, temp_file)
            except PermissionError:
                GLOBAL_LOGGER.write_log("Permission denied while accessing log files.")
                time.sleep(5)
                continue

            last_main_player_join_time = self.find_latest_main_player_join(temp_file, main_username)

            if not last_main_player_join_time:
                GLOBAL_LOGGER.write_log("Main player has not joined recently.")
                current_players_info.clear()
                joined_players.clear()
                left_players.clear()
                time.sleep(5)
                continue

            try:
                with open(temp_file, "r", encoding="utf-8", errors="ignore") as file:
                    lines = file.readlines()

                found_main_player_join = False
                new_events_detected = False
                latest_event_timestamp = last_processed_timestamp

                for line in lines:
                    add_match = pattern_add.search(line)
                    remove_match = pattern_remove.search(line)

                    if add_match:
                        timestamp, username = add_match.groups()

                        if timestamp >= last_main_player_join_time:
                            found_main_player_join = True

                        if not found_main_player_join or (last_processed_timestamp and timestamp <= last_processed_timestamp):
                            continue

                        if username == main_username:
                            continue

                        if username in left_players:
                            left_players.remove(username)

                        if username not in joined_players:
                            joined_players.add(username)

                            if username not in current_players_info:
                                user_data = self.fetch_user_data(username)
                                if user_data:
                                    display_name = user_data.get("displayName", "Unknown")
                                    current_players_info[display_name] = user_data
                                    GLOBAL_LOGGER.write_log(f"Fetched user data for player {display_name}.")
                                    new_events_detected = True

                        latest_event_timestamp = timestamp

                    elif remove_match:
                        timestamp, username = remove_match.groups()

                        if timestamp < last_main_player_join_time or (last_processed_timestamp and timestamp <= last_processed_timestamp):
                            continue

                        if username == main_username:
                            current_players_info.clear()
                            joined_players.clear()
                            left_players.clear()
                            GLOBAL_LOGGER.write_log(f"Main player '{main_username}' left. Resetting list.")
                            latest_event_timestamp = timestamp
                            break

                        if username in joined_players:
                            joined_players.remove(username)
                            left_players.add(username)

                            for display_name, data in list(current_players_info.items()):
                                if data["name"] == username:
                                    del current_players_info[display_name]
                                    GLOBAL_LOGGER.write_log(f"{display_name} has disconnected.")
                                    new_events_detected = True
                                    break

                        latest_event_timestamp = timestamp

                if new_events_detected:
                    last_processed_timestamp = latest_event_timestamp

            except Exception as e:
                GLOBAL_LOGGER.write_log(f"Error processing log file: {e}")

            time.sleep(2)







root = tk.Tk()
app = SettingsApp(root)
root.withdraw()

def exists_procs_by_name(name):
    for p in psutil.process_iter(['name']):
        if p.info['name'].lower() == name.lower():
            return True
    return False

def update_settings(settings):
    with open(f"{MACROPATH}/settings.json", "w") as f:
        json.dump(settings, f, indent=4)

def reload_settings():
    global settings
    with open(f"{MACROPATH}/settings.json", "r") as f:
        settings = json.load(f)

def validate_settings():
    found_keys = []
    todel = []
    for k in settings.keys():
        if k not in VALIDSETTINGSKEYS:
            todel.append(k)
            GLOBAL_LOGGER.write_log(f"Invalid setting ({k}) detected")
        else:
            found_keys.append(k)
    for _ in todel:
        del settings[_]
        GLOBAL_LOGGER.write_log(f"Invalid setting ({_}) deleted")
    for _ in VALIDSETTINGSKEYS:
        if _ not in found_keys:
            settings[_] = DEFAULTSETTINGS[_]
            GLOBAL_LOGGER.write_log(f"Missing setting ({_}) added")
    update_settings(settings)
    reload_settings()

if exists_procs_by_name("Windows10Universal.exe"):
    rblx_log_dir = MSRBLX_LOGSDIR
    GLOBAL_LOGGER.write_log("Using Microsoft Store Roblox (detected as running)")
elif exists_procs_by_name("RobloxPlayerBeta.exe"):
    rblx_log_dir = RBLXPLAYER_LOGSDIR
    GLOBAL_LOGGER.write_log("Using Roblox Player (detected as running)")
else:
    messagebox.showerror(MACROTITLE, "Roblox is not running.")
    sys.exit()


def get_latest_donation(logs_dir):
    log_files = glob.glob(os.path.join(logs_dir, "*.log"))
    if not log_files:
        return None

    latest_log_file = max(log_files, key=os.path.getctime)

    try:
        temp_file = os.path.join(tempfile.gettempdir(), "plsgib_dd.log")
        shutil.copy2(latest_log_file, temp_file)
    except PermissionError:
        GLOBAL_LOGGER.write_log("Permission denied while accessing log files.")
        return None

    donation_pattern = re.compile(r'💰\s+(\w+)\s+tipped\s+.*?(\d+)\s+to\s+(\w+)')
    global_pattern = re.compile(r'<b>\[GLOBAL\]: </b>')
    timestamp_pattern = re.compile(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z)')

    latest_donation = None

    try:
        with open(temp_file, "r", encoding="utf-8", errors="ignore") as file:
            for line in reversed(file.readlines()):
                if global_pattern.search(line):
                    continue
                match = donation_pattern.search(line)
                if match:
                    donor, amount, recipient = match.groups()

                    timestamp_match = timestamp_pattern.search(line)
                    
                    if not timestamp_match:
                        prev_line_idx = file.tell() - len(line)
                        if prev_line_idx >= 0:
                            file.seek(prev_line_idx)
                            prev_line = file.readline()
                            timestamp_match = timestamp_pattern.search(prev_line)

                    if timestamp_match:
                        timestamp_str = timestamp_match.group(1)
                        timestamp = datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%S.%fZ")
                    else:
                        timestamp = None

                    latest_donation = {
                        "donor": donor,
                        "amount": int(amount),
                        "recipient": recipient,
                        "timestamp": timestamp.isoformat() if timestamp else "Unknown"
                    }
                    return latest_donation
    except Exception as e:
        GLOBAL_LOGGER.write_log(f"An error occurred: {e}")
        return None

    return latest_donation

def get_user_info_from_logs(logs_dir):
    log_files = glob.glob(os.path.join(logs_dir, "*.log"))
    if not log_files:
        GLOBAL_LOGGER.write_log("No log files found.")
        return None

    latest_log_file = max(log_files, key=os.path.getctime)

    try:
        temp_file = os.path.join(tempfile.gettempdir(), "plsgib_userinfo.log")
        shutil.copy2(latest_log_file, temp_file)
    except PermissionError:
        GLOBAL_LOGGER.write_log("Permission denied while accessing log files.")
        return None

    username = None
    pattern = r"playerlistdbg, adding player @(\w+)"

    try:
        with open(temp_file, "r", encoding="utf-8", errors="ignore") as file:
            for line in file:
                match = re.search(pattern, line)
                if match:
                    username = match.group(1)
                    break

        if not username:
            GLOBAL_LOGGER.write_log("No username found in the log.")
            return None

        url = "https://users.roblox.com/v1/usernames/users"
        headers = {
            "Content-Type": "application/json"
        }
        payload = {
            "usernames": [username],
            "excludeBannedUsers": True
        }

        response = requests.post(url, headers=headers, data=json.dumps(payload))

        if response.status_code == 200:
            data = response.json()
            if "data" in data and data["data"]:
                return data["data"][0]
            else:
                GLOBAL_LOGGER.write_log("No data returned for the username.")
                return None
        else:
            GLOBAL_LOGGER.write_log(f"Failed to retrieve user info: {response.status_code} - {response.text}")
            return None

    except Exception as e:
        GLOBAL_LOGGER.write_log(f"An error occurred: {e}")
        return None
    
    
def get_user_headshot_from_userdata(userdata: dict):
    if not userdata or "id" not in userdata:
        return None

    user_id = userdata["id"]
    
    url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size=150x150&format=Png"
    
    response = requests.get(url)
    return response.json()["data"][0]["imageUrl"]

    
if not os.path.exists(f"{MACROPATH}"):
    os.mkdir(MACROPATH)

if not os.path.isfile(f"{MACROPATH}/settings.json"):
    with open(f"{MACROPATH}/settings.json", "w") as f:
        json.dump(DEFAULTSETTINGS, f, indent=4)

if not os.path.isfile(f"{MACROPATH}/icon.ico"):
    dl = requests.get("https://raw.githubusercontent.com/bazthedev/plsgib/main/plsgib.ico")
    f = open(f"{MACROPATH}/icon.ico", "wb")
    f.write(dl.content)
    f.close()

reload_settings()

new_ver = requests.get(f"https://api.github.com/repos/bazthedev/plsgib/releases/latest")
new_ver_str = new_ver.json()["name"]

if settings["__version__"] < LOCALVERSION:
    settings["__version__"] = LOCALVERSION
    update_settings(settings)
    reload_settings()
    GLOBAL_LOGGER.write_log(f"The macro has been updated to version {LOCALVERSION}!")

if LOCALVERSION < new_ver_str:
    confirm_dl = messagebox.askyesno(MACROTITLE, f"A new version has been found ({new_ver_str}), would you like to visit the GitHub page to download it? ")
    if confirm_dl:
        webbrowser.open("https://github.com/bazthedev/plsgib/releases/latest")

validate_settings()
if not settings["viewed_warning"]:
    ask_proceed = messagebox.askyesno(f"{MACROTITLE} - WARNING", "WARNING!\nTHIS MACRO IS ARGUABLY BOTTING, WHICH CAN POTENTIALLY GET YOU BANNED FROM PLS DONATE!\nARE YOU SURE YOU WISH TO PROCEED?")
    if ask_proceed:
        settings["viewed_warning"] = True
        update_settings(settings)
        reload_settings()
    else:
        sys.exit()
try:
    mkey.enable_failsafekill(settings["failsafe_key"])
except Exception as e:
    messagebox.showerror(MACROTITLE, f"A fatal error has occured.\nError Details:\n{e}")
    sys.exit()
userdata = get_user_info_from_logs(rblx_log_dir)
if userdata == None:
    messagebox.showerror(MACROTITLE, "You probably aren't in pls donate, join the game and then rerun this script.")
    sys.exit()


GLOBAL_LOGGER.write_log(f"\nDetected user information:\n\nUsername: {userdata['name']}\nDisplay Name: {userdata['displayName']}\nUser ID: {userdata['id']}\n")
GLOBAL_LOGGER.write_log(f"Starting {MACROTITLE}")
GLOBAL_LOGGER.write_log(f"Opened {MACROTITLE} menu")
root.deiconify()
root.mainloop()
