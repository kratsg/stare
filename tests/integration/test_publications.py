import betamax


def test_get(auth_session):
    with betamax.Betamax(auth_session).use_cassette('test_publications.test_get'):
        response = auth_session.get('publications/HDBS-2018-33')
        assert auth_session._response.status_code == 200
        assert response
        assert 'publications' in response.json()
        assert len(response.json()['publications']) == 1


def test_search(auth_session):
    with betamax.Betamax(auth_session).use_cassette('test_publications.test_search'):
        response = auth_session.get(
            'publications/search', params={'activityId': 26, 'referenceCode': 'HIGG'}
        )
        assert auth_session._response.status_code == 200
        assert response
        assert 'publications' in response.json()
        # assert stare.models.publication.make_publication_list(response['publications'])
