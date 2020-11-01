import pytest
from assertpy import assert_that, fail
import pycount
import os
import yaml
import logging

logger = logging.getLogger(__name__)

def remove_if_exists(filepath):
    try:
        os.remove(filepath)
    except:
        pass

class Test機能テスト():
    @pytest.fixture(scope='function', autouse=True)
    def scope_function(self, mocker):
        count_get = mocker.patch.object(pycount.Count, "_get", return_value=100)
        #datastore = pycount.MemoryDataStore()
        remove_if_exists("/tmp/pycount.yml")
        datastore = pycount.YamlDataStore(filename="/tmp/pycount.yml")
        self.pycnt = pycount.PyCount(
            datastore=datastore
        )
        yield (count_get, datastore)
        remove_if_exists("/tmp/pycount.yml")
    
    def test_インスタンスに監視対象をregistできる(self):
        self.pycnt.regist(
            name="ens33.rx_bytes",
            filename="path_to_ens33_rx_bytes"
        )
        assert_that(self.pycnt['ens33.rx_bytes'].cur).is_equal_to(100)
        assert_that(self.pycnt['ens33.rx_bytes'].sum).is_equal_to(0)

    def test_refreshしたら値が更新される(self, scope_function):
        (count_get, datastore) = scope_function
        self.pycnt.regist(
            name="ens33.rx_bytes",
            filename="path_to_ens33_rx_bytes"
        )
        assert_that(self.pycnt['ens33.rx_bytes'].cur).is_equal_to(100)
        assert_that(self.pycnt['ens33.rx_bytes'].sum).is_equal_to(0)
        count_get.return_value = 200
        self.pycnt.refresh()
        assert_that(self.pycnt['ens33.rx_bytes'].cur).is_equal_to(200)
        assert_that(self.pycnt['ens33.rx_bytes'].sum).is_equal_to(100)

    def test_datastoreリセットしたら追従する(self, scope_function):
        (count_get, datastore) = scope_function
        self.pycnt.regist(
            name="ens33.rx_bytes",
            filename="path_to_ens33_rx_bytes"
        )
        assert_that(self.pycnt['ens33.rx_bytes'].cur).is_equal_to(100)
        assert_that(self.pycnt['ens33.rx_bytes'].sum).is_equal_to(0)
        count_get.return_value = 200
        self.pycnt.refresh()
        assert_that(self.pycnt['ens33.rx_bytes'].cur).is_equal_to(200)
        assert_that(self.pycnt['ens33.rx_bytes'].sum).is_equal_to(100)
        datastore.clear()
        assert_that(self.pycnt['ens33.rx_bytes'].cur).is_equal_to(200)
        assert_that(self.pycnt['ens33.rx_bytes'].sum).is_equal_to(0)
        count_get.return_value = 200
        self.pycnt.refresh()

    def test_datastoreファイルを削除したらrefreshの時点で追従する(self, scope_function):
        (count_get, datastore) = scope_function
        self.pycnt.regist(
            name="ens33.rx_bytes",
            filename="path_to_ens33_rx_bytes"
        )
        assert_that(self.pycnt['ens33.rx_bytes'].cur).is_equal_to(100)
        assert_that(self.pycnt['ens33.rx_bytes'].sum).is_equal_to(0)
        count_get.return_value = 200
        self.pycnt.refresh()
        assert_that(self.pycnt['ens33.rx_bytes'].cur).is_equal_to(200)
        assert_that(self.pycnt['ens33.rx_bytes'].sum).is_equal_to(100)
        remove_if_exists("/tmp/pycount.yml")
        assert_that(self.pycnt['ens33.rx_bytes'].cur).is_equal_to(200)
        assert_that(self.pycnt['ens33.rx_bytes'].sum).is_equal_to(100)
        count_get.return_value = 250
        self.pycnt.refresh()
        assert_that(self.pycnt['ens33.rx_bytes'].cur).is_equal_to(250)
        assert_that(self.pycnt['ens33.rx_bytes'].sum).is_equal_to(50)


class Testデータファイルが存在しない場合():
    @pytest.fixture(scope='function', autouse=True)
    def scope_function(self, mocker):
        remove_if_exists("/tmp/pycount.yml")
        # rx_bytes等が存在しない可能性があるのでmock
        count_get = mocker.patch.object(pycount.Count, "_get", return_value=100)
        datastore = pycount.YamlDataStore(filename="/tmp/pycount.yml")
        self.pycnt = pycount.PyCount(
            datastore=datastore
        )
        yield (count_get, datastore)
        remove_if_exists("/tmp/pycount.yml")

    def test_インスタンス作成時にデータファイルが作成される(self):
        assert_that(os.path.exists("/tmp/pycount.yml")).is_true()

    def _test_データファイル作成直後は値が0である(self):
        self.pycnt.regist(
            name="ens33.rx_bytes",
            filename="path_to_ens33_rx_bytes"
        )
        assert_that(self.pycnt.ens33.rx_byte.sum).is_equal_to(0)


class Testデータファイルが存在する場合():
    @pytest.fixture(scope='function', autouse=True)
    def scope_function(self, mocker):
        remove_if_exists("/tmp/pycount.yml")
        # データファイル作成
        data = {'ens33.rx_bytes': 50, 'ens33.tx_bytes': 50}
        with open('/tmp/pycount.yml', 'w') as f:
            yaml.dump(data, f)
        
        # rx_bytes等が存在しない可能性があるのでmock
        count_get = mocker.patch.object(pycount.Count, "_get", return_value=100)
        datastore = pycount.YamlDataStore(filename="/tmp/pycount.yml")
        self.pycnt = pycount.PyCount(
            datastore=datastore
        )
        yield (count_get, datastore)
        remove_if_exists("/tmp/pycount.yml")
    
    def test_インスタンス作成時にデータファイルが読み込まれる(self):
        self.pycnt.regist(
            name="ens33.rx_bytes",
            filename="path_to_ens33_rx_bytes"
        )
        assert_that(self.pycnt['ens33.rx_bytes'].cur).is_equal_to(100)
        assert_that(self.pycnt['ens33.rx_bytes'].sum).is_equal_to(50)

    def test_registしていないメトリクスはデータファイルにあっても読み込めない(self):
        self.pycnt.regist(
            name="ens33.rx_bytes",
            filename="path_to_ens33_rx_bytes"
        )
        try:
            self.pycnt['ens33.tx_bytes']
            fail('should have raised error')
        except KeyError as e:
            assert_that(str(e)).is_equal_to("'ens33.tx_bytes'")

    def test_refreshしたらメモリ情報もデータファイルも更新される(self, scope_function):
        (count_get, datastore) = scope_function
        self.pycnt.regist(
            name="ens33.rx_bytes",
            filename="path_to_ens33_rx_bytes"
        )
        assert_that(self.pycnt['ens33.rx_bytes'].cur).is_equal_to(100)
        assert_that(self.pycnt['ens33.rx_bytes'].sum).is_equal_to(50)
        count_get.return_value = 200
        self.pycnt.refresh()
        assert_that(self.pycnt['ens33.rx_bytes'].cur).is_equal_to(200)
        assert_that(self.pycnt['ens33.rx_bytes'].sum).is_equal_to(150)
        
