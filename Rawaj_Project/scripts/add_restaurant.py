from database.database import SessionLocal
from database.models import Restaurant


def add_restaurant():
    db = SessionLocal()

    try:
        restaurant = Restaurant(
            name="Zaitoon Restaurant",
            instagram_username="zaitoonksa",
            instagram_url="https://www.instagram.com/zaitoonksa",
            email="info@zaitoonksa.com",
            location="Madinah",
        )

        db.add(restaurant)
        db.commit()
        db.refresh(restaurant)

        print("Restaurant added successfully.")
        print(f"Restaurant ID: {restaurant.id}")
        print(f"Restaurant: {restaurant.name}")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    add_restaurant()