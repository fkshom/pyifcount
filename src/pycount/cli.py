from . import pycount
import time
from pprint import pprint as pp

def main():
    pyifcnt = pycount.PyIfCount(
        #datastore=pycount.MemoryDataStore(),
        datastore=pycount.YamlDataStore(filename='unko.yml'),
        autorefresh=True
    )
    pyifcnt.add_interface(interface='ens33', metrics=['tx_bytes', 'rx_bytes'])


    while True:
        print(
            f"rx:{pyifcnt.ens33.rx_bytes.sum}({pyifcnt.ens33.rx_bytes.cur})"
            f"  "
            f"tx:{pyifcnt.ens33.tx_bytes.sum}({pyifcnt.ens33.tx_bytes.cur})"
        )
        print(pyifcnt.interfaces)
        print(pyifcnt['ens33'])
        print(pyifcnt['ens33'].metrics)
        #pyifcnt.refresh()
        time.sleep(1)
        

def main1():
    pyifcnt = pycount.PyIfCount(
        interfaces=['eth0'],
        datastore=pycount.MemoryDataStore()
    )

    while True:
        print(
            f"rx:{pyifcnt.eth0.rx_bytes.sum}({pyifcnt.eth0.rx_bytes.cur})"
            f"  "
            f"tx:{pyifcnt.eth0.tx_bytes.sum}({pyifcnt.eth0.tx_bytes.cur})"
        )
        pyifcnt.refresh()
        time.sleep(1)

if __name__ == "__main__":
    main()