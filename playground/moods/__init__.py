# mood registry
from playground.moods import gremlin, explorer, dj, ghost

MOODS = {
    "gremlin": {
        "label": gremlin.LABEL, "emoji": gremlin.EMOJI,
        "description": gremlin.DESCRIPTION, "behaviors": gremlin.BEHAVIORS,
    },
    "explorer": {
        "label": explorer.LABEL, "emoji": explorer.EMOJI,
        "description": explorer.DESCRIPTION, "behaviors": explorer.BEHAVIORS,
    },
    "dj": {
        "label": dj.LABEL, "emoji": dj.EMOJI,
        "description": dj.DESCRIPTION, "behaviors": dj.BEHAVIORS,
    },
    "ghost": {
        "label": ghost.LABEL, "emoji": ghost.EMOJI,
        "description": ghost.DESCRIPTION, "behaviors": ghost.BEHAVIORS,
    },
    # Surprise Me is a blend: the engine samples behaviors across all moods,
    # weighted by learned preference scores.
    "surprise": {
        "label": "Surprise Me", "emoji": "🎲",
        "description": ("No fixed mood — blends behaviors from every mood, "
                        "leaning toward whatever it has learned you enjoy."),
        "behaviors": [],  # filled dynamically by the engine
        "blend": True,
    },
}
