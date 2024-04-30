import MyLogger as log
import WinterfacePS as win
import sys
from time import sleep
import os
import datetime
import dns.resolver
import socket

domains_to_use = ["google.com", "amazon.com", "whitehouse.gov"]
dns_to_use = ["1.1.1.1", "8.8.8.8", "8.8.4.4"]


print_no_log = print   # We sometimes want to print only to the console (i.e. terminal )
print = log.log_print  # Log all print statements
input = log.log_input

if len(sys.argv) == 1:
    log_dir = "."
else:
    log_dir = sys.argv[1]
log_dir += os.path.sep

log_file_num = 1
while os.path.exists(log_dir + f"log_{log_file_num}.txt"):
    log_file_num += 1
log.setup_logfile(log_dir + f"log_{log_file_num}.txt")


adapter_matchers = "Wi-Fi", "Ethernet"
def match_adapter_name(name):
    for m in adapter_matchers:
        if m in name:
            log.log(f"Categorizing the adapter '{name}' by name gave us {m}.")
            return m
    log.log(f"Unable to categorize the adapter '{name}' into " + " or ".join(adapter_matchers) + ".")
    return "Other"


########## Utilities ##########
def print_further_instructions(resolved=True):
    message = ("Please (somehow) give all log files (i.e. \"log_1\" or \"log_1.txt\") to your resident tech-support person. "
             + "It contains details of what this program did, and all the decisions made behind the scenes.")
    if resolved:
        message = "If issues are still unresolved, p" + message[1:]
    print("\n" + message)

# The 'message' argument works like the first argument in input
# The 'default_value' works as follows:
#   - If None, blank answers are not accepted
#   - If any other value, a blank is returned as that value.
def get_confirmation(message=None, default_value=None):
    if message is not None and message != "":
        print(message)
    print("Type 'yes' or 'no'")
    response = input("> ")
    while True:
        if response == '':
            if default_value is not None:
                break
        elif response[0].lower() in "yn":
            break

        print("I did not understand your response.")
        print("Please type 'yes' or 'no'")
        response = input("> ")
    
    if response == '':
        return default_value

    response = response[0].lower()
    return True if (response == "y") else False

def pause_until_enter():
    print("Press ENTER to continue")
    input()






########## Diagnostics ##########
# Returns `True` if it enabled an adapter, and the connection should be rechecked.
def check_for_disabled_adapters():
    log.log("Running check_for_disabled_adapters routine.")
    found_adapters = {x: [] for x in adapter_matchers}
    found_adapters['Other'] = []

    log.log("Looking for hardware adapters that are disabled.")
    for adapter in win.get_network_adapters():
        if adapter['HardwareInterface'] == 'True':
            a_type = match_adapter_name(adapter['Name'])
            found_adapters[a_type].append(adapter)
        else:
            log.log(f"{adapter['Name']} is not a hardware adapter.")
    
    log.log("Looking for enabled adapters that are disconnected.")

    enabled_an_adapter = False
    for adapter_type in found_adapters:
        adapters = found_adapters[adapter_type]
        enabled = [(a["AdminStatus"] == "Up") for a in adapters]
        if all(enabled):
            continue
        
        if adapter_type == "Other":
            print("We have at least one unrecognized kind of adapter.")
            print("Should we try enabling it/them?")
            print("If you don't know, just say yes.")
        else:
            print(f"\nWe have detected at least one disabled {adapter_type} adapter.")
            print(f"Is your computer hooked up to use {adapter_type}?")
            print("If you don't know, just press enter.")
        if get_confirmation(default_value=False):
            print("Then we will enable it/them for you.")
            for i, e in enumerate(enabled):
                if e: # If it is enabled, skip it.
                    continue
                name = adapters[i]['Name']
                print(f"Enabling {name}")
                win.set_net_adapter_enable_state(name, True)
                enabled_an_adapter = True
        else:
            print("Then we will leave it alone.")

    if enabled_an_adapter:
        print("Giving time for adapters to reinitialize and connect...")
        sleep(20)

        if test_several_ips():
            print("It seems that this has resolved your issues.")
            return True
        print("We still cannot connect to the internet.")
        win.invalidate_network_state_cache()
    else:
        print("We didn't enable any adapters. Skipping connection check.")
    return False


