"""
PyBrick
Olivier Burggraaff

Function definitions
"""

from . import classes as c
import xml.etree.ElementTree as ET
import requests
from bs4 import BeautifulSoup as soup
import random as ran
import ssl

try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    # Legacy Python that doesn't verify HTTPS certificates by default
    pass
else:
    # Handle target environment that doesn't support HTTPS verification
    ssl._create_default_https_context = _create_unverified_https_context

#default_settings = {"shipto": "NL", "region": "Europe", "preferred_countries": \
#["Netherlands", "Germany", "Belgium", "United Kingdom", "Luxembourg"], "maxvendors":\
#5, "timeout": 1./60, "vendorlist_length": 250, "verbose": True, "harsh": False, "weight_close": 20.,\
#"weight_far": 100., "blacklist": []}

def read_settings(args):
    regions = ["None", "Asia", "Africa", "North America", "South America", "Middle East", "Europe", "Australia & Oceania"]
    x = open(args.settings_file, mode = 'r')
    lines = x.readlines()
    s = [line.split('#')[0].strip().split(":") for line in lines]
    k = {s_el[0].strip(): s_el[1].strip() for s_el in s}
    #for key in default_settings.keys():
    #    if key not in k.keys():
    #        print "Did not find key '{0}' in settings; using default ({1})".format(key, default_settings[key])
    #        k[key] = default_settings[key]
    #for key in k.keys():
    #    if key not in default_settings.keys():
    #        print "Unrecognised setting '{0}' entered; will be ignored".format(key)
    #        k.pop(key)
    k["preferred_countries"] = [country.strip() for country in k["preferred_countries"].split(",")]
    k["harsh"] = (k["harsh"] == "1")
    k["weight_close"] = float(k["weight_close"])
    k["weight_far"] = float(k["weight_far"])
    if len(k["preferred_countries"]) == 0:
        raise ValueError("No preferred countries entered. Please enter at least one, otherwise things can go wrong.\n\nIf you think that's poor design, you're right.")
    k["regionID"] = regions.index(k["region"])
    k["blacklist"] = [i.strip() for i in k["blacklist"].split(",")]

    return k

def read_bsx_files(fileloc):
    x = open(fileloc, mode="r")
    lines = x.readlines()
    s = [line.split(" ") for line in lines]
    s1 = [el[0].strip() for el in s if len(el) == 1]
    s2 = [x for y in [[el[0]] * int(el[1]) for el in s if len(el) == 2] for x in y]
    r = sorted(s1 + s2)
    r = [el if ("." in el) else el+".bsx" for el in r]
    return r

def parse_bsx_filename_input(arg):
	if ".bsx" in arg: # single bsx file:
		return [arg]
	else:
		return read_bsx_files(arg)
	
def read_bricks(files, nr = -1, quiet = False):
    """
    Parse a list of BSX files into a list of Brick objects

    Parameters
    ----------
    files: iterable
        List (or other iterable) of files to parse
    nr: int, optional
        Return only the first nr bricks (-1 if all)
		This is for debugging
		Default: -1
    quiet: bool, optional
		If True, do not print outputs
		Default: False

    Returns
    -------
    allbricks: list
        List of unique (item/colour) bricks with total quantities needed
    """

    allbricks_ = []

    if not quiet:
        print "Will now start reading bricks from files:\n{0}".format(files)

    for bsx in files:
        if not quiet:
            print bsx,

        known_parts = [part.code for part in allbricks_]
        tree = ET.parse(bsx)
        root = tree.getroot()
        inventory = root[0]
        bricks_new = [c.Brick(item) for item in inventory.getchildren()]

        for part in bricks_new:
            try: # if we already know about this brick, add the quantity
                ind = known_parts.index(part.code)
                allbricks_[ind] += part
                if not quiet:
                    print "Found duplicate:", part.code
            except ValueError: # if the brick is unknown, add it to the list
                allbricks_.append(part)

    allbricks_.sort(key=lambda part: -part.qty)

    if not quiet:
        print ""

    if nr != -1:
        return allbricks_[:nr]
    else:
        return allbricks_

def prepare_bricks(allbricks):
    optimize_parts = list(allbricks)
    optimize_parts.sort(key=lambda part: len(part.lots))
    for part in optimize_parts:
        part.sort_lots()
	return optimize_parts
		
def find_vendor_name(tdtag):
    return tdtag.findAll("a")[1].text

