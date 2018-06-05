#!/usr/bin/env python3

#
# Main file for APK (alcohol per krona) calculation.
# 
# Copyright (c) 2018 Tobias Olausson
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#

# TODO: Much of this should probably be a class

import xml.etree.ElementTree as ET
import os.path
import urllib.request
from datetime import datetime

def parse_alcohol(alc_as_string):
    if not alc_as_string[-1:] == "%":
        raise ValueError("Not an alcohol percentage, need to end with %")

    # TODO: This would allow 9.3.7.2%
    alc_numbers = alc_as_string[:-1]
    if not all(dig.isdigit() or dig == "." for dig in alc_numbers):
        raise ValueError("Only digits and . allowed in alcohol percentage")

    value = float(alc_numbers)
    if value > 100:
        raise ValueError("Percentage can't be larger than 100%")

    return value

def download_products(products_file_name):
    products_file_url = "https://www.systembolaget.se/api/assortment/products/xml"
    print("Downloading product database file...")
    # Delete the file if already present
    if os.path.exists(products_file_name):
        os.unlink(products_file_name)

    retries = 0
    max_retries = 3
    # Try to download the file
    while not os.path.exists(products_file_name) and retries < max_retries:
        try:
            return urllib.request.urlretrieve(products_file_url, products_file_name)
        except:
            retries = retries + 1
    return None

def open_products():
    products_file_name = "products.xml"

    if not os.path.exists(products_file_name):
        print("No product database file available, downloading...")
        if download_products(products_file_name) is None:
            print("Could not download product database file")
            return None

    try:
        tree = ET.parse(products_file_name)
        root = tree.getroot()
    except ET.ParseError as err:
        (line, column) = err.position
        print("Parse error on line {}, column {}".format(line, column))
        return None

    # Check if it's been more than 24hrs since we downloaded last time
    creation_date_str = root.find('skapad-tid').text
    creation_date = datetime.strptime(creation_date_str, "%Y-%m-%d %H:%M")
    now = datetime.now()

    diff = now - creation_date
    if diff.days > 0:
        # And if so, re-download!
        print("{} days since last database download".format(diff.days))
        download_products(products_file_name)
        tree = ET.parse(products_file_name)

    return tree

tree = open_products()
root = tree.getroot()
apk_values=[]
for artikel in root.findall('.//artikel'):
    nr = artikel.find('nr').text
    name = artikel.find('Namn').text

    if artikel.get('apk') is not None:
        apk_values.append((nr, name, artikel.find('apk').text))
        continue

    cost = float(artikel.find('Prisinklmoms').text)
    alcohol_percent = parse_alcohol(artikel.find('Alkoholhalt').text)

    # Alcohol-free drinks makes this list useless
    if alcohol_percent == 0:
        continue

    volume = float(artikel.find('Volymiml').text)
    alcohol_ml = volume * (alcohol_percent / 100)
    apk = alcohol_ml / cost

    apk_node = ET.SubElement(artikel, 'apk')
    apk_node.text = str(apk)

    # Legacy mode
    apk_values.append((nr, name, apk))

# TODO: Save to right file name
# tree.write('test.xml', encoding='unicode')

# TODO: Just read up all apk+name+id from the XML with xpath

#
# The printout below is just for testing the apk calculation
#

print("*** Highest APK products! ***")
# TODO: Cache the results here, store this list to file as well.
apk_values.sort(key=lambda tup: tup[2], reverse=True)
for art in apk_values[:20]:
    print("apk of {} (# {}) is {}, https://www.systembolaget.se/{}".format(art[1], art[0], art[2], art[0]))

print("*** Lowest APK products! ***")
for art in apk_values[-20:]:
    print("apk of {} (# {}) is {}, https://www.systembolaget.se/{}".format(art[1], art[0], art[2], art[0]))
