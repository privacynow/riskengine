def build_paginated_response(items, total, page, size):
    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
    }


def paginate_query(cur, query, params, page: int, size: int):
    count_query = f"SELECT COUNT(*) FROM ({query}) as sub"
    cur.execute(count_query, params)
    total = cur.fetchone()[0]
    offset = (page - 1) * size
    paged_query = query + f" LIMIT {size} OFFSET {offset}"
    cur.execute(paged_query, params)
    return total, cur.fetchall()
