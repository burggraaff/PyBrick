"""
PyBrick
Olivier Burggraaff

Function definitions
"""
from __future__ import print_function, division
from .classes import Brick, Vendor, Lot, Order
import xml.etree.ElementTree as ET
import requests
from bs4 import BeautifulSoup as soup
import random as ran
import ssl
import datetime

try:
    reduce = reduce  # python 2
except NameError:
    from functools import reduce  # python 3

try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    # Legacy Python that doesn't verify HTTPS certificates by default
    pass
else:
    # Handle target environment that doesn't support HTTPS verification
    ssl._create_default_https_context = _create_unverified_https_context


def read_settings(args):
    regions = ["None", "Asia", "Africa", "North America", "South America",
               "Middle East", "Europe", "Australia & Oceania"]
    x = open(args.settings_file, mode='r')
    lines = x.readlines()
    s = [line.split('#')[0].strip().split(":") for line in lines]
    k = {s_el[0].strip(): s_el[1].strip() for s_el in s}
    k["preferred_countries"] = [country.strip() for country in
                                k["preferred_countries"].split(",")]
    if len(k["preferred_countries"]) == 0:
        raise ValueError("No preferred countries entered. Please enter at \
                         least one, otherwise things can go wrong.\n\nIf you \
                         think that's poor design, you're right.")
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
    if ".bsx" in arg:  # single bsx file:
        return [arg]
    else:
        return read_bsx_files(arg)


