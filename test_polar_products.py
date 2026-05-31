import os
from dotenv import load_dotenv

load_dotenv("d:/saas/inp-backend/app/.env")
from polar_sdk import Polar

polar = Polar(access_token=os.getenv("POLAR_ACCESS_TOKEN"), server=None)
product_id = os.getenv("POLAR_SOLOPRENEUR_PRODUCT_ID")
try:
    with polar as client:
        product_response = client.products.get(id=product_id)
        prices = getattr(product_response, "prices", [])
        if prices:
            print("Success, first price dir:", dir(prices[0]))
            print("Vars:", vars(prices[0]) if hasattr(prices[0], '__dict__') else "No vars")
        else:
            print("No prices found")
except Exception as e:
    print("Error:", str(e))
