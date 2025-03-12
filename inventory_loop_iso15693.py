from PN5180.ISO15693 import ISO15693
import sys
import time


if __name__ == '__main__':
    check_debug = sys.argv[1] if len(sys.argv) == 2 else ''
    debug = True if check_debug == '-v' else False

    reader = ISO15693(debug=debug)
    while True:
        cards = reader.inventory()
        print(f"{len(cards)} card(s) detected: {' - '.join(cards)}")
        time.sleep(.4)