def reset_adapters():
    log.log("Running reset_adapters routine.")
    ### Reset network adapters with phyiscal connectors
    disabled = []
    print("Getting adapters...")
    log.log("Resetting hardware network adapters that are not disabled.")
    log.log("Right now, I don't want to mess with system settings, just try a fix.")
    log.log("So I'm not going to enable disabled adapters right now.")
    log.log("By reset, I mean I will disable then enable them.")
    log.log("I determine if it's a hardware network adapter by 'HardwareInterface'.")
    log.log("I determine whether it's disabled by the 'AdminStatus'.")
    for adapter in win.get_network_adapters():
        name = adapter['Name']
        if adapter['AdminStatus'] == 'Down':
            log.log(f"{name} is disabled.")
            continue
        if adapter['HardwareInterface'] == "False":
            log.log(f"{name} is not a hardware interface.")
            continue

        name = adapter['Name']
        print(f"Disabling {name}...")
        disabled.append(name)
        win.set_net_adapter_enable_state(name, False)

    
    if len(disabled) > 0:
        print("Waiting for a few seconds...")
        sleep(5)

        for name in disabled:
            print(f"Reenabling {name}...")
            win.set_net_adapter_enable_state(name, True)

        print("Done resetting adapters.")
        print("Waiting for adapters to reinitialize and connect...")
        sleep(20)
        print("Checking to see if internet connection is restored...")
        if test_several_ips():
            print("That fixed it. You should be able to connect now.")
            return True
        else:
            print("We're still unable to connect to the internet.")
            win.invalidate_network_state_cache()
    else:
        print("We were unable to find any enabled physical network adapters.")

    return False

def check_for_static_ips():
    log.log("Running check_for_static_ips routine.")
    ip_conf_adapters = win.get_ip_config()[1]
    adapters = win.get_network_adapters()

    log.log("Cross-referencing ipconfig and Get-NetAdapters to find hardware adapters with DHCP disabled and no link.")
    log.log("To detect no link, we reference the 'ifOperStatus'")
    for adapter in adapters:
        if adapter['AdminStatus'] == "Down":
            continue

        name = adapter['Name']
        static_ip_hardware = False
        for ip_a in ip_conf_adapters:
            if ip_a['Name'] == name:
                if adapter['HardwareInterface'] == "False":
                    log.log(f"{name} is not a hardware interface.")
                    pass # Easy to comment out the above line
                elif ip_a['DHCP Enabled'] == "Yes":
                    log.log(f"{name} has DHCP enabled.")
                    pass # Ditto
                elif adapter['ifOperStatus'] == "Down":
                    log.log(f"{name} is not connected anyway.")
                    log.log("Note: Invalid network configuration does not result in an 'ifOperStatus' of 'Down'")
                    pass # Ditto Ditto

                # if adapter['HardwareInterface'] == "True" and ip_a['DHCP Enabled'] == "No":
                else:
                    # log.log(f"Adapter {name} is both a 'HardwareInterface' and has DHCP disabled")
                    static_ip_hardware = True
                    break
        
        if static_ip_hardware:
            print("It seems you have a network adapter with DHCP disabled (static IP)")
            print("Static IPs are a fairly advanced feature.")
            print("Are you aware that your computer was configured this way?")
            if get_confirmation():
                print("Try disabling it, and then we'll check your connection after that.")
                print("\nDo you want us to test your connection now?")
                if get_confirmation() and test_several_ips():
                    print("Great, it worked! Good luck figuring out why the IP was a problem, though.")
                    return True
                win.invalidate_network_state_cache()
            else:
                print("Issues with this feature are difficult to fix with a program like this.")
                print("The feature is also intentially and usually configured in a specific way.")
                print("We will continue trying other things to fix it.")
                print("If we cannot, I advise you to contact whoever set your network up.")
    
    return False

