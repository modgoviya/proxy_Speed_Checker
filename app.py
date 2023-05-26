import time
import datetime
#import psutil
import requests
import socket
import json
from collections import defaultdict
import subprocess
import re
import tkinter as tk
from tkinter import ttk
import logging

logging.basicConfig(filename='ip_logger.log', level=logging.INFO)

def get_public_ip():
    try:
        response = requests.get("https://api.ipify.org?format=json")
        return response.json()["ip"]
    except Exception as e:
        logging.error(f"Failed to get public IP: {e}")
        return None

# def get_interface_name():
    # wifi_interface = None
    # for name, addrs in psutil.net_if_addrs().items():
        # for addr in addrs:
            # if addr.family == socket.AF_INET:
                # if name.startswith("lo") or name.startswith("vmnet") or name.startswith("vEthernet"):
                    # continue
                # if name.startswith("wlan") or name.startswith("Wi-Fi"):
                    # wifi_interface = name
                # else:
                    # return name

    # return wifi_interface or None
def get_interface_name():
    try:
        host_name = socket.gethostname()
        host_ip = socket.gethostbyname(host_name)
        socket_info = socket.getaddrinfo(host_ip, None)

        for info in socket_info:
            if info[0] == socket.AF_INET:
                interface_name = info[4][0]

                if interface_name.startswith("lo") or interface_name.startswith("vmnet") or interface_name.startswith("vEthernet"):
                    continue
                if interface_name.startswith("wlan") or interface_name.startswith("Wi-Fi"):
                    return interface_name
                else:
                    return interface_name
    except Exception as e:
        logging.error(f"Failed to get interface name: {e}")
        return None

def get_ssid(interface_name):
    try:
        output = subprocess.check_output(["netsh", "wlan", "show", "interfaces"], universal_newlines=True)
        pattern = re.compile(r'^\s*SSID\s*:\s*(.+)$', re.MULTILINE)
        ssids = pattern.findall(output)
        return ssids[0] if ssids else None
    except:
        return interface_name

def get_avg_switching_time(records):
    if len(records) > 1:
        total_switching_time = 0
        for i in range(1, len(records)):
            total_switching_time += (records[i]["timestamp"] - records[i - 1]["timestamp"]).total_seconds()
        avg_switching_time = total_switching_time / (len(records) - 1)
    else:
        avg_switching_time = 0

    return avg_switching_time

def load_records():
    try:
        with open("ip_records.json", "r") as file:
            records = json.load(file, object_hook=lambda d: {k: datetime.datetime.fromisoformat(v) if k == "timestamp" else v for k, v in d.items()})
    except (FileNotFoundError, json.JSONDecodeError):
        records = defaultdict(list)

    return records

def save_records(records):
    with open("ip_records.json", "w") as file:
        json.dump(records, file, default=lambda obj: obj.isoformat() if isinstance(obj, datetime.datetime) else obj)

class CustomTheme:
    def apply(self):
        style = ttk.Style()
        style.theme_create('custom', parent='alt', settings={
            'TLabel': {
                'configure': {
                    'background': '#FFFFFF',
                    'foreground': '#333333',
                    'font': ('Arial', 11)
                }
            },
            'TButton': {
                'configure': {
                    'background': '#0099CC',
                    'foreground': '#FFFFFF',
                    'font': ('Arial', 11, 'bold')
                },
                'map': {
                    'background': [('pressed', '#006699'), ('active', '#00B2E0')],
                    'foreground': [('pressed', '#FFFFFF'), ('active', '#FFFFFF')]
                }
            },
            'TEntry': {
                'configure': {
                    'background': '#F0F0F0',
                    'foreground': '#333333',
                    'font': ('Arial', 11)
                }
            },
            'Treeview': {
                'configure': {
                    'background': '#FFFFFF',
                    'fieldbackground': '#F0F0F0',
                    'foreground': '#333333',
                    'font': ('Arial', 11),
                    'rowheight': 25
                },
                'map': {
                    'background': [('selected', '#E0E0E0')]
                }
            },
            'Treeview.Heading': {
                'configure': {
                    'background': '#E0E0E0',
                    'foreground': '#333333',
                    'font': ('Arial', 11, 'bold'),
                    'relief': 'flat'
                },
                'map': {
                    'background': [('active', '#D0D0D0')],
                    'relief': [('active', 'flat')]
                }
            },
            'TScrollbar': {
                'configure': {
                    'background': '#E0E0E0',
                    'troughcolor': '#F0F0F0',
                    'borderwidth': 1
                },
                'map': {
                    'background': [('active', '#D0D0D0')]
                }
            }
        })
        style.theme_use('custom')


