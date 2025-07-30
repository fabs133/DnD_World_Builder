import re

def slugify(name: str) -> str:
    """
    Converts a display name like 'Dragon Turtle' to 'dragon-turtle',
    matching the expected API URL slug.
    """
    name = name.strip().lower()
    name = re.sub(r"[^\w\s-]", "", name)  # remove special chars
    name = re.sub(r"\s+", "-", name)      # replace spaces with dashes
    return name
