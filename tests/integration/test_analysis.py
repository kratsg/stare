import stare
import betamax


def test_get(auth_session):
    with betamax.Betamax(auth_session).use_cassette('test_analysis.test_get'):
        response = auth_session.get('analyses')
        assert auth_session._response.status_code == 200
        assert response
        assert 'analyses' in response
        assert stare.models.analysis.make_analysis_list(response['analyses'])
