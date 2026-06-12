import requests

token = input("Paste your short-lived token here and press Enter: ").strip()

print("\n--- Testing token (what accounts it can access) ---")
r = requests.get(
    "https://graph.facebook.com/v21.0/me/accounts",
    params={"access_token": token, "fields": "id,name,instagram_business_account"},
)
print(r.text)

print("\n--- Exchanging for long-lived token ---")
r2 = requests.get(
    "https://graph.facebook.com/oauth/access_token",
    params={
        "grant_type": "fb_exchange_token",
        "client_id": "1014677027695395",
        "client_secret": "7453186ab9ee88d14957c2d47ef99e7d",
        "fb_exchange_token": token,
    },
)
print(r2.text)
