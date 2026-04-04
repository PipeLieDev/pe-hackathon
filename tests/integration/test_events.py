def test_list_events_empty(client):
    res = client.get("/events")
    assert res.status_code == 200
    assert res.json == []


def test_list_events(client, sample_event):
    res = client.get("/events")
    assert res.status_code == 200
    assert len(res.json) == 1
    event = res.json[0]
    assert event["event_type"] == "created"
    assert event["details"]["short_code"] == "abc123"
    assert event["details"]["original_url"] == "https://example.com"


def test_list_events_filter_by_type(client, sample_event):
    res = client.get("/events?event_type=created")
    assert res.status_code == 200
    assert len(res.json) == 1

    res = client.get("/events?event_type=deleted")
    assert res.status_code == 200
    assert len(res.json) == 0


def test_list_events_filter_by_user(client, sample_event, sample_user):
    res = client.get(f"/events?user_id={sample_user}")
    assert res.status_code == 200
    assert len(res.json) == 1

    res = client.get("/events?user_id=9999")
    assert res.status_code == 200
    assert len(res.json) == 0
