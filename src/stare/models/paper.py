import attr


def make_supporting_note(data):
    return SupportingNote(id=data['id'], label=data['label'], url=data['url'])


def make_supporting_note_list(data):
    return list(map(make_supporting_note, data))


def make_paper(data):
    return Paper(
        id=data['id'],
        short_title=data['short_title'],
        full_title=data['full_title'],
        pub_short_title=data['pub_short_title'],
        creation_date=data['creation_date'],
        status=data['status'],
        deletion_request=data['deletion_request'],
        deletion_reason=data['deletion_reason'],
        deletion=data['deletion'],
        supporting_notes=make_supporting_note_list(data['supporting_notes'])
        if 'supporting_notes' in data
        else [],
    )


def make_paper_list(data):
    return PaperList(papers=list(map(make_paper, data)))


@attr.s
class SupportingNote(object):
    id = attr.ib()
    label = attr.ib()
    url = attr.ib()


@attr.s
class Paper(object):
    id = attr.ib()
    short_title = attr.ib()
    full_title = attr.ib()
    pub_short_title = attr.ib()
    creation_date = attr.ib()
    status = attr.ib()
    deletion_request = attr.ib()
    deletion_reason = attr.ib()
    deletion = attr.ib()
    supporting_notes = attr.ib()


@attr.s
class PaperList(object):
    papers = attr.ib(type=list)
