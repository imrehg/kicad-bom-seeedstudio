#!/usr/bin/env python3
"""Kicad script to create a BOM according to the Seeed Studio Fusion PCBA."""

import csv
import sys
import xml.etree.ElementTree as ET

# Natural key sorting for orders like:
# C1, C5, C10, C12 ... (instead of C1, C10, C12, C5...)
# http://stackoverflow.com/a/5967539
import re


def atoi(text):
    """Atoi."""
    return int(text) if text.isdigit() else text

def natural_keys(text):
    """
    alist.sort(key=natural_keys) sorts in human order.
    http://nedbatchelder.com/blog/200712/human_sorting.html
    (See Toothy's implementation in the comments)
    """
    return [atoi(c) for c in re.split('(\d+)', text)]


def parse_kicad_xml(input_file):

    """
    Kicad XML parser.
    Parse the KiCad XML file and look for the part designators
    as done in the case of the official KiCad Open Parts Library:
    * OPL parts are designated with "SKU" (preferred)
    * other parts are designated with "MPN"
    """
    components = {}
    parts = {}
    missing = []
    dnm_components = []

    tree = ET.parse(input_file)
    root = tree.getroot()
    for f in root.findall('./components/'):
        name = f.attrib['ref']
        info = {}
        fields = f.find('fields')
        opl, mpn, dnm = None, None, False
        if fields is not None:
            dnm = False
            for x in fields:
                if x.attrib['name'].upper() == 'DNM':
                    dnm = True
                if x.attrib['name'].upper() == 'SKU':
                    opl = x.text
                elif x.attrib['name'].upper() == 'MPN':
                    mpn = x.text
        if not dnm:
            if opl:
                components[name] = opl
            elif mpn:
                components[name] = mpn
            else:
                missing += [name]
                continue
        else:
            dnm_components += [name]
            continue

        if components[name] not in parts:
            parts[components[name]] = []

        parts[components[name]] += [name]
    return components, missing, dnm_components


def write_bom_seeed(output_file_slug, components):

    """
    Write the BOM according to the Seeed Studio Fusion PCBA.
    Template available at:
    https://statics3.seeedstudio.com/assets/file/fusion/bom_template_2016-08-18.csv

    ```
    Ref,MPN/SKU,Qtd
    C1,RHA,1
    "D1,D2",CC0603KRX7R9BB102,2
    ```

    The output is a CSV file at the `output_file_slug`.csv location.
    """

    parts = {}
    for c in components:
        if components[c] not in parts:
            parts[components[c]] = []
        parts[components[c]] += [c]

    field_names = ['Ref', 'MPN/SKU', 'Qtd']
    with open("{}.csv".format(output_file_slug), 'w') as csvfile:
        bomwriter = csv.DictWriter(
            csvfile, fieldnames=field_names,
            delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        bomwriter.writeheader()
        for p in sorted(parts.keys()):
            pieces = sorted(parts[p], key=natural_keys)
            designators = ",".join(pieces)
            bomwriter.writerow({'Ref': designators,
                                'MPN/SKU': p,
                                'Qtd': len(pieces)})


if __name__ == "__main__":
    input_file = sys.argv[1]
    output_file = sys.argv[2]

    components, missing, dnm_components = parse_kicad_xml(input_file)
    write_bom_seeed(output_file, components)
    if len(dnm_components) > 0:
        print("\n** Info **:parts with do not mount (DNM) atributte were not included")
        print(dnm_components)
    if len(missing) > 0:
        print("\n** Warning **: there were parts with missing SKU/MFP")
        print(missing)