class IPLoggerApp(tk.Tk):
    def __init__(self, refresh_interval=60000):
        super().__init__()

        CustomTheme().apply()

        self.title("IP Logger")
        self.geometry("1000x600")
        self.configure(bg="#FFFFFF")

        self.ip_records = load_records()

        self.current_ip_label = ttk.Label(self, text="Current IP: N/A")
        self.current_ip_label.pack(pady=10)

        self.current_interface_label = ttk.Label(self, text="Current Interface: N/A")
        self.current_interface_label.pack(pady=5)

        self.refresh_button = ttk.Button(self, text="Refresh", command=self.update_info)
        self.refresh_button.pack(pady=10)

        self.search_label = ttk.Label(self, text="Search by SSID:")
        self.search_label.pack(side='left', padx=10)

        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(self, textvariable=self.search_var)
        self.search_entry.pack(side='left')

        self.records_frame = ttk.Frame(self)
        self.records_frame.pack(expand=True, fill="both")

        self.treeview = ttk.Treeview(self.records_frame, columns=("SSID", "Average IP Switching Time", "Timestamp", "IP"))
        self.treeview.heading("SSID", text="SSID")
        self.treeview.heading("Average IP Switching Time", text="Average IP Switching Time")
        self.treeview.heading("Timestamp", text="Timestamp")
        self.treeview.heading("IP", text="IP")
        self.treeview.column("SSID", anchor="w", width=200)
        self.treeview.column("Average IP Switching Time", anchor="w", width=200)
        self.treeview.column("Timestamp", anchor="w", width=300)
        self.treeview.column("IP", anchor="w", width=150)

        self.treeview.pack(expand=True, fill="both")
        self.scrollbar = ttk.Scrollbar(self.records_frame, orient="vertical", command=self.treeview.yview)
        self.scrollbar.pack(side="right", fill="y")
        self.treeview.configure(yscrollcommand=self.scrollbar.set)

        self.search_var.trace("w", lambda *args: self.filter_records())

        self.refresh_interval = refresh_interval
        self.update_info()
        
    def update_info(self):
        current_time = datetime.datetime.now()
        public_ip = get_public_ip()

        if public_ip is None:
            logging.info(f"Update at {current_time} skipped due to no internet connection")
            self.after(self.refresh_interval, self.update_info)
            return

        interface_name = get_interface_name()
        ssid = get_ssid(interface_name)

        if ssid not in self.ip_records:
            self.ip_records[ssid] = []

        if not self.ip_records[ssid] or self.ip_records[ssid][-1]["ip"] != public_ip:
            record = {
                "timestamp": current_time,
                "ip": public_ip,
            }
            self.ip_records[ssid].append(record)

        save_records(self.ip_records)

        self.current_ip_label["text"] = f"Current IP: {public_ip}"
        self.current_interface_label["text"] = f"Current Interface: {interface_name} ({ssid})"

        self.populate_treeview()

        self.after(self.refresh_interval, self.update_info)


    def populate_treeview(self):
        self.treeview.delete(*self.treeview.get_children())

        for ssid in self.ip_records:
            records = self.ip_records[ssid]
            avg_switching_time = get_avg_switching_time(records)

            for record in reversed(records):
                self.treeview.insert("", "end", values=(ssid, f"{avg_switching_time:.2f} seconds", record['timestamp'], record['ip']))

    def filter_records(self):
        search_term = self.search_var.get().lower()

        for item in self.treeview.get_children():
            ssid = self.treeview.item(item, "values")[0]
            if search_term in ssid.lower():
                self.treeview.item(item, tags=("matched",))
            else:
                self.treeview.item(item, tags=("unmatched",))

        self.treeview.tag_configure("matched", foreground="#333333")
        self.treeview.tag_configure("unmatched", foreground="#CCCCCC")

if __name__ == "__main__":
    app = IPLoggerApp(refresh_interval=60000)  # Set refresh interval to 1 minute
    app.mainloop()
