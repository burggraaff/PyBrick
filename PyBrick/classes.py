"""
PyBrick
Olivier Burggraaff

Class definitions
"""
from __future__ import print_function, division
import xml.etree.ElementTree as ET
try:
    from urllib import urlencode  # python2
except ImportError:
    from urllib.parse import urlencode  # python3


class Brick(object):
    """
    This class represents a unique LEGO brick, defined with an itemID
    (which brick) and a colorID (which colour).
    """
    def __init__(self, itemID, colorID, qty=0, condition="",
                 itemname="itemName?", colourname="colourName?", **attributes):
        self.itemID = itemID
        self.colorID = colorID
        self.qty = qty
        self.condition = condition
        self.itemname = itemname
        self.colourname = colourname
        self.code = self.itemID + "|" + self.colorID
        for attr in attributes:
            setattr(self, attr, attributes[attr])
        self.vendors = []
        self.lots = []

    @classmethod
    def fromXML(cls, item):
        """
        Create a Brick object from an XML item
        """
        asdict = {b.tag: b.text for b in item.getchildren()}
        itemID = asdict.pop("ItemID")
        colorID = asdict.pop("ColorID")
        qty = int(asdict.pop("Qty"))
        condition = asdict.pop("Condition", "")
        itemname = asdict.pop("ItemName", "itemName?")
        colourname = asdict.pop("ColorName", "colourName?")
        return cls(itemID, colorID, qty=qty, condition=condition,
                   itemname=itemname, colourname=colourname, **asdict)

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
        self.lots.sort(key=lambda lot: lot.price_total)

    def cheapest_lot(self, vendors):
        """
        Find the cheapest lot of this item from the given vendors
        """
        available_lots = [lot for lot in self.lots if lot.vendor in vendors]
        available_lots.sort(key=lambda lot: lot.price_total)
        return available_lots[0]

    def enough(self):
        """
        Does any single lot have enough of this brick?
        """
        return any(lot.qty >= self.qty for lot in self.lots)

    def URL(self, settings):
        params = {"invNew": self.condition, "q": self.itemID, "qMin": self.qty,
                  "colorID": self.colorID}
        params.update(settings)
        data = urlencode(params)
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
        properties = "\n".join([self.code, self.itemname, self.colourname,
                                self.condition, str(self.qty)])
        vendorline = "{v} vendors".format(v=self.nrvendors())
        return "\n".join([line, properties, vendorline, line])


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
        self.order_amount = self.step * (minqty//self.step + (minqty % self.step > 0))
        self.price_total = round(self.order_amount * self.price, 2)

    @classmethod
    def fromHTML(cls, tag, part, vendor):
        price1 = tag.find("font", attrs={"face": "Verdana", "size": "-2"}).text
        if "EUR" in price1:
            price = float(price1.strip(")").strip("(EUR "))
        else:
            price = float(tag.findAll("b")[1].text.strip("EUR "))
        qty = int(tag.findAll("b")[0].text.replace(",", ""))
        asstr = str(tag)
        asstr_b = asstr.find("</b>")+6
        if asstr[asstr_b] == "(":
            step = int(asstr[asstr_b:asstr_b+asstr[asstr_b:].find(")")][2:])
        else:
            step = 1
        lotnr = tag.findAll("a")[1].attrs["href"].split("=")[-1]
        return cls(part, vendor, price, qty, step, lotnr)

    def __repr__(self):
        return "Lot (Part {part:8}; Price {price:>6.2f}; Vendor {vendor}, {loc})"\
               .format(part=self.part.code, price=self.price_total,
                       vendor=self.vendor.storename, loc=self.vendor.loc)

class Vendor(object):
    def __init__(self, name, storename, loc, minbuy, preferred=[]):
        self.loc = loc
        self.close = self.loc in preferred
        self.minbuy = minbuy
        self.name = name
        self.storename = storename
        self.URL = "https://store.bricklink.com/{0}".format(self.storename)
        self.stock = []
        self.stock_parts = []

    @classmethod
    def fromHTML(cls, font, td, **kwargs):
        name = td.findAll("a")[1].text
        font_ = font.text.split("Min Buy: ")
        loc = font_[0][5:][:-2]
        if "EUR" in font_[1]:
            try:
                minbuy = float(font_[1][5:])
            except ValueError:
                minbuy = 0.0
        else:
            minbuy = 0.0
        linktag = td.findAll("a")[1]
        storename = linktag.attrs["href"].split("&")[0].split("=")[1]
        return cls(name, storename, loc, minbuy, **kwargs)

    def add_lot(self, lot):
        self.stock.append(lot)
        if lot.part not in self.stock_parts:
            self.stock_parts.append(lot.part)

    def __eq__(self, other):
        return self.storename == other.storename

    def __hash__(self):
        return hash(self.storename)

    def __repr__(self):
        return "{name} ({loc}, {stock})".format(name=self.storename,
                                                loc=self.loc,
                                                stock=len(self.stock))


class Order(object):
    def __init__(self, lots, weight, w_far):
        self.lots = lots
        self.vendors = {lot.vendor for lot in self.lots}
        self.weight = weight
        self.w_far = w_far

    def add_lot(self, lot):
        self.lots.append(lot)
        self.vendors.add(lot.vendor)

    def totalprice(self):
        return round(sum(lot.price_total for lot in self.lots), 3)

    def score(self):
        return round(self.totalprice() + self.weight * len(self.vendors)
                     + self.w_far * len([v for v in self.vendors
                                         if not v.close]))

    def give_URLs(self):
        URLs = sorted([lot.URL+" | "+str(lot.order_amount)+"\n" for lot in self.lots])
        URLstring = "".join(URLs)[:-1]  # [:-1] to remove trailing \n
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
        return self.score() == other.score()

    def __lt__(self, other):
        return self.score() < other.score()

    def __hash__(self):
        return hash(self.score())

    def __repr__(self):
        return "Order (Score {score:>5}; Price {price:>8.2f}; \
Vendors {vendors:>3})".format(score=self.score(), price=self.totalprice(),
                              vendors=len(self.vendors))
