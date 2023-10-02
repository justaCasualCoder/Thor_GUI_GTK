"""
Thor GUI - A GUI for the Thor Flash Utility
Copyright (C) 2023  ethical_haquer

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import tkinter as tk
from tkinter import scrolledtext
from tkinter import messagebox
from tkinter import filedialog
import pexpect
from threading import Thread
import re
import webbrowser
from time import sleep
import tarfile
import os
from functools import partial
import zipfile
from collections import deque
import sv_ttk
from tkinter import ttk
import pickle

# The path to 'TheAirBlow.Thor.Shell.dll', including the filename itself. Example: '/home/billy25/Thor/TheAirBlow.Thor.Shell.dll'.
path_to_thor = '/PATH/TO/TheAirBlow.Thor.Shell.dll'

# The directory containing the 'Thor_GUI.py' file, should end in a '/'. Example: 'home/billy25/Thor_GUI/'
path_to_thor_gui = "/PATH/TO/DIRECTORY/CONTAINING/THOR_GUI's/FILES/"

version = 'Alpha v0.3.0'

currently_running = False
odin_running = False
Thor = None
connection = False
tag = 'green'
graphical_flash = False
prompt_available = False

successful_commands = []

odin_archives = []

print(f'''
 _____ _                   ____ _   _ ___
|_   _| |__   ___  _ __   / ___| | | |_ _|
  | | | '_ \ / _ \| '__| | |  _| | | || |
  | | | | | | (_) | |    | |_| | |_| || |
  |_| |_| |_|\___/|_|     \____|\___/|___|

              {version}
''')

if os.path.isfile(f'{path_to_thor_gui}/thor_gui_settings.pkl'):
    print('Case 1')
    theme = pickle.load(open(f'{path_to_thor_gui}/thor_gui_settings.pkl', 'rb'))
else:
    print(f'The \'thor_gui_settings.pkl\' file was not found in \'{path_to_thor_gui}\', so Thor GUI is creating it.')
    theme = 'light'
    pickle.dump([theme], open(f'{path_to_thor_gui}/thor_gui_settings.pkl', 'wb'))
    theme = pickle.load(open(f'{path_to_thor_gui}/thor_gui_settings.pkl', 'rb'))

# This starts and stops Thor
def start_thor():
    global Thor, output_thread, currently_running, prompt_available
    try:
        if currently_running:
            on_window_close()
        elif not currently_running:
            Thor = pexpect.spawn(f'dotnet {path_to_thor}', timeout=None, encoding='utf-8')
            output_thread = Thread(target=update_output)
            output_thread.daemon = True
            output_thread.start()
            currently_running = True
            Start_Button.configure(text='Stop Thor')
            print('Started Thor')
    except pexpect.exceptions.TIMEOUT:
            print('A Timeout Occurred in start_thor')
    except Exception as e:
        print(f"An exception occurred in start_thor: {e}")

# What most commands go through
def send_command(command):
    global Thor, successful_commands, prompt_available
    if currently_running:
        try:
            if 'exit' in command or 'quit' in command:
                print('Sadly, stopping Thor independently is currently not supported by Thor GUI. To stop Thor, either click the: \'Stop Thor\' button (which will close the window), or close the window.')
            else:
                if prompt_available == True:
                    Thor.sendline(command)
                    Output_Text.see(tk.END)
                    successful_commands.append(command)
                    print(f'Sent command: \'{command}\'')
                else:
                    print(f'Couldn\'t send the command: \'{command}\', as the \'shell>\' prompt wasn\'t available')
        except Exception as e:
            print(f"An exception occurred in send_command: {e}")

# What commands from the Command Entry go through, allowing more than just 'shell>' as the prompt
def other_send_command(command):
    global Thor, successful_commands, prompt_available
    if currently_running:
        try:
            if 'exit' in command or 'quit' in command:
                print('Sadly, stopping Thor independently is currently not supported by Thor GUI. To stop Thor, either click the: \'Stop Thor\' button (which will close the window), or close the window.')
            else:
                if prompt_available == True or clean_line.endswith('[y/n] (n):'):
                    Thor.sendline(command)
                    Output_Text.see(tk.END)
                    successful_commands.append(command)
                    print(f'Sent command: \'{command}\'')
                else:
                    print(f'Couldn\'t send the command: \'{command}\', as no prompt (\'shell>\', \'[y/n] (n):\') was available')
        except Exception as e:
            print(f"An exception occurred in other_send_command: {e}")

# Perhaps the most important part of the program, along with scan_output - Handles displaying the output from Thor, while scan_output calls other functions when it detects certain lines in the output
def update_output():
    global last_lines
    global tag
    global connection
    global clean_line
    last_lines = deque(maxlen=300)
    output_buffer = ''
    output_text_lines = []
    next_line = ''
    while True:
        try:
            chunk = Thor.read_nonblocking(4096, timeout=0)
            if chunk:
                chunk = output_buffer + chunk
                output_lines = chunk.splitlines()
                for line in output_lines:
                    mostly_clean_line = re.sub(r'\x1b\[[?0-9;]*[A-Za-z]', '', line)
                    clean_line = re.sub('\x1b=', '', mostly_clean_line).strip()

                    if clean_line.startswith(("AP", "BL", "CP", "CSC", "HOME_CSC", "USERDATA")):
                        if clean_line.endswith(":"):
                            determine_tag(clean_line)
                            output_text_lines.append((clean_line, tag))
                            scan_output()
                            last_lines.append((clean_line, tag))
                            next_line = ''
                        else:
                            next_line = clean_line
                    elif next_line:
                        clean_line = next_line + clean_line
                        next_line = ''
                        determine_tag(clean_line)
                        output_text_lines.append((clean_line, tag))
                        scan_output()
                        last_lines.append((clean_line, tag))
                    else:
                        determine_tag(clean_line)
                        output_text_lines.append((clean_line, tag))
                        scan_output()
                        last_lines.append((clean_line, tag))

                    output_buffer = ''

        except pexpect.exceptions.TIMEOUT:
            pass
        except pexpect.exceptions.EOF:
            break
        except Exception as e:
            print(f"An exception occurred in update_output: '{e}'")

        # Update the Output_Text widget
        if output_text_lines:
            for line, tag in output_text_lines:
                Output_Text.configure(state='normal')
                Output_Text.insert(tk.END, line + '\n', tag)
                Output_Text.configure(state='disabled')
            Output_Text.see(tk.END)
            output_text_lines = []

        # Delay between each update
        sleep(0.1)

def scan_output():
    global graphical_flash, last_lines, clean_line, archive_name, odin_archives, prompt_available, first_prompt
    try:
        prompt_available = False
        if 'shell>' in clean_line:
            set_thor('on')
            prompt_available = True
        elif 'Successfully began an Odin session!' in clean_line:
            set_odin('on')
        elif 'Successfully disconnected the device!' in clean_line:
            set_connect('off')
        elif 'Successfully connected to the device!' in clean_line:
            set_connect('on')
        elif "Choose a device to connect to:" in clean_line and last_lines[-1][0] == "Cancel operation":
            run_select_device()
        elif 'Successfully ended an Odin session!' in clean_line:
            set_odin('off')
        elif '> [ ]' in clean_line:
            if 'Choose what partitions to flash from' in last_lines[-3][0]:
                if '(Press <space> to select, <enter> to accept)' in last_lines[-4][0]:
                    found_index = None
                    for i in range(len(last_lines) - 1, -1, -1):
                        if last_lines[i][0].startswith('Choose what partitions to flash from'):
                            found_index = i
                            break
                    if found_index is not None:
                        archive_name_pre = last_lines[found_index + 1][0].rstrip(':')
                        last_flash_command = get_last_flash_tar_command()
                        archive_path = last_flash_command.split(' ')[1]
                        archive_name = os.path.basename(archive_name_pre.strip())
                        combined_file = os.path.join(archive_path, archive_name)
                        if graphical_flash == False:
                            run_select_partitions(archive_path, archive_name)
                            return False
                        else:
                            if combined_file in odin_archives:
                                run_select_partitions(archive_path, archive_name)
                                return False
                            else:
                                Thor.send('\n')
        elif 'Are you absolutely sure you want to flash those? [y/n] (n):' in clean_line:
            run_verify_flash()
            graphical_flash = False
        elif '" is set to "' in clean_line:
            if 'Option "T-Flash" is set to "False"' in clean_line:
                TFlash_Option_var = ttk.IntVar(value=False)
            if 'Option "T-Flash" is set to "True"' in clean_line:
                TFlash_Option_var = ttk.IntVar(value=True)
            if 'Option "EFS Clear" is set to "False"' in clean_line:
                EFSClear_Option_var = ttk.IntVar(value=False)
            if 'Option "EFS Clear" is set to "True"' in clean_line:
                EFSClear_Option_var = ttk.IntVar(value=True)
            if 'Option "Bootloader Update" is set to "False"' in clean_line:
                BootloaderUpdate_Option_var = ttk.IntVar(value=False)
            if 'Option "Bootloader Update" is set to "True"' in clean_line:
                BootloaderUpdate_Option_var = ttk.IntVar(value=True)
            if 'Option "Reset Flash Count" is set to "False"' in clean_line:
                ResetFlashCount_Option_var = ttk.IntVar(value=False)
            if 'Option "Reset Flash Count" is set to "True"' in clean_line:
                ResetFlashCount_Option_var = ttk.IntVar(value=True)
    except Exception as e:
        print(f"An exception occurred in scan_output: '{e}'")

# Handles coloring the output, as the original ANSI escape sequences are stripped out
def determine_tag(line):
    global tag
    green = [
        'Total commands: 11',
        'Choose a device to connect to:',
        'Choose what partitions to flash from',
        'Successfully connected to the device!',
        'Successfully disconnected the device!',
        'Successfully began an Odin session!',
        'Successfully ended an Odin session!',
        'Option "',
        'Successfully set "',
        'Total protocol commands: 11',
        'You chose to flash '
    ]
    yellow = [
        '~~~~~~~~ Platform specific notes ~~~~~~~~',
        '[required] {optional} - option list',
        'Are you absolutely sure you want to flash those? [y/n] (n):'
    ]
    blue = [
        'exit - Closes the shell, quit also works'
    ]
    orange = [
        'Cancel operation'
    ]
    dark_blue = [

    ]
    red = [
        '~~~~~~~^'
    ]
    green_italic = [
        'Note: beginning a protocol session unlocks new commands for you to use'
    ]
    if line.startswith('Welcome to Thor Shell v1.0.4!'):
        Output_Text.configure(state='normal')
        Output_Text.delete("1.0", "end")
        Output_Text.configure(state='disabled')
        tag = 'green'
    elif line.startswith('shell>'):
        tag = 'default_tag'
    elif 'Phone [' in line:
        tag = 'dark_blue'
    elif line in green:
        tag = 'green'
    elif line in yellow:
        tag = 'yellow'
    elif line in blue:
        tag = 'blue'
    elif line in orange:
        tag = 'orange'
    elif line in dark_blue:
        tag = 'dark_blue'
    elif line in red:
        tag = 'red'
    elif line in green_italic:
        tag = 'green_italic'

# Figures out what the last "flashTar" command run was
def get_last_flash_tar_command():
    global successful_commands
    for command in reversed(successful_commands):
        if command.startswith("flashTar"):
            return command
    return None

# Deals with enabling/disabling buttons - Mainly used by set_thor(), set_connect(), and set_odin()
def set_widget_state(*args, state="normal", text=None, color=None):
    for widget in args:
        widget.configure(state=state, text=text)
        if color is not None:
            widget.configure(fg=color)
        if text is not None:
            widget.configure(text=text)

# Tells the program whether Thor is running or not
def set_thor(value):
    if value == 'on':
        set_widget_state(Connect_Button, Command_Entry, Page_Up_Button, Page_Down_Button, Enter_Button, Space_Button)
    elif value == 'off':
        set_widget_state(Connect_Button, Command_Entry, Page_Up_Button, Page_Down_Button, Enter_Button, Space_Button, state='disabled')
        set_connect('off')

# Tells the program whether a device is connected or not
def set_connect(value):
    global connection
    if value == 'on':
        if connection == False:
            set_widget_state(Connect_Button, text='Disconnect', color='#F66151')
            Begin_Button.configure(state='normal')
            connection = True
    elif value == 'off':
        if connection == True:
            set_odin('off')
            Connect_Button.configure(text='Connect device', fg='#26A269')
            Begin_Button.configure(state='disabled')
            connection = False

# Tells the program whether an Odin session is running or not
def set_odin(value):
    global odin_running
    if value == 'on':
        if odin_running == False:
            Begin_Button.configure(text='End Odin Protocol', fg='#F66151')
            set_widget_state(Apply_Options_Button, Start_Flash_Button)
            odin_running = True
    elif value == 'off':
        if odin_running == True:
            Begin_Button.configure(text='Start Odin Protocol', fg='#26A269')
            set_widget_state(Apply_Options_Button, Start_Flash_Button, state='disabled')
            odin_running == False

# Handles connecting / disconnecting devices
def toggle_connection():
    global currently_running
    global connection
    try:
        if currently_running:
            if not connection:
                send_command('connect')
            elif connection:
                send_command('disconnect')
    except Exception as e:
        print(f"An exception occurred in toggle_connection: {e}")

# This starts and stops the Odin protocol
def toggle_odin():
    global currently_running
    global odin_running
    try:
        if currently_running:
            if not odin_running:
                send_command('begin odin')
            elif odin_running:
                send_command('end')
    except Exception as e:
        print(f"An exception occurred in toggle_odin: {e}")

# Runs the "flashTar" command when the "Start" button is clicked
def start_flash():
    global currently_running, odin_archives, graphical_flash
    try:
        checkboxes = [
            (BL_Checkbox_var, BL_Entry, "BL"),
            (AP_Checkbox_var, AP_Entry, "AP"),
            (CP_Checkbox_var, CP_Entry, "CP"),
            (CSC_Checkbox_var, CSC_Entry, "CSC"),
            (USERDATA_Checkbox_var, USERDATA_Entry, "USERDATA")
        ]
        odin_archives = []
        unique_directories = set()

        def validate_file(file_path, file_type):
            if os.path.exists(file_path):
                if file_path.endswith(('.tar', '.zip', '.md5')):
                    return True
                else:
                    print(f"Invalid {file_type} file selected - Files must be .tar, .zip, or .md5")
                    show_message("Invalid file", f"Files must be .tar, .zip, or .md5", [{'text': 'OK', 'fg': 'black'}], window_size=(400, 200))
            else:
                print(f"Invalid {file_type} file selected - The file does not exist")
                show_message("Invalid file", f"The selected {file_type} file does not exist", [{'text': 'OK', 'fg': 'black'}], window_size=(400, 200))
            return False

        for checkbox_var, entry, file_type in checkboxes:
            if checkbox_var.get():
                file_path = entry.get()
                if not validate_file(file_path, file_type):
                    return False
                odin_archives.append(file_path)
                unique_directories.add(os.path.dirname(file_path))

        if len(odin_archives) == 0:
            print("No files were selected - Please select at least one file")
            show_message("No files selected", "Please select at least one file", [{'text': 'OK', 'fg': 'black'}], window_size=(400, 200))
            return False

        if len(unique_directories) > 1:
            print("Invalid files - All selected files must be in the same directory")
            show_message("Invalid files", "All selected files must be in the same directory", [{'text': 'OK', 'fg': 'black'}], window_size=(400, 200))
            return False

        common_directory = unique_directories.pop()
        graphical_flash = True
        send_command(f"flashTar {common_directory}")

    except Exception as e:
        print(f"An exception occurred in start_flash: {e}")

    return True

# Sets the "Options" back to default and resets the Odin archive Check-buttons/Entries
def reset():
    global currently_running
    try:
        print('Changed theme')
#        TFlash_Option_var.set(False)
        EFSClear_Option_var.set(False)
        BootloaderUpdate_Option_var.set(False)
        ResetFlashCount_Option_var.set(True)
        BL_Checkbox_var.set(False)
        AP_Checkbox_var.set(False)
        CP_Checkbox_var.set(False)
        CSC_Checkbox_var.set(False)
        USERDATA_Checkbox_var.set(False)
        BL_Entry.delete(0, 'end')
        AP_Entry.delete(0, 'end')
        CP_Entry.delete(0, 'end')
        CSC_Entry.delete(0, 'end')
        USERDATA_Entry.delete(0, 'end')
    except Exception as e:
        print(f"An exception occurred in reset: {e}")

# Moves the correct frame to the top
def toggle_frame(name):
    frame_name = name + "_Frame"
    button_name = name + "_Button"
    frame = globals()[frame_name]
    button = globals()[button_name]
    frame.lift()
    buttons = [Log_Button, Options_Button, Pit_Button, Settings_Button, Help_Button, About_Button]
    for btn in buttons:
        if btn == button:
            btn.grid_configure(pady=0)
        else:
            btn.grid_configure(pady=5)

# Handles setting the options
# NOTE: The T Flash option is currently disabled
def apply_options():
#    tflash_status = TFlash_Option_var.get()
    efs_clear_status = EFSClear_Option_var.get()
    bootloader_update_status = BootloaderUpdate_Option_var.get()
    reset_flash_count_status = ResetFlashCount_Option_var.get()
#    if tflash_status == 1:
    if efs_clear_status == 1:
        Thor.sendline('options efsclear true')
    elif efs_clear_status == 0:
        Thor.sendline('options efsclear false')
    if bootloader_update_status == 1:
        Thor.sendline('options blupdate true')
    elif bootloader_update_status == 0:
        Thor.sendline('options blupdate false')
    if reset_flash_count_status == 1:
        Thor.sendline('options resetfc true')
    elif reset_flash_count_status == 0:
        Thor.sendline('options resetfc false')

# Runs select_device in the main thread
def run_select_device():
    window.after(0, select_device)

# Runs select_device in the main thread
def run_select_partitions(*args):
    window.after(0, select_partitions, *args)

# Runs verify_flash in the main thread
def run_verify_flash():
    window.after(0, verify_flash)

# Will soon replace the above three functions ^
"""
def run_function(function):
    window.after(0, function, *args)
