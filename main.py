import src.pycount as pycount
import time

def main():
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