def find_vendor_storename(tdtag):
    return tdtag.findAll("a")[1].attrs["href"].split("&")[0].split("=")[1]

def parse_vendor(fonttag, tdtag, settings):
    name = find_vendor_name(tdtag)
    font_ = fonttag.text.split("Min Buy: ")
    loc = font_[0][5:][:-2]
    if settings["harsh"] and (loc not in settings["close_countries"]):
        raise ValueError("Vendor not close")
    if "EUR" in font_[1]:
        try:
            minbuy = float(font_[1][5:])
        except:
            minbuy = None
    else:
        minbuy = None
    storename = find_vendor_storename(tdtag)
    linktag = tdtag.findAll("a")[1]
    storename = linktag.attrs["href"].split("&")[0].split("=")[1]
    return c.Vendor(name, storename, loc, minbuy, settings)

def parse_lot(part, tdtag, vendor):
    price1 = tdtag.find("font", attrs={"face": "Verdana", "size": "-2"}).text
    if "EUR" in price1:
        price = float(price1.strip(")").strip("(EUR "))
    else:
        price = float(tdtag.findAll("b")[1].text.strip("EUR "))
    qty = int(tdtag.findAll("b")[0].text.replace(",", ""))
    asstr = str(tdtag)
    asstr_close_b = asstr.find("</b>")+6
    if asstr[asstr_close_b] == "(":
        step = int(asstr[asstr_close_b:asstr_close_b+asstr[asstr_close_b:].find(")")][2:])
    else:
        step = 1
    lotnr = tdtag.findAll("a")[1].attrs["href"].split("=")[-1]
    return c.Lot(part, vendor, price, qty, step, lotnr)

def read_vendors(allbricks, settings, quiet = False):
    """
    Parse the Bricklist website to look for vendors of the bricks you wish to purchase

    Parameters
    ----------
    allbricks: iterable
        List of unique (item/colour) bricks with total quantities needed
        ***N.B.*** This is modified in-place
    settings: dict
        Dictionary with settings
    quiet: bool, optional
		If True, do not print outputs
		Default: False

    Returns
    -------
    Vendors: dict
        Dictionary with {vendor_name: Vendor_object}
    """
    vendors = {}
    params_init = {"itemType": "P", "sellerLoc": "R", "regionID": settings["regionID"],\
        "shipCountryID": settings["shipto"], "viewFrom": "sf", "sz": settings["vendorlist_length"],\
        "searchSort": "Q", "pg": "1", "pmt": "18"}
    if not quiet:
        print "Will now look for vendors for {0} types of bricks".format(len(allbricks))
    try:
        for j, part in enumerate(allbricks):
            if not quiet:
                print j, part.code
            URL = part.URL(params_init)
            html = requests.get(URL, headers={'User-Agent': 'Mozilla/5.0'}).text
            htmlsoup = soup(html, "html.parser")
            if "No Item(s) were found.  Please try again!" in htmlsoup.text:
                params_init_ = params_init.copy()
                params_init_["qMin"] = 1
                URL = part.URL(params_init_)
                html = requests.get(URL, headers={'User-Agent': 'Mozilla/5.0'}).text
                htmlsoup = soup(html, "html.parser")
            qtylinkprice = htmlsoup.findAll("td", {"valign": "TOP"})
            locminbuy = htmlsoup.findAll("font", {"color": r"#606060"})
            for l, q in zip(locminbuy, qtylinkprice):
                try:
                    storename = find_vendor_storename(q)
                    if storename in settings["blacklist"]:
                        continue
                    if storename not in vendors:
                        vendors[storename] = parse_vendor(l, q, settings)
                    lot = parse_lot(part, q, vendors[storename])
                    vendors[storename].add_lot(lot)
                    part.add_vendor(vendors[storename])
                    part.add_lot(lot)
                except ValueError:
                    continue
    except Exception as e:
        raise e

    try:
        for vendor in vendors.values():
            if sum(lot.price_total for lot in vendor.stock) < vendor.minbuy:
                del vendor # remove vendors you can never buy from
    except Exception as e:
        raise e

    return vendors

def cheapest_lot(part, vendors):
    available_lots = [lot for lot in part.lots if lot.vendor in vendors]
    available_lots.sort(key = lambda lot: lot.price_total)
    return available_lots[0]

def vendors_of_rare_bricks(bricks, N = None):
    if N is None:
        N = len(bricks) // 25
    return list(set(ran.choice(part.vendors) for part in bricks[:N] if part.enough()))
