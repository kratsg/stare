This document maps all **statuses** and **states** of the Analysis and Documents
API.

### `status` — Analysis

| Raw Value         | Display Label   |
| ----------------- | --------------- |
| `created`         | Created         |
| `analysis_closed` | Analysis Closed |
| `phase0_active`   | Phase 0 Active  |
| `phase0_closed`   | Phase 0 Closed  |

### `status` — Paper

| Raw Value           | Display Label            |
| ------------------- | ------------------------ |
| `created`           | Not Started              |
| `analysis_closed`   | Closed                   |
| `phase1_active`     | Phase 1 Active           |
| `phase1_closed`     | Phase 1 Closed           |
| `phase3_active`     | Phase 2 Active           |
| `phase3_closed`     | Phase 2 Closed           |
| `submission_active` | Publication Phase Active |
| `submission_closed` | Completed                |

### `status` — Confnote

| Raw Value         | Display Label   |
| ----------------- | --------------- |
| `created`         | Created         |
| `analysis_closed` | Analysis Closed |
| `phase1_active`   | Phase 1 Active  |
| `phase1_closed`   | Phase 1 Closed  |

---

### `phase0.state` — Phase 0 (Analysis)

| Raw Value                          | Display Label                                                          |
| ---------------------------------- | ---------------------------------------------------------------------- |
| `not_started`                      | Phase 0 Data                                                           |
| `eoi_meeting`                      | Expression of interest (EOI) meeting data                              |
| `analysis_definition`              | Analysis definition after EOI meeting                                  |
| `analysis_coordinators_selection`  | Analysis contact and expert review selection                           |
| `first_analysis_data`              | Analysis metadata                                                      |
| `analysis_coordinators_timeline`   | Analysis contacts' target date                                         |
| `second_analysis_data`             | Auxiliary metadata                                                     |
| `internal_note_editors_definition` | Internal note editors and contact editors appointment                  |
| `edboard_request_meeting_data`     | Editorial Board request meeting and formation data                     |
| `edboard_meeting_data`             | Editorial Board meeting data                                           |
| `pre_approval_meeting_data`        | Pre approval meeting data                                              |
| `pgc_sgc_contact_signoff`          | PGC or SGC pre approval sign-off                                       |
| `publication_draft`                | Publication draft                                                      |
| `approval_meeting_data`            | Approval meeting data                                                  |
| `approval_acceptance`              | Approval acceptance                                                    |
| `finished`                         | Publications definition                                                |
| `paper_skip`                       | Skipped to Paper                                                       |
| `conf_skip`                        | Skipped to CONF Note                                                   |
| `pub_skip`                         | Skipped to PUB Note                                                    |
| `paper_contact_editors_definition` | Contact editors and Editorial Board appointment (skipped to Paper)     |
| `conf_contact_editors_definition`  | Contact editors and Editorial Board appointment (skipped to CONF note) |
| `pub_contact_editors_definition`   | Contact editors appointment (skipped to PUB note)                      |

---

### `phase1.state` — Phase 1 (Paper)

| Raw Value              | Display Label                  |
| ---------------------- | ------------------------------ |
| `not_started`          | Phase 1 Data                   |
| `started`              | Editorial Board                |
| `approved_by_reviewer` | Analysis Review                |
| `lgp_approved`         | Editorial Board Draft Sign-off |
| `review_closed`        | Draft 1 Released to ATLAS      |
| `finished`             | Phase Closed                   |

---

### `phase2.state` — Phase 2 (Paper)

| Raw Value                  | Display Label                                                         |
| -------------------------- | --------------------------------------------------------------------- |
| `started`                  | Phase 2 Data                                                          |
| `final_review_closed`      | Draft 2 Approval Process                                              |
| `update_edboard`           | Revised Draft Final Sign-off by Editorial Board Chair                 |
| `updated_Pubcomm`          | Revised Draft Final Sign-off by Publication Committee Chair or Deputy |
| `updated_SpokespersonDate` | Final Sign-off by Spokesperson or Deputy                              |
| `finished`                 | Phase Closed                                                          |

---

### `submission.state` — Submission phase (Paper)

| Raw Value                 | Display Label             |
| ------------------------- | ------------------------- |
| `not_started`             | Publication Phase Launch  |
| `started`                 | Tarball Receiving         |
| `tarball_received`        | CERN and ATLAS Collection |
| `submitted_to_arxiv`      | Journal Submission        |
| `submitted_to_journal`    | Journal Reports Receiving |
| `journal_report_received` | Journal Reports Answering |
| `journal_report_answered` | Journal Acceptance        |
| `accepted_by_journal`     | Proofs Receiving          |
| `proof_received`          | Proofs Answering          |
| `proof_answered`          | Online Publication        |
| `published_online`        | Final ArXiv Replacement   |
| `erratum_requested`       | Erratum Submission        |
| `erratum_submitted`       | Erratum Acceptance        |
| `final_arxiv_replaced`    | Paper Finish              |
| `finished`                | Submission Closed         |

---

### `phase1.state` — Phase 1 (Confnote)

| Raw Value              | Display Label                                 |
| ---------------------- | --------------------------------------------- |
| `not_started`          | Phase 1 Data                                  |
| `started`              | Editorial Board                               |
| `approved_by_reviewer` | Analysis Review                               |
| `lgp_approved`         | Editorial Board Draft Sign-off                |
| `phase1_active`        | Phase 1 Active                                |
| `second_signed`        | CONF Release                                  |
| `atlas_approved`       | Final Sign-off                                |
| `edBoardSignOff`       | Editorial Board Draft Sign-off                |
| `draft_released`       | ATLAS Review Organized by Physics Coordinator |
| `review_closed`        | Draft 1 Released to ATLAS                     |
| `finished`             | Phase Closed                                  |
