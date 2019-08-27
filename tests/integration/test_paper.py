import stare
import betamax


def test_get(auth_session):
    with betamax.Betamax(auth_session).use_cassette('test_paper.test_get'):
        response = auth_session.get('papers')
        assert auth_session._response.status_code == 200
        assert response
        assert 'papers' in response
        assert stare.models.paper.make_paper_list(response['papers'])
