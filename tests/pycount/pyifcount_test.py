import pytest
from assertpy import assert_that, fail
import pycount
import os
import yaml
import logging

logger = logging.getLogger(__name__)

class Test結合テスト():
    def scope_function_(self, mocker):
        count_get = mocker.patch.object(pycount.Count, "_get_from_file", return_value=100)
        datastore = pycount.YamlDataStore(filename="/tmp/pycount.yml")
        self.pycnt = pycount.PyCount(
            datastore=datastore
        )
        yield (count_get, datastore)

    @pytest.fixture(scope='function', autouse=True)
    def scope_function(self, mocker):
        self.mock_tx_bytes = 200
        self.mock_rx_bytes = 100
        def _get_from_file_mock(filename):
            filemap = {
                '/sys/class/net/some_interface/statistics/tx_bytes': lambda: self.mock_tx_bytes,
                '/sys/class/net/some_interface/statistics/rx_bytes': lambda: self.mock_rx_bytes,
            }
            try:
                return filemap[filename]()
            except KeyError as e:
                raise FileNotFoundError()
        
        pycount.Count._get_from_file = mocker.MagicMock(side_effect=_get_from_file_mock)
        yield


    def test_インタフェースを登録することができる(self):
        pyifcnt = pycount.PyIfCount(
            datastore=pycount.MemoryDataStore(),
            autorefresh=True,
        )
        pyifcnt.add_interface(interface='some_interface', metrics=['tx_bytes', 'rx_bytes'])

    def test_値を取得することができる(self):
        pyifcnt = pycount.PyIfCount(
            datastore=pycount.MemoryDataStore(),
            autorefresh=True,
        )
        pyifcnt.add_interface(interface='some_interface', metrics=['tx_bytes', 'rx_bytes'])
        assert_that(pyifcnt.some_interface.tx_bytes.sum).is_equal_to(0)
        assert_that(pyifcnt.some_interface.tx_bytes.cur).is_equal_to(200)
        assert_that(pyifcnt.some_interface.rx_bytes.sum).is_equal_to(0)
        assert_that(pyifcnt.some_interface.rx_bytes.cur).is_equal_to(100)
        self.mock_tx_bytes += 100
        self.mock_rx_bytes += 50
        assert_that(pyifcnt.some_interface.tx_bytes.sum).is_equal_to(100)
        assert_that(pyifcnt.some_interface.tx_bytes.cur).is_equal_to(300)
        assert_that(pyifcnt.some_interface.rx_bytes.sum).is_equal_to(50)
        assert_that(pyifcnt.some_interface.rx_bytes.cur).is_equal_to(150)
