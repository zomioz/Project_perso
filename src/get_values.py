import pandas as pd

def _as_list(x):
    return list(x) if isinstance(x, (list, tuple, set, pd.Index)) else [x]

def _row_mask(df, user_id=None, section=None, row=None, field=None, value=None):

    '''
    Boolean mask of the rows matching every given criterion (None = no criterion).
    '''

    mask = pd.Series(True, index=df.index)
    for level, wanted in (("user_id", user_id), ("section", section),
                          ("row", row), ("field", field)):
        if wanted is not None:
            mask &= df.index.get_level_values(level).isin(_as_list(wanted))
    if value is not None:
        mask &= df["value"].astype(str).isin([str(v) for v in _as_list(value)])
    return mask

def search(df, user_id=None, section=None, row=None, field=None, value=None,
           where=None, filters=None):

    '''
    Generic filter on the DataFrame built by to_long_dataframe.
    Every argument is optional: None means "all". Each one accepts a single
    element or a list/set/Index of elements (ex: field=["login", "pool_month"]).

    - user_id, section, row, field, value: which ROWS to return.
    - filters: shortcut {field: value(s)}. The user must match EVERY field (AND),
      and any of the values listed for a field (OR).
      ex: filters={"pool_year": 2025, "pool_month": ["august", "july"]}
    - where: same idea with full control. A dict, or a list of dicts (all must be
      true, AND). Each dict accepts section, row, field, value.
      ex: where=[{"field": "pool_month", "value": "august"},
                 {"section": "campus", "field": "id", "value": 31}]

    Return: the matching rows (same USER_ID | SECTION | ROW | FIELD | VALUE layout)
    '''

    mask = _row_mask(df, user_id, section, row, field, value)

    conditions = [] if where is None else _as_list(where)
    for filter_field, filter_value in (filters or {}).items():
        conditions.append({"field": filter_field, "value": filter_value})

    users = None
    for condition in conditions:
        matching = df.index[_row_mask(df, **condition)].get_level_values("user_id")
        users = set(matching) if users is None else users & set(matching)
    if users is not None:
        mask &= df.index.get_level_values("user_id").isin(list(users))

    return df[mask]