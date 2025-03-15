import sys
from PN5180.iClass import iClass
from PN5180 import definitions
import time


if __name__ == '__main__':
    check_debug = sys.argv[1] if len(sys.argv) == 2 else ''
    debug = True if check_debug == '-v' else False

    reader = iClass(debug=debug)
    reader.activate_all()
    '''
    while True:
        cards = reader.inventory()
        print(f"{len(cards)} card(s) detected: {' - '.join(cards)}")
        time.sleep(1)
'''