import pyifcount
import time
from pprint import pprint as pp
import argparse
import sys
import logging
import glob
import os

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.WARN)

def main(args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--datastore', choices=['yaml', 'memory'], default='yaml')
    parser.add_argument('-f', '--filename', default='data.yaml')
    args = parser.parse_args(args)

    if args.datastore == 'yaml':
        datastore = pyifcount.YamlDataStore(filename=args.filename)
    elif args.datastore == 'memory':
        datastore = pyifcount.MemoryDataStore()
    else:
        print(f"datastore must be yaml or memory. {args.datastore}", file=sys.stderr)
        exit(1)

    pyifcnt = pyifcount.PyIfCount(
        datastore=datastore,
        autorefresh=False,
    )

    interfacenames = []
    for ifdir in list(glob.glob("/sys/class/net/*")):
        print(ifdir)
        if os.path.isfile(f"{ifdir}/statistics/rx_bytes"):
            interfacenames.append(os.path.basename(ifdir))

    print(interfacenames)

    for ifname in interfacenames:
        pyifcnt.add_interface(interface=ifname, metrics=['tx_bytes', 'rx_bytes'])

    while True:
        pyifcnt.refresh()
        print("-" * 80)
        for ifname in interfacenames:
            print(
                f"{ifname:<15}"
                f"  "
                f"rx:{pyifcnt[ifname].rx_bytes.sum:>8}({pyifcnt[ifname].rx_bytes.cur:>10})"
                f"  "
                f"tx:{pyifcnt[ifname].tx_bytes.sum:>8}({pyifcnt[ifname].tx_bytes.cur:>10})"
            )
        time.sleep(1)

if __name__ == "__main__":
    main()