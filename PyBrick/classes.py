"""
PyBrick
Olivier Burggraaff

Class definitions
"""
from __future__ import print_function, division
import xml.etree.ElementTree as ET
try:
    from urllib import urlencode #  python2
except:
    from urllib.parse import urlencode #  python3

class Brick(object):
    """
    This class represents a unique LEGO brick, defined with an ItemID
    (which brick) and a ColorID (which colour).
    """
    def __init__(self, item):
        """
        Create a Brick object from an XML item
        """
        assert isinstance(item, ET.Element), "Did not get XML item to create Brick object; instead got "+str(type(item))
        asdict = {b.tag: b.text for b in item.getchildren()}
        for key in asdict:
            setattr(self, key, asdict[key])
        self.qty = int(self.Qty) ; del self.Qty
        self.code = self.ItemID+"|"+self.ColorID
        self.vendors = []
        self.lots = []
    def add_vendor(self, vendor):
        """
        Add a vendor to the list of vendors for this Brick
        """
        self.vendors.append(vendor)
    def nrvendors(self):
        """
        How many vendors sell this brick?
        """
        return len(self.vendors)
    def add_lot(self, lot):
        """
        Add a lot to the list of lots for this Brick
        """
        self.lots.append(lot)
    def sort_lots(self):
        """
        Sort the lots of this brick from cheapest to most expensive
        """
        self.lots.sort(key = lambda lot: lot.price_total)
    def enough(self):
        """
        Does any single lot have enough of this brick?
        """
        return any(lot.qty >= self.qty for lot in self.lots)
    def URL(self, settings):
        params_main = dict({"invNew": self.Condition, "q": self.ItemID, "qMin": self.qty, "colorID": self.ColorID}, **settings)
        data = urlencode(params_main)
        URL = "http://www.bricklink.com/search.asp?"+data
        return URL
    def __iadd__(self, other):
        """
        Lets you add to the quantity of a Brick object:
            >>> part = Brick(...)
            >>> part.qty = 5
            >>> part.qty
            5
            >>> part += 1
            >>> part.qty
            6
        """
        if type(other) is int:
            self.qty += other
        elif type(other) is float:
            self.qty += int(other)
        elif type(other) is Brick:
            if other.code == self.code:
                self.qty += other.qty
            else:
                raise ValueError("Trying to add Brick "+other.code+" to Brick "+self.code)
        return self
    def __repr__(self):
        line = "----------"
        properties = reduce(lambda x,y:x+y, ["\n"+key+": "+str(self.__dict__[key]) for key in ["code", "ItemName", "ColorName", "qty", "Condition"]])
        vendorline = "\n# Vendors: "+str(self.nrvendors())
        return line+properties+vendorline+"\n"+line

class Lot(object):
    def __init__(self, part, vendor, price, qty, step, lotnr):
        self.part = part
        self.vendor = vendor
        self.price = price
        self.qty = qty
        self.step = step
        self.nr = lotnr
        self.URL = self.vendor.URL + '#/shop?o={{"showHomeItems":0,"q":"{nr}"}}'.format(nr=self.nr)
        minqty = min(self.qty, self.part.qty)
        self.order_amount = self.step * (minqty//self.step + (minqty%self.step > 0))
        self.price_total = round(self.order_amount * self.price, 2)
    def __repr__(self):
        return "E"+str(self.price_total)+" for "+self.part.code+" at "+self.vendor.storename.encode("ascii", "replace")+" ("+self.vendor.loc+")"

class Vendor(object):
    def __init__(self, name, storename, loc, minbuy, settings):
        self.loc = loc
        if settings["harsh"] and (self.loc not in settings["close_countries"]):
            raise ValueError("Vendor not close")
        self.minbuy = minbuy
        self.name = name
        self.storename = storename
        self.URL = "https://store.bricklink.com/{0}".format(self.storename)
        self.stock = []
        self.stock_parts = []
    def add_lot(self, lot):
        self.stock.append(lot)
        if lot.part not in self.stock_parts:
            self.stock_parts.append(lot.part)
    def close(self, settings):
        return (self.loc in settings["preferred_countries"])
    def __repr__(self):
        return self.storename.encode("ascii", "replace")+" in "+self.loc+" with "+str(len(self.stock))+" items"

class Order(object):
    def __init__(self, settings, *lots):
        self.lots = [lot for lot in lots]
        self.vendors = set(lot.vendor for lot in lots)
        self._score(settings)
    def add_lot(self, lot, settings):
        self.lots.append(lot)
        self.vendors.add(lot.vendor)
        self._score(settings)
    def totalprice(self):
        return round(sum(lot.price_total for lot in self.lots), 3)
    def _score(self, settings): # NOTE THIS DOES NOT RETURN ANYTHING
        self.score = round(self.totalprice() + settings["weight_close"] * len(self.vendors) +settings["weight_far"] * len([v for v in self.vendors if not v.close(settings)]), 3)
    def give_URLs(self):
        URLs = sorted([lot.URL+" | "+str(lot.order_amount)+"\n" for lot in self.lots])
        URLstring = "".join(URLs)[:-1] #[:-1] to remove trailing \n
        return URLstring
    def save(self, filename="a.order"):
        string = self.give_URLs()
        with open(filename, "w") as f:
            f.write(string)
    def valid_minbuy(self):
        return all([sum(lot.price_total for lot in self.lots if lot.vendor == vendor) >= vendor.minbuy for vendor in self.vendors])
    def lots_per_vendor(self):
        return {vendor: len([lot for lot in self.lots if lot.vendor == vendor]) for vendor in self.vendors}
    def money_per_vendor(self):
        return {vendor: round(sum([lot.price_total for lot in self.lots if lot.vendor == vendor]), 3) for vendor in self.vendors}
    def __eq__(self, other):
        return self.score == other.score
    def __lt__(self, other):
        return self.score < other.score
    def __repr__(self):
        return "Order of score "+str(self.score)+" with price "+str(self.totalprice())+" at "+str(len(self.vendors))+" vendors"
