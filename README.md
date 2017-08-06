The code expects BSX files as given by BrickStock. Files from similar programmes may work (since there is a lot of standardisation in the community) but this is not guaranteed.

It should be possible to create orders by only editing settings.txt and bsx_list.txt without touching the Python code.

You can order the same BSX file multiple times by putting the number of times behind the name, as in the example:

examplebsx1            [ordered once]

examplebsx2 5          [ordered five times]

If the files have no extension then ".bsx" is assumed.

If there is a brick you cannot order enough of with your settings then it is ignored and you will get an order file without this. 
You will be notified in this case. Usually changing from new to used or changing the colour of the brick fixes this.

The actual ordering of the items is still done manually -- since Bricklink stores are all a bit different, this would be very hard to automate. 
However, it is much less work than it seems. You just copy a link, go to the website, enter the number and click "add to cart". It's a few seconds per brick.
