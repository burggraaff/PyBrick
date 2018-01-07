"""
PyBrick
Olivier Burggraaff

Main script
"""
from __future__ import print_function

from PyBrick import functions as f
from argparse import ArgumentParser

parser = ArgumentParser()
parser.add_argument("bsx_list", help="Location of file with list of BSX files\
                    to import")
parser.add_argument("-s", "--save_to", help="Location to save order list to",
                    default="best.order")
parser.add_argument("-e", "--settings_file", help="File containing settings",
                    default="settings.txt")
parser.add_argument("-t", "--timeout", help="How many minutes to optimise for",
                    type=float, default=10.0)
parser.add_argument("-m", "--max_vendors", help="Maximum number of vendors to\
                    use", type=int, default=10)
parser.add_argument("-l", "--len_vendors", help="Number of vendors per brick\
                    to fetch from Bricklink per brick", type=int, default=100)
parser.add_argument("-w", "--weight", help="Weight to add for nearby vendors",
                    type=int, default=20)
parser.add_argument("-f", "--w_far", help="Weight to add for faraway vendors",
                    type=int, default=150)
parser.add_argument("-H", "--harsh", action="store_true", help="If True, only\
                    use vendors from preferred countries")
parser.add_argument("-q", "--quiet", action="store_true")
args = parser.parse_args()
args.timeout *= 60.

# print if not quiet, else do nothing
verboseprint = print if not args.quiet else lambda *args, **kwargs: None

settings = f.read_settings(args)
verboseprint("Read settings from {0}".format(args.settings_file))

bsx_files = f.parse_bsx_filename_input(args.bsx_list)
verboseprint("Read BSX filenames from {0}".format(args.bsx_list))

allbricks = f.read_bricks(bsx_files, verboseprint=verboseprint)
verboseprint("Made list of {0} types of bricks".format(len(allbricks)))

vendors = f.read_vendors(allbricks, settings, harsh=args.harsh,
                         verboseprint=verboseprint,
                         len_vendors=args.len_vendors)
verboseprint("Made list of vendors, {nr} in total".format(nr=len(vendors)))

optimize_parts, lots_always = f.prepare_bricks(allbricks)

vendors_always, vendors_close_big, vendors_close, vendors_far = \
    f.divide_vendors(vendors, lots_always)

optimize_parts, notenough = f.check_enough(optimize_parts)

best_order = f.find_order(optimize_parts, lots_always, vendors_always,
                          vendors_close_big, vendors_close, vendors_far,
                          notenough, max_vendors=args.max_vendors,
                          harsh=args.harsh, weight=args.weight,
                          w_far=args.w_far, verboseprint=verboseprint,
                          timeout=args.timeout)

if len(notenough):
    print("\nNote: with current settings for finding vendors, you cannot order\
          a full lot of:")
    for n in notenough:
        print(n.code, ",")
    print("\nConsider ordering these in different colours.")

verboseprint("The following parts have the fewest available lots:")
for part in optimize_parts[:10]:
    verboseprint(part.code, "({0})".format(len(part.lots)), end=" ")

verboseprint("\nSaving best order to file:", args.save_to)
best_order.save(args.save_to)
