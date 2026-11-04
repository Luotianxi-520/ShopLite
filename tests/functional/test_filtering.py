from tests.functional.helpers import product_cards


def fetch(client, **params):
    return client.get("/", query_string=params)


def test_filter_by_category(client):
    resp = fetch(client, category="电子产品")
    cards = product_cards(resp.text)
    assert len(cards) == 6
    assert all(category == "电子产品" for _, category, _ in cards)


def test_filter_by_price_range(client):
    resp = fetch(client, min_price=100, max_price=300)
    cards = product_cards(resp.text)
    ids = {int(pid) for pid, _, _ in cards}
    prices = [float(price) for _, _, price in cards]
    assert ids == {1, 4, 9, 10, 14, 18, 19}
    assert all(100 <= price <= 300 for price in prices)


def test_price_boundary_is_inclusive(client):
    resp = fetch(client, min_price=39, max_price=39)
    cards = product_cards(resp.text)
    assert len(cards) == 1
    assert cards[0][0] == "12"


def test_search_by_keyword(client):
    resp = fetch(client, q="键盘")
    cards = product_cards(resp.text)
    assert len(cards) == 1
    assert "机械键盘" in resp.text


def test_search_without_results_shows_empty_state(client):
    resp = fetch(client, q="不存在的商品xyz")
    assert len(product_cards(resp.text)) == 0
    assert "未找到相关商品" in resp.text


def test_combined_filters(client):
    resp = fetch(client, category="图书", max_price=100)
    cards = product_cards(resp.text)
    ids = {int(pid) for pid, _, _ in cards}
    assert ids == {7, 8, 11}
    assert all(category == "图书" for _, category, _ in cards)
    assert all(float(price) <= 100 for _, _, price in cards)


def test_sort_by_price_ascending(client):
    resp = fetch(client, sort="price_asc")
    prices = [float(price) for _, _, price in product_cards(resp.text)]
    assert len(prices) == 8  # 第一页
    assert prices == sorted(prices)


def test_sort_by_price_descending(client):
    resp = fetch(client, sort="price_desc")
    prices = [float(price) for _, _, price in product_cards(resp.text)]
    assert prices == sorted(prices, reverse=True)


def test_pagination_pages_are_disjoint(client):
    page1 = {int(pid) for pid, _, _ in product_cards(fetch(client, page=1).text)}
    page2 = {int(pid) for pid, _, _ in product_cards(fetch(client, page=2).text)}
    page3 = {int(pid) for pid, _, _ in product_cards(fetch(client, page=3).text)}

    assert len(page1) == 8
    assert len(page2) == 8
    assert len(page3) == 4
    assert not page1 & page2
    assert not page2 & page3
    assert page1 | page2 | page3 == set(range(1, 21))


def test_page_out_of_range_is_clamped(client):
    resp = fetch(client, page=99)
    assert len(product_cards(resp.text)) == 4


def test_invalid_price_input_is_ignored(client):
    resp = fetch(client, min_price="abc")
    assert resp.status_code == 200
    assert len(product_cards(resp.text)) == 8


def test_search_special_characters_do_not_crash(client):
    resp = fetch(client, q="' OR '1'='1")
    assert resp.status_code == 200
    assert len(product_cards(resp.text)) == 0