def read_bricks(files, nr=-1, verboseprint=print):
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
    verboseprint: function
        Function to print with
        Default: print

    Returns
    -------
    allbricks: list
        List of unique (item/colour) bricks with total quantities needed
    """

    allbricks_ = []

    verboseprint("Will now start reading bricks from files:\n{0}".format(files))

    for bsx in files:
        verboseprint(bsx, end=" ")

        known_parts = [part.code for part in allbricks_]
        tree = ET.parse(bsx)
        root = tree.getroot()
        inventory = root[0]
        bricks_new = [Brick.fromXML(item) for item in inventory.getchildren()]

        for part in bricks_new:
            try:  # if we already know about this brick, add the quantity
                ind = known_parts.index(part.code)
                allbricks_[ind] += part
                verboseprint("Found duplicate:", part.code)
            except ValueError:  # if the brick is unknown, add it to the list
                allbricks_.append(part)

    allbricks_.sort(key=lambda part: -part.qty)

    verboseprint("")

    if nr != -1:
        return allbricks_[:nr]
    else:
        return allbricks_


def prepare_bricks(allbricks):
    """
    Sorts bricks by amount of lots, and sorts lots within each brick by price

    Splits bricks that should always be ordered from a particular lot off, so
    these are not optimised.
    """
    optimize_parts = list(allbricks)  # copy
    optimize_parts.sort(key=lambda part: len(part.lots))
    for part in optimize_parts:
        part.sort_lots()

    # if there is a brick with only one lot, always use that vendor and lot
    lots_always = []
    for part in optimize_parts:
        if part.nrvendors() == 1:
            lots_always.append(part.lots[0])
            optimize_parts.remove(part)

    return optimize_parts, lots_always


def check_enough(bricks):
    parts = list(bricks)  # copy
    never = [part for part in parts if sum(lot.qty for lot in part.lots) <
             part.qty]
    if len(never):
        raise ValueError("You will NEVER be able to order sufficient parts of \
                         the following bricks with current settings. Consider \
                         ordering these in different colours:\n \
                         {never}".format(never))
    notenough = []
    for part in parts:
        if not part.enough():
            parts.remove(part)
            notenough.append(part)

    return parts, notenough


def divide_vendors(vendors, lots_always):
    close = [vendor for vendor in vendors.values() if vendor.close]
    far = [vendor for vendor in vendors.values() if not vendor.close]
    for l in (close, far):  # sort lists to have preferred vendors at the top
        l.sort(key=lambda vendor: -len(vendor.stock_parts))
    always = {lot.vendor for lot in lots_always}
    close_big = close[:20]
    return always, close_big, close, far


def read_vendors(allbricks, settings, len_vendors=100, harsh=False,
                 verboseprint=print):
    """
    Parse the Bricklist website to look for vendors of the bricks you wish to
    purchase

    Parameters
    ----------
    allbricks: iterable
        List of unique (item/colour) bricks with total quantities needed
        ***N.B.*** This is modified in-place
    settings: dict
        Dictionary with settings
    verboseprint: function
        Function to print with
        Default: print

    Returns
    -------
    Vendors: dict
        Dictionary with {vendor_name: Vendor_object}
    """
    vendors = {}
    params_init = {"itemType": "P", "sellerLoc": "R", "regionID":
                   settings["regionID"], "shipCountryID": settings["shipto"],
                   "viewFrom": "sf", "sz": len_vendors, "searchSort": "Q",
                   "pg": "1", "pmt": "18"}
    verboseprint("Will now look for vendors for {0} types of bricks"
                 .format(len(allbricks)))
    for j, part in enumerate(allbricks):
        verboseprint(j, part.code)
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
            new_vendor = Vendor.fromHTML(l, q, preferred=settings["preferred_countries"])
            if harsh and new_vendor.loc not in settings["preferred_countries"]:
                continue
            new_name = new_vendor.storename
            if new_name not in vendors:
                vendors[new_name] = new_vendor
            lot = Lot.fromHTML(q, part, vendors[new_name])
            vendors[new_name].add_lot(lot)
            part.add_vendor(vendors[new_name])
            part.add_lot(lot)

    for vendor in vendors.values():
        if sum(lot.price_total for lot in vendor.stock) < vendor.minbuy:
            del vendor  # remove vendors you can never buy from
        elif vendor.storename in settings["blacklist"]:
            del vendor

    return vendors


def _vendors_of_rare_bricks(bricks, N=None):
    if N is None:
        N = len(bricks) // 25
    return {ran.choice(part.vendors) for part in bricks[:N] if part.enough()}


def _trim_orders(order_list, limit=50):
    orders = sorted(order_list)
    orders = orders[:limit]
    orders = set(orders)
    return orders


def _not_enough(notenough):
    lots = []
    vendors = []
    for part in notenough:
        lots_part = []
        all_lots_part = part.lots[:]
        ran.shuffle(lots_part)
        amount = 0
        while amount < part.qty:
            lots_part.append(all_lots_part.pop())
            amount = sum(lot.order_amount for lot in lots_part)
        lots_part = list(lots_part)
        if amount != part.qty:
            lots_part.sort(key=lambda lot: lot.order_amount)
            while amount > part.qty:
                temp = lots_part.pop()
                amount = sum(lot.order_amount for lot in lots_part)
                if amount < part.qty:
                    lots_part.append(temp)
                    break
        lots.extend(lots_part)
    vendors = {lot.vendor for lot in lots}
    return lots, vendors


def _generate_vendors(optimize_parts, notenough, vendors_always,
                      vendors_close_big, vendors_close, vendors_far,
                      max_vendors, harsh=False):
    lots_notenough, vendors_notenough = _not_enough(notenough)

    vendors_rare = _vendors_of_rare_bricks(optimize_parts)

    vendors_pre = set.union(vendors_always, vendors_notenough, vendors_rare)
    nrvendors_pre = len(vendors_pre)

    choices_left = max_vendors - nrvendors_pre
    howmany_vendors = ran.randint(1, choices_left)

    if harsh:
        which_far = set()
    else:
        howmany_far = ran.randint(0, howmany_vendors//7)
        which_far = set(ran.sample(vendors_far, howmany_far))

    howmany_close_big = ran.randint(1, howmany_vendors//2 + 1)
    which_close_big = set(ran.sample(vendors_close_big, howmany_close_big))

    howmany_close = howmany_vendors - howmany_close_big - howmany_far
    which_close = set(ran.sample(vendors_close, howmany_close))

    vendors = set.union(vendors_pre, which_far, which_close_big, which_close)
    print(choices_left, howmany_vendors, len(vendors), howmany_far, howmany_close_big, howmany_close)

    return lots_notenough, vendors


def find_order(optimize_parts, lots_always, vendors_always, vendors_close_big,
               vendors_close, vendors_far, notenough,
               max_vendors=10, harsh=False, weight=20, w_far=150,
               verboseprint=print, timeout=10.):
    now = datetime.datetime.now
    t_end = now() + datetime.timedelta(minutes=timeout)
    verboseprint("Starting optimisation; will take until {0:02d}:{1:02d}"
                 .format(t_end.hour, t_end.minute))
    i = j = 0
    vendorwarning_given = False
    orders = set()
    while (now() < t_end):
        i += 1
        try:
            lots_notenough, try_vendors = _generate_vendors(optimize_parts,
                                                            notenough,
                                                            vendors_always,
                                                            vendors_close_big,
                                                            vendors_close,
                                                            vendors_far,
                                                            max_vendors,
                                                            harsh=harsh)
        except ValueError:
            if not vendorwarning_given:
                vendorwarning_given = True
                print("ValueError -- consider changing MaxVendors")
            continue
        available_parts = list(set(reduce(lambda a, b: a + b, (vendor.stock_parts for vendor in try_vendors))))
        if not all(part in available_parts for part in optimize_parts):
            continue

        lots = lots_always + lots_notenough + \
            [part.cheapest_lot(try_vendors) for part in optimize_parts]

        order = Order(lots, weight, w_far)
        if len(order.vendors) > max_vendors:
            continue
        if not order.valid_minbuy():
            continue

        j += 1
        #verboseprint(j, order)
        orders.add(order)

        if len(orders) == 400:
            verboseprint("Trimming list of orders...")
            orders = _trim_orders(orders)

    verboseprint("\nFinished optimalisation")
    orders = sorted(orders)
    verboseprint("Found", j, "valid orders ( out of", i, "attempts -",
                 round(float(j)/i * 100, 1), "% )")
    verboseprint("in", timeout, "minutes")

    try:
        best = orders[0]
        verboseprint("Best:", best)
    except IndexError:
        print("Did not find any orders!")
        print("Consider changing the maxvendors and/or timeout parameters.")

    return best, orders
