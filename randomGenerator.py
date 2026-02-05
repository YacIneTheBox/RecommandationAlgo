import json
import random


def generate_mock_users(n):
    users_list = []
    tags = [
        "Math",
        "Physique",
        "Psycho",
        "Medecine",
        "Histoire",
        "Geographie",
        "Geologie",
        "Informatique",
        "Art",
    ]  # Tu pourras en ajouter d'autres ici

    for i in range(n):
        user = {
            "user_id": f"user_{i}",
            "name": f"User{i}",
            "weights": {tag: round(random.uniform(0.5, 3.0), 2) for tag in tags},
            "history": [],
            "mastery": {tag: random.randint(1, 3) for tag in tags},
        }
        users_list.append(user)

    # On écrit TOUTE la liste une seule fois à la fin
    with open("users.json", "w") as f:
        json.dump(users_list, f, indent=4)

    print(f"Simulation terminée : {n} utilisateurs générés dans users.json")


def generate_mock_articles(n):
    articles_list = []
    tags = [
        "Math",
        "Physique",
        "Psycho",
        "Medecine",
        "Histoire",
        "Geographie",
        "Geologie",
        "Informatique",
        "Art",
    ]  # Tu pourras en ajouter d'autres ici

    for i in range(n):
        article = {
            "article_id": f"article_{i}",
            "title": f"Article{i}",
            "tags": random.sample(tags, random.randint(1, 2)),
            "content": f"Content{i}",
            "level": random.randint(1, 3),
        }
        articles_list.append(article)

    # On écrit TOUTE la liste une seule fois à la fin
    with open("articles.json", "w") as f:
        json.dump(articles_list, f, indent=4)

    print(f"Simulation terminée : {n} articles générés dans articles.json")


generate_mock_users(10)
generate_mock_articles(200)
