########################################################################
# parse-netlist-to-scoap.py 
# Takes in a verilog netlist in the contest format and creates three files:
# 1) scoap_formatX.txt a version of the netlist that is compatble for 
# putting into the SCOAP tool
# 2) net_mappingX.txt: a file that maps the net numbers used in the original .v file to the 
# numbering used in the SCOAP tool (not actually useful for anything)
# 3) gate_output_mappingX.txt: a file that maps the gate numbers to their output
# nets and the numbering used in the scoap tool
#
# Usage: > python parse-netlist-to-scoap.py path_to/designX.v X
# where X is the design number which will be used to name the output files
#
# For example, running 
# > python parse-netlist-to-scoap.py test-cases/trojan/design7.v 7
# will create the following files:
# scoap_format7.txt
# net_mapping7.txt
# gate_output_mapping7.txt
#
########################################################################

import re
import sys

# === Input files via command line ===
if len(sys.argv) != 3:
    print("Usage: python3 parse-netlist-to-scoap.py <verilog-netlist> <design_number>")
    sys.exit(1)

input_file = sys.argv[1]
design_number = sys.argv[2]
scoap_output_file = f"scoap_format{design_number}.txt"
net_mapping_file = f"net_mapping{design_number}.txt"
gate_mapping_file = f"gate_output_mapping{design_number}.txt"

# Constants
net_id_map = {"1'b0": 0, "1'b1": 1}
net_id_counter = 2

gate_lines = []
input_ports = []
output_ports = []
gate_output_map = {}  # maps gXX -> (net_name, net_id)

def get_net_id(net):
    global net_id_counter
    if net == "x":
        return None
    if net not in net_id_map:
        net_id_map[net] = net_id_counter
        net_id_counter += 1
    return net_id_map[net]

def expand_multibit(name, msb, lsb):
    if msb < lsb:
        msb, lsb = lsb, msb
    return [f"{name}[{i}]" for i in range(lsb, msb + 1)]

with open(input_file, "r") as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith("//"):
            continue

        # Handle input/output/wire
        match = re.match(r"(input|output|wire)\s*(\[\d+:\d+\])?\s*(.*);", line)
        if match:
            kind, range_str, names_str = match.groups()
            names = [n.strip() for n in names_str.split(",") if n.strip()]
            if range_str:
                msb, lsb = map(int, re.findall(r"\d+", range_str))
                for base in names:
                    for full_name in expand_multibit(base, msb, lsb):
                        get_net_id(full_name)
                        if kind == "input":
                            input_ports.append((full_name, net_id_map[full_name]))
                        elif kind == "output":
                            output_ports.append((full_name, net_id_map[full_name]))
            else:
                for name in names:
                    get_net_id(name)
                    if kind == "input":
                        input_ports.append((name, net_id_map[name]))
                    elif kind == "output":
                        output_ports.append((name, net_id_map[name]))
            continue

        # Match regular gates
        match = re.match(r"(and|or|not|xor|xnor|nor|nand|buf)\s+(\w+)\((.*?)\);", line)
        if match:
            gate_type, gate_name, ports = match.groups()
            if gate_type == 'buf':
                gate_type = 'buff'
            port_list = [p.strip() for p in ports.split(",")]
            out_net = port_list[0]
            in_nets = port_list[1:]
            out_id = get_net_id(out_net)
            in_ids = [get_net_id(n) for n in in_nets]
            gate_lines.append((out_net, f"{out_id}={gate_type}({','.join(map(str, in_ids))})"))
            gate_output_map[gate_name] = (out_net, out_id)
            continue

        # Match dff with named ports
        if line.startswith("dff"):
            dff_match = re.match(r"dff\s+(\w+)\((.*?)\);", line)
            if not dff_match:
                continue
            gate_name, port_block = dff_match.groups()
            port_matches = re.findall(r"\.(\w+)\(([^)]+)\)", port_block)
            port_dict = {k: v.strip() for k, v in port_matches}
            if not all(k in port_dict for k in ["Q", "D", "CK"]):
                continue
            q = get_net_id(port_dict["Q"])
            d = get_net_id(port_dict["D"])
            ck = get_net_id(port_dict["CK"])
            rn = get_net_id(port_dict.get("RN", "1'b1"))
            sn = get_net_id(port_dict.get("SN", "1'b1"))
            gate_lines.append((port_dict["Q"], f"{q}=dffcr({d},{ck},{rn},{sn})"))
            gate_output_map[gate_name] = (port_dict["Q"], q)

# Write SCOAP-compatible file
with open(scoap_output_file, "w") as f:
    f.write("input(0)\n")
    f.write("input(1)\n")
    f.write("input(x)\n")

    for name, nid in input_ports:
        f.write(f"input({nid})\n")
        f.write(f"#{name}  input {nid}\n")

    for name, nid in output_ports:
        f.write(f"output({nid})\n")
        f.write(f"#{name}  output {nid}\n")

    for _, expr in gate_lines:
        f.write(expr + "\n")

# Write net_mapping.txt
with open(net_mapping_file, "w") as f:
    for net_name, net_id in sorted(net_id_map.items(), key=lambda x: x[1]):
        f.write(f"{net_name} -> {net_id}\n")

# Write gate_output_mapping.txt
with open(gate_mapping_file, "w") as f:
    for gate_name, (net_name, net_id) in sorted(gate_output_map.items()):
        f.write(f"{gate_name} -> {net_name} (ID: {net_id})\n")
