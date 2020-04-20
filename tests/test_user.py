import stare
import time
import pickle
import logging
import pytest

# set some things on user that we expect to persist or not persist
_name = 'Test User'
_response = 'A response'
_status_code = 200
_access_token = '4cce$$T0k3n'
_subject_token = 'subj3cTt0k3n'
_raw_id_token = 'R4w1DT0k3n'


@pytest.fixture
def user_temp(tmpdir):
    temp = tmpdir.join("auth.pkl")
    assert temp.isfile() == False

    u = stare.core.User(save_auth=temp.strpath)
    u._id_token = {'exp': time.time() + 3600, 'name': _name}
    u._response = _response
    u._status_code = _status_code
    u._subject_token = _subject_token
    u._access_token = _access_token
    u._raw_id_token = _raw_id_token
    return u, temp


def test_user_expires(user_temp):
    user, _ = user_temp
    assert user.is_authenticated()
    assert user.is_expired() == False
    assert user.expires_in > 0
    user._id_token['exp'] = time.time() - 1
    assert user.is_authenticated()
    assert user.is_expired()
    assert user.expires_in == 0


def test_user_serialization(user_temp, caplog):
    user, temp = user_temp
    # set up first user and check that we can dump
    session = stare.core.Session(user=user)
    assert temp.isfile() == False
    assert session.user._dump()
    assert temp.isfile()
    assert temp.size()
    assert pickle.load(open(user._save_auth, 'rb'))

    # check if we can reload user
    session.user._id_token = None
    assert session.user._load()
    assert session.user.name == _name
    del session

    # check if session can load user
    session = stare.core.Session(user=user, save_auth=temp.strpath)
    assert session.user.name == _name
    assert session.user._session
    assert session.user._response == _response
    assert session.user._status_code == _status_code
    assert session.user._subject_token == _subject_token
    assert session.user._access_token == _access_token
    assert session.user._raw_id_token == _raw_id_token

    # check what happens if the saved user has expired
    session.user._id_token['exp'] = time.time() + 4
    session.user._dump()
    time.sleep(5)
    with caplog.at_level(logging.INFO, 'stare'):
        assert session.user._load() == False
        assert 'Expired saved user session in' in caplog.text
    del session

    # check what happens if corruption
    temp.write('fake')
    with caplog.at_level(logging.INFO, 'stare'):
        user = stare.core.User(save_auth=temp.strpath)
        assert 'Unable to load user session' in caplog.text
        caplog.clear()
        assert user._load() == False
        assert 'Unable to load user session' in caplog.text
        caplog.clear()
        stare.core.Session(save_auth=temp.strpath)
        assert 'Unable to load user session' in caplog.text
