import stare
import logging
import betamax

# because expiration will fail (since we cache this information) skip the verification of expiration
jwtOptions = {'verify_signature': False, 'verify_iat': False, 'verify_exp': False}


def test_user_create():
    user = stare.core.User(username='foo', password='bar')
    assert user.subject_token is None
    assert user.access_token is None
    assert user.bearer == ''
    assert user.id_token == {}
    assert user.name == ''
    assert user.expires_at == 0
    assert user.expires_in == 0
    assert user.is_expired()


def test_user_bad_login(caplog):
    user = stare.core.User(username='foo', password='bar', jwtOptions=jwtOptions)
    with betamax.Betamax(user._session).use_cassette('test_user.test_user_bad_login'):
        with caplog.at_level(logging.INFO, 'stare'):
            user.authenticate()
            assert 'Invalid user credentials' in caplog.text
        assert user.is_authenticated() == False
        assert user._response


# NB: because we are using betamax - the ID token which is invalid after 2
# hours is kept so user.is_expired() will be true for testing, do not assert it
def test_user_good_login(caplog):
    user = stare.core.User(jwtOptions=jwtOptions)
    with betamax.Betamax(user._session).use_cassette('test_user.test_user_good_login'):
        with caplog.at_level(logging.INFO, 'stare'):
            user.authenticate()
            assert caplog.text == ''
        assert user.is_authenticated()
        assert user._response