def check_for_down_adapters():
    log.log("Running check_for_down_adapters routine.")
    adapters = win.get_network_adapters()
    
    log.log("Looking for enabled hardware adapters that have an 'ifOperStatus' of 'Down'")
    log.log("Disabled adapters have an 'AdminStatus' of 'Down'")
    log.log("Hardware adapters have a 'HardwareInterface' of 'True'")
    got_link = False
    got_disconnected_adapter = False
    for a in adapters:
        if (a['HardwareInterface'] == 'False'):
            log.log(f"{a['Name']} is not a hardware interface.")
            continue

        if (a['AdminStatus'] == 'Down'):
            log.log(f"{a['Name']} is Disabled.")
            continue

        got_disconnected_adapter = True
        name = a['Name']
        a_type = match_adapter_name(a['Name'])
        
        if a['ifOperStatus'] == "Up":
            print("{name} is connected...")
            got_link = True
        elif a['ifOperStatus'] == "Down":
            print(f"\nYou have a disconnected {a_type}-type adapter.")
            print(f"It is known by the system as {name}.")
            if get_confirmation("Is this intentional (should we skip fixing it)?"):
                print("In that case, we'll skip it.")
            elif a_type == "Wi-Fi":
                print("At the bottom-right of the screen, click your Wi-Fi icon.")
                if get_confirmation("Do you see a list of Wi-Fi networks?"):
                    run_test = True
                    if get_confirmation("Do you see *your* Wi-Fi network?"):
                        print("Please verify that you are connected to that network.")
                        print("Make sure you type the password in right, if applicable.")
                    else:
                        print("Try moving close to your router.")
                        if get_confirmation("Do you see it now?"):
                            print("Try to connect to it.")
                            print("Make sure you type the password in right, if applicable.")
                        else:
                            print("Then there's probably an issue with your Wi-Fi network.")
                            print("Issues of that nature are very difficult to fix with code.")
                            print("We'll still try to fix the issue, but it is unlikely to work.")
                            print("If we can't, contact your preferred tech support person, and let them know about this.")
                            run_test = False
                    
                    if run_test:
                        pause_until_enter()
                        if win.get_network_adapter_link_status(name):
                            print("We're detecting a connection now.")
                        else:
                            print("We still don't detect a connetion, but we'll test it anyway.")
                            print("If you were unable to connect to it for some reason, it is unlikely we can fix it.")
                            print("We'll still try, but if we can't, contact your preferred tech wizard, and let them know about this.")

                        if test_several_ips():
                            print("Great! That seems to have worked.")
                            return True
                        else:
                            print("Still no connection, unfortunately.")
                else:
                    print("It is unlikely we will be able to fix this problem.")
                    print("We will still attempt to resolve this issue.")
                    print("If we cannot, contact your tech support guru of choice.")
                
            elif a_type == "Ethernet":
                print("Please verify that your Ethernet cable is plugged in.")
                print("If it is, try unplugging and plugging it back in at both ends.")
                print("Also ensure that the device on the other end is powered on.")
                print("If there's a connection, the lights on the port should be flashing or solid.")
                print("If your device doesn't have lights, check the other end of the ethernet cable.")
                print("Some devices you might encounter at the other end have numbered lights on the other side.")
                print("In this case, the lights would correspond to specific ports.")
                print()
                if get_confirmation("Were you able to find the lights, even if they weren't on?"):
                    if not get_confirmation("Are the lights flashing?"):
                        print("Please try another ethernet cable.")
                        print("The goal is to get the lights to flash.")
                        pause_until_enter()
                        if win.get_network_adapter_link_status(name):
                            got_link = True
                            print("We've detected a connection.")
                            print("We'll test for connectivity.")
                        else:
                            print("We still don't detect a connection.")
                            print("Testing for a connection anyway.")
                        
                        print("Let's give it a few seconds...")
                        sleep(5)
                        if test_several_ips():
                            print("Great! That seems to have worked.")
                            return True
                        else:
                            print("Still no connection, unfortunately.")
                    else:
                        if win.get_network_adapter_link_status(name):
                            got_link = True
                            print("Great, we're detecting a link, so we'll test your network, then.")
                        else:
                            print("That's odd. We're still not detecting anything. We'll test it anyway.")
                        
                        print("Let's give it a few seconds to connect...")
                        sleep(5)
                        if test_several_ips():
                            print("Excellent! We were able to connect to the internet.")
                            return True
                        else:
                            print("Still no internet connection.")
                else:
                    if win.get_network_adapter_link_status(name):
                        got_link = True
                        print("At the very least, we're detecting a connection.")
                        print("We're going to try connecting to the internet.")
                        if test_several_ips():
                            print("Excellent! We were able to connect to the internet.")
                            return True
                        else:
                            print("Still no luck, unfortunately. But that's probably one problem solved.")
                    else:
                        print("Well, we're still not detecting a connection.")
                        print("Try changing Ethernet cables.")
                        pause_until_enter()
                        if win.get_network_adapter_link_status(name):
                            got_link = True
                            print("Great, we're detecting a link, so we'll test your network, then.")
                        else:
                            print("We still don't detect a connection. We'll test it anyway")                    
                        
                        if test_several_ips():
                            print("Excellent! We were able to connect to the internet.")
                            return True
                        else:
                            print("Still no internet connection.")

            else:
                print("We've detected a disconnected internet adapter we don't recognize.")
                print(f"It's known by the computer as {name}.")
                print("Please check to see if it is connected, if possible.")
                print("If you are unsure about it yourself, just ignore this step.")
                pause_until_enter()
                    
                if test_several_ips():
                    print("Great! That seems to have worked.")
                    return True
                else:
                    print("Still no connection, unfortunately.")
                    win.invalidate_network_state_cache()
        
    if not got_link:
        print("We were unable to detect any connections.")
        print("It's ",end='')
        print("*extremely*", color=log.colors.STRONG_EMPHASIS, end='')
        if got_disconnected_adapter:
            print(" likely that the problem lies at this step.")
        else:
            print(" likely that the problem lies at a previous step.")
        print("We will continue trying things to fix the issue.")
    else:
        print("Seems that didn't solve it.")
    return False

