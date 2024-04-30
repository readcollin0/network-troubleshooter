import WinterfacePS as win

INTERFACE_NAME = "Ethernet"

def meta_prop(name):
    return f"#: {name} :#"

def combine_adapter(ps, ipconf):
    final = {}
    
    if ps is not None:
        for key in ps:
            if key == "Name":
                final["PS " + meta_prop("Name")] = ps[key]
            else:
                final["PS " + key] = ps[key]
        final["PS " + meta_prop("ADAPTER PRESENT")] = "True"
    else:
        final["PS " + meta_prop("ADAPTER PRESENT")] = "False"

    if ipconf is not None:
        for key in ipconf:
            if key == "Name":
                final["CMD " + meta_prop("Name")] = ipconf[key]
            else:
                final["CMD " + key] = ipconf[key]
        final["CMD " + meta_prop("ADAPTER PRESENT")] = "True"
    else:
        final["CMD ADAPTER PRESENT"] = "False"
    
    return final

def apply_mask(mask, to_list):
    assert(len(mask) == len(to_list))

    result = []
    for i in range(len(mask)):
        if mask[i]:
            result.append(to_list[i])
    return result

def sample(interface):
    win.invalidate_network_state_cache()
    adapters = win.dict_by_name(win.get_network_adapters(prop_list_type="all"))
    ip_adapters = win.dict_by_name(win.get_ip_config()[1])
    sample = combine_adapter(adapters.get(interface), ip_adapters.get(interface))
    return sample


# NOTE: You can easily comment out these lines to get custom samples.
# For example, if you wanted to compare a Wi-Fi adapter to an Ethernet adapter.
# Example of such a replacement:
# samples = [sample("Ethernet"), sample("Wi-Fi")]

print("Press ENTER when ready to take first sample.")
input()
samples = [sample(INTERFACE_NAME)]
print(f"1 sample collected.")

print("Press ENTER to take another sample, or type DONE to stop")
while input() != "DONE":
    samples.append(sample(INTERFACE_NAME))
    print(f"{len(samples)} samples collected.")
    print("Press ENTER to take another sample, or type DONE to stop")
print("\n")


ps_prop_mask = [(s["PS " + meta_prop("ADAPTER PRESENT")] == "True") for s in samples]
cmd_prop_mask = [(s["CMD " + meta_prop("ADAPTER PRESENT")] == "True") for s in samples]

# Check for property differences
set_of_props = set().union(*[list(s.keys()) for s in samples])
values_differed = 0
results_table = []
for prop in sorted(set_of_props):
    values = [s.get(prop) for s in samples]
    for i, v in enumerate(values):
        if v is None:
            values[i] = "[MISSING]"
        elif v == "":
            values[i] = "______"
        elif v is list:
            values[i] = ";".join(v)

    if prop.startswith("CMD"):
        check_values = apply_mask(cmd_prop_mask, values)
    else:
        check_values = apply_mask(ps_prop_mask, values)

    if len(set(check_values)) == 1:
        continue
    
    values_differed += 1
    table_row = [prop] + values
    results_table.append(table_row)

    # print(f"{prop}: \t{values[0]}", end='')
    # for val in values[1:]:
    #     print(f"\t-> {val}",end='')
    # print()

if values_differed == 0:
    print("All samples were identical")
else:
    format_str = "|"
    for col in range(len(results_table[0])):
        max_width = 0
        for row in results_table:
            length = len(row[col])
            if length > max_width:
                max_width = length
        format_str += " {:<" + str(max_width) + "} |"

    for row in results_table:
        print(format_str.format(*row))
    print(f"States differed by {values_differed} keys.")