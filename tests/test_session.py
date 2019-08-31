import stare
import pytest
import requests


@pytest.fixture
def session(mocker):
    mocker.patch('stare.core.User.authenticate', return_value=True)
    mocker.patch('stare.core.Session._handle_response', return_value=True)
    # patch objects
    s = stare.core.Session()
    mocker.patch.object(
        requests.Session, 'request', wraps=super(stare.core.Session, s).request
    )
    mocker.patch.object(stare.core.Session, 'request', wraps=s.request)

    mocker.patch('requests.Session.send', return_value=None)
    mocker.patch.object(stare.core.Session, 'send', wraps=s.send)

    mocker.patch.object(
        requests.Session,
        'prepare_request',
        wraps=super(stare.core.Session, s).prepare_request,
    )
    mocker.patch.object(stare.core.Session, 'prepare_request', wraps=s.prepare_request)

    mocker.patch.object(stare.core.Session, '_normalize_url', wraps=s._normalize_url)
    return s


# FIXME
def test_session_handle_response():
    session = stare.core.Session()
    pass


def test_session_normalize_url():
    session = stare.core.Session()
    url = 'analyses'
    new_url = session._normalize_url(url)
    assert url != new_url
    assert new_url.startswith(stare.settings.SITE_URL)


# NB: Session.request is delegated through to Session.send
def test_session_request(session):
    session.get('analyses')
    assert session._normalize_url.called
    assert session.request.called
    assert super(stare.core.Session, session).request.called
    assert session.send.called
    assert super(stare.core.Session, session).send.called
    assert session._handle_response.call_count == 1


def test_session_request_call(session):
    session('GET', 'analyses')
    assert session._normalize_url.called
    assert session.request.called
    assert super(stare.core.Session, session).request.called
    assert session.send.called
    assert super(stare.core.Session, session).send.called
    assert session._handle_response.call_count == 1


def test_session_prepare_request(session):
    req = requests.Request('GET', 'analyses')
    prep = session.prepare_request(req)
    assert session._normalize_url.called
    assert 'Authorization' in prep.headers
    assert super(stare.core.Session, session).prepare_request.called
    assert session._handle_response.call_count == 0


def test_session_send(session):
    req = requests.Request('GET', 'analyses')
    prep = session.prepare_request(req)
    session.send(prep)
    assert super(stare.core.Session, session).send.called
    assert session._handle_response.call_count == 1


def test_session_send_call(session):
    req = requests.Request('GET', 'analyses')
    session(req)
    assert super(stare.core.Session, session).send.called
    assert session._handle_response.call_count == 1