def print_instructions_for_broken_link():
    print("If you use Wi-Fi:")
    print("  - Please contact your tech support person.")
    print("If you use Ethernet:")
    print("  - Please ensure an unbroken Ethernet connection to your router.")
    print("  - Please ensure that all Ethernet ports have blinking lights.")
    print("      Note: these lights may be on the other side of some devices.")

def print_instructions_for_dhcp():
    print("A DHCP server is what helps computers configure themselves to connect to the network.")
    print("  Note: Typically, a computer relies on the DHCP server once a day.")
    print("Please try rebooting the router by unplugging it, waiting 30 seconds, and plugging it back in.")
    print("If that doesn't work, contact your preferred technomancer.")

def computer_has_DHCP_issue():
    log.log("Running check_for_no_DHCP routine.")
    adapters = win.get_network_adapters()
    ip_conf_adapters_by_name = win.dict_by_name(win.get_ip_config()[1])

    dhcp_issue = False

    log.log("We're going to look for broken DHCP connection.")
    log.log("We do this by looking for an 'Up' connection with an 'Autoconfiguration IPv4 Address' starting with 169.254")
    for a in adapters:
        name = a['Name']
        if a['ifOperStatus'] == "Down":
            log.log(f"Skipping '{name}' due to it being down.")
            continue
        
        ip_a = ip_conf_adapters_by_name[name]
        autoconf_ipv4 = ip_a.get("Autoconfiguration IPv4 Address")
        if autoconf_ipv4 is not None:
            if autoconf_ipv4.startswith("169.254."):
                log.log(f"We detected that adapter '{name}' has an autoconfig IP.")
                dhcp_issue = True
    
    return dhcp_issue

