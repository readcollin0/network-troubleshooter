import subprocess
import re

# NOTE: I realized that I needed to interface with Windows using
#       PowerShell. Windows is phasing out support for some cmd
#       utilities, such as wmic, so certain commands no longer
#       appear to work.
#       This file is kept simply as a reminder of how I did things.

def _run_get_lines(command):
    output = subprocess.check_output(command).decode()
    return re.split("\r*\n", output)

def _get_fields(line):
    fields = [[[0, None], None]]
    state = 0
    for i, c in enumerate(line):
        if state == 0:
            if c == ' ':
                state = 1

        elif state == 1:
            if c == ' ':
                state = 2
            else:
                state = 0

        elif state == 2:
            if c != ' ':
                last_i = fields[-1][0][0]
                last_name = line[last_i:i].strip()
                fields[-1][1] = last_name
                fields[-1][0][1] = i
                fields.append([[i, None], None])
                state = 0
        
        else:
            raise Exception("Invalid State")
    
    last_name = line[fields[-1][0][0]:].strip()
    fields[-1][1] = last_name
    fields[-1][0][1] = None

    return fields

def _extract_fields(fields, line):
    extracted = {}
    for f in fields:
        start, end = f[0]
        value = line[start:end].strip()
        extracted[f[1]] = value
    
    return extracted





def get_network_adapters():
    comm_lines = _run_get_lines("wmic nic get name, index")
    # comm_lines = _run_get_lines("wmic nic get")
    fields = _get_fields(comm_lines[0])

    adapters = []
    for line in comm_lines[1:-2]:
        adapter = _extract_fields(fields, line)
        adapters.append(adapter)

    return adapters

def enable_network_adapter(index, state=True):
    state_str = "enable" if (state == True) else "disable"
    command = f"wmic path win32_networkadapter where index={index} call {state_str}"
    print(command)
    print(subprocess.check_output(command).decode())




# Purely for testing purposes.
if __name__ == '__main__':
    print(get_network_adapters())