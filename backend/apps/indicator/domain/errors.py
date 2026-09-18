"""indicator BC 도메인 예외 — 적재 경로(리포지토리·CLI)가 잡아 적재를 중단시킨다."""


class DatasetNotFoundError(Exception):
    """external_dataset에 등록되지 않은 dataset_id — 출처 없는 지표는 받지 않는다."""


class DatasetNotApprovedError(Exception):
    """export_approved_on이 NULL인 데이터셋 — 센터 반출 심사 전 수치는 적재하지 않는다."""
