import sqlite3
import os
import pandas as pd
from datetime import datetime, timedelta
from tkinter import Tk, filedialog, Button, Label, messagebox, Frame, Entry, Toplevel
from tkinter import ttk
import pytz
import sys

# Global variables
dfs = {}
selected_export_path = ""

# Function to convert Firefox's timestamp to human-readable format in Paris time
def convert_firefox_time(firefox_time):
    epoch_start = datetime(1970, 1, 1)
    utc_time = epoch_start + timedelta(microseconds=firefox_time)
    paris_tz = pytz.timezone('Europe/Paris')
    paris_time = utc_time.replace(tzinfo=pytz.utc).astimezone(paris_tz)
    return paris_time

# Function to convert Chromium's timestamp to human-readable format
def convert_chrome_time(chromium_time):
    epoch_start = datetime(1601, 1, 1)
    utc_time = epoch_start + timedelta(microseconds=chromium_time)
    paris_tz = pytz.timezone('Europe/Paris')
    paris_time = utc_time.replace(tzinfo=pytz.utc).astimezone(paris_tz)
    return paris_time

def detect_firefox_profiles(username):
    profiles_path = os.path.expandvars(f"C:\\Users\\{username}\\AppData\\Roaming\\Mozilla\\Firefox\\Profiles")
    profiles = []
    if os.path.exists(profiles_path):
        for profile in os.listdir(profiles_path):
            history_path = os.path.join(profiles_path, profile, "places.sqlite")
            if os.path.exists(history_path):
                profiles.append((profile, history_path))
    return profiles

def detect_chrome_profiles(username):
    profiles_path = os.path.expandvars(f"C:\\Users\\{username}\\AppData\\Local\\Google\\Chrome\\User Data")
    profiles = []
    if os.path.exists(profiles_path):
        for profile in os.listdir(profiles_path):
            history_path = os.path.join(profiles_path, profile, "History")
            if os.path.exists(history_path):
                profiles.append((profile, history_path))
    return profiles

def detect_opera_profiles(username):
    profiles_path = os.path.expandvars(f"C:\\Users\\{username}\\AppData\\Roaming\\Opera Software\\Opera GX Stable")
    profiles = []
    if os.path.exists(profiles_path):
        history_path = os.path.join(profiles_path, "History")
        if os.path.exists(history_path):
            profiles.append(("Opera", history_path))
    return profiles

def detect_edge_profiles(username):
    profiles_path = os.path.expandvars(f"C:\\Users\\{username}\\AppData\\Local\\Microsoft\\Edge\\User Data")
    profiles = []
    if os.path.exists(profiles_path):
        for profile in os.listdir(profiles_path):
            history_path = os.path.join(profiles_path, profile, "History")
            if os.path.exists(history_path):
                profiles.append((profile, history_path))
    return profiles

def process_file(filepath, browser_type):
    try:
        conn = sqlite3.connect(filepath)
        if browser_type == 'Firefox':
            query = '''
            SELECT h.id, p.url, h.visit_date, h.from_visit, h.visit_type
            FROM moz_historyvisits AS h
            LEFT JOIN moz_places AS p ON h.place_id = p.id
            '''
            df = pd.read_sql_query(query, conn)
            df['visit_date'] = df['visit_date'].apply(convert_firefox_time)
        elif browser_type in ['Chrome', 'Opera', 'Edge']:
            query = '''
            SELECT visits.id, urls.url, visits.visit_time, visits.from_visit, visits.transition, 
                visits.segment_id, visits.visit_duration
            FROM visits
            LEFT JOIN urls ON visits.url = urls.id
            '''
            df = pd.read_sql_query(query, conn)
            df['visit_time'] = df['visit_time'].apply(convert_chrome_time)
            df['visit_duration'] = df['visit_duration'].apply(lambda x: timedelta(microseconds=x) if x else None)
        
        conn.close()
        return df

    except sqlite3.OperationalError as e:
        messagebox.showerror("Database Error", f"SQLite Operational Error: {e}\n\nMake sure the database file is not currently open by another application.")
        return None

    except Exception as e:
        messagebox.showerror("Error", f"An error occurred: {e}")
        return None


