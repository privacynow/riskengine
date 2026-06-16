DEFAULT_PAGE = 1
DEFAULT_SIZE = 10
MAX_PAGE_SIZE = 100


def clamp_pagination(page: int, size: int) -> tuple[int, int]:
    safe_page = max(1, int(page))
    safe_size = min(max(1, int(size)), MAX_PAGE_SIZE)
    return safe_page, safe_size


def build_paginated_response(items, total, page, size):
    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
    }


def paginate_query(cur, query, params, page: int, size: int):
    page, size = clamp_pagination(page, size)
    count_query = f"SELECT COUNT(*) FROM ({query}) as sub"
    cur.execute(count_query, params)
    total = cur.fetchone()[0]
    offset = (page - 1) * size
    paged_query = query + " LIMIT %s OFFSET %s"
    cur.execute(paged_query, [*params, size, offset])
    return total, cur.fetchall(), page, size
