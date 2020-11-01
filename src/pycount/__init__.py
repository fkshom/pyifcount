import os
import yaml
import logging
import contextlib

logger = logging.getLogger(__name__)

class Count():
    def __init__(self, filename, initial=0):
        self.filename = filename
        self.sum = initial
        self.diff = None
        self.cur = self._get()

    def _get(self):
        with open(self.filename, 'r') as f:
            return int(f.read())

    def set(self, value):
        self.sum = value

    def refresh(self):
        new = self._get()
        self.diff = new - self.cur
        self.sum += self.diff
        self.cur = new


class AbstructDataStore():
    def __init__(self):
        self.event_listener = {}

    def __str__(self): return str(self.__dict__)
    def __repr__(self): return str(self.__dict__)

    def get(self, key, default=None):
        raise NotImplementedError()

    def set(self, key, value):
        raise NotImplementedError()

    def clear(self):
        raise NotImplementedError()

    def reload(self):
        raise NotImplementedError()
    
    def save(self):
        raise NotImplementedError()

    def add_event_listener(self, event_name, func):
        if not self.event_listener.get(event_name):
            self.event_listener[event_name] = []
        self.event_listener[event_name].append(func)

    def notify(self, event_name):
        for listener in self.event_listener.get(event_name, []):
            listener()


class MemoryDataStore(AbstructDataStore):
    def __init__(self):
        self.data = {}
        super().__init__()
    
    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value

    def clear(self):
        self.data = {}
        self.notify('store_reloaded')


class YamlDataStore(AbstructDataStore):
    def __init__(self, filename):
        self.data = {}
        self.filename = filename
        self.data = self._load_or_create_datafile()
        super().__init__()

    def _load_or_create_datafile(self):
        if not os.path.exists(self.filename):
            logger.debug("new file created")
            self._create_datafile()
        
        with open(self.filename, 'r') as f:
            tmp = yaml.safe_load(f) or {}
            logger.debug(f"file loaded: " + str(tmp))
            return tmp

    def _create_datafile(self):
        with open(self.filename, 'w') as f:
            yaml.dump({}, f)

    def _write_datafile(self):
        logger.debug("write_datafile: " + str(self.data))

        with open(self.filename, 'w') as f:
            yaml.dump(self.data, f)

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value

    def clear(self):
        self.data = {}
        self._write_datafile()
        self.notify('store_reloaded')

    def save(self):
        self._write_datafile()

    def reload(self):
        logger.debug("reload called")
        self.data = self._load_or_create_datafile()
        self.notify('store_reloaded')

    @contextlib.contextmanager
    def update(self):
        self.reload()
        yield self
        self.save()

class PyCount():
    def __init__(self, datastore):
        self.datastore = datastore
        self.datastore.add_event_listener('store_reloaded', self._store_reloaded_event)
        self.targets = {}

    def _store_reloaded_event(self):
        logger.debug("_store_reloaded_event called")
        for name in self.targets.keys():
            self.targets[name].set(self.datastore.get(name, 0))

    def regist(self, name, filename):
        initial_value = self.datastore.get(name, 0)
        self.targets[name] = Count(filename=filename, initial=initial_value)

    def refresh(self):
        with self.datastore.update() as ds:
            for name in self.targets.keys():
                self.targets[name].refresh()
                ds.set(name, self.targets[name].sum)

    def refresh1(self):
        self.datastore.reload()
        for name in self.targets.keys():
            self.targets[name].refresh()
            self.datastore.set(name, self.targets[name].sum)
        self.datastore.save()

    def __getitem__(self, key):
        return self.targets[key]



class PyIfCount():
    def __init__(self, interfaces, datastore):
        self.interfaces = interfaces
        self.datastore = datastore
        self.pycnt = PyCount(datastore=self.datastore)

        class Interface():
            def __str__(self): return str(self.__dict__)
            def __repr__(self): return str(self.__dict__)

        # interfacesを列挙して、必要なメトリクスをwatchする
        metrics = ['rx_bytes', 'tx_bytes']
        for interface in interfaces:
            self.__dict__[interface] = Interface()
            for metric in metrics:
                self.pycnt.regist(
                    name=f"{interface}.{metric}",
                    filename=f"/sys/class/net/{interface}/statistics/{metric}",
                )
                self.__dict__[interface].__dict__[metric] = self.pycnt[f'{interface}.{metric}']
        
    def refresh(self):
        self.pycnt.refresh()

