import subprocess
import sys
import MyLogger as log
import os
import time
import re

print = log.log_print
input = log.log_input

def _run_PS_get_lines(command, display=True, ignore_error=False):
    command = f"powershell.exe {command}"
    if display:
        log.print_command_execution(command)

    try:
        output = subprocess.check_output(command).decode()
    except subprocess.CalledProcessError as e:
        if ignore_error:
            output = e.output
        else:
            log.log_command_execution(command, e.output)
            log.log("Command returned non-zero status. Raising exception.")
            raise e
    log.log_command_execution(command, output)
    return re.sub("\r+", "", output).split("\n") # Unify \r\n and \n commands. In case it matters.

def _decode_PS_line(line):
    split = line.split(":")
    name = split[0].strip()
    value = ":".join(split[1:]).strip()
    return name, value





adapters = None
def get_network_adapters(force_update=False, prop_list_type="limited"):
    global adapters
    if (not force_update) and (adapters is not None):
        log.log("Using cached adapters")
        return adapters

    # properties = "'*'"
    properties = "Name, AdminStatus, HardwareInterface, ifOperStatus"

    assert prop_list_type in ("limited","default","all")
    if prop_list_type == "limited":
        properties = "Name, AdminStatus, HardwareInterface, ifOperStatus"
    elif prop_list_type == "all":
        properties = "'*'"
    elif prop_list_type == "default":
        properties = ""
    
    properties = "" if (properties == "") else f"-Property {properties}"

    lines = _run_PS_get_lines(f"Get-NetAdapter | Format-List {properties}")

    adapters = []
    current = {}
    for line in lines:
        if line == '':
            if current != {}:
                adapters.append(current)
                current = {}
        else:
            name, value = _decode_PS_line(line)
            current[name] = value
    
    if current != {}:
        adapters.append(current)
    
    return adapters

def get_network_adapter_link_status(name):
    lines = _run_PS_get_lines(f'Get-NetAdapter | Where Name -EQ "{name}" | Format-List -Property ifOperStatus')
    for line in lines:
        if line.strip() != "":
            name, value = _decode_PS_line(line)
            return value == "Up"
    raise Exception("No results!")







def _decode_cmd_property_line(line):
    # Format:     Name. . . . . : Value
    parts = line.split(":")
    if len(parts) == 1:  # Additional value to a property
        return None, parts[0].strip()
    
    name = parts[0].replace(".", "").strip()
    value = ':'.join(parts[1:]).strip()
    return name, value

ip_config = None
def get_ip_config(force_update=False):
    global ip_config
    if (not force_update) and (ip_config is not None):
        log.log("Using cached ipconfig")
        return ip_config

    lines = _run_PS_get_lines("ipconfig /all")

    general_config = {}

    processing_line = 3 # start on third line, where computer properties start
    while True:
        line = lines[processing_line]
        processing_line += 1
        if line.strip() == "":
            break
        
        name, value = _decode_cmd_property_line(line)
        general_config[name] = value
    
    adapters = []
    last_prop_name = None
    while processing_line < len(lines):
        line = lines[processing_line]
        processing_line += 1
        if line.strip() == "":
            continue

        if not line.startswith(" "):  # New adapter line
            adapter_type, name = line.split(" adapter ")
            adapter = {}
            adapter["Type"] = adapter_type
            adapter["Name"] = name[:-1]
            adapters.append(adapter)
        else:
            prop_name, value = _decode_cmd_property_line(line)
            if prop_name is not None:
                adapters[-1][prop_name] = value
                last_prop_name = prop_name
            else:
                saved_value = adapters[-1][last_prop_name]
                if type(saved_value) is not list:
                    if saved_value == "":
                        saved_value = []
                    else:
                        saved_value = [saved_value]
                saved_value.append(value)
                adapters[-1][last_prop_name]
    
    ip_config = general_config, adapters

    return general_config, adapters



# This is to be used for the adapters.
# It takes a list of adapters, each with the 'Name' property,
# and puts them into a dictionary by name.
def dict_by_name(adapter_list):
    new_dict = {}
    for a in adapter_list:
        name = a['Name']
        new_dict[name] = a
    return new_dict





def invalidate_network_state_cache():
    log.log("Invalidating network state cache due to state updates")
    global adapters, ip_config
    adapters = None
    ip_config = None


    

def set_net_adapter_enable_state(name, state=True):
    command = "Enable" if (state == True) else "Disable"
    _run_PS_get_lines(f"{command}-NetAdapter -name '{name}' -Confirm:$false")



# Gotten (modified) from: https://stackoverflow.com/questions/2946746/python-checking-if-a-user-has-administrator-privileges
def has_admin():
    log.log("Checking admin privileges...")
    as_user = os.environ['USERNAME']
    try:
        # only windows users with admin privileges can read the C:\windows\temp
        log.log("Attempting to access the Windows 'temp' directory")
        temp = os.listdir(os.sep.join([os.environ.get('SystemRoot','C:\\windows'),'temp']))
    except:
        log.log(f"We do *not* have admin privileges as user '{as_user}'")
        return (os.environ['USERNAME'],False)
    else:
        log.log(f"We do have admin privileges as user '{as_user}'")
        return (as_user,True)


def test_ip_connection(ip):
    try:
        # # This code will test for IPv6. I don't know if it will autodetect.
        # if ":" in ip:
        #     _run_PS_get_lines(f"ping -n 1 {ip}")
        # else:
        #     _run_PS_get_lines(f"ping -n 1 -6 {ip}")
        _run_PS_get_lines(f"ping -n 1 {ip}")
        log.log("Ping returned a 0. Taking that as a successful connection.")
        return True
    except subprocess.CalledProcessError as e:
        log.log("Interpreting exception as a failed connection.")
        return False

def test_http_connection(domain):
    # TODO: Doesn't really work, probably. Need alternative.
    try:
        _run_PS_get_lines(f"curl {domain}")
        log.log("Curl returned a 0. Taking that as a successful connection.")
        return True
    except subprocess.CalledProcessError as e:
        log.log("Interpreting exception as a failed connection.")
        return False

# Purely for testing purposes.
if __name__ == '__main__':
    print(get_ip_config())