"""

# Handles asking the user if they'd like to connect to a device
def select_device():
    global last_lines
    devices = []
    start_index = None
    try:
        for i in range(len(last_lines)-1, -1, -1):
            if last_lines[i][0].startswith("Choose a device to connect to:"):
                start_index = i
                break

        if start_index is not None:
            for i in range(start_index+1, len(last_lines)):
                line = last_lines[i][0]
                if line.startswith("Cancel operation"):
                    break
                if line.strip() != '':
                    devices.append(line.strip("> "))

        if devices:
            title = "Connect device"
            message = "Choose a device to connect to:"
            selected_device = ttk.StringVar(value=None)

            Connect_Device_Window = ttk.Toplevel(window, bg='#F0F0F0')
            Connect_Device_Window.title(title)
            Connect_Device_Window.wm_transient(window)
            Connect_Device_Window.grab_set()
            Connect_Device_Window.update_idletasks()

            window_size = (550, 200)
            width, height = window_size
            x = window.winfo_rootx() + (window.winfo_width() - width) // 2
            y = window.winfo_rooty() + (window.winfo_height() - height) // 2
            Connect_Device_Window.geometry(f"{width}x{height}+{x}+{y}")
            Connect_Device_Window.grid_columnconfigure(0, weight=1)
            Connect_Device_Window.grid_columnconfigure(1, weight=1)

            message_label = ttk.Label(Connect_Device_Window, text=message, bg='#F0F0F0')
            message_label.grid(sticky='ew', columnspan=2, row=0)

            radio_buttons = []
            even = False
            row = 1
            for device in devices:
                var = ttk.StringVar(value=device)
                radio_button = ttk.Radiobutton(Connect_Device_Window, text=device, variable=selected_device, value=device, bg='#E1E1E1', highlightbackground='#ACACAC', relief='flat', borderwidth=0, font=("Monospace", 11))
                radio_buttons.append((radio_button, var))
                if even == False:
                    radio_button.grid(pady=5, padx=5, columnspan=2, row=row)
                    even = True
                else:
                    radio_button.grid(padx=5, columnspan=2, row=row)
                    even = False
                row = row + 1

                def handle_connect():
                    KEY_DOWN = '\x1b[B'
                    selected = selected_device.get()
                    if selected == '':
                        print("No device was selected")
                    else:
                        print({selected})
                        for radio_button, var in radio_buttons:
                            if var.get() == selected:
                                Thor.send('\n')
                                close_connect_window()
                                return False
                            else:
                                Thor.send(KEY_DOWN)

                def close_connect_window():
                    Connect_Device_Window.destroy()
                    Connect_Button.event_generate('<Leave>')

                def cancel_connect():
                    KEY_DOWN = '\x1b[B'
                    for radio_button, var in radio_buttons:
                        Thor.send(KEY_DOWN)
                    Thor.send('\n')
                    close_connect_window()

            # Create the Connect button
            Connect_Button_2 = ttk.Button(Connect_Device_Window, text="Connect", command=handle_connect, bg='#E1E1E1', fg='#26A269', highlightbackground='#ACACAC', relief='flat', borderwidth=0, font=("Monospace", 11))
            Connect_Button_2.grid(pady=5, padx=5, column=1, row=row, sticky='we')

            # Create the Cancel button
            Cancel_Button = ttk.Button(Connect_Device_Window, text="Cancel", command=cancel_connect, bg='#E1E1E1', fg='#F66151', highlightbackground='#ACACAC', relief='flat', borderwidth=0, font=("Monospace", 11))
            Cancel_Button.grid(pady=5, padx=5, column=0, row=row, sticky='we')

            Connect_Device_Window.protocol("WM_DELETE_WINDOW", close_connect_window)
            Connect_Device_Window.mainloop()
        else:
            print("No devices available.")
    except Exception as e:
        print(f"An exception occurred in select_device: {e}")

# Handles asking the user what partitions they'd like to flash
def select_partitions(path, name):
    try:
        selected_files = []
        selected_files.clear()
        combined_file = os.path.join(path, name)
        def get_files_from_tar(path, name):
            file_names = []
            with tarfile.open(os.path.join(path, name), "r") as tar:
                for member in tar.getmembers():
                    file_names.append(member.name)
            return file_names

        def get_files_from_zip(path, name):
            file_names = []
            with zipfile.ZipFile(os.path.join(path, name), "r") as zip:
                for file_info in zip.infolist():
                    file_names.append(file_info.filename)
            return file_names

        def select_all(checkboxes, select_all_var):
            select_all_value = select_all_var.get()
            for checkbox, var in checkboxes:
                var.set(select_all_value)

        def flash_selected_files(checkboxes, Select_Partitions_Window):
            for checkbox, var in checkboxes:
                if var.get() == 1:
                    selected_files.append(checkbox.cget("text"))
            if not selected_files:
                print(f'You chose not to select any partitions from {name}')
                Thor.send('\n')
                Select_Partitions_Window.destroy()
                return False

            for file_name in file_names:
                sleep(0.05)
                if file_name in selected_files:
                    Thor.send('\x20')
                Thor.send('\x1b[B')
            Thor.send('\n')
            Select_Partitions_Window.destroy()
            return False

        if name.endswith('.tar') or name.endswith('.md5'):
            file_names = get_files_from_tar(path, name)
        elif name.endswith('.zip'):
            file_names = get_files_from_zip(path, name)
        else:
            print("Invalid file format. Please provide a .tar, .zip, or .md5 file.")
            return

        Select_Partitions_Window = ttk.Toplevel(window, bg='#F0F0F0')
        Select_Partitions_Window.title("Select partitions")
        Select_Partitions_Window.wm_transient(window)
        Select_Partitions_Window.grab_set()
        Select_Partitions_Window.update_idletasks()

        window_height = 30
        checkboxes = []
        shortened_file = name[:34]

        Label = ttk.Label(Select_Partitions_Window, text=f"Select what partitions to flash from\n{shortened_file}...", font=("Monospace", 10), bg='#F0F0F0')
        Label.pack(pady=5)
        window_height = window_height + 50

        select_all_var = ttk.IntVar()
        select_all_button = ttk.Checkbutton(Select_Partitions_Window, text="Select all", variable=select_all_var, command=lambda: select_all(checkboxes, select_all_var), bg='#F0F0F0', highlightbackground='#F0F0F0', highlightcolor='#F0F0F0', activebackground='#F0F0F0', relief='flat')
        select_all_button.pack(pady=5)

        for file_name in file_names:
            var = ttk.IntVar()
            checkbox = ttk.Checkbutton(Select_Partitions_Window, text=file_name, variable=var, bg='#FFFFFF', highlightbackground='#F0F0F0', highlightcolor='#F0F0F0', activebackground='#F0F0F0', relief='flat', font=("Monospace", 10))
            checkbox.pack(anchor='w', pady=(0,5), padx=5)
            checkboxes.append((checkbox, var))
            window_height = window_height + 28

        Select_Partitions_Button = ttk.Button(Select_Partitions_Window, text="Select", command=lambda: flash_selected_files(checkboxes, Select_Partitions_Window), bg='#E1E1E1', fg='#26A269', highlightbackground='#ACACAC', relief='flat', borderwidth=0, font=("Monospace", 11))
        window_height = window_height + 38
        Select_Partitions_Button.pack()

        window_size=(330, window_height)
        width, height = window_size
        x = window.winfo_rootx() + (window.winfo_width() - width) // 2
        y = window.winfo_rooty() + (window.winfo_height() - height) // 2
        Select_Partitions_Window.geometry(f"{width}x{height}+{x}+{y}")

        Select_Partitions_Window.mainloop()

    except Exception as e:
        print(f"An exception occurred in select_partitions: {e}")

# Asks the user if they'd like to flash the selected partitions
def verify_flash():
    global last_lines
    try:
        message = "\nAre you absolutely sure you want to flash the partitions you selected?"
        Verify_Flash_Window = ttk.Toplevel(window, bg='#F0F0F0')
        Verify_Flash_Window.title('Verify Flash')
        Verify_Flash_Window.wm_transient(window)
        Verify_Flash_Window.grab_set()
        Verify_Flash_Window.update_idletasks()
        Label = ttk.Label(Verify_Flash_Window, text=message, bg='#F0F0F0', font=("Monospace", 11))
        Label.grid(row=0, column=0, columnspan=2)
        def send_no():
            print('Sent \'n\'')
            Thor.sendline('n')
            Verify_Flash_Window.destroy()
        def send_yes():
            Thor.sendline('y')
            print('Sent \'y\'')
            Verify_Flash_Window.destroy()
        No_Button = ttk.Button(Verify_Flash_Window, text="No", command=send_no, bg='#E1E1E1', fg='#F66151', highlightbackground='#ACACAC', relief='flat', borderwidth=0, font=("Monospace", 11))
        No_Button.grid(row=1, column=0, sticky='we', pady=5, padx=(5,2.5))
        Yes_Button = ttk.Button(Verify_Flash_Window, text="Yes", command=send_yes, bg='#E1E1E1', fg='#26A269', highlightbackground='#ACACAC', relief='flat', borderwidth=0, font=("Monospace", 11))
        Yes_Button.grid(row=1, column=1, sticky='we', pady=5, padx=(2.5,5))

        Verify_Flash_Window.mainloop()

    except Exception as e:
        print(f"An exception occurred in verify_flash: {e}")

# Opens file picker when Odin archive button is clicked
def open_file(type):
    try:
        file_path = filedialog.askopenfilename(title=f"Select the {type} file", initialdir='~', filetypes=[(f'{type} file', '.tar .zip .md5')])
        if file_path:
            if type == "BL":
                BL_Entry.delete(0, 'end')
                BL_Entry.insert(0, file_path)
            elif type == "AP":
                AP_Entry.delete(0, 'end')
                AP_Entry.insert(0, file_path)
            elif type == "CP":
                CP_Entry.delete(0, 'end')
                CP_Entry.insert(0, file_path)
            elif type == "CSC":
                CSC_Entry.delete(0, 'end')
                CSC_Entry.insert(0, file_path)
            elif type == "USERDATA":
                USERDATA_Entry.delete(0, 'end')
                USERDATA_Entry.insert(0, file_path)
            print(f'Selected {type}: \'{file_path}\' with file picker')
    except ttk.TclError:
        print('Thor GUI was closed with the file picker still open - Don\'t do that. :)')
    except Exception as e:
        print(f"An exception occurred in open_file: {e}")

# Opens message-boxes - Used primarily by start_flash, but is also used by on_window_close
def show_message(title, message, buttons, window_size=(300, 200)):
    global Message_Window
    def handle_window_close():
        Message_Window.destroy()
        Start_Button.event_generate('<Leave>')
        Start_Flash_Button.event_generate('<Leave>')

    Message_Window = ttk.Toplevel(window, bg='#F0F0F0')
    Message_Window.title(title)
    Message_Window.wm_transient(window)
    Message_Window.grab_set()
    Message_Window.update_idletasks()
    width, height = window_size
    x = window.winfo_rootx() + (window.winfo_width() - width) // 2
    y = window.winfo_rooty() + (window.winfo_height() - height) // 2
    Message_Window.geometry(f"{width}x{height}+{x}+{y}")
    message_label = ttk.Label(Message_Window, text=message, bg="#F0F0F0")
    message_label.pack(padx=20, pady=20)

    for button in buttons:
        button_text = button.get('text', 'OK')
        button_fg = button.get('fg', 'black')
        button_command = button.get('command', handle_window_close)
        button_widget = ttk.Button(Message_Window, text=button_text, fg=button_fg, bg='#E1E1E1', highlightbackground='#ACACAC', relief='flat', borderwidth=0, command=button_command)
        button_widget.pack(pady=5)

    Message_Window.protocol("WM_DELETE_WINDOW", handle_window_close)
    Message_Window.mainloop()

# Opens websites
def open_link(link):
    webbrowser.open(link)

# Deals with showing links - From https://github.com/GregDMeyer/PWman/blob/master/tkHyperlinkManager.py, which itself is from http://effbot.org/zone/tkinter-text-hyperlink.htm, but that site no longer exists
class HyperlinkManager:

    def __init__(self, text):
        self.text = text
        self.text.tag_config("hyper", foreground="blue")
        self.text.tag_bind("hyper", "<Enter>", self._enter)
        self.text.tag_bind("hyper", "<Leave>", self._leave)
        self.text.tag_bind("hyper", "<ButtonRelease-1>", self._click)
        self.reset()

    def reset(self):
        self.links = {}

    def add(self, action):
        tag = "hyper-%d" % len(self.links)
        self.links[tag] = action
        return "hyper", tag

    def _enter(self, event):
        self.text.config(cursor="hand2")

    def _leave(self, event):
        self.text.config(cursor="")

    def _click(self, event):
        for tag in self.text.tag_names(ttk.CURRENT):
            if tag[:6] == "hyper-":
                self.links[tag]()
                return

def change_theme():
    if sv_ttk.get_theme() == "dark":
        theme = 'light'
        sv_ttk.use_light_theme()
    elif sv_ttk.get_theme() == "light":
        theme = 'dark'
        sv_ttk.use_dark_theme()
    pickle.dump([theme], open(f'{path_to_thor_gui}/thor_gui_settings.pkl', 'wb'))

# Handles stopping everthing when the window is closed, or the 'Stop Thor' button is clicked
def on_window_close():
    global Thor, currently_running, output_thread, prompt_available, Message_Window
    try:
        def force_stop():
            currently_running = False
            window.after_cancel(start_flash)
            Thor.sendline('exit')
            Thor.terminate()
            Thor.wait()
            print('Stopped Thor (possibly forcibly)')
            output_thread.join(timeout=0.5)  # Wait for the output thread to finish with a timeout
            Message_Window.destroy()
            print('Stopping Thor GUI...')
            window.destroy()
        if currently_running:
            if prompt_available == True:
                currently_running = False
                window.after_cancel(start_flash)
                Thor.sendline('exit')
                Thor.terminate()
                Thor.wait()
                print('Stopped Thor')
                output_thread.join(timeout=0.5)  # Wait for the output thread to finish with a timeout
                print('Stopping Thor GUI...')
                window.destroy()
            elif prompt_available == False:
                show_message("Force Stop Thor", "The 'shell>' prompt isn't available, so the 'exit' command can't be sent.\nThor may be busy or locked up.\nYou may force stop Thor by clicking the 'Force Stop' button.\nHowever, if Thor is in the middle of a flash or something, there will be consequences.", [{'text': 'Cancel', 'fg': '#26A269'}, {'text': 'Force Stop', 'fg': '#F66151', 'command': force_stop}], window_size=(700, 200))
        else:
            window.after_cancel(start_flash)
            print('Stopping Thor GUI...')
            window.destroy()
    except Exception as e:
        print(f"An exception occurred in on_window_close: {e}")

# Creates the Tkinter window
window = tk.Tk(className='Thor GUI')
window.title(f"Thor GUI - {version}")

# Sets the window size
window.geometry("985x600")

# Sets the row and column widths
window.grid_rowconfigure(3, weight=1)
window.grid_rowconfigure(4, weight=1)
window.grid_rowconfigure(5, weight=1)
window.grid_rowconfigure(6, weight=1)
window.grid_rowconfigure(7, weight=1)
window.grid_columnconfigure(6, weight=1)

# Creates the Title Label
Title_Label = ttk.Label(window, text="Thor Flash Utility v1.0.4", font=("Monospace", 20), anchor="center")
Title_Label.grid(row=0, column=0, columnspan=7, rowspan=2, sticky="nesw")

# Creates the "Start Thor" Button
Start_Button = ttk.Button(window, text="Start Thor", command=start_thor)
Start_Button.grid(row=0, column=8, padx=5, sticky='ew')

# Creates the "Begin Odin" Button
Begin_Button = ttk.Button(window, text="Begin Odin Protocol", command=toggle_odin, state='disabled')
Begin_Button.grid(row=0, column=10, columnspan=2, sticky='we', pady=5, padx=5)

# Creates the "Connect" Button
Connect_Button = ttk.Button(window, text="Connect", command=toggle_connection, state='disabled')
Connect_Button.grid(row=0,column=9, sticky='we', pady=5)

# Creates the Command Entry
Command_Entry = ttk.Entry(window, state='disabled')
Command_Entry.grid(row=1, column=8, columnspan=4, padx=5, sticky='nesw')
Command_Entry.bind('<Return>', lambda event: other_send_command(Command_Entry.get()))

# Creates the "Enter" Button
Enter_Button = ttk.Button(window, text="Enter", command=lambda: Thor.send('\n'), state='disabled')
Enter_Button.grid(row=2, column=8, sticky='ew', padx=5)

# Creates the "Space" Button
Space_Button = ttk.Button(window, text="Space", command=lambda: Thor.send('\x20'), state='disabled')
Space_Button.grid(row=2, column=9, padx=(0, 5), sticky='ew')

# Creates the "PgUp" Button
Page_Up_Button = ttk.Button(window, text="PgUp", command=lambda: Thor.send('\x1b[A'), state='disabled')
Page_Up_Button.grid(row=2, column=10, sticky='ew')

# Creates the "PgDn" Button
Page_Down_Button = ttk.Button(window, text="PgDn", command=lambda: Thor.send('\x1b[B'), state='disabled')
Page_Down_Button.grid(row=2, column=11, sticky='ew', padx=5)

# Creates the "Start" Button
Start_Flash_Button = ttk.Button(window, text="Start", command=start_flash, state='disabled')
Start_Flash_Button.grid(row=8, column=8, columnspan=2, sticky='ew', pady=5)

# Creates the "Reset" Button
Reset_Button = ttk.Button(window, text="Reset", command=reset)
Reset_Button.grid(row=8, column=10, columnspan=2, sticky='we', pady=5, padx=5)

# Creates the Odin Archive Check-boxes
BL_Checkbox_var = tk.IntVar()
BL_Checkbox = ttk.Checkbutton(window, variable=BL_Checkbox_var)
BL_Checkbox.grid(row=3, column=7)

AP_Checkbox_var = tk.IntVar()
AP_Checkbox = ttk.Checkbutton(window, variable=AP_Checkbox_var)
AP_Checkbox.grid(row=4, column=7)

CP_Checkbox_var = tk.IntVar()
CP_Checkbox = ttk.Checkbutton(window, variable=CP_Checkbox_var)
CP_Checkbox.grid(row=5, column=7)

CSC_Checkbox_var = tk.IntVar()
CSC_Checkbox = ttk.Checkbutton(window, variable=CSC_Checkbox_var)
CSC_Checkbox.grid(row=6, column=7)

USERDATA_Checkbox_var = tk.IntVar()
USERDATA_Checkbox = ttk.Checkbutton(window, variable=USERDATA_Checkbox_var)
USERDATA_Checkbox.grid(row=7, column=7)

# Creates the Odin archive Buttons
BL_Button = ttk.Button(window, text="Bl", command=lambda: open_file('BL'))
BL_Button.grid(row=3, column=8, padx='4', sticky='ew')

AP_Button = ttk.Button(window, text="AP", command=lambda: open_file('AP'))
AP_Button.grid(row=4, column=8, padx='4', sticky='ew')

CP_Button = ttk.Button(window, text="CP", command=lambda: open_file('CP'))
CP_Button.grid(row=5, column=8, padx='4', sticky='ew')

CSC_Button = ttk.Button(window, text="CSC", command=lambda: open_file('CSC'))
CSC_Button.grid(row=6, column=8, padx='4', sticky='ew')

USERDATA_Button = ttk.Button(window, text="USERDATA", command=lambda: open_file('USERDATA'))
USERDATA_Button.grid(row=7, column=8, padx='4', sticky='ew')

# Creates the Odin archive Entries
BL_Entry = ttk.Entry(window)
BL_Entry.grid(row=3, column=9, columnspan=3, sticky='we', padx=5)

AP_Entry = ttk.Entry(window)
AP_Entry.grid(row=4, column=9, columnspan=3, sticky='we', padx=5)

CP_Entry = ttk.Entry(window)
CP_Entry.grid(row=5, column=9, columnspan=3, sticky='we', padx=5)

CSC_Entry = ttk.Entry(window)
CSC_Entry.grid(row=6, column=9, columnspan=3, sticky='we', padx=5)

USERDATA_Entry = ttk.Entry(window)
USERDATA_Entry.grid(row=7, column=9, columnspan=3, sticky='we', padx=5)

# Creates the five Frame Buttons
Log_Button = ttk.Button(window, text='Log', command=lambda:toggle_frame('Log'))
Log_Button.grid(row=2, column=0, sticky='wes', pady=(0, 0), padx=(5, 0))

Options_Button = ttk.Button(window, text='Options', command=lambda:toggle_frame('Options'))
Options_Button.grid(row=2, column=1, sticky='wes', pady=(0, 5))

Pit_Button = ttk.Button(window, text='Pit', command=lambda:toggle_frame('Pit'))
Pit_Button.grid(row=2, column=2, sticky='wes', pady=5)

Help_Button = ttk.Button(window, text='Help', command=lambda:toggle_frame('Help'))
Help_Button.grid(row=2, column=4, sticky='wes', pady=5)

About_Button = ttk.Button(window, text='About', command=lambda:toggle_frame('About'))
About_Button.grid(row=2, column=5, sticky='wes', pady=5)

Settings_Button = ttk.Button(window, text='Settings', command=lambda:toggle_frame('Settings'))
Settings_Button.grid(row=2, column=3, sticky='wes', pady=5)

# Creates the "Log" frame
Log_Frame = ttk.Frame(window)
Log_Frame.grid(row=3, rowspan=6, column=0, columnspan=7, sticky='nesw', padx=5)
Log_Frame.grid_columnconfigure(0, weight=1)
Log_Frame.grid_rowconfigure(0, weight=1)

Output_Text = scrolledtext.ScrolledText(Log_Frame, state="disabled", highlightthickness=0, font=("Monospace", 9))
Output_Text.grid(row=0, column=0, rowspan=6, sticky='nesw')

# Creates the "Options" frame and check-boxes
Options_Frame = ttk.Frame(window)
Options_Frame.grid(row=3, rowspan=6, column=0, columnspan=7, sticky='nesw', padx=5)

NOTE_Label = ttk.Label(Options_Frame, text='NOTE: The "T Flash" option is temporarily not supported by Thor GUI.')
NOTE_Label.grid(row=0, column=0, pady=10, padx=10, sticky='w')

TFlash_Option_var = tk.IntVar()
TFlash_Option = ttk.Checkbutton(Options_Frame, variable=TFlash_Option_var, text='T Flash', state='disabled')
TFlash_Option.grid(row=1, column=0, pady=10, padx=10, sticky='w')

TFlash_Label = ttk.Label(Options_Frame, text='Writes the bootloader of a working device onto the SD card', cursor='hand2')
TFlash_Label.grid(row=2, column=0, pady=10, padx=10, sticky='w')

TFlash_Label.bind("<ButtonRelease-1>", lambda e: open_link('https://android.stackexchange.com/questions/196304/what-does-odins-t-flash-option-do'))

EFSClear_Option_var = tk.IntVar()
EFSClear_Option = ttk.Checkbutton(Options_Frame, variable=EFSClear_Option_var, text='EFS Clear')
EFSClear_Option.grid(row=3, column=0, pady=10, padx=10, sticky='w')

EFSClear_Label = ttk.Label(Options_Frame, text='Wipes the EFS partition (WARNING: You better know what you\'re doing!)', cursor='hand2')
EFSClear_Label.grid(row=4, column=0, pady=10, padx=10, sticky='w')

EFSClear_Label.bind("<ButtonRelease-1>", lambda e: open_link('https://android.stackexchange.com/questions/185679/what-is-efs-and-msl-in-android'))

BootloaderUpdate_Option_var = tk.IntVar()
BootloaderUpdate_Option = ttk.Checkbutton(Options_Frame, variable=BootloaderUpdate_Option_var, text='Bootloader Update')
BootloaderUpdate_Option.grid(row=5, column=0, pady=10, padx=10, sticky='w')

BootloaderUpdate_Label = ttk.Label(Options_Frame, text='')
BootloaderUpdate_Label.grid(row=6, column=0, pady=10, padx=10, sticky='w')

ResetFlashCount_Option_var = tk.IntVar(value=True)
ResetFlashCount_Option = ttk.Checkbutton(Options_Frame, variable=ResetFlashCount_Option_var, text='Reset Flash Count')
ResetFlashCount_Option.grid(row=7, column=0, pady=10, padx=10, sticky='w')

ResetFlashCount_Label = ttk.Label(Options_Frame, text='')
ResetFlashCount_Label.grid(row=8, column=0, pady=10, padx=10, sticky='w')

Apply_Options_Button = ttk.Button(Options_Frame, text='Apply', command=apply_options, state='disabled')
Apply_Options_Button.grid(row=9, column=0, pady=10, padx=10, sticky='w')

# Creates the "Pit" frame
Pit_Frame = ttk.Frame(window)
Pit_Frame.grid(row=3, rowspan=6, column=0, columnspan=7, sticky='nesw', padx=5)

Test_Label = ttk.Label(Pit_Frame, text='Just a test :)')
Test_Label.grid(row=0, column=0, pady=10, padx=10, sticky='w')

Although_Label = ttk.Label(Pit_Frame, text='Pull requests are always welcome though!')
Although_Label.grid(row=1, column=0, pady=10, padx=10, sticky='w')

# Creates the "Settings" frame
Settings_Frame = ttk.Frame(window)
Settings_Frame.grid(row=3, rowspan=6, column=0, columnspan=7, sticky='nesw', padx=5)
Settings_Frame.grid_columnconfigure(0, weight=1)

Theme_Label = ttk.Label(Settings_Frame, text='Appearance', font=("Monospace", 12))
Theme_Label.grid(row=0, column=0, sticky='w')

if theme == ['light']:
    other_theme = 'Dark'
elif theme == ['dark']:
    other_theme = 'Light'

Theme_Toggle = ttk.Checkbutton(Settings_Frame, text=f'{other_theme} theme', style="Switch.TCheckbutton", command=change_theme)
Theme_Toggle.grid(row=1, column=0, sticky='w')

# Creates the "Help" frame
Help_Frame = ttk.Frame(window)
Help_Frame.grid(row=3, rowspan=6, column=0, columnspan=7, sticky='nesw', padx=5)
Help_Frame.grid_columnconfigure(0, weight=1)

Help_Label = ttk.Label(Help_Frame, text='Need help?', font=("Monospace", 13), anchor="center")
Help_Label.grid(row=0, column=0, sticky='ew')

Get_Help_Text = tk.Text(Help_Frame, font=("Monospace", 11), height=1, bd=0, highlightthickness=0, wrap="word")
Get_Help_Text.grid(row=2, column=0, sticky='ew')
hyperlink = HyperlinkManager(Get_Help_Text)
Get_Help_Text.tag_configure("center", justify='center')
Get_Help_Text.insert(tk.END, "Let me know on ")
Get_Help_Text.insert(tk.END, "XDA", hyperlink.add(partial(open_link, 'https://forum.xda-developers.com/t/poll-would-a-gui-for-linux-odin4-and-or-thor-be-helpful.4604333/')))
Get_Help_Text.insert(tk.END, ", or open an issue on ")
Get_Help_Text.insert(tk.END, "GitHub", hyperlink.add(partial(open_link, 'https://github.com/ethical-haquer/Thor_GUI')))
Get_Help_Text.insert(tk.END, ".")
Get_Help_Text.tag_add("center", "1.0", "end")
Get_Help_Text.config(state=tk.DISABLED)

Help_Label_2 = ttk.Label(Help_Frame, text='\nFound an issue?', font=("Monospace", 13), anchor="center")
Help_Label_2.grid(row=4, column=0, sticky='ew')

Report_Text = tk.Text(Help_Frame, font=("Monospace", 11), height=1, bd=0, highlightthickness=0, wrap="word")
Report_Text.grid(row=5, column=0, sticky='ew')
hyperlink = HyperlinkManager(Report_Text)
Report_Text.tag_configure("center", justify='center')
Report_Text.insert(tk.END, "If it isn't listed ")
Report_Text.insert(tk.END, "here", hyperlink.add(partial(open_link, 'https://github.com/ethical-haquer/Thor_GUI#known-bugs')))
Report_Text.insert(tk.END, ", you can ")
Report_Text.insert(tk.END, "report it", hyperlink.add(partial(open_link, 'https://github.com/ethical-haquer/Thor_GUI/issues/new?assignees=&labels=&projects=&template=bug_report.md&title=')))
Report_Text.insert(tk.END, ".")
Report_Text.tag_add("center", "1.0", "end")
Report_Text.config(state=tk.DISABLED)

# Creates the "About" frame
About_Frame = ttk.Frame(window)
About_Frame.grid(row=3, rowspan=6, column=0, columnspan=7, sticky='nesw', padx=5)
About_Frame.grid_columnconfigure(0, weight=1)

Thor_GUI_Label = ttk.Label(About_Frame, text='Thor GUI', font=("Monospace", 13), anchor="center")
Thor_GUI_Label.grid(sticky='ew')

Thor_GUI_Label_2 = ttk.Label(About_Frame, text=f'{version}', font=('Monospace', 11), anchor="center")
Thor_GUI_Label_2.grid(sticky='ew')

Thor_GUI_Label_3 = ttk.Label(About_Frame, text='A GUI for the Thor Flash Utility', font=('Monospace', 11), anchor="center")
Thor_GUI_Label_3.grid(sticky='ew')

Thor_GUI_Websites_Text = tk.Text(About_Frame, font=("Monospace", 11), height=1, bd=0, highlightthickness=0, wrap="word")
Thor_GUI_Websites_Text.grid(sticky='ew')
hyperlink = HyperlinkManager(Thor_GUI_Websites_Text)
Thor_GUI_Websites_Text.tag_configure("center", justify='center')
Thor_GUI_Websites_Text.insert(tk.END, "GitHub", hyperlink.add(partial(open_link, 'https://github.com/ethical-haquer/Thor_GUI')))
Thor_GUI_Websites_Text.insert(tk.END, ", ")
Thor_GUI_Websites_Text.insert(tk.END, "XDA", hyperlink.add(partial(open_link, 'https://forum.xda-developers.com/t/poll-would-a-gui-for-linux-odin4-and-or-thor-be-helpful.4604333/')))
Thor_GUI_Websites_Text.tag_add("center", "1.0", "end")
Thor_GUI_Websites_Text.config(state=tk.DISABLED)

Thor_GUI_Label_4 = ttk.Label(About_Frame, text='Built around the:', font=('Monospace', 11), anchor="center")
Thor_GUI_Label_4.grid(sticky='ew')

Thor_GUI_Label_5 = ttk.Label(About_Frame, text='\nThor Flash Utility', font=("Monospace", 13), anchor="center")
Thor_GUI_Label_5.grid(sticky='ew')

Thor_GUI_Label_6 = ttk.Label(About_Frame, text='v1.0.4', font=('Monospace', 11), anchor="center")
Thor_GUI_Label_6.grid(sticky='ew')

Thor_GUI_Label_7 = ttk.Label(About_Frame, text='An alternative to Heimdall', font=('Monospace', 11), anchor="center")
Thor_GUI_Label_7.grid(sticky='ew')

Thor_Websites_Text = tk.Text(About_Frame, font=("Monospace", 11), height=1, bd=0, highlightthickness=0, wrap="word")
Thor_Websites_Text.grid(sticky='ew')
hyperlink = HyperlinkManager(Thor_Websites_Text)
Thor_Websites_Text.tag_configure("center", justify='center')
Thor_Websites_Text.insert(tk.END, "GitHub", hyperlink.add(partial(open_link, 'https://github.com/Samsung-Loki/Thor')))
Thor_Websites_Text.insert(tk.END, ", ")
Thor_Websites_Text.insert(tk.END, "XDA", hyperlink.add(partial(open_link, 'https://forum.xda-developers.com/t/dev-thor-flash-utility-the-new-samsung-flash-tool.4597355/')))
Thor_Websites_Text.tag_add("center", "1.0", "end")
Thor_Websites_Text.config(state=tk.DISABLED)

Thor_GUI_Label_7 = ttk.Label(About_Frame, text='\nCredits:', font=('Monospace', 13), anchor="center")
Thor_GUI_Label_7.grid(sticky='ew')

TheAirBlow_Text = tk.Text(About_Frame, font=("Monospace", 11), height=1, bd=0, highlightthickness=0, wrap="word")
TheAirBlow_Text.grid(sticky='ew')
hyperlink = HyperlinkManager(TheAirBlow_Text)
TheAirBlow_Text.tag_configure("center", justify='center')
TheAirBlow_Text.insert(tk.END, "TheAirBlow", hyperlink.add(partial(open_link, 'https://github.com/TheAirBlow')))
TheAirBlow_Text.insert(tk.END, " for Thor Flash Utility")
TheAirBlow_Text.tag_add("center", "1.0", "end")
TheAirBlow_Text.config(state=tk.DISABLED)

ethical_haquer_Text = tk.Text(About_Frame, font=("Monospace", 11), height=1, bd=0, highlightthickness=0, wrap="word")
ethical_haquer_Text.grid(sticky='ew')
hyperlink = HyperlinkManager(ethical_haquer_Text)
ethical_haquer_Text.tag_configure("center", justify='center')
ethical_haquer_Text.insert(tk.END, "Myself, ")
ethical_haquer_Text.insert(tk.END, "ethical_haquer", hyperlink.add(partial(open_link, 'https://github.com/ethical-haquer')))
ethical_haquer_Text.insert(tk.END, ", for Thor GUI")
ethical_haquer_Text.tag_add("center", "1.0", "end")
ethical_haquer_Text.config(state=tk.DISABLED)

Disclaimer_Label = ttk.Label(About_Frame, text='\n\nThis program comes with absolutely no warranty.', font=("Monospace", 9), anchor="center")
Disclaimer_Label.grid(sticky='ew')

Disclaimer_Label = ttk.Label(About_Frame, text='See the GNU General Public License, version 3 or later for details.\n', font=("Monospace", 9), anchor="center")
Disclaimer_Label.grid(sticky='ew')

Disclaimer_Label = ttk.Label(About_Frame, text='Thor Flash Utility comes with absolutely no warranty.', font=("Monospace", 9), anchor="center")
Disclaimer_Label.grid(sticky='ew')

Disclaimer_Label = ttk.Label(About_Frame, text='See the Mozilla Public License, version 2 or later for details.', font=("Monospace", 9), anchor="center")
Disclaimer_Label.grid(sticky='ew')

# Configures the tags for coloring the output text
Output_Text.tag_configure('green', foreground='#26A269')
Output_Text.tag_configure('yellow', foreground='#E9AD0C')
Output_Text.tag_configure('red', foreground='#F66151')
Output_Text.tag_configure('blue', foreground='#33C7DE')
Output_Text.tag_configure('green_italic', foreground='#26A269', font=('Monospace', 9, 'italic'))
Output_Text.tag_configure('orange', foreground='#E9AD0C')
Output_Text.tag_configure('dark_blue', foreground='#2A7BDE')

# Raises the "Log" frame to top on start-up
toggle_frame('Log')

# Binds the on_window_close function to the window's close event
window.protocol("WM_DELETE_WINDOW", on_window_close)

# Sets what theme to use
if theme == ['light']:
    sv_ttk.use_light_theme()
elif theme == ['dark']:
    sv_ttk.use_dark_theme()

# Runs the Tkinter event loop
window.mainloop()
