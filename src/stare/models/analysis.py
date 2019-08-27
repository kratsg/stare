import attr


def make_phase0(data):
    return Phase0(
        id=data['id'],
        start_date=data['start_date'],
        state=data['state'],
        main_physics_aim=data['main_physics_aim'],
        dataset_used=data['dataset_used'],
        model_tested=data['model_tested'],
        methods=data['methods'],
        editorial_board_formed_date=data['editorial_board_formed_date'],
        group_pre_sign_off_date=data['group_pre_sign_off_date'],
        ana_coord_target_date_comment=data['ana_coord_target_date_comment'],
    )


def make_analysis(data):
    return Analysis(
        id=data['id'],
        short_title=data['short_title'],
        full_title=data['full_title'],
        pub_short_title=data['pub_short_title'],
        creation_date=data['creation_date'],
        status=data['status'],
        deletion_request=data['deletion_request'],
        deletion_reason=data['deletion_reason'],
        deletion=data['deletion'],
        phase_0=make_phase0(data['phase_0']) if 'phase_0' in data else None,
    )


def make_analysis_list(data):
    return AnalysisList(analyses=list(map(make_analysis, data)))


@attr.s
class Phase0(object):
    id = attr.ib()
    start_date = attr.ib()
    state = attr.ib()
    main_physics_aim = attr.ib()
    dataset_used = attr.ib()
    model_tested = attr.ib()
    methods = attr.ib()
    editorial_board_formed_date = attr.ib()
    group_pre_sign_off_date = attr.ib()
    ana_coord_target_date_comment = attr.ib()


@attr.s
class Analysis(object):
    id = attr.ib()
    short_title = attr.ib()
    full_title = attr.ib()
    pub_short_title = attr.ib()
    creation_date = attr.ib()
    status = attr.ib()
    deletion_request = attr.ib()
    deletion_reason = attr.ib()
    deletion = attr.ib()
    phase_0 = attr.ib()


@attr.s
class AnalysisList(object):
    analyses = attr.ib(type=list)
