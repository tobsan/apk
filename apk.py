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

import xml.etree.ElementTree as ET
import os.path
import urllib.request
from datetime import datetime

def parse_alcohol(alc_as_string):
    if not alc_as_string[-1:] == "%":
        raise ValueError("Not an alcohol percentage, need to end with %")

    # Shave off the percentage sign
    alc_numbers = alc_as_string[:-1]

    # This will throw ValueError in case it can't be converted
    value = float(alc_numbers)
    if value > 100:
        raise ValueError("Percentage can't be larger than 100%")

    return value

class APKError(Exception):
    def __init__(self, expression, message):
        self.expression = expression
        self.message = message

class APK:
    """
    A class abstracting the XML format for the APK state
    """

    products_file_url = "https://www.systembolaget.se/api/assortment/products/xml"

    def __init__(self, file_name = "products.xml"):
        self.__products_file_name = file_name
        self.__tree = None

        if not os.path.exists(self.__products_file_name):
            print("No product database file available, downloading...")
            if not self.__download_products():
                raise APKError("Could not download product database file")

        if not self.__parse_products_file():
            raise APKError("Could not open product database file")

        # TODO: Check for errors?
        self.__calculate_apk()

    def __download_products(self):
        """
            Downloads the product database file from systembolaget's API
        """
        print("Downloading product database file...")
        # Delete the file if already present
        if os.path.exists(self.__products_file_name):
            os.unlink(self.__products_file_name)

        retries = 0
        max_retries = 3
        # Try to download the file
        while not os.path.exists(self.__products_file_name) and retries < max_retries:
            try:
                return urllib.request.urlretrieve(self.products_file_url, self.__products_file_name)
            except:
                retries = retries + 1
        return None

    def __parse_products_file(self):
        try:
            self.__tree = ET.parse(self.__products_file_name)
            root = self.__tree.getroot()
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
            if not self.__download_products():
                raise APKError("Could not download product database file")
            return self.__parse_products_file()

        return self.__tree

    def __calculate_apk(self):
        """
            For every product in the database, calculate the APK value and add it as an xml node to
            the tree. Then save the tree.
        """
        root = self.__tree.getroot()
        for artikel in root.findall('.//artikel'):
            nr = artikel.find('nr').text
            name = artikel.find('Namn').text

            # If an APK value is present in any node, we assume it is present in all nodes, and we
            # can stop processing here.
            if artikel.find('apk') is not None:
                print("Already has APK in file, stopping")
                break

            cost = float(artikel.find('Prisinklmoms').text)
            # TODO: Handle possible errors from this call
            alcohol_percent = parse_alcohol(artikel.find('Alkoholhalt').text)

            # Alcohol-free drinks makes this list useless
            # TODO: Is this a good idea really?
            if alcohol_percent == 0:
                continue

            volume = float(artikel.find('Volymiml').text)
            alcohol_ml = volume * (alcohol_percent / 100)
            apk = alcohol_ml / cost

            apk_node = ET.SubElement(artikel, 'apk')
            apk_node.text = str(apk)

        # Save the apk annotated file
        self.__tree.write(self.__products_file_name, encoding='unicode')


apk_values=[]
apk = APK()
# TODO: Retrieval function for APK values

#
# The printout below is just for testing the apk calculation
# FIXME: For now, this prints nothing.
#

print("*** Highest APK products! ***")
# TODO: Cache the results here, store this list to file as well.
apk_values.sort(key=lambda tup: tup[2], reverse=True)
for art in apk_values[:20]:
    print("apk of {} (# {}) is {}, https://www.systembolaget.se/{}".format(art[1], art[0], art[2], art[0]))

print("*** Lowest APK products! ***")
for art in apk_values[-20:]:
    print("apk of {} (# {}) is {}, https://www.systembolaget.se/{}".format(art[1], art[0], art[2], art[0]))