def run_dhcp_issues():
    log.log("Running run_dhcp_issues routine.")
    print("Is the problem limited to wireless devices?")

    print("Is there another computer on the same network that has a working internet connection?")
    do_print_broken_link = False
    if get_confirmation():
        print("Would it be acceptable to cause that computer to also have the same issue?")
        # print("And are you comfortable entering commands on that computer?")
        if get_confirmation():
            print("Go to that computer, ensure it's logged in, and press Windows+R on the keyboard.")
            print("In the box that pops up, type \"cmd\" and press Enter")
            print("A black box with white text should pop up on the screen.")
            print("In that box, type this command exactly (omit the quotes): \"ipconfig /renew\"")
            print("Wait a moment and then try accessing the internet from that computer.")
            print("Does the computer's internet still work? Just hit enter if you want to skip this step.")
            result = get_confirmation(default_value=0)
            if result == True:
                print("Then the issue is probably with your connection to the router.")
                print_instructions_for_broken_link()
            elif result == False:
                print("Then the issue is almost certainly with your router's DHCP server.")
                print_instructions_for_dhcp()
            else:  # Nothing entered (default)
                print("Skipping that step.")
                print("It's hard to determine what the issue is.")
                print("It could be that your computer cannot contact the router.")
                print_instructions_for_broken_link()
                pause_until_enter()

                print()
                print("It could also be that your router's DHCP server isn't working.")
                print_instructions_for_dhcp()
        else:
            print("It's hard to determine what the issue is.")
            print("It could be that your computer cannot contact the router.")
            print_instructions_for_broken_link()
            pause_until_enter()

            print()
            print("It could also be that your router's DHCP server isn't working.")
            print_instructions_for_dhcp()
    else:
        print("It's hard to determine what the issue is.")
        print("It could be that your computer cannot contact the router.")
        print_instructions_for_broken_link()
        pause_until_enter()

        print()
        print("It could also be that your router's DHCP server isn't working.")
        print_instructions_for_dhcp()
    
    pause_until_enter()
    print("Waiting a few seconds for a connection...")
    sleep(5)
    if test_several_ips():
        print("Great! That worked!")
        return True
    else:
        print("There's still no connection, unfortunately.")

    win.invalidate_network_state_cache()

def print_can_connect_to_router_instructions():
    print("Since we can connect to your router, here are a few steps to try.")
    print("Between each step, check to see if your internet connection has been restored.")
    print("1. Double check that your router and modem are both on (may be combined into one box).")
    print("     Pretty much every modern router or modem has some kind of light on it.")
    print("     If the lights are off, then ensure the device is plugged in.")
    print("     You can also test the outlet with something else to make sure it works.")
    print("     If one still doesn't turn on, then either it, or the power cable has an issue.")
    print("     If the device came from your ISP, contact them for assistance.")
    print("     If not, contact the person who bought it, or a techie they can't help.")
    print("2. Reboot your router and modem.")
    print("     Unplug both from the wall, wait 30 seconds, and plug it back it in.")
    print("     Wait another minute for it to initialize before testing your connection.")
    print("3. Check all the cables between your ISP, modem, and router.")
    print("     Check Ethernet, as well as the cable from the modem to your ISP.")
    print("     Try unplugging them, and plugging them back in.")
    print("4. Contact your ISP for assistance.")
    # TODO: Explain that the router not working or the ISP not working is hard to discern

default_gateways_to_test = []
def check_connection_to_router():
    log.log("Running check_connection_to_router routine.")
    default_gateways = []
    adapters = win.get_network_adapters()
    ip_conf_adapters_by_name = win.dict_by_name(win.get_ip_config()[1])
    log.log("Gathering all the adapter's Default Gateways")
    for a in adapters:
        name = a['Name']
        if a['HardwareInterface'] == "False":
            log.log(f"Skipping {name} because it is not a hardware interface.")
            continue

        if a['ifOperStatus'] == "Down":
            log.log(f"Skipping {name} because it is down.")
            continue

        ip_a = ip_conf_adapters_by_name.get(name)
        if ip_a is None:
            log.log(f"WARNING: Adapter {name} was Up, but had no listing in `ipconfig /all`")
            log.log("I don't know what that means! Maybe nothing?")
            continue

        gateway = ip_a.get("Default Gateway")
        if gateway is not None:
            gateway = gateway.sub("(Preferred)","")
            default_gateways.append(gateway)
            log.log(f"Adapter {name} has a Default Gateway of {gateway}")
        else:
            log.log(f"Adapter {name} does not have a Default Gateway")
    
    if len(default_gateways) == 0:
        print("We couldn't find a router.")
        log.log("No Default Gateways found. Assuming no connection to router.")
    else:
        print("We're going to try to contact your router.")
        failures = 0
        successess = 0
        for gateway in default_gateways:
            if win.test_ip_connection(gateway):
                successess += 1
            else:
                failures += 1
                default_gateways_to_test.append(gateway)
        
        if failures > 0 and successess > 0:
            print("We're detecting multiple routers, and some fail and some succeed.")
            log.log("Yes, I know that gateway != router. I didn't know how to better explain this.")
            log.log("I'm not sure how to handle this. Please contact the author of this program.")
            print("Here are the instructions for if we are able to connect to your router:")
            print_can_connect_to_router_instructions()
            pause_until_enter()

            print()
            print("We're going to move forward on the assumption that you cannot connect.")
            print("This is because there's not much else we can do if we can connect to the router.")
            return False
            # FIXME: See the above.
        elif failures > 0:
            print("We're unable to connect to your router.")
            return False
        else: 
            print("We got a connection to your router.")
            return True

