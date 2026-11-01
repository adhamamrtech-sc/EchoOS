from actions.system_network import (get_time, get_system_info,volume_up,set_volume,lock_screen,get_network_status,show_processes,screenshot,set_brightness)
def test_get_time():
    res =get_time({})
    assert res["status"]=="ok"
def test_get_system_info():
    res =get_system_info({})
    assert res["status"]=="ok"
def test_volume_up():
    res = volume_up({})
    assert res["status"]=="ok"
def test_set_volume():
    res= set_volume({"params":{"value":30}})
    assert res["status"]=="ok"
def test_lock_screen():
    res =lock_screen({})
    assert res["status"]=="ok"
def test_get_network_status():
    res=lock_screen({})
    assert res["status"]=="ok"
def test_show_processes():
    res =show_processes({})
    assert res["status"]=="ok"
def test_screenshot():
    res =screenshot({})
    assert "status" in res
def test_set_brightness():
    res= set_brightness({"params":{"value":50}})
    assert "status" in res

