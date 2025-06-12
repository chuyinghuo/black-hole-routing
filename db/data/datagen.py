from faker import Faker
import csv
from random import choice, randint
from datetime import datetime, timedelta as dt

import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from models import UserRole

fake = Faker()


# Generate fake Users, always includes "Apiary" and "Splunk"
def generate_users(n):
    users = []

    # Add Apiary and Splunk
    special_users = ["Apiary", "Splunk"]
    for i, name in enumerate(special_users):
        users.append({
            "user_id": i + 1,
            "username": name,
            "role": choice([r.value for r in UserRole]),
            "added_at": fake.date_time_this_year().isoformat(),
            "token": fake.sha256(),
            "active": True
        })

    # Add the rest
    for i in range(n - len(special_users)):
        users.append({
            "user_id": i + 3,
            "username": fake.user_name(),
            "role": choice([r.value for r in UserRole]),
            "added_at": fake.date_time_this_year().isoformat(),
            "token": fake.sha256(),
            "active": True
        })
    return users


# Generate fake Blocklist entries, favoring Apiary and Splunk
def generate_blocklist(n, user_ids, apiary_id, splunk_id):
    blocklist = []

    # Bias: more likely to choose Apiary or Splunk
    weighted_users = (
        [apiary_id] * 6 +
        [splunk_id] * 6 +
        user_ids * 1
    )

    for _ in range(n):
        added = fake.date_time_this_year()
        total_minutes = randint(10, 2880)
        hours = total_minutes // 60
        minutes = total_minutes % 60
        duration_str = f"{hours} hours {minutes} minutes" if hours > 0 else f"{minutes} minutes"

        blocklist.append({
            "ip_address": fake.ipv4() if choice([True, False]) else fake.ipv6(),
            "created_by": choice(weighted_users),
            "comment": choice(["honeypot", "vpn brute forcing"]),
            "added_at": added.isoformat(),
            "duration": duration_str,
            "blocks_count": randint(1, 200),
            "expires_at": (added + dt(minutes=total_minutes)).isoformat()
        })
    return blocklist


# Generate fake Safelist entries
def generate_safelist(n, user_ids):
    safelist = []
    for _ in range(n):
        added = fake.date_time_this_year()
        total_minutes = randint(30, 720)
        hours = total_minutes // 60
        minutes = total_minutes % 60
        duration_str = f"{hours} hours {minutes} minutes" if hours > 0 else f"{minutes} minutes"

        safelist.append({
            "ip_address": fake.ipv4() if choice([True, False]) else fake.ipv6(),
            "created_by": choice(user_ids),
            "added_at": added.isoformat(),
            "comment": fake.text(max_nb_chars=50),
            "duration": duration_str,
            "expires_at": (added + dt(minutes=total_minutes)).isoformat()
        })
    return safelist


# Generate fake Historical entries
def generate_historical(n, user_ids):
    historical = []
    for _ in range(n):
        added = fake.date_time_this_year()
        unblock_delay = randint(10, 1440)
        unblocked_at = added + dt(minutes=unblock_delay)
        duration_str = f"{unblock_delay // 60} hours {unblock_delay % 60} minutes"

        historical.append({
            "ip_address": fake.ipv4() if choice([True, False]) else fake.ipv6(),
            "created_by": choice(user_ids),
            "comment": fake.sentence(),
            "added_at": added.isoformat(),
            "unblocked_at": unblocked_at.isoformat(),
            "duration": duration_str,
            "blocks_count": randint(1, 100)
        })
    return historical


# Generate fake BlockHistory entries
def generate_block_history(n, user_ids):
    block_history = []
    for i in range(n):
        added = fake.date_time_this_year()
        unblocked_at = added + dt(minutes=randint(5, 1440))
        block_history.append({
            "id": str(i + 1),
            "ip_address": fake.ipv4() if choice([True, False]) else fake.ipv6(),
            "created_by": choice(user_ids),
            "comment": fake.sentence(),
            "added_at": added.isoformat(),
            "unblocked_at": unblocked_at.isoformat()
        })
    return block_history


# Generate fake UserToken entries
def generate_user_tokens(n, user_ids):
    tokens = []
    for _ in range(n):
        tokens.append({
            "token": fake.sha256(),
            "user_id": choice(user_ids),
            "created_at": fake.date_time_this_year().isoformat(),
            "revoked": choice([True, False]),
            "purpose": choice(["API access", "login session", "automation script"])
        })
    return tokens


# Write a list of dictionaries to a CSV file
def write_csv(filename, fieldnames, rows):
    with open(f"{filename}", mode="w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


# Main function
def main():
    users = generate_users(10)
    write_csv("Users.csv", ["user_id", "username", "role", "added_at", "token", "active"], users)

    user_ids = [user["user_id"] for user in users]
    usernames = {user["username"]: user["user_id"] for user in users}
    apiary_id = usernames.get("Apiary")
    splunk_id = usernames.get("Splunk")

    blocklist = generate_blocklist(20, user_ids, apiary_id, splunk_id)
    write_csv("Blocklist.csv", ["ip_address", "created_by", "comment", "added_at", "duration", "blocks_count", "expires_at"], blocklist)

    safelist = generate_safelist(10, user_ids)
    write_csv("Safelist.csv", ["ip_address", "created_by", "added_at", "comment", "duration", "expires_at"], safelist)

    historical = generate_historical(15, user_ids)
    write_csv("Historical.csv", ["ip_address", "created_by", "comment", "added_at", "unblocked_at", "duration", "blocks_count"], historical)

    block_history = generate_block_history(15, user_ids)
    write_csv("BlockHistory.csv", ["id", "ip_address", "created_by", "comment", "added_at", "unblocked_at"], block_history)

    user_tokens = generate_user_tokens(20, user_ids)
    write_csv("UserTokens.csv", ["token", "user_id", "created_at", "revoked", "purpose"], user_tokens)


# Entry point
if __name__ == "__main__":
    main()
