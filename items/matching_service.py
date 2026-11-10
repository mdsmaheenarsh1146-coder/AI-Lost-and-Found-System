from .models import Item


def find_matching_items(new_item, threshold=0.80):
    matches = []

    # Find items of the opposite type
    if new_item.item_type == "FOUND":
        opposite_type = "LOST"
    else:
        opposite_type = "FOUND"

    existing_items = Item.objects.filter(
        item_type=opposite_type,
        status="OPEN",
        image_embedding__isnull=False
    ).exclude(user=new_item.user)

    # Compare the new image with existing images
    for item in existing_items:

        if not new_item.image_embedding:
            continue

        if not item.image_embedding:
            continue

        similarity = cosine_similarity(
            new_item.image_embedding,
            item.image_embedding
        )

        if similarity >= threshold:
            matches.append({
                "item": item,
                "similarity": similarity
            })

    matches.sort(
        key=lambda match: match["similarity"],
        reverse=True
    )

    return matches


def cosine_similarity(vector_a, vector_b):
    import math

    if len(vector_a) != len(vector_b):
        return 0.0

    dot_product = sum(
        a * b for a, b in zip(vector_a, vector_b)
    )

    magnitude_a = math.sqrt(sum(a * a for a in vector_a))
    magnitude_b = math.sqrt(sum(b * b for b in vector_b))

    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0

    return dot_product / (magnitude_a * magnitude_b)