"""
PyBL
Olivier Burggraaff

Main script
"""

from PyBrick import classes as c, functions as f
from argparse import ArgumentParser
import time
import datetime
import random as ran

parser = ArgumentParser()
parser.add_argument("bsx_list", help = "Location of file with list of BSX files to import")
parser.add_argument("-s", "--save_to", help = "Location to save order list to", default = "best.order")
parser.add_argument("-e", "--settings_file", help = "File containing settings", default = "settings.txt")
parser.add_argument("-t", "--timeout", help = "How many minutes to optimise for", type = float, default = 10.0)
parser.add_argument("-m", "--max_vendors", help = "Maximum number of vendors to use", type = int, default = 10)
parser.add_argument("-q", "--quiet", action = "store_true")
args = parser.parse_args()
args.timeout *= 60.
settings = f.read_settings(args)
if not args.quiet:
	print "Read settings from {0}".format(args.settings_file)

bsx_files = f.read_bsx_files(args.bsx_list)
if not args.quiet:
	print "Read BSX filenames from {0}".format(args.bsx_list)

allbricks = f.read_bricks(bsx_files, quiet = args.quiet)
if not args.quiet:
	print "Made list of {0} types of bricks".format(len(allbricks))

vendortime = time.time()
vendors = f.read_vendors(allbricks, settings, quiet = args.quiet)
if not args.quiet:
	print "Made list of vendors;", len(vendors), "(", round(time.time() - vendortime, 2), ")"

allbricks.sort(key=lambda part: len(part.lots))

for part in allbricks:
    part.sort_lots()

optimize_parts = allbricks[:] # this is here for debugging purposes

# if there is a brick with only one lot, always use that vendor and lot
lots_always = []
for part in allbricks:
    if part.nrvendors() == 1:
        lots_always.append(part.lots[0])
        optimize_parts.remove(part)

vendors_close = filter(lambda vendor: vendor.close(settings), vendors.values())
vendors_far = filter(lambda vendor: not vendor.close(settings), vendors.values())
for l in (vendors_close, vendors_far):
    l.sort(key = lambda vendor: -len(vendor.stock_parts))
vendors_always = [lot.vendor for lot in lots_always]

vendors_close_big = vendors_close[:20]

neverenough = [part for part in allbricks if sum(lot.qty for lot in part.lots) < part.qty]
if len(neverenough):
    print "\nNote: with current settings for finding vendors, you will ***NEVER***"
    print "be able to find enough of",
    for n in neverenough:
        print n.code, ",",
    print "\nConsider ordering these in different colours."

for n in neverenough:
    optimize_parts.remove(n)

notenough = []
for part in optimize_parts:
	if part.enough():
		continue
	optimize_parts.remove(part)
	notenough.append(part)

t_end = datetime.datetime.now() + datetime.timedelta(seconds = args.timeout)
if not args.quiet:
	print "Starting optimisation; will take until {0:02d}:{1:02d}".format(t_end.hour, t_end.minute)
j = 0
i = 0
vendorwarning_given = False
try:
    assert orders
except:
    orders = []
endat = time.time() + args.timeout
while (time.time() < endat):
    i += 1
    lots_notenough = []
    vendors_notenough = []
    if len(notenough):
        for part in notenough:
            lots_part = []
            all_lots_part = part.lots[:]
            ran.shuffle(lots_part)
            amount = 0
            while amount < part.qty:
                lots_part.append(all_lots_part.pop())
                amount = sum(lot.order_amount for lot in lots_part)
            lots_part = list(lots_part)
            if amount == part.qty:
                lots_notenough.extend(lots_part)
                continue
            lots_part.sort(key = lambda lot: lot.order_amount)
            while amount > part.qty:
                temp = lots_part.pop()
                amount = sum(lot.order_amount for lot in lots_part)
                if amount < part.qty:
                    lots_part.append(temp)
                    break
            lots_notenough.extend(lots_part)
        vendors_notenough = list(set(lot.vendor for lot in lots_notenough))

    try:
        vendors_rare = f.vendors_of_rare_bricks(optimize_parts)

        nrvendors_now = len(vendors_always) + len(vendors_rare) + len(vendors_notenough)
        x = args.max_vendors-nrvendors_now
        howmany_vendors = ran.randint(1, x)
        howmany_far = 0 if settings["harsh"] else ran.randint(0, int(howmany_vendors/7))
        howmany_close_big = ran.randint(1, howmany_vendors/2+1)
        howmany_close = howmany_vendors - howmany_close_big - howmany_far
    except NameError:
        print "NameError (in choosing random values)!"
        break
    except ValueError:
        if not vendorwarning_given:
            print "ValueError -- probably not enough vendors"
            vendorwarning_given = True
        continue
    except:
        continue
    try:
        try_vendors = list(set(vendors_always + vendors_notenough + vendors_rare \
        + ran.sample(vendors_close_big, howmany_close_big) + ran.sample(vendors_close, howmany_close) \
        + ran.sample(vendors_far, howmany_far)))
        available_parts = list(set(reduce(lambda a, b: a + b, (vendor.stock_parts for vendor in try_vendors))))
    except NameError:
        print "NameError (in choosing random vendors)!"
        break
    except:
        continue
    if not all(part in available_parts for part in allbricks):
        continue

    lots = lots_always + lots_notenough + [f.cheapest_lot(part, try_vendors) for part in optimize_parts]

    order = c.Order(settings, *lots)
    if len(order.vendors) > args.max_vendors:
        continue
    if not order.valid_minbuy():
        continue

    j += 1
    if not args.quiet:
        print j, order #printing the orders does not significantly slow the loop down
    orders.append(order)

    if len(orders) == 400: # to conserve memory, we remove bad orders
        if not args.quiet:
            print "Trimming list of orders..."
        orders.sort()
        orders = orders[:50]

    if not j%20000:
        if not args.quiet:
            print "Removing duplicates..."
        orders.sort()
        orders = [order_ for z, order_ in enumerate(orders) if not any(order_ == order2 for order2 in orders[:z])] # remove duplicates

if not args.quiet:
	print ""
	print "Finished optimalisation"
orders.sort()
orders = [order_ for z, order_ in enumerate(orders) if not any(order_ == order2 for order2 in orders[:z])] # remove duplicates
orders = orders[:50]
if not args.quiet:
	print "Found", j, "valid orders ( out of", i, "attempts -", round(float(j)/i * 100, 1) , "% )"
	print "in", args.timeout/60., "minutes"

try:
	best = orders[0]
	if not args.quiet:
		print "Best:", best
except IndexError:
    print "Did not find any orders!"
    print "Consider changing the maxvendors and/or timeout parameters."

if len(notenough):
    print "\nNote: with current settings for finding vendors, you cannot order a full lot of:"
    for n in notenough:
        print n.code, ","
    print "\nConsider ordering these in different colours."

if len(neverenough):
    print "\nNote: with current settings for finding vendors, you will ***NEVER*** be able to find enough of:"
    for n in neverenough:
        print n.code, ",",
    print "\nConsider ordering these in different colours."

if not args.quiet:
	print "The following parts have the fewest available lots:"
	for part in optimize_parts[:10]:
		print part.code, "({0})".format(len(part.lots)),

if len(orders) > 0:
	if not args.quiet:
		print "\nSaving best order to file:", args.save_to
	orders[0].save(args.save_to)