def test_default_gateways_again():
    # Right now, we assume that there's only one issue.
    # By that assumption, if we fix the problem, then an internet test is as good as a router test
    # However, that might not always hold true.
    # This function will retest the default gateways that could not be connected to during the first test.
    # To change the program to make that assumption not hold would require a general change in logic flow.
    # I am not willing to do that right now, so this function will remain unused for now.
    # I will leave a TODO: here to signal that something needs to be done at some point.
    successess = 0
    failures = 0
    for gateway in default_gateways_to_test:
        if win.test_ip_connection(gateway):
            successess += 1
        else:
            failures += 1
    
    if failures > 0 and successess > 0:
        print("Successfully connected to least one previously inaccessible routers.")
        print("Assuming successful connection to router.")
        return True
    elif failures > 0:
        return False
    else:
        return True

def run_dhcp_works_cant_connect_to_router():
    print_instructions_for_broken_link()
    # TODO: Wireshark?
    # Maybe assume that if there are DHCP packets from other computers, it's probably a server issue.
    # Well, but that doesn't necessarily hold true. Probably a low-priority TODO
    pass

def check_dns_issues():
    log.log("Running check_dns_issues routine.")
    log.log("Using system DNS resolver to attempt to query about 'amazon.com'")
    
    for domain in domains_to_use:
        try:
            log.log(f"Trying to resolve {domain} with system resolver...")
            socket.getaddrinfo(domain, 53)
            log.log("DNS query succeeded. DNS check passed.")
            print("DNS check passed.")
            return True
        except socket.gaierror as e:
            log.log("Domain resolution failed.")
    
    print("I'm detecting some issues with DNS. Let me try using a different system.")
    print("This may take a bit...")


    log.log("Using the 'dnspython' library to attempt to query servers about 'amazon.com'.")
    log.log("'dnspython' is its own DNS resolver, should bypass the system resolver.")
    log.log("If it does work, something is wrong with the DNS.")
    log.log("Specifically using `dns.resolver.resolve_at(dns_ip, domain, 'NS')")

    # print("Trying to use a DNS server...")

    dns_succeeded = False
    for dns_ip in dns_to_use:
        for domain in domains_to_use:
            try:
                log.log(f"Attempting to resolve '{domain}' using DNS {dns_ip}")
                response = dns.resolver.resolve_at(dns_ip, domain, "NS")
                log.log("Resolve attempt succeeded.")
                dns_succeeded = True
                break
            except dns.resolver.LifetimeTimeout as e:
                log.log(f"LifetimeTimeout error means we could not connect.")
        
        if dns_succeeded:
            break
    
    if dns_succeeded:
        print("It seems there's something wrong with your DNS system.")
    else:
        print("We were unable to use DNS in any way.")
        print("It is possible that something is blocking DNS queries.")

    print("Please contact a technologically-inclined individual for assistance.")
    return False

    

    




########## TESTS ##########
def test_several_ips():
    for ip in dns_to_use:
        if win.test_ip_connection(ip):
            return True
    return False

# def test_several_domains():
#     domains = "microsoft.com", "google.com", "youtube.com"



