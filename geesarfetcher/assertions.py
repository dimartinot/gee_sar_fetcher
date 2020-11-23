from datetime import datetime, date, timedelta

def _fetch_assertions(top_left=None,
    bottom_right=None,
    coords=None,
    start_date: datetime = date.today()-timedelta(days=365),
    end_date: datetime = date.today(),
    ascending: bool = True,
    scale: int = 20,
    n_jobs: int = 8):

    assert(coords is None or (
        (
            type(coords) == list
            or type(coords) == tuple
        )
        and len(coords) == 2)
        and len(coords[0]) == len(coords[1])
        and len(coords[0]) == 2
    )
    assert(
            (
                top_left is None
                and bottom_right is None
            )
            or (
                type(top_left) == type(bottom_right)
                and (
                    type(top_left) == tuple
                    or type(top_left) == list)
            )
            and len(top_left) == len(bottom_right)
            and len(top_left) == 2
    )
    assert(start_date is not None)
    assert(end_date is not None)
    assert(end_date > start_date)

    if (top_left is not None
            and bottom_right is not None
            and coords is not None
    ):
        raise ValueError(
            "coords must be None if top_left and bottom_right are not None.")

def _fetch_point_assertions(
    coords,
    start_date: datetime = date.today()-timedelta(days=365),
    end_date: datetime = date.today(),
    ascending: bool = True,
    scale: int = 20,
    n_jobs: int = 8):

    assert(len(coords) == 2 and type(coords[0]) != list and type(coords[0]) != tuple)
    assert(start_date is not None)
    assert(end_date is not None)
    assert(end_date > start_date)