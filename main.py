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
from win10toast import ToastNotifier

MACROPATH = os.path.expandvars(r"%localappdata%\plsgib") # Windows Roaming Path
LOCALVERSION = "1.0.0"
DEFAULTSETTINGS = {"WEBHOOK_URL" : "", "__version__" : LOCALVERSION, "say_random_stuff" : True, "stuff_to_say" : ["pls gib", "goal progress: {goal_progress}"], "thank_you_messages" : ["tysm {donor}", "ty!", "ty", "thanks!"], "do_emotes" : True, "emotes" : ["dance1", "dance2", "dance3", "wave"], "goal" : 0, "goal_progress" : 0, "booth_msg" : "goal: {goal_progress}", "goal_reached_msg" : "goal reached tysm!", "1_rbx_1_jump" : False, "failsafe_key" : "ctrl+e"}
VALIDSETTINGSKEYS = ["WEBHOOK_URL", "__version__", "say_random_stuff", "stuff_to_say", "thank_you_messages", "do_emotes", "emotes", "goal", "goal_progress", "booth_msg", "goal_reached_msg", "1_rbx_1_jump", "failsafe_key"]

RBLXPLAYER_LOGSDIR = os.path.expandvars(r"%localappdata%\Roblox\logs") # This is for the Roblox Player
MSRBLX_LOGSDIR = os.path.expandvars(r"%LOCALAPPDATA%\Packages\ROBLOXCorporation.ROBLOX_55nm5eh3cm0pr\LocalState\logs") # This is for the Microsoft Store version of Roblox
TOAST = ToastNotifier()
MACROTITLE = "plsgib"

previous_dono = {"donor" : "", "amount": 0, "recipient" : "", "timestamp" : "1970-1-1T0:0:0.0"}
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
            print(f"Invalid setting ({k}) detected")
        else:
            found_keys.append(k)
    for _ in todel:
        del settings[_]
        print(f"Invalid setting ({_}) deleted")
    for _ in VALIDSETTINGSKEYS:
        if _ not in found_keys:
            settings[_] = DEFAULTSETTINGS[_]
            print(f"Missing setting ({_}) added")
    update_settings(settings)
    reload_settings()

if exists_procs_by_name("Windows10Universal.exe"):
    rblx_log_dir = MSRBLX_LOGSDIR
    print("Using Microsoft Store Roblox (detected as running)")
elif exists_procs_by_name("RobloxPlayerBeta.exe"):
    rblx_log_dir = RBLXPLAYER_LOGSDIR
    print("Using Roblox Player (detected as running)")
else:
    messagebox.showerror(MACROTITLE, "Roblox is not running.")
    sys.exit()


def get_latest_donation(logs_dir):
    log_files = glob.glob(os.path.join(logs_dir, "*.log"))
    if not log_files:
        return None

    latest_log_file = max(log_files, key=os.path.getctime)

    try:
        temp_file = os.path.join(tempfile.gettempdir(), "pls_donate_macro.log")
        shutil.copy2(latest_log_file, temp_file)
    except PermissionError:
        print("Permission denied while accessing log files.")
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
        print(f"An error occurred: {e}")
        return None

    return latest_donation

def get_user_info_from_logs(logs_dir):
    log_files = glob.glob(os.path.join(logs_dir, "*.log"))
    if not log_files:
        print("No log files found.")
        return None

    latest_log_file = max(log_files, key=os.path.getctime)

    try:
        temp_file = os.path.join(tempfile.gettempdir(), "pls_donate_macro.log")
        shutil.copy2(latest_log_file, temp_file)
    except PermissionError:
        print("Permission denied while accessing log files.")
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
            print("No username found in the log.")
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
                print("No data returned for the username.")
                return None
        else:
            print(f"Failed to retrieve user info: {response.status_code} - {response.text}")
            return None

    except Exception as e:
        print(f"An error occurred: {e}")
        return None
    

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
validate_settings()
try:
    mkey.enable_failsafekill(settings["failsafe_key"])
except Exception as e:
    messagebox.showerror(MACROTITLE, f"A fatal error has occured.\nError Details:\n{e}")
    sys.exit()
userdata = get_user_info_from_logs(rblx_log_dir)
if userdata == None:
    messagebox.showerror(MACROTITLE, "You probably aren't in pls donate, join the game and then rerun this script.")
    sys.exit()
