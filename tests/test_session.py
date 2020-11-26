import stare
import pytest
import requests


def test_urljoin(auth_session):
    assert (
        auth_session._normalize_url('/resource/')
        == 'https://atlas-glance.cern.ch/resource/'
    )
    assert (
        auth_session._normalize_url('resource/')
        == 'https://atlas-glance.cern.ch/atlas/analysis/api/resource/'
    )
    assert (
        auth_session._normalize_url('/resource')
        == 'https://atlas-glance.cern.ch/resource'
    )
    assert (
        auth_session._normalize_url('resource')
        == 'https://atlas-glance.cern.ch/atlas/analysis/api/resource'
    )
    assert (
        auth_session._normalize_url(
            'https://atlas-glance.cern.ch/atlas/analysis/api/resource'
        )
        == 'https://atlas-glance.cern.ch/atlas/analysis/api/resource'
    )
    assert (
        auth_session._normalize_url('https://google.com/resource')
        == 'https://google.com/resource'
    )


def test_expires_after(auth_user):
    assert stare.core.Session(expires_after=dict(days=1))


@pytest.fixture
def session(mocker):
    mocker.patch('stare.core.User.authenticate', return_value=True)
    mocker.patch('stare.core.Session._check_response', return_value=True)
    # patch objects
    s = stare.core.Session()
    mocker.patch.object(
        requests.Session, 'request', wraps=super(stare.core.Session, s).request
    )
    mocker.patch.object(stare.core.Session, 'request', wraps=s.request)

    mocked_response = mocker.MagicMock()
    mocked_response.status_code = 200
    mocked_response.headers = {'content-length': 0}
    mocker.patch('requests.Session.send', return_value=mocked_response)
    mocker.patch.object(stare.core.Session, 'send', wraps=s.send)

    mocker.patch.object(
        requests.Session,
        'prepare_request',
        wraps=super(stare.core.Session, s).prepare_request,
    )
    mocker.patch.object(stare.core.Session, 'prepare_request', wraps=s.prepare_request)

    mocker.patch.object(stare.core.Session, '_normalize_url', wraps=s._normalize_url)
    return s


def test_session_normalize_url():
    session = stare.core.Session()
    url = 'publications'
    new_url = session._normalize_url(url)
    assert url != new_url
    assert new_url.startswith(stare.settings.STARE_SITE_URL)


# NB: Session.request is delegated through to Session.send
def test_session_request(session):
    session.get('publications')
    assert session._normalize_url.called
    assert session.request.called
    assert super(stare.core.Session, session).request.called
    assert session.send.called
    assert super(stare.core.Session, session).send.called
    assert session._check_response.call_count == 1


def test_session_request_call(session):
    session('GET', 'publications')
    assert session._normalize_url.called
    assert session.request.called
    assert super(stare.core.Session, session).request.called
    assert session.send.called
    assert super(stare.core.Session, session).send.called
    assert session._check_response.call_count == 1


def test_session_prepare_request(session):
    req = requests.Request('GET', 'publications')
    prep = session.prepare_request(req)
    assert session._normalize_url.called
    assert 'Authorization' in prep.headers
    assert super(stare.core.Session, session).prepare_request.called
    assert session._check_response.call_count == 0


def test_session_send(session):
    req = requests.Request('GET', 'publications')
    prep = session.prepare_request(req)
    session.send(prep)
    assert super(stare.core.Session, session).send.called
    assert session._check_response.call_count == 1


def test_session_send_call(session):
    req = requests.Request('GET', 'publications')
    session(req)
    assert super(stare.core.Session, session).send.called
    assert session._check_response.call_count == 1
