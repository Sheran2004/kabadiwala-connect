import datetime

def test_register_requires_valid_otp(api):
    assert api.post("/auth/register", json={"phone": "9111111101", "name": "Aa Bb", "password": "password1", "role": "collector", "code": "000000"}).status_code == 400
    r = api.register("9111111101", "Ram Kumar", "collector"); assert r["role"] == "collector" and r["verified"] is False

def test_login_is_rate_limited(api):
    api.register("9111111102", "Sita Devi", "collector")
    codes = [api.post("/auth/login", json={"phone": "9111111102", "password": "wrong-pass"}).status_code for _ in range(6)]
    assert codes[:5] == [401] * 5 and codes[5] == 429
    assert api.post("/auth/login", json={"phone": "9111111102", "password": "password1"}).status_code == 429   # even the right password waits

def test_change_and_reset_password(api):
    t = api.register("9111111103", "Mohan Lal", "collector")["token"]
    assert api.post("/auth/change-password", json={"current": "bad-pass-1", "new": "newpass123"}, headers=api.H(t)).status_code == 400
    assert api.post("/auth/change-password", json={"current": "password1", "new": "newpass123"}, headers=api.H(t)).status_code == 200
    assert "token" in api.login("9111111103", "newpass123") and api.post("/auth/login", json={"phone": "9111111103", "password": "password1"}).status_code == 401
    api.skip_cd("9111111103"); code = api.post("/auth/otp/request", json={"phone": "9111111103"}).json()["dev_code"]
    assert api.post("/auth/reset-password", json={"phone": "9111111103", "code": code, "new": "resetpass99"}).status_code == 200
    assert "token" in api.login("9111111103", "resetpass99")

def test_full_deal_pickup_payment_rating(api):
    col = api.register("9111111104", "Seller One", "collector")["token"]; rec = api.register("9111111105", "Buyer One", "recycler")["token"]
    adm = api.login("9000000000", "admin-pass-123")["token"]
    d = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
    lot = api.post("/lots", json={"type": "iron", "kg": 50, "city": "Lucknow", "lat": 26.8, "lng": 80.9, "pickup_date": d, "pickup_slot": "morning"}, headers=api.H(col)).json()["id"]
    assert api.post(f"/lots/{lot}/bids", json={"amount": 1300}, headers=api.H(rec)).status_code == 403          # not approved yet
    rid = [x for x in api.get("/admin/recyclers", headers=api.H(adm)).json() if x["phone"] == "9111111105"][0]["id"]
    assert api.post(f"/admin/recyclers/{rid}/approve", headers=api.H(adm)).status_code == 200
    assert api.post(f"/lots/{lot}/bids", json={"amount": 1300}, headers=api.H(rec)).status_code == 200
    bid = api.get(f"/lots/{lot}/bids", headers=api.H(col)).json()[0]
    sid = api.post(f"/bids/{bid['id']}/accept", headers=api.H(col)).json()["sale"]
    S = lambda path, tok, body=None: api.post(f"/sales/{sid}/{path}", json=body, headers=api.H(tok)) if body is not None else api.post(f"/sales/{sid}/{path}", headers=api.H(tok))
    assert S("stage", rec, {"stage": "picked_up"}).status_code == 409                    # cannot skip a step
    assert api.post(f"/sales/{sid}/rate", json={"stars": 5}, headers=api.H(col)).status_code == 409   # rate only after pickup
    assert S("stage", rec, {"stage": "on_the_way"}).status_code == 200 and S("stage", rec, {"stage": "picked_up"}).status_code == 200
    assert S("stage", col, {"stage": "on_the_way"}).status_code == 403                    # only the buyer moves the order
    assert S("confirm", rec).status_code == 403 and S("pay", rec, {"method": "upi", "ref": "UTR123"}).status_code == 200
    led = api.get("/ledger", headers=api.H(col)).json(); row = led["sales"][0]
    assert row["pay_status"] == "sent" and row["stage"] == "picked_up" and row["other_phone"] == "9111111105" and led["received"] == 0
    assert S("confirm", col).status_code == 200 and api.get("/ledger", headers=api.H(col)).json()["received"] == 1300
    assert api.post(f"/sales/{sid}/rate", json={"stars": 5, "comment": "ok"}, headers=api.H(col)).status_code == 200
    kinds = {n["kind"] for n in api.get("/notifications", headers=api.H(col)).json()["items"]}; assert {"bid", "ontheway", "pickedup", "paysent"} <= kinds

def test_lot_edit_cancel_rules(api):
    col = api.register("9111111106", "Seller Two", "collector")["token"]
    lot = api.post("/lots", json={"type": "paper", "kg": 10, "city": "Noida"}, headers=api.H(col)).json()["id"]
    assert api.put(f"/lots/{lot}", json={"kg": 12}, headers=api.H(col)).status_code == 200
    assert api.delete(f"/lots/{lot}", headers=api.H(col)).status_code == 200 and api.put(f"/lots/{lot}", json={"kg": 5}, headers=api.H(col)).status_code == 409
    assert api.post("/lots", json={"type": "paper", "kg": 10, "city": "Noida", "pickup_date": "2001-01-01"}, headers=api.H(col)).status_code == 422

def test_rates_median_and_roles(api):
    adm = api.login("9000000000", "admin-pass-123")["token"]; col = api.register("9111111107", "Seller Three", "collector")["token"]
    assert api.put("/rates/cu", json={"amount": 560}, headers=api.H(col)).status_code == 403
    for p in (540, 560, 9999): api.put("/admin/rates/cu", json={"amount": p}, headers=api.H(adm))
    cu = api.get("/rates").json()["cu"]; assert cu["reports"] == 2 and cu["price"] == 550.0     # 9999 is rejected as a wild price
