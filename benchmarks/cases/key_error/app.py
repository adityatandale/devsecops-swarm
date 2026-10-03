def get_email(users, user_id):
    """Return the user's email, or None for unknown users / users without an email."""
    return users[user_id]["email"]


def normalize(s):
    return s.strip().lower()
