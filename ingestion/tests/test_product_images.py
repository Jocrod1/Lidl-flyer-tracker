from lidl_tracker.product_images import object_key_for_card


def test_object_key_for_card_uses_dedicated_cards_prefix():
    assert object_key_for_card(42, 7, "png") == "cards/42/Cards/7/product-image.png"


def test_object_key_for_card_normalizes_extension():
    assert object_key_for_card(42, 7, ".jpg") == "cards/42/Cards/7/product-image.jpg"
