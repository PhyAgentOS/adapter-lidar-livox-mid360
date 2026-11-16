import json
import pytest
from forge_devices_livox_mid360 import managed


def test_external_mode_never_starts_driver():
    cfg={'clock_confirmed':True}
    with managed.capture(cfg) as value:
        assert value is cfg


def test_managed_clock_failure_cleans_owned_driver(tmp_path, monkeypatch):
    network=tmp_path/'network.json'
    network.write_text(json.dumps({'MID360':{'host_net_info':{}},'lidar_configs':[{}]}))
    states=[]
    class Process:
        def start(self,*args,**kwargs): states.append('started')
        def stop(self): states.append('stopped')
    def fail(*args): raise ValueError('unverified clock')
    monkeypatch.setattr(managed,'OwnedProcess',Process)
    monkeypatch.setattr(managed,'scout',fail)
    cfg={'ros_domain_id':12,'cloud_topic':'/custom/cloud','imu_topic':'/custom/imu',
         'imu_acceleration_unit':'g','managed_driver':{'session_dir':str(tmp_path/'session'),
         'network_config':str(network),'executable':'/external/driver',
         'host_ip':'192.0.2.1','lidar_ip':'192.0.2.2','time_mapping_id':'test'}}
    with pytest.raises(ValueError,match='unverified clock'):
        with managed.capture(cfg): pass
    assert states==['started','stopped']
    assert json.loads(network.read_text())['MID360']['host_net_info']=={}
