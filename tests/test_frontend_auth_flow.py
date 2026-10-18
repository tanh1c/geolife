"""Local-only browser smoke: FRONTEND_DEMO_PASSWORD and both localhost servers required."""

import os

import pytest


def test_session_survives_navigation_until_logout():
    if not os.getenv("FRONTEND_DEMO_PASSWORD"):
        pytest.skip("Requires local frontend, API, and FRONTEND_DEMO_PASSWORD")
    playwright_api = pytest.importorskip("playwright.sync_api")
    expect, sync_playwright = playwright_api.expect, playwright_api.sync_playwright
    password = os.environ["FRONTEND_DEMO_PASSWORD"]
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.goto("http://127.0.0.1:3000/")
        page.get_by_role("button", name="Tài khoản cá nhân").click()
        page.locator("#demo-password").fill(password)
        page.get_by_role("button", name="Đăng nhập ngay").click()
        expect(page.get_by_role("button", name="Tài khoản cá nhân")).to_be_visible()
        page.get_by_role("button", name="Tài khoản cá nhân").click()
        expect(page.get_by_text("demo_000", exact=True).last).to_be_visible()
        page.get_by_role("button", name="Dự đoán điểm đến").click()
        expect(page.get_by_text("Điểm đến gợi ý (3)")).to_be_visible()
        page.get_by_role("button", name="Quay lại").click()
        requests = []
        page.on("request", lambda request: requests.append(request.url) if "/v2/me/destination-suggestions" in request.url else None)
        page.get_by_label("Giờ mô phỏng").select_option("18:00")
        page.get_by_role("button", name="Đặt ô tô").click()
        expect(page.get_by_text("Giờ mô phỏng: 18:00")).to_be_visible()
        assert "when=2026-09-24T18%3A00%3A00%2B07%3A00" in requests[-1]
        expect(page.locator("ol li")).to_have_count(3)
        page.locator("ol li button").first.click()
        expect(page.get_by_text("Xanh Car", exact=True).first).to_be_visible()
        page.get_by_role("button", name="Quay lại").click()
        page.get_by_role("button", name="Quay lại trang chủ").click()
        page.get_by_role("button", name="Tài khoản cá nhân").click()
        expect(page.get_by_text("demo_000", exact=True).last).to_be_visible()
        expect(page.get_by_text("Điểm đến gợi ý (3)")).to_be_visible()
        page.get_by_role("button", name="Đăng xuất tài khoản").click()
        page.get_by_role("button", name="Tài khoản cá nhân").click()
        expect(page.locator("#demo-password")).to_be_visible()
        browser.close()
