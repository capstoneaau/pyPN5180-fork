import sys
from PN5180.ISO14443 import ISO14443
from PN5180 import definitions
import time


if __name__ == '__main__':
    check_debug = sys.argv[1] if len(sys.argv) == 2 else ''
    debug = True if check_debug == '-v' else False

    reader = ISO14443(debug=True)
    reader.activate_type_A(kind=definitions.ISO14443InitCommand.WupA)
    '''
    while True:
        cards = reader.inventory()
        print(f"{len(cards)} card(s) detected: {' - '.join(cards)}")
        time.sleep(1)
'''