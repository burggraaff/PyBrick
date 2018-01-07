# PyBrick

PyBrick is a Python module that allows optimisation of large orders on [BrickLink](https://www.bricklink.com). It allows the user to reduce an unwieldy offer, consisting of possibly hundreds of different parts, into a short list of lots to purchase.

# Usage

For inexperienced users, it is suggested to use the *main.py* script to do the optimisation. Usage of this script will be further explained later in this paragraph. Advanced users may prefer to directly use the functions and classes present in the PyBrick module, by importing it: `import PyBrick`. This paragraph will focus only on usage of the *main.py* script.

The installation of PyBrick is very simple: simply clone or copy the files in this repository to your computer. PyBrick works for Python versions 2.7 and 3+. Some additional Python modules are also required; if these are not present, simply install these, for example with [pip](https://pypi.python.org/pypi/pip). The required modules are:

* requests
* bs4

The script is called from the command line as follows:

```
python main.py <bsx-list> <options>
```

If the command line is run in a different directory from that in which PyBrick is located, please specify its full location (e.g. `python C:\my\folders\and\things\main.py ...`).

## Command line input

PyBrick works using BSX files, which are XML files containing all the information of the bricks one wants to purchase. These files can be generated using programmes such as [BrickStore](http://www.brickforge.de/software/brickstore/). Any number of BSX files can be used at once.

The `<bsx-list>` parameter is the only required argument for *main.py*, and should be simply the location of a plain text file containing the list of BSX files one wants the programme to parse. For example:

```
plane.bsx
train.bsx
car.bsx 10
dog.bsx 2
```

PyBrick will interpret the file given above as follows: order each brick in *plane.bsx* once, each in *train.bsx* once, each brick in *car.bsx* 10 times and each brick in *dog.bsx* twice. Any duplicate bricks between these files will be handled such that the total amount required will be used in the further optimisation.

Additionally, there are several optional arguments to tweak the performance of the *main.py* script. A short explanation of these can be found by running `python main.py --help` in the command line, or below:

| Key | Name | Function | Default |
| --- | ---- | -------- | ------- |
| `-s` | `save_to` | Desired location of output file | `best.order` in current folder |
| `-e` | `settings_file` | Location of file containing advanced settings | `settings.txt` in current folder | 
| `-t` | `timeout` | Number of minutes to run the optimisation for | 10.0 |
| `-m` | `max_vendors` | Maximum number of different vendors to buy from | 10 |
| `-l` | `len_vendors` | Number of vendors from BrickLink to parse for each brick. Higher values allow for more options to test in the optimisation, but consequently slow the process down. | `100` |
| `-H` | `harsh` | **Only** use vendors within your preferred countries | False |
| `-q` | `quiet` | Suppress text output in command line | False |

These keywords are used in the same way as those for any other command line programmes. Some examples:

```
python main.py my_bsx_list.txt -s final_order_here.order -m 25
```

This will read BSX files as specified in `my_bsx_list.txt`, save the final result to a text file named `final_order_here.order`, and use at most 25 different vendors on BrickLink.

```
python main.py my_bsx_list.txt -t 60 -q
```

This will read BSX files as specified in `my_bsx_list.txt`, save the final result to the default location (`best.order`), optimise for 60 minutes, and not give any text output on the command line.

## Advanced settings

As mentioned earlier, the `-e` keyword can be used to specify advanced settings for PyBrick. These settings are specified in a plain text file, such as the default in `settings.txt`. An explanation of these settings is given in that file, as well as below. Generally one will want to change these settings once during setup, e.g. to specify their home country, and then not again.

| Setting | Explanation | Default |
| ------- | ----------- | --------|
| `shipto` | Code of the country you want your bricks shipped to; these can be determined using the BrickLink search function | `NL` (Netherlands) |
| `region` | Region from which you would like to purchase. Possibilities are `None`, `Asia`, `Africa`, `North America`, `South America`, `Middle East`, `Europe`, `Australia & Oceania`. `None` allows vendors from all regions of the world to be used. | `Europe` |
| `preferred_countries` | Countries within the given region that you prefer to source bricks from, e.g. for quick or cheap shipment. | `Netherlands, Germany` |
| `weight_close` | Weight to be given to each individual vendor. High values favour using fewer vendors, low values favour using more vendors. | `20` |
| `weight_far` | Additional weight given to countries that are *not* preferred. High values favour vendors in preferred countries. | `150` |
| `blacklist` | Names of vendors that one **never** wants to order from, e.g. due to doubtful reputation or temporary shop closures. |  (none) |

## Output

If the `quiet` (`-q`) parameter is not used, some performance statistics will be output to the command line. These can provide insight into the performance of the script and into possible problems that may occur.

The main output of PyBrick is a file, by default located at `best.order`, containing the optimal order. Note that PyBrick does **not** automatically order bricks; this process is still done manually. The output consists of a list of URLs, each linking to a specific lot of bricks, as well as the number of those bricks one wishes to purchase. Simply paste these URLs to your preferred browser and place the items in the shopping basket, and finish the orders as one normally would.

# Troubleshooting

If no result is achieved, one of several problems may be occurring. The most common ones are listed below. Please carefully look through these!

A good practice is to run *main.py* on the example files included in this repository as follows:

```
python main.py bsx_list.txt
```

If this works, then you can move on to using your own BSX files. If not, then something is wrong either with your Python installation (e.g. missing packages) or with the script itself (e.g. if BrickLink have made changes to their website).

If your problem is not solved using these example cases, feel free to contact me using the details on my profile page.

### I'm getting an ImportError message!

If you get a message in the command line saying `ImportError` or something similar, this indicates you are missing one of the required Python packages. Please install these (they are named in the error message), for example using [pip](https://pypi.python.org/pypi/pip).

### I'm not getting any orders!

If no possible orders are found, one or more of the following may be the case:

- Your desired bricks are unavailable. Some bricks just are not for sale, so consider buying these in a different condition (new/used), colour or even a completely different brick. Alternatly consider buying from a different region or from more countries (if using the `harsh` settings). You can manually check the availability of bricks on BrickLink. In almost all cases, PyBrick will warn you about bricks that are impossible or very difficult to get.

- The number of vendors being used is incorrect. Sometimes one is forced to use many different vendors at once, for example when ordering many different rare parts. Alternately one may want to set this number to a low value, for exmaple when only ordering a few different parts in very large quantities, to massively speed up the optimisation. Tweak the `-m` command line argument as explained above to see what works best for your case.

- The timeout is too short. Optimisation takes time, so do not expect a good result within half a second. For most orders, an optimisation time on the order of 10-20 minutes is ideal. Very long optimisation times (>24 hours) are often inconvenient since the information on BrickLink may change during the optimisation process. In any case, one should expect to see at least one possible order with a timeout as low as 1 minute. If this is not the case, consider changing the other parameters as mentioned above.

### My result is not optimal!

The optimisation used in PyBrick is not strictly optimisation - instead, random orders are generated, checked, and ranked by their cost and the number and locations of vendors to use. Due to the random nature of this process, occasionally a better solution than the one given may exist. However, this will only rarely make a noticeable difference.

### The output is telling me to order more bricks than I want!

Some vendors on BrickLink only sell items in multiples, e.g. in lots of 10 or 100. This means that it may sometimes be necessary to purchase 10 of an item one only needs 8 of. This is taken into account during the optimisation process and thus should not negatively affect the results.

### The output does not take shipping and handling costs into account!

Shipping and handling costs are very diverse across BrickLink, and there is no standard way to parse these for many vendors at once. The weights given to individual vendors are used in part to simulate shipping and handling costs (by minimising the number of vendors, one usually also minimises the shipping costs) so this can be seen as a proxy.
