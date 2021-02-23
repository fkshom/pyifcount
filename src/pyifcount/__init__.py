__version__ = '0.0.3'

import os
import yaml
import logging
import contextlib
import datetime

logger = logging.getLogger(__name__)

class Count():
    def __init__(self, filename, initial=0) -> None:
        self._filename = filename
        self._sum = initial
        self._cur = None

    def _get_from_file(self, filename) -> int:
        with open(filename, 'r') as f:
            return int(f.read())

    def set_sum(self, value) -> None:
        self._sum = value

    def refresh(self) -> None:
        new = self._get_from_file(self._filename)
        self._sum += new - (self._cur or new)
        self._cur = new

    @property
    def sum(self) -> int:
        return self._sum
    
    @property
    def cur(self) -> int:
        return self._cur

class AbstructDataStore():
    def __init__(self):
        self.event_listener = {}

    def __str__(self): return str(self.__dict__)
    def __repr__(self): return str(self.__dict__)

    # リスナーにイベントを通知する
    def _notify(self, event_name):
        for listener in self.event_listener.get(event_name, []):
            listener()

    # keyの値を返す
    def get(self, key, default=None):
        raise NotImplementedError()

    # keyの値を設定する
    def set(self, key, value):
        raise NotImplementedError()

    # ストアをクリアする
    def clear(self):
        raise NotImplementedError()

    # ストアファイルから値を読み込む
    def reload(self):
        raise NotImplementedError()
    
    # ストアファイルに値を保存する
    def save(self):
        raise NotImplementedError()

    # イベントリスナの登録
    def add_event_listener(self, event_name, func):
        self.event_listener.setdefault(event_name, [])
        self.event_listener[event_name].append(func)

    # ストアファイルに値を保存する。ストアファイルの情報が更新されている可能性があるので、事前に再読み込みする
    # yieldで、値の更新（self.set）が行われる想定
    @contextlib.contextmanager
    def update(self):
        self.reload()
        yield self
        self.save()

class MemoryDataStore(AbstructDataStore):
    def __init__(self):
        self._data = {}
        super().__init__()
    
    def get(self, key, default=None):
        return self._data.get(key, default)

    def set(self, key, value):
        self._data[key] = value

    def clear(self):
        self._data = {}
        self._notify('store_reloaded')

    def save(self):
        return None

    def reload(self):
        self._notify('store_reloaded')

class YamlDataStore(AbstructDataStore):
    def __init__(self, filename, write_interval=0):
        self._data = {}
        self._filename = filename
        self._write_interval = write_interval or 0
        self._seved_datetime = datetime.datetime.now()
        self._data = self._load_or_create_datafile()
        super().__init__()

    def _load_or_create_datafile(self):
        if not os.path.exists(self._filename):
            logger.debug("new file created")
            self._create_datafile()
        
        with open(self._filename, 'r') as f:
            tmp = yaml.safe_load(f) or {}
            logger.debug(f"file loaded: " + str(tmp))
            return tmp

    def _create_datafile(self):
        with open(self._filename, 'w') as f:
            yaml.dump({}, f)

    def _write_datafile(self):
        logger.debug("write_datafile: " + str(self._data))
        with open(self._filename, 'w') as f:
            yaml.dump(self._data, f)

    def get(self, key, default=None):
        return self._data.get(key, default)

    def set(self, key, value):
        self._data[key] = value

    def clear(self):
        self._data = {}
        self._write_datafile()
        self._notify('store_reloaded')

    def save(self):
        now = datetime.datetime.now()
        if now.timestamp() - self._seved_datetime.timestamp() > self._write_interval:
            logger.debug(f'save data in {now.strftime("%Y/%m/%d %H:%M:%S.%f")}')
            self._write_datafile()
            self._seved_datetime = now

    # TODO: saveせずにreloadした場合は、save直前の状態に戻ってしまう
    def reload(self):
        logger.debug("reload called")
        self._data = self._load_or_create_datafile()
        self._notify('store_reloaded')


class PyCount():
    def __init__(self, datastore, autorefresh=True):
        self.datastore = datastore
        self.autorefresh = autorefresh
        self.datastore.add_event_listener('store_reloaded', self._store_reloaded_event)
        self.targets = {}

    def _store_reloaded_event(self):
        logger.debug("_store_reloaded_event called")
        for name in self.targets.keys():
            self.targets[name].set_sum(self.datastore.get(name, 0))

    def regist(self, name, filename):
        initial_value = self.datastore.get(name, 0)
        self.targets[name] = Count(filename=filename, initial=initial_value)

    def refresh(self, names=None):
        names = names or self.targets.keys()
        with self.datastore.update() as ds:
            for name in names:
                self.targets[name].refresh()
                ds.set(name, self.targets[name].sum)

    def __getitem__(self, key):
        logger.debug('PyCount.getitem called')
        if self.autorefresh:
            self.refresh(names=[key])
        return self.targets[key]

class Interface():
    def __init__(self) -> None:
        self._metrics = {}

    def __getattr__(self, key):
        return self._metrics[key]

    def __getitem__(self, key):
        return self._metrics[key]

    @property
    def metrics(self):
        return list(self._metrics.keys())

        
class Interface2():
    def __init__(self, interfacename, pycnt) -> None:
        self._metrics = {}
        self._interfacename = interfacename
        self._pycnt = pycnt

    def __getattr__(self, key):
        return self._pycnt[f'{self._interfacename}.{key}']

    def __getitem__(self, key):
        return self._pycnt[f'{self._interfacename}.{key}']

    @property
    def metrics(self):
        return list(self._metrics.keys())

class PyIfCount():
    def __init__(self, datastore, interfaces=[], autorefresh=False, write_interval=1):
        self._pycnt = PyCount(datastore=datastore, autorefresh=autorefresh,)
        self._interfaces = {}

        for interface in interfaces:
            self.add_interface(interface)

    def add_interface(self, interface, metrics=['rx_bytes', 'tx_bytes']):
        self._interfaces[interface] = type('Interface', (), {})()
        self._interfaces[interface] = Interface2(interface, self._pycnt)
        for metric in metrics:
            self._pycnt.regist(
                name=f"{interface}.{metric}",
                filename=f"/sys/class/net/{interface}/statistics/{metric}",
            )
            self._interfaces[interface]._metrics[metric] = self._pycnt[f'{interface}.{metric}']

    def __getattr__(self, key):
        return self._interfaces[key]

    def __getitem__(self, key):
        return self._interfaces[key]

    @property
    def autorefresh(self):
        return self._pycnt.autorefresh

    @autorefresh.setter
    def autorefresh(self, value):
        self._pycnt.autorefresh = value

    @property
    def interfaces(self):
        return list(self._interfaces.keys())

    def refresh(self):
        self._pycnt.refresh()