def search_website():
    global dfs

    if dfs:
        website_url = entry_website.get().strip()
        if website_url:
            for profile, df in dfs.items():
                filtered_df = df[df['url'].str.contains(website_url, case=False)]
                if not filtered_df.empty:
                    update_treeview(profile, filtered_df)
                else:
                    messagebox.showinfo("Info", f"No data found for {website_url} in profile {profile}.")
        else:
            messagebox.showwarning("Warning", "Please enter a website URL.")
    else:
        messagebox.showerror("Error", "No history file processed. Please select and process a history file first.")

def update_treeview(profile, df):
    global treeviews, label_summary

    treeview = treeviews[profile]
    clear_treeview(treeview)
    
    if 'visit_time' in df.columns:
        df_sorted = df.sort_values(by='visit_time', ascending=False)
        if 'visit_duration' in df.columns:
            for _, row in df_sorted.iterrows():
                treeview.insert('', 'end', values=(row['url'], row['visit_time'], row['visit_duration']))
        else:
            for _, row in df_sorted.iterrows():
                treeview.insert('', 'end', values=(row['url'], row['visit_time']))
    else:
        for _, row in df.iterrows():
            treeview.insert('', 'end', values=(row['url'], row['visit_date'], row.get('visit_duration', '')))

def clear_treeview(treeview):
    for row in treeview.get_children():
        treeview.delete(row)

