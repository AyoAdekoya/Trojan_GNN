#!/bin/bash
# Automates running the parse-scoap-output.py script for all contest designs
# Usage: ./get_csv.sh
# (Run this in the SCOAP working directory)

for i in {0..19}
do
    echo "Running design $i"
    python3 parse-scoap-output.py scoap_outputs/SCOAP_Output$i.txt gate_mappings/gate_mapping$i.txt ../test-cases/trojan/result$i.txt $i
done

for i in {20..29}
do
    echo "Running design $i"
    python3 parse-scoap-output.py scoap_outputs/SCOAP_Output$i.txt gate_mappings/gate_mapping$i.txt ../test-cases/trojan_free/result$i.txt $i
done

mkdir scoap_scores
mv gate_scores*.csv scoap_scores