########## MAIN ###########
# TODO: Check we're running on Windows.
# TODO: Add a tool to download necessities ahead of time.
# TODO: Make it easy for a layman to install and run.
try:
    resolved = True
    while True:  # Simply to allow a "break" to leave quickly.
        log.clear_screen()

        ### Note to loggers

        log.log("")
        log.log("NOTE TO LOG READER: This log was designed to be as useful to you as possible.")
        log.log("                    While you may need to consult the code, most of the meat should be here.")
        log.log("                    I tried to put all details here. It may be a little too much, even.")
        log.log("ALSO: Any lines beginning with ### are log-only lines")
        log.log("", prefix="")

        ### Verify admin privileges, notify user if no admin rights
        _, admin = win.has_admin()
        if not admin:
            print("This program needs to be run as administrator to work.")
            print("Please right click on whatever you used to run this, and click")
            print('     "Run As Administrator"')
            exit(1)

        ### Introduction
        print("Welcome to the network troubleshooting tool.")
        print("Any gray lines beginning with a '$' are commands we run.")
        print("Also, we may use the word 'adapter' a lot.")
        print("In case you are unfamiliar with it in this context, it basically just means something your computer uses to connect to the internet.")
        print()

        ### Test connection to 1.1.1.1
        print("We'll start by testing your internet connection.")
        if test_several_ips():
            print("We successfully connected to an internet server.")
            print("We're going to test your DNS.")
            if check_dns_issues():
                print("We were unable to find any issues.")
                break

        else:
            print("We were unable to connect to any internet servers.")
            print("Instead, we're going to see if we can connect to your router.")
            print("First, we're going to check for an error in automatic network configuration.")
            dhcp_issues = computer_has_DHCP_issue() # We'll need this value later.
            if dhcp_issues:
                print("We detected an error in the automatic configuration of your network.")
                print("Your computer has an issue with network configuration.")
                print("But we're going to run some other diagnostics before handling that.")
            else:
                print("Alright, there's no issue with network configuration at the moment.")
                print("Next, we're going to try connecting to your router.")
                if check_connection_to_router():
                    print_can_connect_to_router_instructions()
                    break
                else:
                    print("We were unable to connect to your router. We will move forward with local diagnostics.")

            print()

            ### Try resetting enabled physical adapters
            print("\nWe're going to disable and reenable your network adapters.")
            print("This will reset them in case they broke in software.")
            print("It is a quick and easy thing to try, and it fixes a lot of issues.")
            if reset_adapters():
                break

            ### Look for disabled Wi-Fi or Ethernet adapters
            print("\nNext we're going to look for disabled network adapters.")
            if check_for_disabled_adapters():
                break
            
            ### Check to see if adapters are "Up"
            print("Let's check to see that the computer can communicate with something else.")
            if check_for_down_adapters():
                break
            
            if dhcp_issues:
                run_dhcp_issues()
            else:
                print("There's likely a disconnection somewhere between your computer and the router.")
                run_dhcp_works_cant_connect_to_router()

            ### Check for static IPs.
            if check_for_static_ips():
                break
            
            # TODO: Figure out some way to send the log file. (very-high-priorty, this is a very important thing to be able to do)
            # TODO: Add sleeps or something to make the fast output more readable. (very-high-priority)
            # TODO: Wi-Fi could, but likely doesn't have issues with broken links.


            # TODO: Maybe do a traceroute? (actually, very-low-priority, as it probably wouldn't help)

            # TODO: Check if Wi-Fi is disabled system-wide (low-priority, unlikely, not trivial to implement)

            # TODO: make constants for the properties? (med-priority, good code issue, other issues I should fix first)

            # TODO: For DHCP/broken link issues, try asking if multiple computers stopped working at the same time. (high-priority)
            # TODO: For DHCP/broken link issues, try checking log viewer to determine when: (high-priority)
            #    - Connection was broken
            #    - DHCP configuration was renewed
            # If connection was broken at the same time DHCP went was renewed, probably DHCP issue.

            # TODO: Improve detection of Ethernet/Wi-Fi? (low-priority, doesn't change much)
            # Note: Can use CMD Type, PS MediaType, maybe others

            # TODO: Refactor to use the PowerShell State property? (med-priority, might be more reliable, or make better code)
            # Note: Has the known values: "Disabled", "Disconnected", and "Up"

            # TODO: Make important instructions appear in yellow. (med-priority, might make it more user-friendly, but might not change much either)

        print("We were unable to resolve your issues.")
        resolved = False
        break

    print_further_instructions(resolved=resolved)
    print("\nWe're going to collect a little more relevant information.")
    print("This will tell the reader of the logs what's presently the case.")

    log.log()
    log.log()
    log.log("Here's the state of the network stuff after everything's been done.")
    win.invalidate_network_state_cache()
    win.get_network_adapters(prop_list_type="default")
    win.get_ip_config()


except Exception as e:
    log.log_exception(e)
    print("The program has run into an error.")
    if log.logger_active():
        print_further_instructions()
    else:
        print("Please send the above error message to the author of this program.")

finally:
    log.clean_up()
