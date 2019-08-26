import stare
import betamax


def test_get(auth_session):
    with betamax.Betamax(auth_session).use_cassette('test_paper.test_get'):
        response = auth_session.get('papers')
        assert auth_session._response.status_code == 200
        assert response
        assert 'analyses' in response
        assert stare.models.institution.make_paper_list(response['papers'])