print(f"Detected user information:\n\nUsername: {userdata['name']}\nDisplay Name: {userdata['displayName']}")

class SettingsApp:
    def __init__(self, root):
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
        self.stop_event = threading.Event()
    

        self.create_ui()

    def load_settings(self):
        try:
            with open(f"{MACROPATH}/settings.json", "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def create_ui(self):
        container = ttk.Frame(self.root)
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

    def start_macro(self):
        changes = self.save_settings()
        
        reload_settings()
        if changes:
            print("Changes detected and saved.")
        else:
            print("No changes detected.")

        
        if self.running:
            messagebox.showerror("Error", "Macro is already running!")
            return
        
        if settings["WEBHOOK_URL"] == "":
            messagebox.showerror("Error", "You need to provide a Webhook URL")
            return
        
        self.webhook = discord.Webhook.from_url(settings["WEBHOOK_URL"], adapter=discord.RequestsWebhookAdapter())

        self.running = True
        self.stop_event.clear()

        print("Starting Macro in 5 seconds")
        time.sleep(5)

        if settings["booth_msg"] != "":
            if settings["goal_progress"] >= settings["goal"]:
                print("Your goal has already been completed. You may want to update this in the settings.")
                self.edit_booth_text(settings["goal_reached_msg"])
            else:
                if "{goal_progress}" in settings["booth_msg"].lower() and settings["goal_progress"] < settings["goal"]:
                    self.edit_booth_text(settings["booth_msg"].replace("{goal_progress}", f"{str(settings['goal_progress'])}/{str(settings['goal'])}"))
                else:
                    self.edit_booth_text(settings["booth_msg"])
            time.sleep(2)
        for i in range(3):
            if i == 0:
                thread = threading.Thread(target=self.donation_detection)
                thread.start()
                print("Started Donation Detection")
                self.threads.append(thread)
            elif i == 1 and settings["say_random_stuff"] and len(settings["stuff_to_say"]) > 0:
                thread = threading.Thread(target=self.periodic_chat_messages)
                thread.start()
                print("Started Periodic Chat Messages")
                self.threads.append(thread)
            elif i == 2 and settings["do_emotes"]:
                if settings["say_random_stuff"]:
                    time.sleep(10)
                thread = threading.Thread(target=self.do_emotes)
                thread.start()
                print("Started Periodic Emotes")
                self.threads.append(thread)

        print("Macro has started.")
        emb = discord.Embed(
            title=f"{MACROTITLE} has started.",
            description=f"Detected user: {userdata['name']} ({userdata['displayName']})",
            colour=discord.Colour.green()
        )
        self.webhook.send(username=f"{MACROTITLE} Notifications", embed=emb)
        TOAST.show_toast(f"{MACROTITLE}", "Macro has started.", icon_path=f"{MACROPATH}/icon.ico", duration=5, threaded=True)

    def stop_macro(self):
        if not self.running:
            messagebox.showerror("Error", "Macro is not running!")
            return

        self.stop_event.set()

        for thread in self.threads:
            thread.join()

        self.threads.clear()
        self.running = False

        print("Macro has stopped")
        emb = discord.Embed(
            title=f"{MACROTITLE} has stopped.",
            colour=discord.Colour.red()
        )
        self.webhook.send(username=f"{MACROTITLE} Notifications", embed=emb)
        TOAST.show_toast(f"{MACROTITLE}", "Macro has stopped.", icon_path=f"{MACROPATH}/icon.ico", duration=5, threaded=True)

    def donation_detection(self):
        while True:
            latest_dono = get_latest_donation(rblx_log_dir)
            try:
                if latest_dono["recipient"] == userdata["displayName"] and latest_dono["timestamp"] > previous_dono["timestamp"]:
                    print(f"Donation Detected at time: {str(latest_dono['timestamp'])}\nDonated to: {latest_dono['recipient']}\nAmount: {str(latest_dono['amount'])}\nDonor: {latest_dono['donor']}")
                    previous_dono = latest_dono
                    emb = discord.Embed(
                            title="Donation Received!",
                            description=f"You were sent {latest_dono['amount']} by the user {latest_dono['donor']} at time {latest_dono['timestamp']}\n\nFull detection: `{str(latest_dono)}`",
                            colour=discord.Colour.from_rgb(255, 255, 255)
                    )
                    self.webhook.send(username=f"{MACROTITLE} Notifications", embed=emb)
                    TOAST.show_toast(f"Donation Received - {MACROTITLE}", f"Donation Detected at time: {str(latest_dono['timestamp'])}, Donated to: {latest_dono['recipient']}, Amount: {str(latest_dono['amount'])}, Donor: {latest_dono['donor']}", icon_path=f"{MACROPATH}/icon.ico", duration=5, threaded=True)#
                    if len(settings["thank_you_messages"]) > 0:
                        self.thank_user(latest_dono["donor"])
                    if settings["1_rbx_1_jump"] and not (settings["do_emotes"] or settings["say_random_stuff"]):
                        for _ in range(latest_dono["amount"] + 1):
                            _KEYBOARD.press(pynput.keyboard.Key.space)
                            time.sleep(0.2)
                            _KEYBOARD.release(pynput.keyboard.Key.space)
                            time.sleep(0.2)
            except Exception:
                pass

    def periodic_chat_messages(self):
        while True:
            msg = random.choice(settings["stuff_to_say"])
            if msg == self.previous_message:
                continue
            if "{goal_remainder}" in msg:
                msg = msg.replace("{goal_remainder}", f"{str(settings['goal'] - settings['goal_progress'])}")
            if "{goal_progress}" in msg:
                msg = msg.replace("{goal_progress}", f"{str(settings['goal_progress'])}/{str(settings['goal'])}")
            self.send_message(f"{msg}")
            self.previous_message = msg
            time.sleep(random.randint(100, 180))

    def thank_user(self, user):
        msg = random.choice(settings["thank_you_messages"])
        self.send_message(msg.replace("{donor}", f"{user.lower()}"))

    def do_emotes(self):
        while True:
            emote = random.choice(settings["emotes"])
            self.send_message(f"/e {emote}")
            time.sleep(random.randint(59, 73))

    def send_message(self, message):
        _KEYBOARD.press("/")
        time.sleep(0.1)
        _KEYBOARD.release("/")
        time.sleep(0.2)
        _KEYBOARD.type(message)
        time.sleep(0.1)
        _KEYBOARD.press(pynput.keyboard.Key.enter)
        time.sleep(0.1)
        _KEYBOARD.release(pynput.keyboard.Key.enter)
        time.sleep(0.1)
    
    def edit_booth_text(self, text):
        _KEYBOARD.press("e")
        time.sleep(3)
        _KEYBOARD.release("e")
        time.sleep(0.3)
        mkey.left_click_xy_natural(booth_edit_text_pos[0], booth_edit_text_pos[1])
        time.sleep(0.5)
        mkey.left_click_xy_natural(booth_edit_text_pos[0], booth_edit_text_pos[1])
        _KEYBOARD.press(pynput.keyboard.Key.ctrl)
        _KEYBOARD.press("a")
        time.sleep(0.2)
        _KEYBOARD.release("a")
        _KEYBOARD.release(pynput.keyboard.Key.ctrl)
        time.sleep(0.5)
        _KEYBOARD.type(text)
        time.sleep(0.5)        
        mkey.left_click_xy_natural(booth_close_pos[0], booth_close_pos[1])
        time.sleep(0.5)        
        mkey.left_click_xy_natural(booth_close_pos[0], booth_close_pos[1])

    def update_goal(self, donation):
        settings["goal_progress"] += donation
        update_settings(settings)
        reload_settings()
        if settings["goal_progress"] >= settings["goal"] and settings["goal_reached_msg"] != "":
            self.edit_booth_text(settings["goal_reached_msg"])
        if "{goal_progress}" in settings["booth_msg"].lower() and settings["goal_progress"] < settings["goal"]:
            self.edit_booth_text(settings["booth_msg"].replace("{goal_progress}", f"{str(settings['goal_progress'])}/{str(settings['goal'])}"))

print(f"Starting {MACROTITLE}")
root = tk.Tk()
app = SettingsApp(root)
print(f"Opened {MACROTITLE} menu")
root.mainloop()
print(f"{MACROTITLE} has stopped.")