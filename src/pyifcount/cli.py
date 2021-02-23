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
    parser.add_argument('--write-interval', type=int, default=0)
    parser.add_argument('--http', nargs='?', type=int, const=6000)
    parser.add_argument('--read-interval', type=int, default=1)
    args = parser.parse_args(args)

    if args.datastore == 'yaml':
        datastore = pyifcount.YamlDataStore(filename=args.filename, write_interval=args.write_interval)
    elif args.datastore == 'memory':
        datastore = pyifcount.MemoryDataStore()
    else:
        print(f"datastore must be yaml or memory. {args.datastore}", file=sys.stderr)
        exit(1)

    pyifcnt = pyifcount.PyIfCount(
        datastore=datastore,
        autorefresh=False,
        write_interval=args.write_interval,
    )

    for ifdir in list(glob.glob("/sys/class/net/*")):
        if os.path.isfile(f"{ifdir}/statistics/rx_bytes"):
            ifname = os.path.basename(ifdir)
            pyifcnt.add_interface(interface=ifname, metrics=['tx_bytes', 'rx_bytes'])

    # TODO: pyifcountがスレッドセーフではない（refreshの書き込み排他制御をしていない）ので
    # httpかstdoutのどちらかしか起動できない
    if args.http:
        logger.info(f'http server start in port {args.http}')
        print(f'http server start in port {args.http}', file=sys.stderr)
        logger.info('stdout is supressed.')
        print(f'stdout is supressed.', file=sys.stderr)

        from prometheus_client import start_http_server, Counter
        from prometheus_client.core import REGISTRY, CounterMetricFamily
        class CustomCollector(object):
            def __init__(self, pyifcount, manual_refresh=False):
                self._pyifcount = pyifcount
                self._manual_refresh = manual_refresh

            def collect(self):
                if self._manual_refresh:
                    pyifcnt.refresh()

                rx_bytes_sum = CounterMetricFamily('rx_bytes', 'Help text', labels=['interface']) # metric name: rx_bytes_total
                tx_bytes_sum = CounterMetricFamily('tx_bytes', 'Help text', labels=['interface']) # metric name: tx_bytes_total
                for interfacename in self._pyifcount.interfaces:
                    rx_bytes_sum.add_metric([interfacename], pyifcnt[interfacename].rx_bytes.sum)
                    tx_bytes_sum.add_metric([interfacename], pyifcnt[interfacename].tx_bytes.sum)
                yield rx_bytes_sum
                yield tx_bytes_sum

        if args.read_interval and args.read_interval > 0:
            manual_refresh = False
        else:
            manual_refresh = True

        REGISTRY.register(CustomCollector(pyifcount=pyifcnt, manual_refresh=manual_refresh))
        start_http_server(args.http)

        while True:
            if args.read_interval and args.read_interval > 0:
                pyifcnt.refresh()
                time.sleep(args.read_interval)
            else:
                time.sleep(60)
    else:
        while True:
            pyifcnt.refresh()
            print("-" * 80)
            for ifname in pyifcnt.interfaces:
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