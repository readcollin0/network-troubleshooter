import sys
import traceback

from colorama import just_fix_windows_console
just_fix_windows_console()

log_file = None

class colors:
    CSI = '\033['
    NORMAL = CSI + '0m'
    COMMAND = CSI + '38;5;238m'
    STRONG_EMPHASIS = CSI + '38;5;9m'

class con_codes:
    CSI = '\033['
    CLEAR_SCREEN = CSI + "2J"
    CURSUR_TOP_LEFT = CSI + "H"

def clear_screen():
    print(con_codes.CLEAR_SCREEN + con_codes.CURSUR_TOP_LEFT,end='')

def setup_logfile(filename):
    global log_file
    clean_up()
    log_file = open(filename, "w")

def logger_active():
    return log_file is not None

def log_print(*args, display=True, log=True, prefix="", color="", **kwargs):
    if display:
        print(color + prefix, end='')
        print(*args, **kwargs)
        print(colors.NORMAL,end='')
        sys.stdout.flush()

    if log and log_file:
        print(prefix, file=log_file, end='')
        print(*args, **kwargs, file=log_file)

def log(*args, prefix="### ", **kwargs):
    log_print(*args, display=False, prefix=prefix, **kwargs)

def log_input(prompt=""):
    result = input(prompt)
    
    if log_file:
        log_file.write(f"{prompt}{result}\n")

    return result

def print_command_execution(command):
    log_print(command, color=colors.COMMAND, prefix="$ ")
    

def log_command_execution(command, output):
    if log_file:
        log_file.write(f"\n### Running command: `{command}`")
        log_file.write(f"\n### ============ COMMAND OUTPUT ============\n")
        if type(output) == bytes:
            output = output.decode()
        # output = re.sub("\r+", "", output)
        output = "### " + output.replace("\r","").replace("\n","\n### ")
        log_file.write(output)
        log_file.write(f"\n### ========== END COMMAND OUTPUT ==========\n")
        log_file.write(f"")

def log_exception(e):
    if log_file is not None:
        for line in traceback.format_exception(e):
            log_print(line, display=False)
    else:
        traceback.print_exception(e)

def clean_up():
    global log_file
    if log_file:
        log_file.close()
    
    log_file = None


if __name__ == "__main__":
    print("Testing command colors.")
    log_command_execution("rem test", "")