def create_gui(username):
    global label_selected_file, label_export_path, label_selected_file_tooltip, label_export_path_tooltip
    global selected_file_path, selected_export_path, treeviews, label_summary, entry_website

    root = Tk()
    root.title("Browser History Processor")
    root.geometry("800x800")
    root.resizable(True, True)

    icon_path = getattr(sys, '_MEIPASS', os.getcwd())
    root.iconbitmap(os.path.join(icon_path, 'history_process.ico'))

    label_title = Label(root, text="Browser History Processor", font=("Arial", 20))
    label_title.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="n")

    frame_search = Frame(root, padx=10, pady=10)
    frame_search.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky="n")

    label_search = Label(frame_search, text="Search for a website:")
    label_search.grid(row=0, column=0, padx=(0, 10), sticky="w")

    entry_website = Entry(frame_search, width=50)
    entry_website.grid(row=0, column=1, padx=(0, 10), sticky="w")

    search_button = Button(frame_search, text="Search", command=search_website)
    search_button.grid(row=1, column=0, sticky="w")

    frame_summary = Frame(root, padx=10, pady=10)
    frame_summary.grid(row=2, column=0, columnspan=2, padx=10, pady=10, sticky="n")

    label_summary = Label(frame_summary, text="Total visits: 0")
    label_summary.pack(anchor="w")

    notebook = ttk.Notebook(root)
    notebook.grid(row=3, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")

    root.grid_rowconfigure(3, weight=1)
    root.grid_columnconfigure(0, weight=1)

    treeviews = {}
    profiles_firefox = detect_firefox_profiles(username)
    profiles_chrome = detect_chrome_profiles(username)
    profiles_opera = detect_opera_profiles(username)
    profiles_edge = detect_edge_profiles(username)

    def export_to_csv(profile):
        try:
            if profile.startswith("Firefox"):
                selected_profile = combobox_profiles.get()
                if selected_profile in dfs:
                    df = dfs[selected_profile]
                    export_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
                    if export_path:
                        df.to_csv(export_path, index=False)
                        messagebox.showinfo("Export Complete", f"Exported data for profile '{selected_profile}' to {export_path}.")
                else:
                    messagebox.showerror("Error", "Selected profile not found.")
            elif profile.startswith("Chrome"):
                selected_profile = combobox_profiles.get()
                if selected_profile in dfs:
                    df = dfs[selected_profile]
                    export_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
                    if export_path:
                        df.to_csv(export_path, index=False)
                        messagebox                        .showinfo("Export Complete", f"Exported data for profile '{selected_profile}' to {export_path}.")
                else:
                    messagebox.showerror("Error", "Selected profile not found.")
            elif profile.startswith("Opera"):
                selected_profile = combobox_profiles.get()
                if selected_profile in dfs:
                    df = dfs[selected_profile]
                    export_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
                    if export_path:
                        df.to_csv(export_path, index=False)
                        messagebox.showinfo("Export Complete", f"Exported data for profile '{selected_profile}' to {export_path}.")
                else:
                    messagebox.showerror("Error", "Selected profile not found.")
            elif profile.startswith("Edge"):
                selected_profile = combobox_profiles.get()
                if selected_profile in dfs:
                    df = dfs[selected_profile]
                    export_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
                    if export_path:
                        df.to_csv(export_path, index=False)
                        messagebox.showinfo("Export Complete", f"Exported data for profile '{selected_profile}' to {export_path}.")
                else:
                    messagebox.showerror("Error", "Selected profile not found.")
            else:
                messagebox.showerror("Error", "Invalid browser profile.")

        except Exception as e:
            messagebox.showerror("Export Error", f"An error occurred during export: {e}")

    for profile, history_path in profiles_firefox:
        df = process_file(history_path, 'Firefox')
        if df is not None:
            dfs[f"Firefox: {profile}"] = df
            frame = Frame(notebook)
            treeview = ttk.Treeview(frame, columns=("Site", "Visit Time", "Visit Duration"), show='headings')
            treeview.heading("Site", text="Site")
            treeview.heading("Visit Time", text="Visit Time")
            treeview.heading("Visit Duration", text="Visit Duration")
            treeview.pack(fill="both", expand=True)
            scrollbar = ttk.Scrollbar(frame, command=treeview.yview)
            scrollbar.pack(side="right", fill="y")
            treeview.configure(yscrollcommand=scrollbar.set)
            treeviews[f"Firefox: {profile}"] = treeview
            notebook.add(frame, text=f"Firefox: {profile}")

            combobox_frame = Frame(frame)
            combobox_frame.pack(side="top", padx=10, pady=10)

            profiles_list = [f"Firefox: {profile}" for profile, _ in profiles_firefox]
            combobox_profiles = ttk.Combobox(combobox_frame, values=profiles_list, state="readonly")
            combobox_profiles.current(0)  # Select the first profile by default
            combobox_profiles.pack(side="left", padx=5)

            export_button = Button(combobox_frame, text="Export to CSV", command=lambda profile=f"Firefox: {profile}": export_to_csv(profile))
            export_button.pack(side="left", padx=5)

    for profile, history_path in profiles_chrome:
        df = process_file(history_path, 'Chrome')
        if df is not None:
            dfs[f"Chrome: {profile}"] = df
            frame = Frame(notebook)
            treeview = ttk.Treeview(frame, columns=("Site", "Visit Time", "Visit Duration"), show='headings')
            treeview.heading("Site", text="Site")
            treeview.heading("Visit Time", text="Visit Time")
            treeview.heading("Visit Duration", text="Visit Duration")
            treeview.pack(fill="both", expand=True)
            scrollbar = ttk.Scrollbar(frame, command=treeview.yview)
            scrollbar.pack(side="right", fill="y")
            treeview.configure(yscrollcommand=scrollbar.set)
            treeviews[f"Chrome: {profile}"] = treeview
            notebook.add(frame, text=f"Chrome: {profile}")

            combobox_frame = Frame(frame)
            combobox_frame.pack(side="top", padx=10, pady=10)

            profiles_list = [f"Chrome: {profile}" for profile, _ in profiles_chrome]
            combobox_profiles = ttk.Combobox(combobox_frame, values=profiles_list, state="readonly")
            combobox_profiles.current(0)  # Select the first profile by default
            combobox_profiles.pack(side="left", padx=5)

            export_button = Button(combobox_frame, text="Export to CSV", command=lambda profile=f"Chrome: {profile}": export_to_csv(profile))
            export_button.pack(side="left", padx=5)

    for profile, history_path in profiles_opera:
        df = process_file(history_path, 'Opera')
        if df is not None:
            dfs[f"Opera: {profile}"] = df
            frame = Frame(notebook)
            treeview = ttk.Treeview(frame, columns=("Site", "Visit Time", "Visit Duration"), show='headings')
            treeview.heading("Site", text="Site")
            treeview.heading("Visit Time", text="Visit Time")
            treeview.heading("Visit Duration", text="Visit Duration")
            treeview.pack(fill="both", expand=True)
            scrollbar = ttk.Scrollbar(frame, command=treeview.yview)
            scrollbar.pack(side="right", fill="y")
            treeview.configure(yscrollcommand=scrollbar.set)
            treeviews[f"Opera: {profile}"] = treeview
            notebook.add(frame, text=f"Opera: {profile}")

            combobox_frame = Frame(frame)
            combobox_frame.pack(side="top", padx=10, pady=10)

            profiles_list = [f"Opera: {profile}" for profile, _ in profiles_opera]
            combobox_profiles = ttk.Combobox(combobox_frame, values=profiles_list, state="readonly")
            combobox_profiles.current(0)  # Select the first profile by default
            combobox_profiles.pack(side="left", padx=5)

            export_button = Button(combobox_frame, text="Export to CSV", command=lambda profile=f"Opera: {profile}": export_to_csv(profile))
            export_button.pack(side="left", padx=5)

    for profile, history_path in profiles_edge:
        df = process_file(history_path, 'Edge')
        if df is not None:
            dfs[f"Edge: {profile}"] = df
            frame = Frame(notebook)
            treeview = ttk.Treeview(frame, columns=("Site", "Visit Time", "Visit Duration"), show='headings')
            treeview.heading("Site", text="Site")
            treeview.heading("Visit Time", text="Visit Time")
            treeview.heading("Visit Duration", text="Visit Duration")
            treeview.pack(fill="both", expand=True)
            scrollbar = ttk.Scrollbar(frame, command=treeview.yview)
            scrollbar.pack(side="right", fill="y")
            treeview.configure(yscrollcommand=scrollbar.set)
            treeviews[f"Edge: {profile}"] = treeview
            notebook.add(frame, text=f"Edge: {profile}")

            combobox_frame = Frame(frame)
            combobox_frame.pack(side="top", padx=10, pady=10)

            profiles_list = [f"Edge: {profile}" for profile, _ in profiles_edge]
            combobox_profiles = ttk.Combobox(combobox_frame, values=profiles_list, state="readonly")
            combobox_profiles.current(0)  # Select the first profile by default
            combobox_profiles.pack(side="left", padx=5)

            export_button = Button(combobox_frame, text="Export to CSV", command=lambda profile=f"Edge: {profile}": export_to_csv(profile))
            export_button.pack(side="left", padx=5)

    root.mainloop()

def create_selection_gui():
    def set_username():
        username = username_entry.get().strip()
        if username:
            selection_root.destroy()
            create_gui(username)
        else:
            messagebox.showwarning("Warning", "Please enter a username.")

    selection_root = Tk()
    selection_root.title("Browser History Processor - Username Entry")
    selection_root.geometry("400x200")

    icon_path = getattr(sys, '_MEIPASS', os.getcwd())
    selection_root.iconbitmap(os.path.join(icon_path, 'history_process.ico'))

    label = Label(selection_root, text="Enter a username:")
    label.pack(pady=10)

    username_entry = Entry(selection_root, width=30)
    username_entry.pack(pady=10)

    select_button = Button(selection_root, text="Submit", command=set_username)
    select_button.pack(pady=10)

    selection_root.mainloop()

create_selection_gui()
